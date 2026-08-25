import asyncio
import os
import uuid
import tempfile
import math
import re
import time
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from reportlab.pdfgen import canvas
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).parent

logging.basicConfig(level=getattr(logging, os.getenv("HTML_CONVERTER_LOG_LEVEL", "INFO").upper(), logging.INFO), format="%(asctime)s | %(levelname)s | %(message)s")
LOGGER = logging.getLogger("html_pdf_converter")

def _env_int(name, default, minimum=1, maximum=None):
    try: value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError): value = default
    value = max(minimum, value)
    return min(value, maximum) if maximum is not None else value

def _launch_kwargs():
    args = ["--enable-gpu", "--ignore-gpu-blocklist", "--enable-accelerated-2d-canvas", "--enable-zero-copy", "--enable-native-gpu-memory-buffers"]
    if os.getenv("HTML_CONVERTER_DISABLE_SOFTWARE_RASTERIZER", "0") == "1": args.append("--disable-software-rasterizer")
    angle = os.getenv("HTML_CONVERTER_ANGLE", "")
    if angle: args.append(f"--use-angle={angle}")
    kwargs = {"headless": True, "args": args}
    executable = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if executable: kwargs["executable_path"] = executable
    return kwargs

def _workers(slide_count):
    cpu = os.cpu_count() or 1
    workers = _env_int("HTML_CONVERTER_WORKERS", min(cpu, 4), 1, max(1, slide_count))
    LOGGER.info("CPU cores=%s | slides=%s | parallel workers=%s", cpu, slide_count, workers)
    return workers

def _scale():
    try: return max(1.0, min(3.0, float(os.getenv("HTML_CONVERTER_SCALE", "2"))))
    except ValueError: return 2.0
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def safe_pdf_filename(source_filename: str | None = None) -> str:
    """Create PDF output name from the original uploaded HTML file name."""
    if not source_filename:
        return f"{uuid.uuid4().hex}.pdf"
    stem = Path(str(source_filename)).stem.strip()
    if not stem:
        return f"{uuid.uuid4().hex}.pdf"
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', stem)
    stem = re.sub(r'\s+', ' ', stem).strip().rstrip('.')
    return f"{stem}.pdf" if stem else f"{uuid.uuid4().hex}.pdf"


def unique_output_path(file_name: str) -> Path:
    output_path = OUTPUT_DIR / file_name
    if not output_path.exists():
        return output_path
    stem, suffix = Path(file_name).stem, Path(file_name).suffix or ".pdf"
    counter = 1
    while True:
        candidate = OUTPUT_DIR / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _soup(html_content: str):
    return BeautifulSoup(html_content, "html.parser")


def is_slide_deck(html_content: str) -> bool:
    soup = _soup(html_content)
    return len(soup.select(".slide")) > 0 or len(soup.select(".slide-shell")) > 0


def count_slides(html_content: str) -> int:
    soup = _soup(html_content)
    count = len(soup.select(".slide"))
    if count == 0:
        count = len(soup.select(".slide-shell"))
    return count if count > 0 else 1


def is_native_stacked_deck(html_content: str) -> bool:
    """Detect stacked .deck > .slide HTML such as Jammu Frontier.
    These slides already have native fixed size and should not be forced to 1280x720.
    """
    soup = _soup(html_content)
    # Treat both .deck > .slide and #deck > .slide as native fixed-canvas decks.
    # Exclude #presentation-container decks because those rely on the dedicated
    # 1280x720 export CSS and force_final_state path.
    has_native_slides = len(soup.select(".deck > .slide, #deck > .slide")) > 0
    return has_native_slides and len(soup.select("#presentation-container, .slide-shell")) == 0


def px_to_pt(px: float) -> float:
    return px * 72.0 / 96.0


def build_pdf_from_images(slides, output_file):
    c = None
    for idx, slide_data in enumerate(slides):
        page_width_pt = px_to_pt(slide_data["width"])
        page_height_pt = px_to_pt(slide_data["height"])
        if idx == 0:
            c = canvas.Canvas(output_file, pagesize=(page_width_pt, page_height_pt))
        else:
            c.setPageSize((page_width_pt, page_height_pt))
        c.drawImage(
            str(slide_data["img_path"]),
            0,
            0,
            width=page_width_pt,
            height=page_height_pt,
            preserveAspectRatio=False,
            mask="auto",
        )
        c.showPage()
    if c:
        c.save()


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


