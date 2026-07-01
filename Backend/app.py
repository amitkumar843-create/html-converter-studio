import os
import sys
import asyncio
import traceback
from pathlib import Path
from urllib.parse import quote
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# IMPORTANT for Playwright on Windows:
# Playwright launches Chromium as a subprocess. Windows requires Proactor event loop.
# Keep this before converter imports.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from converter_pdf import generate_pdf
from converter_pptx import generate_pptx

app = FastAPI(title="Unified HTML to PDF & PPTX Converter")

# ==========================================
# CORS CONFIGURATION
# ==========================================
# Local frontend URLs are always allowed.
# For Render deployment, set environment variable CORS_ORIGINS like:
# CORS_ORIGINS=https://your-frontend-name.onrender.com
# Multiple origins can be comma-separated.
DEFAULT_CORS_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

render_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=DEFAULT_CORS_ORIGINS + render_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

UPLOAD_DIR = OUTPUT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


class RequestModel(BaseModel):
    html: str
    filename: Optional[str] = None


def build_download_url(request: Request, file_path: str) -> str:
    """Builds a download URL that works locally and on Render."""
    return str(request.base_url).rstrip("/") + f"/download?path={quote(str(file_path))}"


async def read_uploaded_html(file: UploadFile) -> str:
    """Validates and reads uploaded .html/.htm file content."""
    if not file.filename or not file.filename.lower().endswith((".html", ".htm")):
        raise HTTPException(status_code=400, detail="Please upload a .html or .htm file only.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise HTTPException(status_code=400, detail="Unable to decode uploaded HTML file.")


def is_supported_slide_html(html: str) -> bool:
    """Restrict hosted converter to slide-based HTML only."""
    html_lower = (html or "").lower()
    markers = [
        'class="slide"',
        "class='slide'",
        'class="slide ',
        "class='slide ",
        'class="slide-shell"',
        "class='slide-shell'",
        'class="slide-shell ',
        "class='slide-shell ",
        'class="deck"',
        "class='deck'",
        "data-slide=",
    ]
    return any(marker in html_lower for marker in markers)


def _safe_stem(original_filename: Optional[str]) -> str:
    safe_stem = Path(original_filename or "uploaded").stem
    safe_stem = "".join(c for c in safe_stem if c.isalnum() or c in ("-", "_"))[:80]
    return safe_stem or "uploaded"


def save_uploaded_html_to_temp(html: str, original_filename: Optional[str]) -> str:
    """
    Saves raw HTML content to a temporary file and returns the file path.

    This prevents Render/Linux from treating a long raw HTML string as a file path.
    PDF conversion uses this path-based flow.
    """
    safe_stem = _safe_stem(original_filename)
    temp_path = UPLOAD_DIR / f"{safe_stem}.html"

    counter = 1
    while temp_path.exists():
        temp_path = UPLOAD_DIR / f"{safe_stem}_{counter}.html"
        counter += 1

    temp_path.write_text(html, encoding="utf-8")
    return str(temp_path)


def normalize_converter_input(html_or_path: str, original_filename: Optional[str]) -> str:
    """
    Keeps valid HTML file paths unchanged.
    Saves raw HTML content to temp file and returns the temp file path.
    Used for PDF endpoint to avoid Render file-name-too-long failures.
    """
    value = (html_or_path or "").strip()

    try:
        possible_path = Path(value)
        if possible_path.exists() and possible_path.suffix.lower() in {".html", ".htm"}:
            return str(possible_path)
    except OSError:
        pass

    return save_uploaded_html_to_temp(value, original_filename)


def enforce_slide_html_only(html: str):
    if not is_supported_slide_html(html):
        raise HTTPException(
            status_code=400,
            detail=(
                "This converter supports slide-based HTML only. "
                "Please upload an HTML file with .slide, .slide-shell, or deck slide structure."
            ),
        )


@app.get("/")
def root():
    return {
        "status": "running",
        "service": "Unified HTML to PDF & PPTX Converter",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


# ==========================================
# PDF ENDPOINTS
# ==========================================
@app.post("/convert/pdf")
async def convert_pdf(req: RequestModel, request: Request):
    try:
        enforce_slide_html_only(req.html)
        converter_input = normalize_converter_input(req.html, req.filename)
        file_path = await generate_pdf(converter_input, original_filename=req.filename)
        return {
            "status": "success",
            "pdf_file": file_path,
            "output_file_name": Path(file_path).name,
            "download_url": build_download_url(request, file_path),
        }
    except HTTPException:
        raise
    except Exception as e:
        print("ERROR in /convert/pdf:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or repr(e))


@app.post("/convert/pdf/file")
async def convert_html_file_to_pdf(request: Request, file: UploadFile = File(...)):
    try:
        html = await read_uploaded_html(file)
        enforce_slide_html_only(html)

        # PDF converter receives a temp HTML file path to avoid Render path-length issue.
        html_file_path = save_uploaded_html_to_temp(html, file.filename)
        file_path = await generate_pdf(html_file_path, original_filename=file.filename)
        return {
            "status": "success",
            "pdf_file": file_path,
            "output_file_name": Path(file_path).name,
            "download_url": build_download_url(request, file_path),
        }
    except HTTPException:
        raise
    except Exception as e:
        print("ERROR in /convert/pdf/file:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or repr(e))


# ==========================================
# PPTX ENDPOINTS
# ==========================================
@app.post("/convert/pptx")
async def convert_pptx(req: RequestModel, request: Request):
    try:
        enforce_slide_html_only(req.html)

        # PPTX converter keeps original behavior: raw HTML content is passed through.
        file_path = await generate_pptx(req.html, original_filename=req.filename)
        return {
            "status": "success",
            "pptx_file": file_path,
            "output_file_name": Path(file_path).name,
            "download_url": build_download_url(request, file_path),
        }
    except HTTPException:
        raise
    except Exception as e:
        print("ERROR in /convert/pptx:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or repr(e))


@app.post("/convert/pptx/file")
async def convert_html_file_to_pptx(request: Request, file: UploadFile = File(...)):
    try:
        html = await read_uploaded_html(file)
        enforce_slide_html_only(html)

        # IMPORTANT: keep PPTX conversion raw-HTML based.
        # Passing temp file path to converter_pptx can produce blank PPTX output in Render.
        file_path = await generate_pptx(html, original_filename=file.filename)
        return {
            "status": "success",
            "pptx_file": file_path,
            "output_file_name": Path(file_path).name,
            "download_url": build_download_url(request, file_path),
        }
    except HTTPException:
        raise
    except Exception as e:
        print("ERROR in /convert/pptx/file:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or repr(e))


# ==========================================
# DOWNLOAD ENDPOINT
# ==========================================
@app.get("/download")
def download_file(path: str):
    file_path = Path(path).resolve()

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")

    # Only allow downloading generated output files from backend/output.
    try:
        file_path.relative_to(OUTPUT_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied for this file path.")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )
