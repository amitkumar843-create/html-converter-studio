import os
import sys
import asyncio
import traceback
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
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

# CORS: defaults to local dev origins; set CORS_ORIGINS (comma-separated)
# in production, e.g. CORS_ORIGINS=https://your-frontend.onrender.com
_default_origins = "http://127.0.0.1:5173,http://localhost:5173"
allow_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", _default_origins).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class RequestModel(BaseModel):
    html: str
    filename: Optional[str] = None


def download_url(base_url: str, file_path: str) -> str:
    return f"{str(base_url).rstrip('/')}/download?path={quote(str(file_path))}"


@app.get("/")
def root(request: Request):
    return {
        "status": "running",
        "service": "Unified HTML to PDF & PPTX Converter",
        "docs": f"{str(request.base_url).rstrip('/')}/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


# ==========================================
# SAMPLES ENDPOINTS
# ==========================================
SAMPLES_DIR = BASE_DIR / "HTML Sample Files"


@app.get("/samples")
def list_samples():
    if not SAMPLES_DIR.exists():
        return {"samples": []}

    samples = []
    for p in sorted(SAMPLES_DIR.glob("*.htm*"), key=lambda x: x.name.lower()):
        name = p.name
        try:
            stat = p.stat()
            size_bytes = stat.st_size
            mtime = stat.st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime("%b %d, %Y")
        except Exception:
            size_bytes = 0
            mtime = 0
            date_str = "Recent"

        # Automatic category classification
        category = "General Presentations"
        name_lower = name.lower()
        if "ey" in name_lower or "opportunity" in name_lower:
            category = "EY Corporate"
        elif "delhi" in name_lower or "safecity" in name_lower or "safe city" in name_lower:
            category = "Delhi Safe City"
        elif "meity" in name_lower:
            category = "Meity Presentations"
        elif any(k in name_lower for k in ["dashboard", "dpsc", "nms", "psu"]):
            category = "Dashboards & Ops"
        elif any(k in name_lower for k in ["architeture", "architecture", "gnida", "iccc", "surveillance"]):
            category = "Architecture & Systems"
        elif "gemini" in name_lower or "claude" in name_lower or "animated" in name_lower:
            category = "AI & Animated Decks"

        clean_title = (
            p.stem.replace("_", " ")
            .replace("-", " ")
            .replace("  ", " ")
            .strip()
        )

        samples.append({
            "id": p.name,
            "filename": p.name,
            "title": clean_title,
            "size": size_bytes,
            "category": category,
            "modified_at": mtime,
            "date": date_str,
        })

    return {"samples": samples}


@app.get("/samples/{filename:path}")
def get_sample_content(filename: str):
    target = SAMPLES_DIR / filename
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Sample file not found.")

    try:
        content = target.read_text(encoding="utf-8", errors="ignore")
        return {
            "filename": target.name,
            "html": content,
            "size": target.stat().st_size,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")

# PDF ENDPOINTS
# ==========================================
@app.post("/convert/pdf")
async def convert_pdf(req: RequestModel, request: Request):
    try:
        file_path = await generate_pdf(req.html, original_filename=req.filename)
        return {
            "status": "success",
            "pdf_file": file_path,
            "output_file_name": Path(file_path).name,
            "download_url": download_url(request.base_url, file_path),
        }
    except Exception as e:
        print("ERROR in /convert/pdf:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or repr(e))


@app.post("/convert/pdf/file")
async def convert_html_file_to_pdf(request: Request, file: UploadFile = File(...)):
    try:
        if not file.filename or not file.filename.lower().endswith((".html", ".htm")):
            raise HTTPException(status_code=400, detail="Please upload a .html or .htm file only.")

        raw = await file.read()
        html_content = raw.decode("utf-8", errors="ignore")

        file_path = await generate_pdf(
            html_content,
            original_filename=file.filename,
        )

        return {
            "status": "success",
            "input_file": file.filename,
            "pdf_file": file_path,
            "output_file_name": Path(file_path).name,
            "download_url": download_url(request.base_url, file_path),
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
        file_path = await generate_pptx(req.html, original_filename=req.filename)
        return {
            "status": "success",
            "pptx_file": file_path,
            "output_file_name": Path(file_path).name,
            "download_url": download_url(request.base_url, file_path),
        }
    except Exception as e:
        print("ERROR in /convert/pptx:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or repr(e))


@app.post("/convert/pptx/file")
async def convert_html_file_to_pptx(request: Request, file: UploadFile = File(...)):
    try:
        if not file.filename or not file.filename.lower().endswith((".html", ".htm")):
            raise HTTPException(status_code=400, detail="Please upload a .html or .htm file only.")

        raw = await file.read()
        html_content = raw.decode("utf-8", errors="ignore")

        file_path = await generate_pptx(
            html_content,
            original_filename=file.filename,
        )

        return {
            "status": "success",
            "input_file": file.filename,
            "pptx_file": file_path,
            "output_file_name": Path(file_path).name,
            "download_url": download_url(request.base_url, file_path),
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
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")

    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        media_type = "application/pdf"
    elif suffix == ".pptx":
        media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=media_type,
    )