async def get_html_resolution(browser, html_content: str):
    page = await browser.new_page(viewport={"width": 1280, "height": 720})
    await page.set_content(html_content, wait_until="load", timeout=60000)
    try:
        await page.evaluate("document.fonts && document.fonts.ready")
        await _load_icon_fonts(page)
    except Exception:
        pass
    dims = await page.evaluate(
        """
        () => {
            const preferred =
                document.querySelector('#presentation-container') ||
                document.querySelector('#deck') ||
                document.querySelector('.slide.active') ||
                document.querySelector('.slide') ||
                document.querySelector('.slide-shell');
            if (preferred) {
                const w = preferred.offsetWidth || parseFloat(getComputedStyle(preferred).width) || 1280;
                const h = preferred.offsetHeight || parseFloat(getComputedStyle(preferred).height) || 720;
                return { width: Math.ceil(w), height: Math.ceil(h) };
            }
            const scrollW = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth, document.documentElement.offsetWidth, 1280);
            const scrollH = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight, document.documentElement.offsetHeight, 720);
            return { width: Math.ceil(scrollW), height: Math.ceil(scrollH) };
        }
        """
    )
    await page.close()
    return dims


def get_export_css(width=1280, height=720):
    return f"""
* {{
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
}}
html, body {{
    margin: 0 !important;
    padding: 0 !important;
    width: {width}px !important;
    height: {height}px !important;
    min-width: {width}px !important;
    min-height: {height}px !important;
    max-width: {width}px !important;
    max-height: {height}px !important;
    overflow: hidden !important;
    background: #ffffff !important;
    display: block !important;
}}
#presentation-container, #deck {{
    position: fixed !important;
    left: 0 !important;
    top: 0 !important;
    right: auto !important;
    bottom: auto !important;
    width: {width}px !important;
    height: {height}px !important;
    transform: none !important;
    transform-origin: top left !important;
    margin: 0 !important;
    padding: 0 !important;
    box-shadow: none !important;
    overflow: hidden !important;
}}
/* Navigation panels are intentionally not hidden here.
   Keep source HTML/CSS responsible for exact top/bottom nav alignment. */
*, *::before, *::after {{
    transition: none !important;
    transition-duration: 0s !important;
    transition-delay: 0s !important;
    animation-delay: 0s !important;
    animation-duration: 0s !important;
    animation-iteration-count: 1 !important;
}}
.slide, .slide-shell {{
    position: absolute !important;
    left: 0 !important;
    top: 0 !important;
    width: {width}px !important;
    height: {height}px !important;
    opacity: 0 !important;
    visibility: hidden !important;
    pointer-events: none !important;
    overflow: hidden !important;
}}
.slide.export-active, .slide-shell.export-active {{
    display: flex !important;
    opacity: 1 !important;
    visibility: visible !important;
    pointer-events: auto !important;
}}
.slide.export-active .animate,
.slide.export-active .sel-anim,
.slide.export-active .s2-col-card,
.slide.export-active .s2-col-icon,
.slide.export-active .s2-chart-fill,
.slide.export-active .s2-big-num,
.slide.export-active .timeline-table tbody tr,
.slide.export-active .thankyou-mini-wheel,
.slide.export-active .opt5-wheel {{
    opacity: 1 !important;
    transform: none !important;
    animation: none !important;
}}
.slide.export-active .thankyou-final-card {{
    isolation: isolate !important;
}}
.slide.export-active .thankyou-mini-wheel {{
    z-index: 0 !important;
    pointer-events: none !important;
}}
.slide.export-active .thankyou-final-card .cover-kicker,
.slide.export-active .thankyou-final-card .thankyou-title,
.slide.export-active .thankyou-final-card .cover-subtitle {{
    position: relative !important;
    z-index: 2 !important;
}}
"""


