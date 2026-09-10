"""Container-aware resource sizing shared by the PPTX and PDF converters.

Both converters drive headless Chromium, so both can OOM-kill the instance the
same way. Keeping this logic in one place is deliberate: it originally lived
only in converter_pptx.py, and converter_pdf.py kept sizing its worker pool from
os.cpu_count(). That is the HOST's core count, not the container's share, so on a
small PaaS instance the PDF path still launched several parallel Chromium pages
on a box provisioned for about one and kept getting OOM-killed after the PPTX
path had been fixed.
"""
import asyncio
import logging
import os
from pathlib import Path

LOGGER = logging.getLogger("html_converter_limits")


def _cgroup_int(path: str):
    try:
        raw = Path(path).read_text().strip().split()[0]
    except (OSError, IndexError):
        return None
    if raw in ("max", "-1"):
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def effective_cpus() -> float:
    """CPUs actually available to THIS container, not the host."""
    # cgroup v2: "<quota> <period>" in cpu.max
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().strip().split()
        if len(parts) == 2 and parts[0] != "max":
            quota, period = int(parts[0]), int(parts[1])
            if quota > 0 and period > 0:
                return max(0.5, quota / period)
    except (OSError, ValueError):
        pass
    # cgroup v1
    quota = _cgroup_int("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    period = _cgroup_int("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if quota and period:
        return max(0.5, quota / period)
    # Respect the process's actual CPU affinity mask before falling back.
    try:
        return float(len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        return float(os.cpu_count() or 1)


def memory_limit_mb():
    """Container memory limit in MB, or None when unconstrained."""
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        value = _cgroup_int(path)
        # Unconstrained cgroups report an enormous sentinel value.
        if value and value < (1 << 62):
            return value / (1024 * 1024)
    return None


def _memory_used_mb():
    """Memory this container is currently holding, in MB, or None."""
    for path in ("/sys/fs/cgroup/memory.current", "/sys/fs/cgroup/memory/memory.usage_in_bytes"):
        value = _cgroup_int(path)
        if value is not None:
            used = value / (1024 * 1024)
            # memory.current counts the page cache, which the kernel reclaims
            # under pressure — treating it as "used" would throttle the worker
            # pool for memory that is in practice available.
            used -= _reclaimable_mb()
            return max(0.0, used)
    return None


def _reclaimable_mb() -> float:
    """Page cache and reclaimable slab inside the cgroup's usage figure."""
    total = 0
    for path in ("/sys/fs/cgroup/memory.stat", "/sys/fs/cgroup/memory/memory.stat"):
        try:
            for line in Path(path).read_text().splitlines():
                key, _, raw = line.partition(" ")
                if key in ("inactive_file", "slab_reclaimable"):
                    try:
                        total += int(raw)
                    except ValueError:
                        pass
            if total:
                break
        except OSError:
            continue
    return total / (1024 * 1024)


def memory_available_mb():
    """Memory actually free RIGHT NOW, not merely the ceiling.

    Sizing against the container's total limit overcommits: by the time slides
    start rendering, the interpreter, the decoded HTML (multi-megabyte decks are
    held as a string, often more than once across the request path) and any
    other in-flight work already occupy part of that ceiling. Budget Chromium
    workers against the remaining headroom instead.
    """
    limit = memory_limit_mb()
    used = _memory_used_mb()
    if limit is not None:
        if used is not None:
            return max(0.0, limit - used)
        return limit
    # Unconstrained cgroup (bare metal, or a dev box): ask the kernel.
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


# Each concurrent Chromium page (2x device scale on a 1280x720 viewport) plus
# its screenshot buffers costs roughly this much; the browser process itself
# needs a similar baseline. Deliberately conservative: being OOM-killed loses
# the whole conversion, while one fewer worker only makes it slower.
_MB_PER_SLIDE_WORKER = 450
_BROWSER_BASE_MB = 350


def slide_worker_budget(slide_count: int) -> int:
    """How many slides may render in parallel without exhausting the container."""
    explicit = os.getenv("HTML_CONVERTER_WORKERS", "").strip()
    if explicit:
        try:
            return max(1, min(slide_count, int(explicit)))
        except ValueError:
            LOGGER.warning("Ignoring non-numeric HTML_CONVERTER_WORKERS=%r", explicit)

    budget = max(1, int(effective_cpus()))

    # Size against memory that is FREE at this moment, not the container's
    # ceiling — see memory_available_mb(). Falls back to the ceiling when usage
    # cannot be read, which is the previous (more optimistic) behaviour.
    mem_mb = memory_available_mb()
    if mem_mb is None:
        mem_mb = memory_limit_mb()
    if mem_mb:
        by_mem = int((mem_mb - _BROWSER_BASE_MB) // _MB_PER_SLIDE_WORKER)
        budget = min(budget, max(1, by_mem))

    # WEB_CONCURRENCY is the platform's own sizing hint (Render sets it from the
    # instance's real CPU allowance); when it says 1, the box is small.
    web_conc = os.getenv("WEB_CONCURRENCY", "").strip()
    if web_conc:
        try:
            if int(web_conc) <= 1:
                budget = min(budget, 2)
        except ValueError:
            pass

    return max(1, min(slide_count, budget))


def device_scale() -> float:
    """Screenshot scale. 2x is crisp but quadruples pixel memory per capture."""
    try:
        return max(1.0, min(3.0, float(os.getenv("HTML_CONVERTER_SCALE", "2"))))
    except ValueError:
        return 2.0


# Nothing stopped a second conversion starting while one was already in flight.
# A user hitting Convert again after a slow run doubled the number of live
# Chromium pages and reliably OOM-killed the instance (observed: a retry landing
# on top of a run still going, process killed ~1 minute later).
#
# This semaphore is deliberately SHARED between the PPTX and PDF converters:
# each holds a Chromium instance, so a PDF running alongside a PPTX exhausts the
# container just as surely as two of either. Serialise whole conversions per
# process by default; raise the limit only on a box with headroom.
try:
    MAX_CONCURRENT = max(1, int(os.getenv("HTML_CONVERTER_MAX_CONCURRENT", "1")))
except ValueError:
    MAX_CONCURRENT = 1

CONVERSION_SLOTS = asyncio.Semaphore(MAX_CONCURRENT)


def describe_limits() -> str:
    """One-line summary for the logs, so undersizing is visible in production."""
    limit = memory_limit_mb()
    free = memory_available_mb()
    used = _memory_used_mb()
    return (
        f"container cpus={effective_cpus():.1f} (host reports {os.cpu_count() or 1}) | "
        f"memory limit={f'{limit:.0f}MB' if limit else 'unset'}"
        f"{f', used={used:.0f}MB' if used is not None else ''}"
        f"{f', free={free:.0f}MB' if free is not None else ''}"
    )
