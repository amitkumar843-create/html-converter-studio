# HTML Converter Studio - React + Vite + Tailwind UI

## Install

```powershell
cd "C:\Users\YP862EB\OneDrive - EY\Desktop\HTML PPT\01_HTML to PDF PPTX Converter"
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npm install lucide-react
npx tailwindcss init -p
```

Replace the generated files with the files from this package.

## Run backend

```powershell
cd "C:\Users\YP862EB\OneDrive - EY\Desktop\HTML PPT\01_HTML to PDF PPTX Converter"
.\venv\Scripts\Activate
python -m uvicorn app:app --reload --port 8000
```

## Run frontend

```powershell
cd "C:\Users\YP862EB\OneDrive - EY\Desktop\HTML PPT\01_HTML to PDF PPTX Converter\frontend"
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Backend requirement

Add the CORS block from `backend_cors_snippet.py` into `app.py` so React can call the FastAPI backend.