async def force_final_state(page, slide_index: int):
    await page.evaluate(
        """
        (idx) => {
            // Do not depend on deck-specific goToSlide indexing; some decks are 0-based, others are 1-based.
            // Direct class/style control below is the authoritative export state.
            const container = document.querySelector('#presentation-container') || document.querySelector('#deck') || document.body;
            if (container) {
                container.style.setProperty('position', 'fixed', 'important');
                container.style.setProperty('left', '0', 'important');
                container.style.setProperty('top', '0', 'important');
                container.style.setProperty('width', '1280px', 'important');
                container.style.setProperty('height', '720px', 'important');
                container.style.setProperty('transform', 'none', 'important');
                container.style.setProperty('transform-origin', 'top left', 'important');
                container.style.setProperty('box-shadow', 'none', 'important');
                container.style.setProperty('overflow', 'hidden', 'important');
            }

            let slides = [...document.querySelectorAll('.slide')];
            if (slides.length === 0) slides = [...document.querySelectorAll('.slide-shell')];

            slides.forEach((s, j) => {
                s.classList.remove('active', 'export-active');
                s.style.setProperty('position', 'absolute', 'important');
                s.style.setProperty('left', '0', 'important');
                s.style.setProperty('top', '0', 'important');
                s.style.setProperty('width', '1280px', 'important');
                s.style.setProperty('height', '720px', 'important');
                s.style.setProperty('overflow', 'hidden', 'important');
                if (j === idx) {
                    s.classList.add('active', 'export-active');
                    s.style.setProperty('display', 'flex', 'important');
                    s.style.setProperty('visibility', 'visible', 'important');
                    s.style.setProperty('opacity', '1', 'important');
                    s.style.setProperty('pointer-events', 'auto', 'important');
                    s.style.setProperty('animation', 'none', 'important');
                    s.style.setProperty('transition', 'none', 'important');
                    s.style.setProperty('transform', 'none', 'important');
                } else {
                    s.style.setProperty('display', 'none', 'important');
                    s.style.setProperty('visibility', 'hidden', 'important');
                    s.style.setProperty('opacity', '0', 'important');
                    s.style.setProperty('pointer-events', 'none', 'important');
                }
            });

            // Sync navigation state only. Do not override nav position/display/alignment.
            const navButtons = [...document.querySelectorAll('.nav button')];
            navButtons.forEach((button, j) => {
                button.classList.remove('active-btn');
                if (j === idx) button.classList.add('active-btn');
            });

            const navDots = [...document.querySelectorAll('.nav-dots .dot, .dot')];
            navDots.forEach((dot, j) => {
                dot.classList.remove('active');
                if (j === idx) dot.classList.add('active');
            });

            const counter = document.querySelector('#counter, .counter');
            if (counter && slides.length > 0) {
                counter.textContent = String(idx + 1) + ' / ' + String(slides.length);
            }

            const progressBar = document.querySelector('#progressBar, .progress-bar');
            if (progressBar && slides.length > 0) {
                progressBar.style.width = (((idx + 1) / slides.length) * 100) + '%';
            }

            const current = slides.length > 0 ? slides[idx] : document.body;
            if (!current) return;

            current.querySelectorAll('*').forEach(el => {
                const cs = getComputedStyle(el);
                const hadAnimation = cs.animationName && cs.animationName !== 'none';
                const wasTransparent = parseFloat(cs.opacity || '1') <= 0.01;
                el.style.setProperty('transition', 'none', 'important');
                el.style.setProperty('animation', 'none', 'important');
                if (cs.display === 'none') el.style.setProperty('display', '', 'important');
                if (cs.visibility === 'hidden') el.style.setProperty('visibility', 'visible', 'important');
                if (hadAnimation || wasTransparent || el.classList.contains('animate') || el.classList.contains('sel-anim')) {
                    el.style.setProperty('opacity', '1', 'important');
                    el.style.setProperty('transform', 'none', 'important');
                }
            });
        }
        """,
        slide_index,
    )


