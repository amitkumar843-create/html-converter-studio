import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDownToLine,
  CheckCircle2,
  FileCode2,
  FileText,
  Loader2,
  Moon,
  Presentation,
  RefreshCcw,
  ShieldCheck,
  Sun,
  UploadCloud,
  XCircle,
} from "lucide-react";

// LOCAL-ONLY backend endpoint. Do not change to window.location.hostname for local mode.
const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000"; 
const PREVIEW_WIDTH = 1366;
const PREVIEW_HEIGHT = 768;

function formatBytes(bytes) {
  if (!bytes && bytes !== 0) return "";
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(size >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function getFileNameFromPath(pathOrUrl) {
  if (!pathOrUrl) return "";
  const clean = String(pathOrUrl).split("?")[0];
  return clean.split(/[\\/]/).pop() || clean;
}

function estimateConversionDurationMs(file, type) {
  const sizeMb = file?.size ? file.size / (1024 * 1024) : 1;
  const base = type === "pdf" ? 18000 : 26000;
  const perMb = type === "pdf" ? 11000 : 16000;
  const estimated = base + sizeMb * perMb;
  return Math.max(18000, Math.min(180000, estimated));
}

function buildEmptyPreview() {
  return `<!doctype html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
      html, body { height: 100%; margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #fff; color: #475569; }
      .empty { height: 100%; display: grid; place-items: center; text-align: center; padding: 18px; box-sizing: border-box; }
      .title { margin: 0 0 8px; font-size: 28px; font-weight: 850; color: #0f172a; }
      .copy { margin: 0 auto; font-size: 18px; line-height: 1.5; max-width: 560px; }
    </style>
  </head>
  <body>
    <div class="empty">
      <div>
        <p class="title">Preview will appear here</p>
        <p class="copy">Upload an HTML file to see a correctly scaled browser preview before conversion.</p>
      </div>
    </div>
  </body>
</html>`;
}

function injectPreviewBase(htmlText) {
  let output = htmlText || "";

  if (!/<meta\s+name=["']viewport["']/i.test(output)) {
    const viewportTag = '<meta name="viewport" content="width=device-width, initial-scale=1.0" />';
    output = /<head[^>]*>/i.test(output)
      ? output.replace(/<head[^>]*>/i, (match) => `${match}${viewportTag}`)
      : `${viewportTag}${output}`;
  }

  const baseStyle = `<style id="hcs-preview-fit-style">html,body{margin:0;min-height:100%;}body{overflow:auto;}img,svg,video,canvas{max-width:100%;}</style>`;
  output = /<head[^>]*>/i.test(output)
    ? output.replace(/<head[^>]*>/i, (match) => `${match}${baseStyle}`)
    : `${baseStyle}${output}`;

  return output;
}

export default function App() {
  const inputRef = useRef(null);
  const progressTimerRef = useRef(null);
  const conversionStartedAtRef = useRef(null);
  const estimatedDurationRef = useRef(30000);
  const previewStageRef = useRef(null);
  const previewScaleShellRef = useRef(null);

  const [theme, setTheme] = useState(() => localStorage.getItem("hcs-theme") || "light");
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState("ready");
  const [message, setMessage] = useState("Select an HTML file to begin.");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [activeConversion, setActiveConversion] = useState(null);
  const [previewSrcDoc, setPreviewSrcDoc] = useState(buildEmptyPreview());
  const [previewScale, setPreviewScale] = useState(1);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("hcs-theme", theme);
  }, [theme]);

  useEffect(() => {
    return () => {
      if (progressTimerRef.current) window.clearInterval(progressTimerRef.current);
    };
  }, []);

  function fitPreview() {
    const stage = previewStageRef.current;
    const shell = previewScaleShellRef.current;
    if (!stage || !shell) return;

    const scale = Math.min(stage.clientWidth / PREVIEW_WIDTH, stage.clientHeight / PREVIEW_HEIGHT);
    const safeScale = Math.max(scale, 0.05);
    shell.style.transform = `translate(-50%, -50%) scale(${safeScale})`;
    setPreviewScale(safeScale);
  }

  useEffect(() => {
    fitPreview();
    window.addEventListener("resize", fitPreview);
    return () => window.removeEventListener("resize", fitPreview);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(fitPreview, 80);
    return () => window.clearTimeout(timer);
  }, [previewSrcDoc]);

  const selectedFileValid = useMemo(() => {
    if (!file) return false;
    const name = file.name.toLowerCase();
    return name.endsWith(".html") || name.endsWith(".htm");
  }, [file]);

  const statusTone = {
    ready: "status-ready",
    working: "status-working",
    success: "status-success",
    error: "status-error",
  }[status];

  function startProgress(type) {
    if (progressTimerRef.current) window.clearInterval(progressTimerRef.current);
    const estimatedDuration = estimateConversionDurationMs(file, type);
    estimatedDurationRef.current = estimatedDuration;
    conversionStartedAtRef.current = Date.now();
    setElapsedSeconds(0);
    setProgress(1);
    progressTimerRef.current = window.setInterval(() => {
      const elapsed = Date.now() - conversionStartedAtRef.current;
      const ratio = Math.min(elapsed / estimatedDurationRef.current, 0.985);
      const eased = 1 - Math.pow(1 - ratio, 2.2);
      const calculated = Math.max(1, Math.min(98, Math.round(eased * 98)));
      setElapsedSeconds(Math.floor(elapsed / 1000));
      setProgress(calculated);
    }, 350);
  }

  function finishProgress(success = true) {
    if (progressTimerRef.current) window.clearInterval(progressTimerRef.current);
    progressTimerRef.current = null;
    if (conversionStartedAtRef.current) {
      setElapsedSeconds(Math.floor((Date.now() - conversionStartedAtRef.current) / 1000));
    }
    setProgress(success ? 100 : 0);
  }

  function resetResult(nextFile = file) {
    if (progressTimerRef.current) window.clearInterval(progressTimerRef.current);
    progressTimerRef.current = null;
    setProgress(0);
    setElapsedSeconds(0);
    setActiveConversion(null);
    setResult(null);
    setError(null);
    setStatus("ready");
    setMessage(nextFile ? "Ready to convert." : "Select an HTML file to begin.");
  }

  function resetPreview() {
    setPreviewSrcDoc(buildEmptyPreview());
  }

  function setSelectedFile(nextFile) {
    if (!nextFile) return;

    setFile(nextFile);
    setResult(null);
    setError(null);
    setProgress(0);
    setElapsedSeconds(0);
    setActiveConversion(null);

    if (!nextFile.name.toLowerCase().endsWith(".html") && !nextFile.name.toLowerCase().endsWith(".htm")) {
      resetPreview();
      setStatus("error");
      setMessage("Only .html or .htm files are supported.");
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      setPreviewSrcDoc(injectPreviewBase(event.target.result));
    };
    reader.onerror = () => {
      resetPreview();
      setStatus("error");
      setMessage("Unable to read selected file.");
    };
    reader.readAsText(nextFile);

    setStatus("ready");
    setMessage("Ready to convert.");
  }

  function handleBrowse() {
    inputRef.current?.click();
  }

  function handleInputChange(event) {
    const nextFile = event.target.files?.[0];
    setSelectedFile(nextFile);
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    const nextFile = event.dataTransfer.files?.[0];
    setSelectedFile(nextFile);
  }

  async function convert(type) {
    if (!file) {
      setStatus("error");
      setMessage("Please select an HTML file first.");
      return;
    }
    if (!selectedFileValid) {
      setStatus("error");
      setMessage("Only .html or .htm files are supported.");
      return;
    }

    setStatus("working");
    setActiveConversion(type);
    setError(null);
    setResult(null);
    setMessage(type === "pdf" ? "Generating PDF..." : "Generating PPTX...");
    startProgress(type);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE}/convert/${type}/file`, {
        method: "POST",
        body: formData,
      });

      let data;
      try {
        data = await response.json();
      } catch {
        data = {};
      }

      if (!response.ok) {
        throw new Error(data.detail || `Conversion failed with HTTP ${response.status}`);
      }

      const downloadUrl = data.download_url;
      const outputPath = data.pdf_file || data.pptx_file || "";
      const outputName =
        data.output_file_name ||
        getFileNameFromPath(outputPath) ||
        `${file.name.replace(/\.(html|htm)$/i, "")}.${type}`;

      finishProgress(true);
      setActiveConversion(null);
      setResult({ type, outputName, downloadUrl, outputPath });
      setStatus("success");
      setMessage(`${type.toUpperCase()} generated successfully.`);
    } catch (err) {
      finishProgress(false);
      setActiveConversion(null);
      setStatus("error");
      setError(err.message || String(err));
      setMessage("Conversion failed. Please check backend logs.");
    }
  }

  const isWorking = status === "working";

  return (
    <main className="app-shell min-h-screen px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <header className="hero-card">
          <div className="hero-copy">
            <h1>HTML Converter Studio</h1>
            <p>Convert presentation-ready HTML files into high-quality PDF and PPTX outputs from a modern browser interface.</p>
          </div>
          <button
            type="button"
            onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
            className="theme-toggle"
            aria-label="Toggle dark and light mode"
            title="Toggle dark/light mode"
          >
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            <span>{theme === "dark" ? "Light" : "Dark"}</span>
          </button>
        </header>

        <section className="grid gap-6 lg:grid-cols-[1.08fr_0.92fr]">
          <div className="glass-card overflow-hidden rounded-[2rem]">
            <div className="border-b border-cardBorder p-5 sm:p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="section-title">Upload HTML file</h2>
                  <p className="section-subtitle">Drag and drop one .html or .htm file.</p>
                </div>
                <div className="icon-tile">
                  <FileCode2 size={24} />
                </div>
              </div>
            </div>
            <div className="p-5 sm:p-6">
              <div
                onDragOver={(event) => {
                  event.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={`upload-zone upload-grid ${isDragging ? "dragging" : ""}`}
              >
                <div className="upload-icon">
                  <UploadCloud size={42} />
                </div>
                <h3>Drop your HTML file here</h3>
                <p>Your file stays local to your FastAPI backend. Supported formats: .html and .htm.</p>
                <button type="button" onClick={handleBrowse} className="primary-button small-button">
                  Browse File
                </button>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".html,.htm"
                  className="hidden"
                  onChange={handleInputChange}
                />
              </div>

              {file && (
                <div className="file-card">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="file-icon">
                      <FileText size={22} />
                    </div>
                    <div className="min-w-0">
                      <div className="truncate text-sm font-bold text-mainText">{file.name}</div>
                      <div className="mt-1 text-xs text-mutedText">{formatBytes(file.size)}</div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setFile(null);
                      if (inputRef.current) inputRef.current.value = "";
                      resetPreview();
                      resetResult(null);
                    }}
                    className="secondary-button"
                  >
                    <RefreshCcw size={14} />
                    Replace
                  </button>
                </div>
              )}
            </div>
          </div>

          <aside className="flex flex-col gap-6">
            <div className="glass-card rounded-[2rem] p-5 sm:p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="section-title">Convert</h2>
                  <p className="section-subtitle">Choose output format.</p>
                </div>
                <div className="icon-tile purple">
                  <Presentation size={24} />
                </div>
              </div>

              <div className="preview-card-ui">
                <div className="preview-toolbar-ui">
                  <div className="preview-title-ui">
                    <Presentation size={15} />
                    Live Preview
                  </div>
                  <div className="preview-file-ui">{file ? file.name : "No file selected"}</div>
                </div>
                <div ref={previewStageRef} className="preview-frame-wrap-ui">
                  <div ref={previewScaleShellRef} className="preview-scale-shell-ui">
                    <iframe
                      title="HTML live preview"
                      srcDoc={previewSrcDoc}
                      sandbox="allow-scripts allow-forms allow-popups allow-modals allow-downloads"
                      onLoad={fitPreview}
                    />
                  </div>
                  <div className="preview-hint-ui">Fit preview {Math.round(previewScale * 100)}%</div>
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
                <button
                  type="button"
                  disabled={!selectedFileValid || isWorking}
                  onClick={() => convert("pdf")}
                  className="convert-button pdf"
                >
                  {isWorking && activeConversion === "pdf" ? <Loader2 className="animate-spin" size={18} /> : <FileText size={18} />}
                  {isWorking && activeConversion === "pdf" ? "Converting PDF" : "Convert PDF"}
                </button>
                <button
                  type="button"
                  disabled={!selectedFileValid || isWorking}
                  onClick={() => convert("pptx")}
                  className="convert-button pptx"
                >
                  {isWorking && activeConversion === "pptx" ? <Loader2 className="animate-spin" size={18} /> : <Presentation size={18} />}
                  {isWorking && activeConversion === "pptx" ? "Converting PPTX" : "Convert PPTX"}
                </button>
              </div>

              {isWorking && (
                <div className="progress-wrap-ui" aria-label="Conversion progress">
                  <div className="flex items-center justify-between text-xs font-bold text-mutedText">
                    <span>{message}</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[11px] font-semibold text-mutedText/80">
                    <span>Elapsed: {elapsedSeconds}s</span>
                    <span>Estimated: {Math.ceil(estimatedDurationRef.current / 1000)}s</span>
                  </div>
                  <div className="progress-track-ui">
                    <div className="progress-bar-ui" style={{ width: `${progress}%` }} />
                  </div>
                </div>
              )}
            </div>

            <div className={`status-card ${statusTone}`}>
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  {status === "success" && <CheckCircle2 size={22} />}
                  {status === "error" && <XCircle size={22} />}
                  {status === "working" && <Loader2 className="animate-spin" size={22} />}
                  {status === "ready" && <ShieldCheck size={22} />}
                </div>
                <div className="min-w-0 flex-1">
                  <h3>Status</h3>
                  <p>{message}</p>
                  {error && <pre>{error}</pre>}
                </div>
              </div>
            </div>

            {result && (
              <div className="glass-card rounded-[2rem] p-5 sm:p-6">
                <div className="flex items-start gap-3">
                  <div className="success-tile">
                    <CheckCircle2 size={24} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-lg font-black text-mainText">Ready to download</h3>
                    <p className="mt-1 truncate text-sm text-mutedText">{result.outputName}</p>
                    <a href={result.downloadUrl} className="download-button">
                      <ArrowDownToLine size={18} />
                      Download {result.type.toUpperCase()}
                    </a>
                  </div>
                </div>
              </div>
            )}
          </aside>
        </section>
      </div>
    </main>
  );
}
