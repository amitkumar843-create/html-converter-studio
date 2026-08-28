import asyncio
import os
import sys
import uuid
import tempfile
import math
import re
import time
import logging
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ADDITIVE (observability): this module previously emitted NOTHING between the
# start of a conversion and its result — no progress, no timings, no phase
# markers. A PPTX export of a heavy deck runs for minutes, so in production the
# logs went silent for the whole run and a slow conversion was indistinguishable
# from a hung or dead one. converter_pdf.py already had a logger; this mirrors
# it (same format, same env var) so both halves of the service report alike.
# Logging goes to stderr, which is not block-buffered when stdout is a pipe, so
# lines appear in the platform log stream as they happen rather than in a burst
# at process exit.
logging.basicConfig(
    level=getattr(logging, os.getenv("HTML_CONVERTER_LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
LOGGER = logging.getLogger("html_pptx_converter")


# BUG FIX (OOM kills in production): os.cpu_count() reports the HOST's cores,
# not the container's share, so on a small PaaS instance it happily reported 8
# and we launched 4 parallel Chromium pages at device_scale_factor=2 on a
# container provisioned for about one. The platform OOM-killed the process
# mid-conversion, which restarts the app, drops the client connection, and
# surfaces in the browser as a generic "Load failed" with no error in the logs.
# Read the real cgroup CPU quota and memory limit instead, and size the work to
# whichever is smaller.
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


def _effective_cpus() -> float:
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


def _memory_limit_mb():
    """Container memory limit in MB, or None when unconstrained."""
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        value = _cgroup_int(path)
        # Unconstrained cgroups report an enormous sentinel value.
        if value and value < (1 << 62):
            return value / (1024 * 1024)
    return None


# Each concurrent Chromium page (2x device scale on a 1280x720 viewport) plus
# its screenshot buffers costs roughly this much; the browser process itself
# needs a similar baseline. Deliberately conservative: being OOM-killed loses
# the whole conversion, while one fewer worker only makes it slower.
_MB_PER_SLIDE_WORKER = 450
_BROWSER_BASE_MB = 350


def _slide_worker_budget(slide_count: int) -> int:
    explicit = os.getenv("HTML_CONVERTER_WORKERS", "").strip()
    if explicit:
        try:
            return max(1, min(slide_count, int(explicit)))
        except ValueError:
            LOGGER.warning("Ignoring non-numeric HTML_CONVERTER_WORKERS=%r", explicit)

    budget = max(1, int(_effective_cpus()))

    mem_mb = _memory_limit_mb()
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


# BUG FIX (OOM kills): nothing stopped a second conversion starting while one
# was already in flight. A user hitting Convert again after a slow run doubled
# the number of live Chromium pages and reliably OOM-killed the instance
# (observed: a retry at 07:40:28 on top of a run still going, process killed at
# 07:41:25). Serialise whole conversions per process by default so a retry
# queues instead of racing; raise the limit only on a box with headroom.
try:
    _MAX_CONCURRENT = max(1, int(os.getenv("HTML_CONVERTER_MAX_CONCURRENT", "1")))
except ValueError:
    _MAX_CONCURRENT = 1
_CONVERSION_SLOTS = asyncio.Semaphore(_MAX_CONCURRENT)


def _device_scale() -> float:
    """Screenshot scale. 2x is crisp but quadruples pixel memory per capture."""
    try:
        return max(1.0, min(3.0, float(os.getenv("HTML_CONVERTER_SCALE", "2"))))
    except ValueError:
        return 2.0


# ADDITIVE (§5.9): emoji-as-icon font fallback. PowerPoint's default font
# substitution renders emoji as tofu boxes; Segoe UI Emoji carries the glyphs.
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\u2190-\u21FF\u2B00-\u2BFF]"
)


def _contains_emoji(text: str) -> bool:
    return bool(text) and bool(_EMOJI_RE.search(text))


# ADDITIVE (§5.6): explicit icon-font glyph loading. document.fonts.ready alone
# can race ahead of CDN-injected @font-face rules, leaving icons blank.
_LOAD_ICON_FONTS_JS = """
    async () => {
        const families = [
            '900 1px "Font Awesome 6 Free"', '400 1px "Font Awesome 6 Free"',
            '400 1px "Font Awesome 6 Brands"',
            '900 1px "Font Awesome 5 Free"', '400 1px "Font Awesome 5 Free"',
            '400 1px "Phosphor"', '700 1px "Phosphor-Bold"',
            '400 1px "Phosphor-Fill"', '400 1px "Phosphor-Regular"',
            '300 1px "Phosphor-Light"', '400 1px "Phosphor-Thin"',
            '400 1px "Phosphor-Duotone"',
            // ADDITIVE: named-library fallback for icon fonts beyond FA/Phosphor.
            // Kept as a named list for speed/accuracy; the generic glyph-font
            // heuristic in isIconElement (see below) catches packs not listed here.
            '400 1px "bootstrap-icons"',
            '400 1px "Material Symbols Outlined"', '400 1px "Material Symbols Rounded"',
            '400 1px "Material Symbols Sharp"',
            '400 1px "remixicon"',
        ];
        await Promise.all(families.map(f => document.fonts.load(f).catch(() => {})));
        await document.fonts.ready;
    }
"""


async def _load_icon_fonts(page):
    try:
        await page.evaluate(_LOAD_ICON_FONTS_JS)
    except Exception:
        pass


# BUG FIX: every card/icon screenshot was being written as an OPAQUE rectangle,
# so each shape dropped onto a PowerPoint slide carried a white (or slide-
# coloured) block behind it. That is the real source of the "shadow"/"box"
# artefacts around the Delhi Police logo and the coloured icon tiles, and it
# only becomes obvious when a shape is dragged off the slide.
#
# omit_background=True was already being passed, but Chromium can only emit an
# alpha channel when nothing opaque paints behind the clip: an ancestor's
# background (body / .slide / the card) fills it in. So before each capture we
# isolate the element — clear the backgrounds of its ANCESTORS only (its own
# background is part of the artwork and must survive), and hide anything else
# that intrudes into the clip box. Everything is restored immediately after.
_ISOLATE_JS = """
    (args) => {
        const el = document.querySelector(args.sel);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        const pad = args.pad || 0;
        const box = { l: r.left - pad, t: r.top - pad, r: r.right + pad, b: r.bottom + pad };
        const saved = [];
        const remember = (n) => saved.push([n, n.getAttribute('style')]);

        const ancestors = new Set();
        let n = el.parentElement;
        while (n) {
            ancestors.add(n);
            remember(n);
            n.style.setProperty('background', 'transparent', 'important');
            n.style.setProperty('background-color', 'transparent', 'important');
            n.style.setProperty('background-image', 'none', 'important');
            n.style.setProperty('box-shadow', 'none', 'important');
            // BUG FIX: an ancestor's ::before/::after cannot be reached through
            // inline style, so decorative pseudo-element blobs (e.g.
            // .info-head.maroon::after — a 105px rgba(255,255,255,.12) circle)
            // bled into every nested capture as a faint wash, showing up as a
            // pale rectangle behind small cards. Tag ancestors so a stylesheet
            // rule can switch their pseudo-elements off. The captured element's
            // OWN pseudo-elements are untouched — they are part of its artwork.
            n.setAttribute('data-ppt-iso', '');
            n = n.parentElement;
        }
        const isoStyle = document.createElement('style');
        isoStyle.id = '__pptIsoStyle';
        isoStyle.textContent =
            '[data-ppt-iso]::before,[data-ppt-iso]::after{content:none !important;' +
            'background:none !important;box-shadow:none !important;border:0 !important;}';
        document.head.appendChild(isoStyle);
        document.documentElement.style.setProperty('background', 'transparent', 'important');
        document.body.style.setProperty('background', 'transparent', 'important');

        // PERF: this used to call getBoundingClientRect() on EVERY element in the
        // body, on EVERY capture, with the expensive DOM-relationship tests run
        // first. On a dense slide (~2000 elements, 17 cards + 127 icons = 144
        // captures) that is ~288,000 layout-forcing measurements for one slide —
        // measured at ~0.82s per icon, 104s of a 127s slide, on a 0.5-CPU box.
        // Two changes, no behaviour difference:
        //   1) Reuse geometry cached once per slide (see _PREPARE_BOXES_JS). The
        //      only things toggled between captures are visibility, background
        //      and box-shadow, none of which affect layout, so the boxes stay
        //      valid for the whole slide.
        //   2) Reject on the cheap numeric box test FIRST; only run contains()
        //      and the ancestor lookup for the few elements that actually
        //      overlap the clip region.
        const cachedEls = window.__pptEls;
        const cachedBoxes = window.__pptBoxes;
        if (cachedEls && cachedBoxes && cachedBoxes.length === cachedEls.length * 4) {
            for (let i = 0; i < cachedEls.length; i++) {
                const j = i * 4;
                const bl = cachedBoxes[j], bt = cachedBoxes[j + 1];
                const br = cachedBoxes[j + 2], bb = cachedBoxes[j + 3];
                if (br <= bl || bb <= bt) continue;
                if (br < box.l || bl > box.r || bb < box.t || bt > box.b) continue;
                const o = cachedEls[i];
                if (o === el || ancestors.has(o) || el.contains(o) || o.contains(el)) continue;
                remember(o);
                o.style.setProperty('visibility', 'hidden', 'important');
            }
        } else {
            document.body.querySelectorAll('*').forEach(o => {
                const b = o.getBoundingClientRect();
                if (b.width === 0 || b.height === 0) return;
                if (b.right < box.l || b.left > box.r || b.bottom < box.t || b.top > box.b) return;
                if (o === el || ancestors.has(o) || el.contains(o) || o.contains(el)) return;
                remember(o);
                o.style.setProperty('visibility', 'hidden', 'important');
            });
        }

        // CHANGE (option B): when capturing a PARENT card, hide the cards nested
        // inside it. Without this the parent's image would contain its children's
        // graphics, and those children are also captured separately — drawing the
        // same artwork twice. Non-card content inside the parent (plain text,
        // connector rules) stays visible, because nothing else captures it.
        if (args.hideNested) {
            el.querySelectorAll('[data-ppt-card]').forEach(o => {
                remember(o);
                o.style.setProperty('visibility', 'hidden', 'important');
            });
        }

        window.__pptIsolated = saved;
        return true;
    }
"""

_RESTORE_JS = """
    () => {
        const st = document.getElementById('__pptIsoStyle');
        if (st) st.remove();
        document.querySelectorAll('[data-ppt-iso]').forEach(n => n.removeAttribute('data-ppt-iso'));
        const saved = window.__pptIsolated || [];
        for (const [n, s] of saved) {
            if (s === null) n.removeAttribute('style');
            else n.setAttribute('style', s);
        }
        window.__pptIsolated = [];
    }
"""


# PERF (companion to the cached lookup in _ISOLATE_JS): measure every element
# once per slide, in a single pass, instead of re-measuring the whole document
# on every one of the ~150 captures a dense slide performs. Safe because the
# capture loop only ever toggles visibility/background/box-shadow, none of which
# change layout geometry.
_PREPARE_BOXES_JS = """
    () => {
        const els = Array.from(document.body.querySelectorAll('*'));
        const boxes = new Float64Array(els.length * 4);
        for (let i = 0; i < els.length; i++) {
            const b = els[i].getBoundingClientRect();
            const j = i * 4;
            boxes[j] = b.left; boxes[j + 1] = b.top;
            boxes[j + 2] = b.right; boxes[j + 3] = b.bottom;
        }
        window.__pptEls = els;
        window.__pptBoxes = boxes;
        return els.length;
    }
"""


async def _prepare_boxes(page):
    try:
        return await page.evaluate(_PREPARE_BOXES_JS)
    except Exception:
        return 0


async def _isolate(page, selector, pad, hide_nested=False):
    try:
        return await page.evaluate(
            _ISOLATE_JS, {"sel": selector, "pad": pad, "hideNested": hide_nested}
        )
    except Exception:
        return None


async def _restore(page):
    try:
        await page.evaluate(_RESTORE_JS)
    except Exception:
        pass


# HARDENING: if a CDN icon font fails to load (offline build box, air-gapped
# network, blocked domain, CDN outage) every <i class="fa-..."> renders as an
# empty box and the converter silently ships a deck of blank icon tiles that
# looks like the infographics vanished. Detect it and say so.
_ICON_FONT_CHECK_JS = """
    () => {
        // document.fonts.check() is NOT usable here: per spec it returns true
        // when the family is simply undefined, because the fallback font is
        // always "available". Measure the symptom instead — an icon element
        // whose glyph never arrived collapses to a zero-sized box (or renders
        // the literal codepoint as tofu).
        const sel = 'i[class*="fa-"], i.fa, i.fas, i.far, i.fab,'
                  + ' i[class*="ph-"], i.ph, span[class*="ph-"],'
                  // ADDITIVE: named-library fallback beyond FA/Phosphor.
                  + ' i[class*="bi-"], i.bi, span[class*="bi-"],'
                  + ' i[class*="ri-"], i.ri, span[class*="ri-"],'
                  + ' .material-icons, .material-symbols-outlined,'
                  + ' .material-symbols-rounded, .material-symbols-sharp';
        let nodes = [];
        try { nodes = Array.from(document.querySelectorAll(sel)); } catch (e) { return []; }
        let results = [];
        if (nodes.length) {
            let checked = 0, blank = 0;
            for (const el of nodes) {
                const cs = getComputedStyle(el);
                if (cs.display === 'none' || cs.visibility === 'hidden') continue;
                checked++;
                const r = el.getBoundingClientRect();
                if (r.width < 1 || r.height < 1) blank++;
            }
            // A few legitimately-hidden icons are normal; a majority is a font failure.
            if (checked && blank / checked >= 0.5) {
                results.push(blank + ' of ' + checked + ' icon elements render with no glyph');
            }
        }

        // ADDITIVE: broader shape/icon diagnostic, independent of the font-glyph
        // check above. A 0-size svg/img/icon-class/mask-image element usually
        // means missing width/height/viewBox (or a bad mask URL) in the source
        // HTML — the browser never painted anything, so there is no pixel data
        // for the converter to recover. Not majority-gated: even one such
        // element is unusual enough to be worth a log line.
        const shapeSel = 'svg, img, [class*="icon" i], [style*="mask-image"], [class*="material-symbols"]';
        let shapeNodes = [];
        try { shapeNodes = Array.from(document.querySelectorAll(shapeSel)); } catch (e) { shapeNodes = []; }

        // BUG FIX: checking only the element's OWN computed style flagged every
        // icon on an INACTIVE slide. Hidden slides use `.slide{display:none}`, and
        // a descendant of a display:none subtree keeps its own computed display
        // while getBoundingClientRect() correctly reports 0x0 — so a healthy
        // 7-slide deck reported "6 zero-size elements" every run. Walk ancestors
        // and only judge elements that are actually being rendered.
        const isRendered = (el) => {
            let n = el;
            while (n && n.nodeType === 1) {
                const s = getComputedStyle(n);
                if (s.display === 'none' || s.visibility === 'hidden') return false;
                n = n.parentElement;
            }
            return true;
        };

        let shapeBlank = 0;
        for (const el of shapeNodes) {
            if (!isRendered(el)) continue;
            const r = el.getBoundingClientRect();
            if (r.width < 1 || r.height < 1) shapeBlank++;
        }
        if (shapeBlank > 0) {
            results.push(shapeBlank + ' icon/shape element(s) rendered with zero size (missing width/height/viewBox in source HTML)');
        }
        return results;
    }
"""


async def _warn_if_icon_fonts_missing(page):
    try:
        missing = await page.evaluate(_ICON_FONT_CHECK_JS)
    except Exception:
        return
    if missing:
        print(
            "WARNING: icon/shape issue(s) detected: " + "; ".join(missing) + ".\n"
            "         Some icons may export BLANK or missing. If the deck loads fonts "
            "from a CDN (e.g. cdnjs.cloudflare.com),\n"
            "         check network access, or vendor the font locally into the HTML "
            "before converting.",
            file=sys.stderr,
        )



def safe_pptx_filename(source_filename: str | None = None) -> str:
    """Create PPTX output name from original uploaded HTML file name."""
    if not source_filename:
        return f"{uuid.uuid4().hex}.pptx"

    stem = Path(str(source_filename)).stem.strip()
    if not stem:
        return f"{uuid.uuid4().hex}.pptx"

    # Windows-safe filename cleanup.
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', stem)
    stem = re.sub(r'\s+', ' ', stem).strip().rstrip('.')
    if not stem:
        return f"{uuid.uuid4().hex}.pptx"

    return f"{stem}.pptx"


def unique_output_path(file_name: str) -> Path:
    """Avoid overwriting existing PPTX by appending _1, _2, etc."""
    output_path = OUTPUT_DIR / file_name
    if not output_path.exists():
        return output_path

    stem = Path(file_name).stem
    suffix = Path(file_name).suffix or ".pptx"
    counter = 1
    while True:
        candidate = OUTPUT_DIR / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1

def is_slide_deck(html_content: str) -> bool:
    soup = BeautifulSoup(html_content, "html.parser")
    return len(soup.select(".slide")) > 1

def warn_if_html_truncated(html_content: str) -> None:
    """Flag input that looks cut off rather than silently exporting a short deck.

    A deck pasted into the editor can be truncated by the BROWSER before it ever
    reaches us — mobile Safari in particular caps very large clipboard/textarea
    content, which lands almost exactly on a 1 MiB boundary. The request itself
    is perfectly well-formed (valid JSON, no error), so nothing downstream
    notices; the converter just faithfully exports the slides that survived.
    Observed in production: a 9-10 slide deck arrived as 1048570 chars — 6 bytes
    under 1 MiB — and exported as 4 slides with no error anywhere.
    Silently shipping a truncated deliverable is worse than a slow one, so say so.
    """
    if not html_content:
        return
    tail = html_content[-512:].strip().lower()
    looks_complete = tail.endswith("</html>") or tail.endswith("</body>") or "</html>" in tail
    if looks_complete:
        return

    size = len(html_content)
    near_power_of_two = any(
        abs(size - (1 << bits)) <= 4096 for bits in (19, 20, 21, 22, 23)
    )
    LOGGER.warning(
        "INPUT LOOKS TRUNCATED: %s chars and no closing </html> tag.%s "
        "Slides after the cut-off point cannot be exported. If you pasted the "
        "deck into the editor, the browser may have capped the paste — upload "
        "the .html file instead, which is not subject to that limit.",
        size,
        " Size sits on a power-of-two boundary, which is characteristic of a"
        " clipboard/buffer cap rather than a real file." if near_power_of_two else "",
    )


def count_slides(html_content: str) -> int:
    soup = BeautifulSoup(html_content, "html.parser")
    # Support normal decks (.slide) and wrapper/iframe decks such as GNIDA_v5 (.slide-shell)
    count = len(soup.select(".slide"))
    if count == 0:
        count = len(soup.select(".slide-shell"))
    # FIX: If no slide container exists, treat the entire body as 1 slide
    return count if count > 0 else 1

def build_layered_pptx(slide_data_list, output_file):
    # NOTE: this is the "packaging" phase and it is fully synchronous CPU work —
    # it blocks the event loop while python-pptx assembles what can be hundreds
    # of pictures per deck. Logged at both ends so a long save is visible rather
    # than looking like a hang.
    _t0 = time.perf_counter()
    _shapes = sum(len(s.get('components', [])) + len(s.get('elements', [])) for s in slide_data_list)
    LOGGER.info(
        "Packaging PPTX: %s slide(s), ~%s shape(s) -> %s",
        len(slide_data_list), _shapes, Path(output_file).name,
    )
    prs = Presentation()
    blank_slide_layout = prs.slide_layouts[6]
    
    for idx, slide_data in enumerate(slide_data_list):
        if idx == 0:
            prs.slide_width = Inches(slide_data["width"] / 96.0)
            prs.slide_height = Inches(slide_data["height"] / 96.0)
        
        slide = prs.slides.add_slide(blank_slide_layout)
        clip_x = slide_data['clip_x']
        clip_y = slide_data['clip_y']

        slide.shapes.add_picture(
            str(slide_data['bg_img_path']), 0, 0,
            width=Inches(slide_data["width"] / 96.0), 
            height=Inches(slide_data["height"] / 96.0)
        )
        
        for comp in slide_data['components']:
            cx = Inches((comp['x'] - clip_x) / 96.0)
            cy = Inches((comp['y'] - clip_y) / 96.0)
            cw = Inches(comp['w'] / 96.0)
            ch = Inches(comp['h'] / 96.0)
            try:
                slide.shapes.add_picture(str(comp['img_path']), cx, cy, width=cw, height=ch)
            except Exception:
                pass

        for el in slide_data['elements']:
            x_px = el['x'] - clip_x
            y_px = el['y'] - clip_y
            
            if x_px < -10 or y_px < -10: continue
                
            x = Inches(max(0, x_px) / 96.0)
            y = Inches(max(0, y_px) / 96.0)
            w = Inches(max(1, el['w']) / 96.0)
            h = Inches(max(1, el['h']) / 96.0)
            
            try:
                txBox = slide.shapes.add_textbox(x, y, w, h)
                tf = txBox.text_frame
                tf.clear()
                tf.margin_left = 0
                tf.margin_top = 0
                tf.margin_right = 0
                tf.margin_bottom = 0
                tf.word_wrap = True
                
                if el['vAlign'] == 'middle':
                    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
                
                p = tf.paragraphs[0]
                p.text = el['text']

                # ADDITIVE (§5.10): PowerPoint's substituted font renders large
                # bold numerals taller than Chromium calculates, bleeding into
                # tightly-spaced sibling labels. Shrink those specifically.
                _size_factor = 0.75
                if el['fontSize'] >= 24 and el['fontWeight']:
                    _size_factor = 0.68

                # ADDITIVE FIX (fidelity): 1 CSS px maps to exactly 0.75 pt at this
                # slide scale (1280px -> 13.333in -> 96 px/in), so 0.75 is the
                # faithful conversion and §5.10's 0.68 makes large bold text ~9%
                # SMALLER than the source deck — visibly so on slide headers
                # ("LATEST TIMELINES COMMITTED BY NEC & RAILTEL" exported at
                # 16.32pt instead of 18pt) and the "Thank You" closer. Under the
                # rule that the converter must reproduce the final HTML exactly,
                # shrinking the text is the wrong remedy for an overflow risk.
                # Restore the exact factor.
                # NOTE: an earlier version of this fix also widened the textbox to
                # absorb a taller substituted font. That was reverted — enlarging
                # the box re-centres centre-aligned text and visibly shifted the
                # slide headers right. The measured box already comes from
                # getClientRects() on the real glyphs, so it is left untouched.
                if _size_factor != 0.75:
                    _size_factor = 0.75
                p.font.size = Pt(max(1, el['fontSize'] * _size_factor))

                # ADDITIVE (§5.9)
                if _contains_emoji(el['text']):
                    p.font.name = 'Segoe UI Emoji'

                if el['color']:
                    p.font.color.rgb = RGBColor(*el['color'])
                p.font.bold = el['fontWeight']
                
                if el['textAlign'] == 'center': p.alignment = PP_ALIGN.CENTER
                elif el['textAlign'] == 'right': p.alignment = PP_ALIGN.RIGHT
                else: p.alignment = PP_ALIGN.LEFT
            except Exception:
                pass

    prs.save(output_file)
    try:
        _size = Path(output_file).stat().st_size
    except OSError:
        _size = 0
    LOGGER.info(
        "Packaging done in %.1fs | %.1f KB", time.perf_counter() - _t0, _size / 1024.0
    )

async def get_html_resolution(browser, html_content: str):
    page = await browser.new_page(viewport={"width": 1280, "height": 720})
    # FIX (§5.6): "load" fires before CDN-injected @font-face rules settle.
    await page.set_content(html_content, wait_until="networkidle", timeout=60000)
    await page.evaluate("document.fonts.ready")
    await _load_icon_fonts(page)
    await _warn_if_icon_fonts_missing(page)
    dims = await page.evaluate("""
        () => {
            const preferred = document.querySelector('.slide.active') || document.querySelector('.slide') || document.querySelector('.slide-shell') || document.querySelector('#presentation-container') || document.querySelector('#deck');
            if (preferred) {
                const rect = preferred.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    return { width: Math.ceil(Math.max(rect.width, 1280)), height: Math.ceil(Math.max(rect.height, 720)) };
                }
            }
            const scrollW = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth, document.documentElement.offsetWidth, 1280);
            const scrollH = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight, document.documentElement.offsetHeight, 720);
            return { width: Math.ceil(scrollW), height: Math.ceil(scrollH) };
        }
    """)
    await page.close()
    return dims

async def force_final_state(page, slide_index: int):
    await page.evaluate("""
        (idx) => {
            if (window.goToSlide) { try { window.goToSlide(idx + 1); } catch(e) {} } 
            else if (window.goTo) { try { window.goTo(idx + 1); } catch(e) {} } 
            else {
                const slides = [...document.querySelectorAll('.slide')];
                slides.forEach((s, j) => { if (j === idx) s.classList.add('active'); else s.classList.remove('active'); });
            }
            if (window.runAnims) { try { window.runAnims(idx); } catch(e) {} }
            let slides = [...document.querySelectorAll('.slide')];
            if (slides.length === 0) slides = [...document.querySelectorAll('.slide-shell')];
            if (slides.length > 0) {
                slides.forEach((s, j) => {
                    if (j === idx) {
                        s.classList.add('active');
                        s.style.display = ''; s.style.visibility = 'visible'; s.style.opacity = '1'; s.style.pointerEvents = 'all';
                        s.scrollIntoView({block:'start', inline:'nearest'});
                    } else {
                        s.classList.remove('active');
                        s.style.display = 'none'; s.style.visibility = 'hidden'; s.style.opacity = '0'; s.style.pointerEvents = 'none';
                    }
                });
            }

            const dots = [...document.querySelectorAll('.nav-dots .dot, .dot')];
            dots.forEach((d, j) => {
                if (j === idx) d.classList.add('active');
                else d.classList.remove('active');
            });
            const current = slides.length > 0 ? slides[idx] : document.body;
            if (!current) return;

            const currentCs = getComputedStyle(current);
            if (currentCs.backgroundAttachment === 'fixed') {
                current.style.setProperty('background-attachment', 'scroll', 'important');
            }

            current.querySelectorAll('*').forEach(el => {
                const cs = getComputedStyle(el);
                if (cs.display === 'none') el.style.display = '';
                if (cs.visibility === 'hidden') el.style.visibility = 'visible';
                if (parseFloat(cs.opacity || '1') === 0) el.style.opacity = '1';
                if (cs.backgroundAttachment === 'fixed') {
                    el.style.setProperty('background-attachment', 'scroll', 'important');
                }
                el.style.transition = 'none';
            });
        }
    """, slide_index)

async def render_deck_to_file(html_content: str, output_file: str):
    slide_count = count_slides(html_content)
    slides_for_output = []
    _deck_t0 = time.perf_counter()
    LOGGER.info("Detected slide deck with %s slide(s) | html=%s chars", slide_count, len(html_content))
    warn_if_html_truncated(html_content)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        async with async_playwright() as p:
            browser = await p.chromium.launch(
            headless=True,
            executable_path=os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE") or None,
            args=[
                "--enable-gpu",
                "--ignore-gpu-blocklist",
                "--enable-accelerated-2d-canvas",
                "--enable-zero-copy",
                "--use-angle=d3d11",
            ]
        )
            dims = await get_html_resolution(browser, html_content)
            _scale = _device_scale()
            context = await browser.new_context(
                viewport={"width": dims["width"], "height": dims["height"]},
                device_scale_factor=_scale,
            )

            # Sized against the CONTAINER's real CPU and memory, not the host's
            # core count (see _slide_worker_budget) — the old os.cpu_count()
            # reading caused OOM kills on small instances.
            max_parallel_slides = _slide_worker_budget(slide_count)
            semaphore = asyncio.Semaphore(max_parallel_slides)
            _mem = _memory_limit_mb()
            LOGGER.info(
                "Viewport %sx%s @%.0fx | container cpus=%.1f (host reports %s) | "
                "memory limit=%s | parallel slide workers=%s",
                dims["width"], dims["height"], _scale,
                _effective_cpus(), os.cpu_count() or 1,
                f"{_mem:.0f}MB" if _mem else "unset",
                max_parallel_slides,
            )

            async def render_slide(i):
                async with semaphore:
                    # BUG FIX: the page was only closed on the success path. Any
                    # exception mid-render (font timeout, screenshot failure)
                    # left the page open and surfaced without saying which slide
                    # died. try/finally guarantees cleanup; the re-raise tags
                    # the slide index for the operator.
                    page = await context.new_page()
                    _t0 = time.perf_counter()
                    LOGGER.info("Slide %s/%s: render started", i + 1, slide_count)
                    try:
                        await _render_slide_inner(i, page)
                        LOGGER.info(
                            "Slide %s/%s: render done in %.1fs", i + 1, slide_count,
                            time.perf_counter() - _t0,
                        )
                    except Exception as exc:
                        LOGGER.error(
                            "Slide %s/%s: FAILED after %.1fs: %s", i + 1, slide_count,
                            time.perf_counter() - _t0, exc,
                        )
                        raise RuntimeError(f"slide {i + 1}/{slide_count} failed to render: {exc}") from exc
                    finally:
                        try:
                            await page.close()
                        except Exception:
                            pass

            async def _render_slide_inner(i, page):
                    # FIX (§5.6): "load" races CDN icon fonts.
                    await page.set_content(html_content, wait_until="networkidle", timeout=60000)
                    await page.evaluate("document.fonts.ready")
                    await _load_icon_fonts(page)
                    await page.wait_for_timeout(300)

                    # §5.5: nav-chrome selector list — hyphenated AND camelCase
                    # conventions both seen across client decks.
                    # §5.8: animation-play-state:paused settles keyframes on the
                    # final frame rather than mid-cycle.
                    await page.add_style_tag(content="""
                        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-attachment: scroll !important; }
                        #dots, #ctr, #counter, #progressBar, .progress-wrap,
                        div.nav, .nav, .slide-nav, .nav-btn, .nav-dots,
                        .navBtn, .navBar, #prevBtn, #nextBtn, #slideCount, .slideCount,
                        [class*="slide-nav"], [class*="nav-btn"], [class*="nav-dot"],
                        [class*="fullscreen"], [class*="full-screen"],
                        /* BUG FIX: the deck's own progress bar (#deck-progress) is navigation
                           chrome and is stripped. NOTE: .page-indicator is deliberately NOT in
                           this list — it is the printed slide number ("» 4") that belongs to
                           each slide's content, not navigation, and removing it silently
                           deleted the page numbering from the deliverable. */
                        #deck-progress, .deck-progress { display: none !important; }
                        *, *::before, *::after { transition-duration: 0s !important; transition-delay: 0s !important; animation-duration: 0s !important; animation-delay: 0s !important; animation-fill-mode: forwards !important; animation-play-state: paused !important; }
                    """)

                    await force_final_state(page, i)
                    await page.wait_for_timeout(2000) 
    
                    await page.evaluate("""
                        () => {
                            if (window.gsap) { try { window.gsap.globalTimeline.progress(1); } catch(e) {} }
                            document.body.querySelectorAll('*').forEach(el => {
                                if (parseFloat(getComputedStyle(el).opacity) === 0) el.style.opacity = '1';
                            });
                        }
                    """)

                    # ADDITIVE (§5.7): automated slide activation doesn't call the
                    # deck's own nav function, so rAF-driven count-up numbers and
                    # width-animated bars never fire. Force final values directly.
                    # No-op on decks without these attributes.
                    try:
                        await page.evaluate("""
                            () => {
                                document.querySelectorAll('[data-to]').forEach(el => {
                                    const to = parseFloat(el.getAttribute('data-to'));
                                    if (Number.isNaN(to)) return;
                                    const prefix = el.getAttribute('data-prefix') || '';
                                    const suffix = el.getAttribute('data-suffix') || '';
                                    const format = el.getAttribute('data-format');
                                    const val = Math.round(to);
                                    const text = format === 'comma' ? val.toLocaleString('en-IN') : String(val);
                                    el.textContent = prefix + text + suffix;
                                });
                                document.querySelectorAll('[data-w]').forEach(el => {
                                    const w = el.getAttribute('data-w');
                                    if (w !== null) el.style.setProperty('width', w + '%', 'important');
                                });
                            }
                        """)
                    except Exception:
                        pass

                    box = await page.evaluate("""
                        () => {
                            const active = document.querySelector('.slide.active') || document.querySelector('.slide-shell.active') || document.querySelector('.slide') || document.querySelector('.slide-shell') || document.body;
                            const rect = active.getBoundingClientRect();
                            return { x: rect.left, y: rect.top, width: rect.width, height: rect.height };
                        }
                    """)
                    
                    bg_x = max(0, math.floor(box["x"] - 2) if box else 0)
                    bg_y = max(0, math.floor(box["y"] - 2) if box else 0)
                    bg_w = max(1, math.ceil(box["width"] + 4) if box else dims["width"])
                    bg_h = max(1, math.ceil(box["height"] + 4) if box else dims["height"])
    
                    bg_x = min(bg_x, dims["width"] - 1)
                    bg_y = min(bg_y, dims["height"] - 1)
                    bg_w = min(bg_w, dims["width"] - bg_x)
                    bg_h = min(bg_h, dims["height"] - bg_y)
                    clip = {"x": bg_x, "y": bg_y, "width": bg_w, "height": bg_h}
    
                    # CRITICAL FIX: Unified Text Engine - Ignores inline elements and extracts full block text
                    text_elements = await page.evaluate("""
                        () => {
                            const elements = [];
                            const rgbToHex = (rgba) => {
                                if (!rgba) return null;
                                const match = rgba.match(/^rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
                                return match ? [parseInt(match[1]), parseInt(match[2]), parseInt(match[3])] : null;
                            };
                            
                            document.body.querySelectorAll('*').forEach(node => {
                                const style = window.getComputedStyle(node);
                                if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) === 0) return;
                                
                                if (style.display === 'inline') return;
    
                                const tag = node.tagName.toLowerCase();
                                if (['script', 'style', 'svg', 'i', 'img'].includes(tag)) return;
                                if (node.classList && node.classList.contains('material-icons')) return;
                                if (node.closest && node.closest('.material-icons, [data-ppt-icon]')) return;
    
                                let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
                                let hasValidRect = false;
                                // Trailing edge of the previous inline run, used to detect a
                                // CSS-produced gap between adjacent runs (see extractTextAndBounds).
                                let _lastRunRight = null, _lastRunTop = null, _lastRunEndedSpace = false;
                                // BUG FIX (see textOwnerStyle below): remember which element each
                                // contributing text node actually belongs to.
                                const textOwners = [];

                                const extractTextAndBounds = (element) => {
                                    let localText = "";
                                    for (let child of element.childNodes) {
                                        if (child.nodeType === 3) { 
                                            const content = child.nodeValue.replace(/\\s+/g, ' '); 
                                            if (content !== ' ' && content !== '') {
                                                // BUG FIX: adjacent inline runs are concatenated
                                                // with nothing between them, so markup like
                                                //   <b>Field Cameras</b><span>3,099 / 9,989</span>
                                                // exported as "Field Cameras3,099 / 9,989". The
                                                // browser shows a gap because .plabel span carries
                                                // margin-left:4px — a layout property with no
                                                // character to carry it across. If the incoming run
                                                // starts to the right of where the previous one
                                                // ended, on the same line, re-create that gap with
                                                // a single space so the exported string reads the
                                                // way the slide does.
                                                // NOTE: localText is local to each recursive call,
                                                // so gap state is tracked in the shared
                                                // _lastRunRight/_lastRunTop/_lastRunEndedSpace vars.
                                                let _gapSpace = "";
                                                if (_lastRunRight !== null && !_lastRunEndedSpace &&
                                                    !/^\\s/.test(content)) {
                                                    const _r = document.createRange();
                                                    _r.selectNode(child);
                                                    const _first = _r.getClientRects()[0];
                                                    if (_first &&
                                                        Math.abs(_first.top - _lastRunTop) < 2 &&
                                                        _first.left - _lastRunRight > 1.5) {
                                                        _gapSpace = " ";
                                                    }
                                                }
                                                _lastRunEndedSpace = /\\s$/.test(content);
                                                localText += _gapSpace + content;
                                                textOwners.push({ el: element, len: content.trim().length });
                                                const range = document.createRange();
                                                range.selectNode(child);
                                                const rects = range.getClientRects();
                                                for (let r of rects) {
                                                    if (r.width > 0 && r.height > 0) {
                                                        minX = Math.min(minX, r.left);
                                                        minY = Math.min(minY, r.top);
                                                        maxX = Math.max(maxX, r.right);
                                                        maxY = Math.max(maxY, r.bottom);
                                                        hasValidRect = true;
                                                        _lastRunRight = r.right;
                                                        _lastRunTop = r.top;
                                                    }
                                                }
                                            }
                                        } else if (child.nodeType === 1) { 
                                            const childTag = child.tagName.toLowerCase();
                                            if (childTag === 'br') {
                                                localText += '\\n';
                                            } else if (!['script', 'style', 'svg', 'i', 'img'].includes(childTag)) {
                                                if (child.classList && child.classList.contains('material-icons')) continue;
                                                if (child.closest && child.closest('.material-icons, [data-ppt-icon]')) continue;
                                                const childStyle = window.getComputedStyle(child);
                                                if (childStyle.display === 'inline') {
                                                    localText += extractTextAndBounds(child);
                                                }
                                            }
                                        }
                                    }
                                    return localText;
                                };
    
                                let textStr = extractTextAndBounds(node).trim();
                                if (!hasValidRect || !textStr) return;

                                // BUG FIX: font size / weight / colour were read from the block
                                // element being walked, but its text often comes entirely from an
                                // INLINE descendant with a different font. e.g.
                                //   <div class="red">            <- 16px, the walked node
                                //     <b>CRITICAL RISK</b>       <- 8px, what actually renders
                                //     <h4>..</h4><p>..</p>       <- block, extracted separately
                                // Inline children are absorbed into the parent's text, so the
                                // label was written at 16*0.75=12pt into a box measured for the
                                // 8px rendering — text at 2x its size overflowing a box a third
                                // its height, spilling over every neighbouring label and reading
                                // as doubled/shadowed text. Attribute the run to the element that
                                // actually owns the text (dominant one by character count).
                                // Measured on Meity Stage-4: 116 mis-sized textboxes, up to 2x.
                                let textOwnerStyle = style;
                                if (textOwners.length) {
                                    let best = textOwners[0];
                                    for (const o of textOwners) if (o.len > best.len) best = o;
                                    if (best.el !== node) textOwnerStyle = window.getComputedStyle(best.el);
                                }

                                const tt = textOwnerStyle.textTransform;
                                if (tt === 'uppercase') textStr = textStr.toUpperCase();
                                else if (tt === 'lowercase') textStr = textStr.toLowerCase();
                                else if (tt === 'capitalize') textStr = textStr.replace(/\\b\\w/g, c => c.toUpperCase());
    
                                const isFlexCenter = style.display === 'flex' && style.alignItems === 'center';
    
                                // TARGETED FIX: Downloading & Retrieval top process only.
                                // Font Awesome icons render slightly taller in PowerPoint than in
                                // Chromium. Move only the editable labels below those icons; do not
                                // alter cards, header, footer, or any other slide.
                                const isSlide7Process = Boolean(node.closest && node.closest('#slide-7 .sop-process'));
                                const slide7ProcessOffset = isSlide7Process
                                    ? (tag === 'b' ? 10 : (tag === 'small' ? 5 : 0))
                                    : 0;

                                elements.push({
                                    text: textStr, 
                                    x: minX, 
                                    y: minY + slide7ProcessOffset, 
                                    w: Math.max(1, maxX - minX + 2), 
                                    h: Math.max(1, maxY - minY + 2),
                                    // BUG FIX: sourced from textOwnerStyle, not the container.
                                    fontSize: parseFloat(textOwnerStyle.fontSize) || 12, 
                                    color: rgbToHex(textOwnerStyle.color),
                                    fontWeight: textOwnerStyle.fontWeight === 'bold' || parseInt(textOwnerStyle.fontWeight) >= 600,
                                    textAlign: style.textAlign || 'left',
                                    vAlign: isFlexCenter ? 'middle' : 'top'
                                });
                            });
                            return elements;
                        }
                    """)

                    # ADDITIVE (§5.11): drop overlapping duplicate labels — the
                    # same string emitted by both a wrapper and its child within
                    # 25px, which stacks two textboxes and reads as bold-ghosting.
                    # BUG FIX: the original substring rule (n1.includes(n2)) is
                    # unsafe for short/numeric strings — a nearby "+16" deleted the
                    # real value "163", and a "15" deleted "15,000", silently
                    # dropping 25 figures from the two Way-Forward plan slides.
                    # Containment now requires a reasonably long, non-numeric
                    # substring; exact matches still dedup as before.
                    try:
                        text_elements = await page.evaluate("""
                            (all) => {
                                const norm = s => s.toLowerCase().replace(/[^a-z0-9]/g, '');
                                const out = [];
                                for (const el of all) {
                                    const isDup = out.some(ex => {
                                        if (Math.abs(ex.x - el.x) > 25 || Math.abs(ex.y - el.y) > 25) return false;
                                        const n1 = norm(ex.text), n2 = norm(el.text);
                                        if (!n1 || !n2) return false;
                                        if (n1 === n2) return true;
                                        const shorter = n1.length <= n2.length ? n1 : n2;
                                        const longer  = n1.length <= n2.length ? n2 : n1;
                                        // Never let a numeric fragment swallow a different number.
                                        if (/^[0-9]+$/.test(shorter)) return false;
                                        // Require a substantial label before containment counts.
                                        if (shorter.length < 6) return false;
                                        return longer.includes(shorter);
                                    });
                                    if (!isDup) out.push(el);
                                }
                                return out;
                            }
                        """, text_elements)
                    except Exception:
                        pass

                    # Used only for the Slide 3 text/icon-container guard below.
                    await page.evaluate("idx => { window.__pptSlideIndex = idx; }", i)
                    await page.evaluate("""
                        () => {
                            const isCard = (el) => {
                                const tag = el.tagName.toUpperCase();
                                // FIX: table cells/rows carry CSS border-right/border-bottom purely
                                // for grid-line styling, which satisfied the border-based card check
                                // below and caused each <td> to be screenshotted as its own "card".
                                // Any icon badge (e.g. .mini-icon, itself a legitimately-detected
                                // small card) nested inside that <td> then got baked into the cell's
                                // own background image AND rendered again as its separate layer,
                                // producing a double-rendered artifact right at the icon/text boundary.
                                if (['BODY', 'HTML', 'MAIN', 'SECTION', 'HEADER', 'FOOTER', 'SVG', 'SCRIPT', 'STYLE', 'IMG', 'I', 'TD', 'TH', 'TR', 'TABLE', 'THEAD', 'TBODY', 'TFOOT'].includes(tag)) return false;
    
                                const excludeClasses = ['slide', 'content-wrap', 'bg-wrap', 'hero-grid', 'hero-split', 'infographic-board', 'outcomes-grid', 'close-layout', 'story-ribbon', 'metric-stack', 'nav', 'top-right'];
                                for (let cls of excludeClasses) { if (el.classList.contains(cls)) return false; }
                                if (el.className && typeof el.className === 'string' && el.className.includes('bg-')) return false;
    
                                const rect = el.getBoundingClientRect();
                                if (rect.width <= 10 || rect.height <= 10) return false;
                                // FIX (§5.1): both dimensions must be huge to count as a
                                // structural wrapper. || wrongly excluded wide-but-short
                                // elements (timeline tables, header bars), baking them into
                                // the background instead of extracting them as cards.
                                if (rect.width >= window.innerWidth * 0.90 && rect.height >= window.innerHeight * 0.90) return false;
    
                                const style = window.getComputedStyle(el);
                                if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) === 0) return false;
    
                                const explicitClasses = [
                                    'ribbon-card', 'metric', 'hero-side', 'issue-card', 'insight-panel',
                                    'kpi-box', 'center-hub', 'spoke', 'narrative-panel', 'checkpoint',
                                    'outcome-board', 'outcome-row', 'data-source', 'central-engine',
                                    'kpi-card', 'phase', 'ey-tag', 'page-chip', 'silo-pillar', 'hub-center', 'counter'
                                ];
    
                                let isExplicit = false;
                                for (let cls of explicitClasses) { if (el.classList.contains(cls)) isExplicit = true; }
                                if (tag === 'BUTTON') isExplicit = true; 
                                if (isExplicit) return true;
    
                                const hasBg = (style.backgroundColor !== 'rgba(0, 0, 0, 0)' && style.backgroundColor !== 'transparent') || (style.backgroundImage !== 'none' && style.backgroundImage !== 'initial');
                                // FIX (§5.2): check all four sides — a card bordered only
                                // on its left or bottom was missed by the top-only test.
                                const hasBorder = ['Top','Right','Bottom','Left']
                                    .some(s => parseFloat(style['border' + s + 'Width']) > 0);
                                const hasShadow = style.boxShadow !== 'none' && style.boxShadow !== '';
                                return hasBg || hasBorder || hasShadow;
                            };
    
                            const cards = Array.from(document.body.querySelectorAll('*')).filter(isCard);
                            // CHANGE (option B, approved): previously only TOP-LEVEL cards were
                            // kept — any card nested inside another was discarded, so the parent
                            // was captured as one flat image swallowing all its children. That
                            // made e.g. slide 5's .timeline-table-wrap a single un-editable
                            // block containing 41 boxes. Tag nested cards too.
                            //
                            // CHANGE (option B-prime, approved): EXCEPT absolutely-positioned
                            // nested cards. Once un-nested, siblings are painted in document
                            // order, which ignores CSS stacking — and absolutely-positioned
                            // decorations (.flow-dot, .flow-icon, .phase-num, .impact-icon,
                            // .thankyou-mini-wheel) overlap by nature, so they landed on top of
                            // artwork the browser paints above them (the slide 6/7 arrowhead was
                            // covered by its own animated dot). Leaving them in the parent's
                            // image preserves the browser's paint order exactly. In-flow nested
                            // cards do not overlap and un-nest safely: 192 of 233 here.
                            const keptCards = cards.filter(c => {
                                let p = c.parentElement, hasCardAncestor = false;
                                while (p && p !== document.body) {
                                    if (cards.includes(p)) { hasCardAncestor = true; break; }
                                    p = p.parentElement;
                                }
                                if (!hasCardAncestor) return true;          // top-level: always
                                const pos = window.getComputedStyle(c).position;
                                return pos !== 'absolute' && pos !== 'fixed';
                            });
                            // Document order, so a parent always precedes its descendants, which
                            // gives the correct back-to-front paint order for free. The parent's
                            // own capture hides its tagged nested cards (see _isolate), so
                            // nothing is drawn twice; untagged absolute children stay visible in
                            // the parent image, which is exactly what we want.
                            keptCards.forEach((c, i) => c.setAttribute('data-ppt-card', i));
                        }
                    """)
    
                    # FIX: Detect and isolate icon elements within cards
                    # BROADENED (icon/shape coverage): the old allowlist only matched
                    # <i>, .material-icons, svg<=150px, img<=100px — any other icon
                    # technique (CSS mask-image icons, sprite <use> refs, oversized
                    # badge icons, icon fonts outside FA/Phosphor, icons that live
                    # OUTSIDE a card) fell through and was silently flattened into the
                    # background, or vanished if it rendered at 0 size. Detection is now
                    # structural/CSS-signal-based first (works for any icon pack, present
                    # or future, without a converter change), with named-library class
                    # checks kept only as a fast, low-risk accuracy boost.
                    await page.evaluate("""
                        () => {
                            // Proportional cap instead of the old fixed 150/100px cutoff —
                            // on the 1280x720 deck canvas this is ~200px, comfortably
                            // covering large hero-section badge icons while staying well
                            // under isCard's 90%-of-viewport structural-wrapper threshold.
                            const ICON_MAX_PX = Math.min(window.innerWidth, window.innerHeight) * 0.28;
                            const SVG_LEAF_TAGS = ['path','use','circle','rect','line','polygon','polyline','g','symbol','ellipse'];

                            const isIconElement = (el) => {
                                // Guard against double-classification with isCard: a shape
                                // that already qualifies as its own card (e.g. a
                                // background-color + border-radius circle) must not also be
                                // captured a second time as an "icon".
                                if (el.hasAttribute('data-ppt-card')) return false;

                                const tag = el.tagName.toLowerCase();
                                const rect = el.getBoundingClientRect();
                                if (rect.width <= 0 || rect.height <= 0) return false;
                                if (el.classList && (
                                    el.classList.contains('material-icons') ||
                                    el.classList.contains('material-symbols-outlined') ||
                                    el.classList.contains('material-symbols-rounded') ||
                                    el.classList.contains('material-symbols-sharp')
                                )) return true;
                                if (tag === 'i') return true;

                                const withinCap = rect.width <= ICON_MAX_PX && rect.height <= ICON_MAX_PX;
                                const aspect = rect.width / rect.height;
                                const nearSquare = aspect >= 0.4 && aspect <= 2.5;
                                const spansSlide = rect.width >= window.innerWidth * 0.5 || rect.height >= window.innerHeight * 0.5;

                                // Size-based svg/img icons: near-square and not spanning the
                                // slide, so a full-bleed decorative SVG background isn't swept
                                // in just because one dimension happens to be small.
                                if ((tag === 'svg' || tag === 'img') && withinCap && nearSquare && !spansSlide) return true;

                                // ADDITIVE, pack-agnostic: CSS mask-image icons (Tailwind /
                                // Heroicons-via-mask and similar). The shape comes from the
                                // author's own mask, not a size guess, so no aspect guard.
                                const cs = window.getComputedStyle(el);
                                const hasMask = (cs.maskImage && cs.maskImage !== 'none') ||
                                                (cs.webkitMaskImage && cs.webkitMaskImage !== 'none');
                                if (hasMask && withinCap) return true;

                                // ADDITIVE, pack-agnostic: an element whose direct children are
                                // ALL raw SVG drawing primitives is an icon regardless of which
                                // pack emitted it (catches sprite <use> refs and multi-path/
                                // multi-group icons on a non-<svg> wrapper). Direct children
                                // only, so a larger multi-part diagram doesn't qualify.
                                if (el.children.length > 0 && withinCap) {
                                    let allLeaves = true;
                                    for (const c of el.children) {
                                        if (SVG_LEAF_TAGS.indexOf(c.tagName.toLowerCase()) === -1) { allLeaves = false; break; }
                                    }
                                    if (allLeaves) return true;
                                }

                                // ADDITIVE, pack-agnostic fallback for icon FONTS with no named
                                // entry above (tag <i> is already unconditionally an icon, so
                                // this only adds coverage for <span>-based icon-font markup): a
                                // <span> rendering 1-2 non-whitespace characters in a font
                                // different from the page's own body text is very likely a
                                // ligature/PUA glyph from an icon pack, not real short text.
                                if (tag === 'span' && withinCap) {
                                    const txt = (el.textContent || '').trim();
                                    if (txt.length > 0 && txt.length <= 2 && !/\\s/.test(txt)) {
                                        if (!window.__pptBodyFont) {
                                            window.__pptBodyFont = window.getComputedStyle(document.body).fontFamily;
                                        }
                                        if (cs.fontFamily && cs.fontFamily !== window.__pptBodyFont) return true;
                                    }
                                }

                                return false;
                            };

                            const isIconContainer = (el) => {
                                if (el.hasAttribute('data-ppt-card')) return false;
                                // BUG FIX: this guard was gated to slide indices 2/3/6 — values
                                // hand-tuned for an earlier deck. An element holding an icon PLUS
                                // its own text (e.g. <span class="status-pill"><i/>Ongoing</span>,
                                // .metric-status, legend chips) was therefore classified as an
                                // "icon" on every other slide. Text inside [data-ppt-icon] is
                                // skipped by the transparent-text pass, so the label got BAKED
                                // into the icon screenshot while still being emitted as an
                                // editable textbox — rendering the word twice, overlapping
                                // (observed: "ONGOING" over "Ongoing" on the timeline table).
                                // The rule is deck-independent: an element with direct text is
                                // never an icon. Measured on Meity Stage-4: 33 doubled labels
                                // across 8 slides with the gate, 0 without it.
                                const hasDirectText = Array.from(el.childNodes).some(n =>
                                    n.nodeType === Node.TEXT_NODE && n.nodeValue.trim().length > 0
                                );
                                if (hasDirectText) return false;
                                const rect = el.getBoundingClientRect();
                                if (rect.width < 10 || rect.height < 10 || rect.width > ICON_MAX_PX || rect.height > ICON_MAX_PX) return false;
                                const visibleChildren = Array.from(el.children).filter(c => {
                                    const cs = getComputedStyle(c);
                                    return cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) > 0;
                                });
                                if (visibleChildren.length === 0) return false;
                                return visibleChildren.every(c => isIconElement(c));
                            };

                            // Same tag/style prefilter is used both inside a card and at
                            // top level below: cheap, and scoped to what isIconElement
                            // actually recognises, rather than calling it on every node.
                            const looksIconish = (el) => {
                                const t = el.tagName.toLowerCase();
                                if (t === 'i' || t === 'svg' || t === 'img' || t === 'span') return true;
                                if (el.classList && el.classList.contains('material-icons')) return true;
                                const cs = window.getComputedStyle(el);
                                return (cs.maskImage && cs.maskImage !== 'none') ||
                                       (cs.webkitMaskImage && cs.webkitMaskImage !== 'none');
                            };

                            document.querySelectorAll('[data-ppt-card]').forEach(card => {
                                card.querySelectorAll('*').forEach(el => {
                                    if (isIconContainer(el)) {
                                        el.setAttribute('data-ppt-icon', '');
                                    }
                                });
                                card.querySelectorAll('*').forEach(el => {
                                    if (el.closest('[data-ppt-icon]')) return;
                                    if (looksIconish(el) && isIconElement(el)) {
                                        el.setAttribute('data-ppt-icon', '');
                                    }
                                });
                            });

                            // ADDITIVE: icons/shapes that live OUTSIDE any card (directly
                            // under .slide or a transparent wrapper) were previously never
                            // visited by any classifier — the loop above only ever walks
                            // inside [data-ppt-card] elements — so a top-level icon could
                            // never be tagged for individual capture no matter what
                            // isIconElement said, and simply vanished into the flat
                            // background screenshot. Mirror the same two-pass logic here,
                            // rooted at document.body, skipping anything already handled.
                            document.body.querySelectorAll('*').forEach(el => {
                                if (el.closest('[data-ppt-card]')) return;
                                if (el.hasAttribute('data-ppt-card')) return;
                                if (el.closest('[data-ppt-icon]')) return;
                                if (isIconContainer(el)) {
                                    el.setAttribute('data-ppt-icon', '');
                                    return;
                                }
                                if (looksIconish(el) && isIconElement(el) && !el.closest('[data-ppt-icon]')) {
                                    el.setAttribute('data-ppt-icon', '');
                                }
                            });

                            // Mark the ONLY icons that can duplicate a text entry: ones
                            // carrying their own glyph text (from the icon-font heuristic).
                            // Every other icon kind (svg/img/mask/sprite) contains no text
                            // node at all, so it can never produce a duplicate textbox.
                            document.querySelectorAll('[data-ppt-icon]').forEach(el => {
                                const t = (el.textContent || '').trim();
                                if (t.length > 0 && t.length <= 2 && !/\\s/.test(t)) {
                                    el.setAttribute('data-ppt-icon-glyph', '');
                                }
                            });

                            document.querySelectorAll('[data-ppt-icon]').forEach((el, i) => {
                                el.setAttribute('data-ppt-icon', i);
                            });

                            // BUG FIX: cards are clipped with a small fixed pad, so any
                            // box-shadow wider than that pad gets sliced off mid-gradient. The
                            // patch is opaque, so pasting it over the background (where the card
                            // was hidden, shadow and all) leaves a hard rectangular edge — the
                            // grey box users see around the Delhi Police logo and the coloured
                            // icon tiles. Measured on this deck: shadows extend 26-68px against
                            // an 8px pad, so every shadowed card was clipped.
                            // Pad by the real shadow extent instead, capped by the clearance to
                            // the nearest other capture region so an enlarged patch can never
                            // paint over a neighbour. Elements without a shadow are unaffected,
                            // which keeps the §5.4 tiny-icon-badge fix intact.
                            // BUG FIX (2nd pass): this originally covered cards only. The header
                            // Delhi Police logo is a 54px .dp-logo-slot with a 20px shadow that
                            // gets captured on the ICON path (4px pad), so it kept its grey
                            // clipped-shadow box after the card fix. Icons are included here now.
                            const padEls = Array.from(document.querySelectorAll('[data-ppt-card], [data-ppt-icon]'));
                            padEls.forEach((c, i) => {
                                const bs = window.getComputedStyle(c).boxShadow;
                                let ext = 0;
                                if (bs && bs !== 'none' && bs.indexOf('inset') === -1) {
                                    const re = /(-?[\\d.]+)px\\s+(-?[\\d.]+)px(?:\\s+(-?[\\d.]+)px)?(?:\\s+(-?[\\d.]+)px)?/g;
                                    let m;
                                    while ((m = re.exec(bs)) !== null) {
                                        const ox = Math.abs(parseFloat(m[1]) || 0);
                                        const oy = Math.abs(parseFloat(m[2]) || 0);
                                        const bl = parseFloat(m[3]) || 0;
                                        const sp = parseFloat(m[4]) || 0;
                                        ext = Math.max(ext, Math.max(ox, oy) + bl + Math.max(0, sp));
                                    }
                                }
                                if (ext <= 0) { c.setAttribute('data-ppt-pad', '0'); return; }
                                // Captures are isolated and alpha-composited, so an enlarged
                                // patch is transparent wherever a neighbour used to be. The old
                                // neighbour-clearance cap is therefore unnecessary — and it was
                                // the thing still slicing the big cover-card and hub-circle
                                // shadows into visible rectangles, because adjacent cards sit
                                // ~15px apart while their shadows reach 26-68px. Pad by the
                                // full shadow extent.
                                c.setAttribute('data-ppt-pad', String(ext));
                            });
                        }
                    """)

                    # ADDITIVE: the broadened icon detection above (specifically the
                    # generic glyph-font heuristic) can match an element that carries a
                    # real text node — unlike the old <i>-tag icon fonts, which render
                    # via ::before and never produce one. Icon tagging necessarily runs
                    # after the text-extraction pass above (it needs the fully measured,
                    # laid-out DOM), so such an element's glyph text was already captured
                    # as a normal textbox before it was ever tagged data-ppt-icon. Left
                    # alone it would export twice — once as the icon's own picture, once
                    # as a stray textbox on top of it.
                    #
                    # BUG FIX: an earlier version of this dropped any text entry whose box
                    # merely INTERSECTED any tagged icon box. That silently deleted whole
                    # lines of legitimate copy: an icon inline in a sentence
                    # ("Network status <svg/> operational across all sites") sits inside
                    # that line's own text box, so the entire line was discarded — and a
                    # picture-count-based regression check cannot see text loss at all.
                    # Restrict it to what actually duplicates: only glyph-bearing icons
                    # (tagged above), and only when the text box is CONTAINED in the icon
                    # box and is itself glyph-length. A real sentence is neither.
                    try:
                        text_elements = await page.evaluate("""
                            (all) => {
                                const glyphBoxes = Array.from(document.querySelectorAll('[data-ppt-icon-glyph]'))
                                    .map(el => el.getBoundingClientRect());
                                if (!glyphBoxes.length) return all;
                                const PAD = 2;
                                const containedIn = (t, b) =>
                                    t.x >= b.left - PAD && t.y >= b.top - PAD &&
                                    t.x + t.w <= b.right + PAD && t.y + t.h <= b.bottom + PAD;
                                return all.filter(t => {
                                    const s = (t.text || '').trim();
                                    if (!s || s.length > 2 || /\\s/.test(s)) return true;
                                    return !glyphBoxes.some(b => containedIn(t, b));
                                });
                            }
                        """, text_elements)
                    except Exception:
                        pass

                    # BUG FIX (layout shift): the TreeWalker span-wrap below inserts a
                    # DOM node around every text node. Inserting ANY element changes
                    # inline layout on some decks — on Meity Stage-4 slide 10 the
                    # .plan-sub flex header collapsed from 44px to 22px (its two flex
                    # items stopped wrapping), which lifted the whole plan table 22px.
                    # Cards are screenshotted after this pass, so the captured images
                    # were of a shifted layout: the dark header row landed at y=149
                    # instead of y=171 and the cream contingency cell rode up over it.
                    # Tested with the wrapper at display:inline, display:contents and
                    # unset — all three shift, so the wrapper's display is irrelevant;
                    # the insertion itself is the problem.
                    #
                    # Hide the text with CSS instead: a blanket transparent colour is
                    # guaranteed layout-neutral because it touches no boxes. The
                    # original reason for wrapping was to leave ::before/::after
                    # content (status dots, bullet icons) at their real colour, so
                    # those are enumerated first and exempted by generated rules.
                    # ADDITIVE: the wrap below is left intact and simply skipped.
                    _css_text_hidden = False
                    try:
                        await page.evaluate("""
                            () => {
                                const rules = [];
                                let k = 0;
                                document.body.querySelectorAll('*').forEach(el => {
                                    let tagged = false;
                                    for (const pe of ['::before', '::after']) {
                                        const cs = window.getComputedStyle(el, pe);
                                        if (!cs.content || cs.content === 'none' || cs.content === 'normal') continue;
                                        if (!tagged) { el.setAttribute('data-ppt-pe', String(k)); tagged = true; }
                                        rules.push('[data-ppt-pe="' + k + '"]' + pe +
                                                   '{color:' + cs.color + ' !important;' +
                                                   '-webkit-text-fill-color:' + cs.color + ' !important;}');
                                    }
                                    if (tagged) k++;
                                });
                                const st = document.createElement('style');
                                st.id = '__pptTextHide';
                                st.textContent =
                                    '*{color:transparent !important;-webkit-text-fill-color:transparent !important;}'
                                    + rules.join('');
                                document.head.appendChild(st);
                            }
                        """)
                        _css_text_hidden = True
                    except Exception:
                        _css_text_hidden = False

                    # CRITICAL FIX: Safe text hiding using TreeWalker to prevent icons from disappearing
                    if not _css_text_hidden:
                      await page.evaluate("""
                          () => {
                              const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                              const textNodes = [];
                            
                              while (walker.nextNode()) {
                                  const parent = walker.currentNode.parentElement || walker.currentNode.parentNode;
                                  const parentTag = parent.tagName ? parent.tagName.toLowerCase() : '';
                                  if (['script', 'style', 'noscript'].includes(parentTag)) continue;
                                  if (parent.closest && parent.closest('[data-ppt-icon], .material-icons')) continue;
                                  if (walker.currentNode.nodeValue.trim().length > 0) {
                                      textNodes.push(walker.currentNode);
                                  }
                              }
                            
                              textNodes.forEach(node => {
                                  const span = document.createElement('span');
                                  span.style.setProperty('color', 'transparent', 'important');
                                  span.style.setProperty('-webkit-text-fill-color', 'transparent', 'important');
                                  // BUG FIX: without this the wrapper generates its own box. Inside
                                  // a flex/grid container that box is blockified into a separate
                                  // flex item, which reflows the parent — a chip like
                                  // <span class="chip"><i/>O&M</span> wrapped onto two lines,
                                  // dropping its icon 8.5px down and 16px across. Icon geometry is
                                  // measured AFTER this pass, so the icon was then screenshotted
                                  // and placed at the reflowed position, landing on top of its own
                                  // label. display:contents makes the wrapper generate no box at
                                  // all while still passing the transparent colour down to the
                                  // text, so layout is untouched (measured: 8.5px shift -> 0.2px).
                                  span.style.setProperty('display', 'contents', 'important');
                                  node.parentNode.insertBefore(span, node);
                                  span.appendChild(node);
                              });
                          }
                      """)
    
                    # Hide icons before capturing card screenshots (preserves layout space)
                    await page.evaluate("""
                        () => {
                            document.querySelectorAll('[data-ppt-icon]').forEach(el => {
                                el.style.setProperty('visibility', 'hidden', 'important');
                            });
                        }
                    """)
    
                    component_elements = []

                    COMPONENT_CLIP_PAD = 8
                    # Upper bound on shadow-driven padding (see data-ppt-pad).
                    MAX_SHADOW_CLIP_PAD = 96

                    # BUG FIX (production crash): this used to walk cards with one
                    # page.locator() per index and TWO round-trips each
                    # (bounding_box() then get_attribute('data-ppt-pad')). A deck whose
                    # own JavaScript is still mutating the DOM — we freeze CSS
                    # animations, but the page's timers keep running — could detach a
                    # tagged element between those two calls. bounding_box() then
                    # succeeded while get_attribute() waited the full 30s for an element
                    # that no longer existed and raised TimeoutError, which the
                    # surrounding `except (TypeError, ValueError)` did not catch, so a
                    # single vanished card killed the entire conversion:
                    #   RuntimeError: slide 3/5 failed to render:
                    #   Locator.get_attribute: Timeout 30000ms exceeded.
                    #   waiting for locator("[data-ppt-card=\"7\"]")
                    # Read every card's geometry AND pad in one evaluate instead: one
                    # atomic snapshot of the DOM, so there is no window to race, no
                    # implicit locator waiting to time out, and 2N fewer round-trips.
                    card_geo = await page.evaluate("""
                        () => Array.from(document.querySelectorAll('[data-ppt-card]')).map(el => {
                            const r = el.getBoundingClientRect();
                            return {
                                sel: el.getAttribute('data-ppt-card'),
                                x: r.x, y: r.y, w: r.width, h: r.height,
                                pad: parseFloat(el.getAttribute('data-ppt-pad')) || 0
                            };
                        })
                    """)

                    # PERF: one geometry pass for the whole slide; every capture
                    # below reuses it instead of re-measuring the document.
                    _measured = await _prepare_boxes(page)
                    LOGGER.info(
                        "Slide %s/%s: capturing %s card(s) (geometry cached for %s element(s))",
                        i + 1, slide_count, len(card_geo), _measured,
                    )
                    for card in card_geo:
                        j = card['sel']
                        cbox = {'x': card['x'], 'y': card['y'], 'width': card['w'], 'height': card['h']}

                        if cbox and cbox['width'] > 0 and cbox['height'] > 0:
                            raw_left = cbox['x']
                            raw_top = cbox['y']
                            raw_right = cbox['x'] + cbox['width']
                            raw_bottom = cbox['y'] + cbox['height']
    
                            # FIX: fixed 8px padding nearly doubles the footprint of tiny
                            # inline icon-badges (e.g. 17x17px .mini-icon elements used right
                            # before inline text in table cells), and the oversized padded
                            # image then visually overlaps the start of the adjacent text
                            # (observed: OCR-garbled "$B." / "@::::" artifacts right where a
                            # small icon meets its label). Clamp padding to a fraction of the
                            # element's own size so small elements get proportionally less.
                            pad = min(COMPONENT_CLIP_PAD, max(1, min(cbox['width'], cbox['height']) * 0.15))

                            # BUG FIX (companion to data-ppt-pad above): extend the pad to
                            # contain the card's box-shadow so it fades out inside the patch
                            # instead of being sliced into a visible rectangle. Already capped
                            # in JS by the clearance to the nearest neighbouring card; capped
                            # again here so one huge shadow can't produce a giant image.
                            # Read from the atomic snapshot above — no locator round-trip.
                            shadow_pad = card['pad']
                            if shadow_pad > pad:
                                pad = min(shadow_pad, MAX_SHADOW_CLIP_PAD)

                            left = max(0, raw_left - pad)
                            top = max(0, raw_top - pad)
                            right = min(dims['width'], raw_right + pad)
                            bottom = min(dims['height'], raw_bottom + pad)
    
                            cw = right - left
                            ch = bottom - top
    
                            if cw <= 0 or ch <= 0:
                                continue
    
                            cx = math.floor(left)
                            cy = math.floor(top)
                            cw = math.ceil(cw)
                            ch = math.ceil(ch)
    
                            if cx + cw > dims['width']:
                                cw = max(1, dims['width'] - cx)
                            if cy + ch > dims['height']:
                                ch = max(1, dims['height'] - cy)
                            
                            c_clip = {"x": cx, "y": cy, "width": cw, "height": ch}
                            c_img_path = temp_dir / f"comp_{i}_{j}.png"
                            
                            try:
                                # Isolate so omit_background actually yields alpha.
                                await _isolate(page, f'[data-ppt-card="{j}"]', pad, hide_nested=True)
                                try:
                                    await page.screenshot(path=str(c_img_path), clip=c_clip, omit_background=True)
                                finally:
                                    await _restore(page)
                                component_elements.append({
                                    'img_path': c_img_path,
                                    'x': cx, 'y': cy, 'w': cw, 'h': ch
                                })
                            except Exception:
                                pass 
    
                    # Restore icons and capture them as separate transparent components
                    await page.evaluate("""
                        () => {
                            document.querySelectorAll('[data-ppt-icon]').forEach(el => {
                                el.style.setProperty('visibility', 'visible', 'important');
                            });
                        }
                    """)
    
                    ICON_CLIP_PAD = 4
                    # Same atomic-snapshot treatment as the card loop above: one
                    # evaluate for every icon's geometry and pad, so a DOM mutation
                    # mid-loop cannot strand a locator and time out the conversion.
                    icon_geo = await page.evaluate("""
                        () => Array.from(document.querySelectorAll('[data-ppt-icon]')).map(el => {
                            const r = el.getBoundingClientRect();
                            return {
                                sel: el.getAttribute('data-ppt-icon'),
                                x: r.x, y: r.y, w: r.width, h: r.height,
                                pad: parseFloat(el.getAttribute('data-ppt-pad')) || 0
                            };
                        })
                    """)

                    LOGGER.info(
                        "Slide %s/%s: capturing %s icon(s)", i + 1, slide_count, len(icon_geo)
                    )
                    for icon in icon_geo:
                        k = icon['sel']
                        ibox = {'x': icon['x'], 'y': icon['y'], 'width': icon['w'], 'height': icon['h']}

                        if ibox and ibox['width'] > 0 and ibox['height'] > 0:
                            # FIX: same proportional-padding fix as card clipping above —
                            # tiny glyph-sized icons (e.g. 8px font-awesome icons inside a
                            # .mini-icon badge) shouldn't get a flat 4px pad on all sides.
                            ipad = min(ICON_CLIP_PAD, max(1, min(ibox['width'], ibox['height']) * 0.2))

                            # BUG FIX: honour the shadow-aware pad here as well, so a shadowed
                            # icon container (e.g. the 54px .dp-logo-slot carrying a 20px
                            # shadow) doesn't get its shadow sliced into a grey rectangle.
                            # Read from the atomic snapshot above — no locator round-trip.
                            icon_shadow_pad = icon['pad']
                            if icon_shadow_pad > ipad:
                                ipad = min(icon_shadow_pad, MAX_SHADOW_CLIP_PAD)
                            left = max(0, ibox['x'] - ipad)
                            top = max(0, ibox['y'] - ipad)
                            right = min(dims['width'], ibox['x'] + ibox['width'] + ipad)
                            bottom = min(dims['height'], ibox['y'] + ibox['height'] + ipad)
    
                            iw = right - left
                            ih = bottom - top
                            if iw <= 0 or ih <= 0:
                                continue
    
                            ix = math.floor(left)
                            iy = math.floor(top)
                            iw = math.ceil(iw)
                            ih = math.ceil(ih)
    
                            if ix + iw > dims['width']:
                                iw = max(1, dims['width'] - ix)
                            if iy + ih > dims['height']:
                                ih = max(1, dims['height'] - iy)
    
                            i_clip = {"x": ix, "y": iy, "width": iw, "height": ih}
                            i_img_path = temp_dir / f"icon_{i}_{k}.png"
    
                            try:
                                # Isolate so omit_background actually yields alpha.
                                await _isolate(page, f'[data-ppt-icon="{k}"]', ipad)
                                try:
                                    await page.screenshot(path=str(i_img_path), clip=i_clip, omit_background=True)
                                finally:
                                    await _restore(page)
                                component_elements.append({
                                    'img_path': i_img_path,
                                    'x': ix, 'y': iy, 'w': iw, 'h': ih
                                })
                            except Exception:
                                pass
    
                    await page.evaluate("""
                        () => {
                            document.querySelectorAll('[data-ppt-card]').forEach(el => {
                                el.style.setProperty('visibility', 'hidden', 'important');
                            });
                            // BUG FIX: icons were restored with an inline
                            // "visibility: visible !important" for their own capture
                            // pass and never re-hidden. Since an explicit
                            // visibility:visible on a descendant overrides the hidden
                            // ancestor card, every icon was ALSO baked into the
                            // "clean" background screenshot — leaving a ghost copy
                            // behind whenever the icon shape is moved in PowerPoint,
                            // and visibly doubling icons on border-only/transparent
                            // cards. Re-hide them before the background capture.
                            document.querySelectorAll('[data-ppt-icon]').forEach(el => {
                                el.style.setProperty('visibility', 'hidden', 'important');
                            });
                        }
                    """)
    
                    bg_img_path = temp_dir / f"bg_slide_{i+1}.png"
                    await page.screenshot(path=str(bg_img_path), clip=clip)
    
                    slides_for_output.append({
                        'bg_img_path': bg_img_path,
                        'width': bg_w, 'height': bg_h,
                        'elements': text_elements, 
                        'components': component_elements,
                        'clip_x': bg_x, 'clip_y': bg_y
                    })
                    slides_for_output[-1]["_slide_index"] = i

            await asyncio.gather(*(render_slide(i) for i in range(slide_count)))
            slides_for_output.sort(key=lambda item: item.pop("_slide_index"))
            LOGGER.info(
                "All %s slide(s) rendered in %.1fs; closing browser",
                slide_count, time.perf_counter() - _deck_t0,
            )

            await context.close()
            await browser.close()

        build_layered_pptx(slides_for_output, output_file)

async def generate_pptx(html_content: str, source_filename: str | None = None, original_filename: str | None = None) -> str:
    """Generate PPTX using original uploaded file name when provided."""
    input_name = source_filename or original_filename
    file_name = safe_pptx_filename(input_name)
    output_path = unique_output_path(file_name)
    started = time.perf_counter()
    # Serialise whole conversions (see _CONVERSION_SLOTS): a retry landing on
    # top of an in-flight run used to double the live Chromium pages and
    # OOM-kill the instance, losing BOTH conversions.
    if _CONVERSION_SLOTS.locked():
        LOGGER.info(
            "Queued PPTX conversion: %s (another conversion is in flight; "
            "limit=%s, set HTML_CONVERTER_MAX_CONCURRENT to raise)",
            input_name or "unnamed HTML", _MAX_CONCURRENT,
        )
    async with _CONVERSION_SLOTS:
        waited = time.perf_counter() - started
        LOGGER.info(
            "Starting PPTX conversion: %s%s",
            input_name or "unnamed HTML",
            f" (waited {waited:.1f}s in queue)" if waited > 1 else "",
        )
        try:
            await render_deck_to_file(html_content, str(output_path))
        except Exception as exc:
            LOGGER.error(
                "PPTX conversion FAILED after %.1fs: %s: %s",
                time.perf_counter() - started, type(exc).__name__, exc,
            )
            raise
    LOGGER.info(
        "Completed PPTX in %.1f seconds: %s", time.perf_counter() - started, output_path
    )
    return str(output_path)