async def render_pptx_style_deck_to_pdf(html_content: str, output_file: str):
    """
    PDF capture path mirroring the working PPTX converter logic:
    - keep the source slide dimensions/layout
    - select one active slide at a time
    - capture active slide bounding box
    This is scoped to native stacked .deck > .slide HTML only.
    """
    slide_count = count_slides(html_content)
    slides_for_output = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        async with async_playwright() as p:
            browser = await p.chromium.launch(**_launch_kwargs())
            dims = await get_html_resolution(browser, html_content)
            context = await browser.new_context(
                viewport={"width": dims["width"], "height": dims["height"]},
                device_scale_factor=_scale(),
            )

            max_parallel_slides = _workers(slide_count)
            semaphore = asyncio.Semaphore(max_parallel_slides)

            async def render_slide(i):
                async with semaphore:
                    page = await context.new_page()
                    await page.set_content(html_content, wait_until="load", timeout=60000)
                    # Native fixed-canvas decks may apply responsive scale transforms.
                    # Capture at their authored dimensions instead of the browser preview scale.
                    await page.evaluate("""
                        () => {
                            const deck = document.querySelector('#deck') || document.querySelector('.deck');
                            if (deck) {
                                deck.style.setProperty('transform', 'none', 'important');
                                deck.style.setProperty('transform-origin', 'top left', 'important');
                                deck.style.setProperty('left', '0', 'important');
                                deck.style.setProperty('top', '0', 'important');
                            }
                        }
                    """)
                    try:
                        await page.evaluate("document.fonts && document.fonts.ready")
                    except Exception:
                        pass
                    await page.wait_for_timeout(300)
    
                    # Same export stabilization approach as PPTX, but no layering/text extraction.
                    await page.add_style_tag(content="""
                        * {
                            -webkit-print-color-adjust: exact !important;
                            print-color-adjust: exact !important;
                            background-attachment: scroll !important;
                        }
                        .progress-wrap { display: none !important; }
                        *, *::before, *::after {
                            transition-duration: 0s !important;
                            transition-delay: 0s !important;
                            animation-duration: 0s !important;
                            animation-delay: 0s !important;
                            animation-fill-mode: forwards !important;
                        }
                    """)
    
                    # This mirrors converter_pptx.py force_final_state behavior for stacked slides.
                    await page.evaluate("""
                        (idx) => {
                            let slides = [...document.querySelectorAll('.slide')];
                            if (slides.length === 0) slides = [...document.querySelectorAll('.slide-shell')];
                            if (slides.length > 0) {
                                slides.forEach((s, j) => {
                                    if (j === idx) {
                                        s.classList.add('active');
                                        s.style.display = '';
                                        s.style.visibility = 'visible';
                                        s.style.opacity = '1';
                                        s.style.pointerEvents = 'all';
                                        s.scrollIntoView({block:'start', inline:'nearest'});
                                    } else {
                                        s.classList.remove('active');
                                        s.style.display = 'none';
                                        s.style.visibility = 'hidden';
                                        s.style.opacity = '0';
                                        s.style.pointerEvents = 'none';
                                    }
                                });
                            }
                            const current = slides.length > 0 ? slides[idx] : document.body;
                            if (!current) return;
                            current.querySelectorAll('*').forEach(el => {
                                const cs = getComputedStyle(el);
                                if (cs.display === 'none') el.style.display = '';
                                if (cs.visibility === 'hidden') el.style.visibility = 'visible';
                                if (parseFloat(cs.opacity || '1') === 0) el.style.opacity = '1';
                                el.style.transition = 'none';
                                el.style.animation = 'none';
                            });
                        }
                    """, i)
    
                    await page.wait_for_timeout(500)
                    box = await page.evaluate("""
                        () => {
                            const active = document.querySelector('.slide.active') ||
                                           document.querySelector('.slide-shell.active') ||
                                           document.querySelector('.slide') ||
                                           document.querySelector('.slide-shell') ||
                                           document.body;
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
    
                    img_path = temp_dir / f"pptx_style_slide_{i + 1}.png"
                    await page.screenshot(
                        path=str(img_path),
                        clip={"x": bg_x, "y": bg_y, "width": bg_w, "height": bg_h},
                        timeout=60000,
                    )
                    slides_for_output.append({"img_path": img_path, "width": bg_w, "height": bg_h, "_slide_index": i})
                    await page.close()

            await asyncio.gather(*(render_slide(i) for i in range(slide_count)))
            slides_for_output.sort(key=lambda item: item.pop("_slide_index"))

            await context.close()
            await browser.close()

        build_pdf_from_images(slides_for_output, output_file)


async def render_framed_deck_to_pdf(html_content: str, output_file: str):
    """Render responsive #viewport > #frame > #deck presentations exactly as previewed."""
    slide_count = count_slides(html_content)
    slides_for_output = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        async with async_playwright() as p:
            browser = await p.chromium.launch(**_launch_kwargs())
            context = await browser.new_context(
                viewport={"width": 1620, "height": 920},
                device_scale_factor=_scale(),
            )
            semaphore = asyncio.Semaphore(_workers(slide_count))

            async def render_slide(i):
                async with semaphore:
                    page = await context.new_page()
                    await page.set_content(html_content, wait_until="load", timeout=60000)
                    try:
                        await page.evaluate("document.fonts && document.fonts.ready")
                    except Exception:
                        pass
                    await page.add_style_tag(content="""
                        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
                        *, *::before, *::after { animation: none !important; transition: none !important; }
                    """)
                    await page.evaluate("""
                        (idx) => {
                            const slides = [...document.querySelectorAll('#deck > .slide')];
                            slides.forEach((slide, j) => {
                                slide.classList.toggle('active', j === idx);
                                slide.style.visibility = j === idx ? 'visible' : 'hidden';
                                slide.style.opacity = j === idx ? '1' : '0';
                                slide.style.transform = j === idx ? 'none' : '';
                            });
                            const cur = document.querySelector('#cur');
                            if (cur) cur.textContent = String(idx + 1);
                            const progress = document.querySelector('#progress');
                            if (progress) progress.style.width = (((idx + 1) / slides.length) * 100) + '%';
                        }
                    """, i)
                    await page.wait_for_timeout(250)
                    frame = page.locator('#frame')
                    box = await frame.bounding_box()
                    if not box:
                        raise RuntimeError('Responsive presentation frame was not found')
                    img_path = temp_dir / f"framed_slide_{i + 1}.png"
                    await frame.screenshot(path=str(img_path), timeout=60000)
                    slides_for_output.append({
                        "img_path": img_path,
                        "width": int(round(box["width"])),
                        "height": int(round(box["height"])),
                        "_slide_index": i,
                    })
                    await page.close()

            await asyncio.gather(*(render_slide(i) for i in range(slide_count)))
            slides_for_output.sort(key=lambda item: item.pop("_slide_index"))
            await context.close()
            await browser.close()
        build_pdf_from_images(slides_for_output, output_file)

async def render_deck_to_pdf(html_content: str, output_file: str):
    soup = _soup(html_content)
    if soup.select_one('#viewport #frame #deck > .slide'):
        await render_framed_deck_to_pdf(html_content, output_file)
        return
    # Scoped fix: for native stacked .deck > .slide HTML, use the same active-slide
    # bounding-box capture logic as the working PPTX converter.
    if is_native_stacked_deck(html_content):
        await render_pptx_style_deck_to_pdf(html_content, output_file)
        return

    slide_count = count_slides(html_content)
    slides_for_output = []

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        async with async_playwright() as p:
            browser = await p.chromium.launch(**_launch_kwargs())
            dims = await get_html_resolution(browser, html_content)
            # Force minimum 1280x720 and use detected size if larger.
            width = max(1280, int(dims.get("width", 1280)))
            height = max(720, int(dims.get("height", 720)))
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=_scale(),
            )

            max_parallel_slides = _workers(slide_count)
            semaphore = asyncio.Semaphore(max_parallel_slides)

            async def render_slide(i):
                async with semaphore:
                    page = await context.new_page()
                    await page.set_content(html_content, wait_until="load", timeout=60000)
                    try:
                        await page.evaluate("document.fonts && document.fonts.ready")
                    except Exception:
                        pass
                    await page.wait_for_timeout(300)
                    await page.add_style_tag(content=get_export_css(width, height))
                    await force_final_state(page, i)
                    await page.wait_for_timeout(300)
    
                    # Export the fixed canvas dimensions.
                    img_path = temp_dir / f"slide_{i + 1}.png"
                    await page.screenshot(
                        path=str(img_path),
                        clip={"x": 0, "y": 0, "width": width, "height": height},
                        timeout=60000,
                    )
                    slides_for_output.append({"img_path": img_path, "width": width, "height": height, "_slide_index": i})
                    await page.close()

            await asyncio.gather(*(render_slide(i) for i in range(slide_count)))
            slides_for_output.sort(key=lambda item: item.pop("_slide_index"))

            await context.close()
            await browser.close()

        build_pdf_from_images(slides_for_output, output_file)


async def render_regular_html_to_pdf(html_content: str, output_file: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(**_launch_kwargs())
        dims = await get_html_resolution(browser, html_content)
        page = await browser.new_page(viewport={"width": dims["width"], "height": dims["height"]})
        page.set_default_timeout(60000)
        await page.set_content(html_content, wait_until="load", timeout=60000)
        try:
            await page.evaluate("document.fonts && document.fonts.ready")
            await _load_icon_fonts(page)
        except Exception:
            pass
        await page.add_style_tag(content="""
            * {
                transition: none !important;
                animation: none !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
        """)
        await page.wait_for_timeout(500)
        await page.pdf(path=output_file, print_background=True, prefer_css_page_size=True)
        await browser.close()


async def generate_pdf(
    html_content: str,
    source_filename: str | None = None,
    original_filename: str | None = None,
) -> str:
    """Generate PDF using original uploaded file name when provided."""
    input_name = source_filename or original_filename

    possible_path = Path(str(html_content))
    if possible_path.exists() and possible_path.suffix.lower() in {".html", ".htm"}:
        if not input_name:
            input_name = possible_path.name
        html_content = possible_path.read_text(encoding="utf-8")

    file_name = safe_pdf_filename(input_name)
    output_path = unique_output_path(file_name)

    started = time.perf_counter()
    LOGGER.info("Starting PDF conversion: %s", input_name or "unnamed HTML")
    if is_slide_deck(html_content):
        LOGGER.info("Detected slide deck with %s slide(s)", count_slides(html_content))
        await render_deck_to_pdf(html_content, str(output_path))
    else:
        LOGGER.info("Detected regular HTML")
        await render_regular_html_to_pdf(html_content, str(output_path))
    LOGGER.info("Completed PDF in %.2f seconds: %s", time.perf_counter() - started, output_path)
    return str(output_path)
