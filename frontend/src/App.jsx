import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowUpDown,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Code2,
  Columns,
  Copy,
  ExternalLink,
  Eye,
  FileCode2,
  FileText,
  Layers,
  Layout,
  LayoutGrid,
  LayoutTemplate,
  List,
  Loader2,
  Maximize2,
  Minimize2,
  Moon,
  Play,
  Presentation,
  RefreshCcw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Sun,
  Trash2,
  UploadCloud,
  X,
  XCircle,
  Zap,
} from "lucide-react";
import { SAMPLE_TEMPLATES } from "./templates";
import StudioLogo from "./StudioLogo";

// Backend endpoint: set VITE_API_BASE_URL at build time for deployed environments
// (e.g. Render), falls back to the local dev backend.
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const CATEGORY_CONFIG = {
  "EY Corporate": {
    badge: "bg-[#F59E0B] text-slate-950 font-black shadow-sm",
    pillActive: "bg-[#F59E0B] text-slate-950 font-black shadow-[0_4px_16px_rgba(245,158,11,0.4)]",
    borderActive: "border-[#F59E0B] ring-2 ring-amber-400/60 shadow-[0_0_25px_rgba(245,158,11,0.25)] bg-amber-500/5",
    borderHover: "hover:border-[#F59E0B] hover:shadow-[0_6px_20px_rgba(245,158,11,0.15)]",
    accentText: "text-amber-700 dark:text-amber-400 font-black",
    buttonActive: "bg-[#F59E0B] text-slate-950 font-black shadow-[0_2px_10px_rgba(245,158,11,0.3)]",
    glowDot: "#F59E0B",
    tag: "EY Corporate",
  },
  "AI & Animated Decks": {
    badge: "bg-[#A855F7] text-white font-black shadow-sm",
    pillActive: "bg-[#A855F7] text-white font-black shadow-[0_4px_16px_rgba(168,85,247,0.4)]",
    borderActive: "border-[#A855F7] ring-2 ring-purple-400/60 shadow-[0_0_25px_rgba(168,85,247,0.25)] bg-purple-500/5",
    borderHover: "hover:border-[#A855F7] hover:shadow-[0_6px_20px_rgba(168,85,247,0.15)]",
    accentText: "text-purple-700 dark:text-purple-400 font-black",
    buttonActive: "bg-[#A855F7] text-white font-black shadow-[0_2px_10px_rgba(168,85,247,0.3)]",
    glowDot: "#A855F7",
    tag: "AI & Motion",
  },
  "Dashboards & Ops": {
    badge: "bg-[#10B981] text-white font-black shadow-sm",
    pillActive: "bg-[#10B981] text-white font-black shadow-[0_4px_16px_rgba(16,185,129,0.4)]",
    borderActive: "border-[#10B981] ring-2 ring-emerald-400/60 shadow-[0_0_25px_rgba(16,185,129,0.25)] bg-emerald-500/5",
    borderHover: "hover:border-[#10B981] hover:shadow-[0_6px_20px_rgba(16,185,129,0.15)]",
    accentText: "text-emerald-700 dark:text-emerald-400 font-black",
    buttonActive: "bg-[#10B981] text-white font-black shadow-[0_2px_10px_rgba(16,185,129,0.3)]",
    glowDot: "#10B981",
    tag: "Dashboards",
  },
  "Delhi Safe City": {
    badge: "bg-[#2563EB] text-white font-black shadow-sm",
    pillActive: "bg-[#2563EB] text-white font-black shadow-[0_4px_16px_rgba(37,99,235,0.4)]",
    borderActive: "border-[#2563EB] ring-2 ring-blue-400/60 shadow-[0_0_25px_rgba(37,99,235,0.25)] bg-blue-500/5",
    borderHover: "hover:border-[#2563EB] hover:shadow-[0_6px_20px_rgba(37,99,235,0.15)]",
    accentText: "text-blue-700 dark:text-blue-400 font-black",
    buttonActive: "bg-[#2563EB] text-white font-black shadow-[0_2px_10px_rgba(37,99,235,0.3)]",
    glowDot: "#2563EB",
    tag: "Public Safety",
  },
  "Architecture & Systems": {
    badge: "bg-[#0891B2] text-white font-black shadow-sm",
    pillActive: "bg-[#0891B2] text-white font-black shadow-[0_4px_16px_rgba(8,145,178,0.4)]",
    borderActive: "border-[#0891B2] ring-2 ring-cyan-400/60 shadow-[0_0_25px_rgba(8,145,178,0.25)] bg-cyan-500/5",
    borderHover: "hover:border-[#0891B2] hover:shadow-[0_6px_20px_rgba(8,145,178,0.15)]",
    accentText: "text-cyan-700 dark:text-cyan-400 font-black",
    buttonActive: "bg-[#0891B2] text-white font-black shadow-[0_2px_10px_rgba(8,145,178,0.3)]",
    glowDot: "#0891B2",
    tag: "Architecture",
  },
  "Built-in Starters": {
    badge: "bg-[#4F46E5] text-white font-black shadow-sm",
    pillActive: "bg-[#4F46E5] text-white font-black shadow-[0_4px_16px_rgba(79,70,229,0.4)]",
    borderActive: "border-[#4F46E5] ring-2 ring-indigo-400/60 shadow-[0_0_25px_rgba(79,70,229,0.25)] bg-indigo-500/5",
    borderHover: "hover:border-[#4F46E5] hover:shadow-[0_6px_20px_rgba(79,70,229,0.15)]",
    accentText: "text-indigo-700 dark:text-indigo-400 font-black",
    buttonActive: "bg-[#4F46E5] text-white font-black shadow-[0_2px_10px_rgba(79,70,229,0.3)]",
    glowDot: "#4F46E5",
    tag: "Starters",
  },
  "All": {
    badge: "bg-[#4F46E5] text-white font-black shadow-sm",
    pillActive: "bg-[#4F46E5] text-white font-black shadow-[0_4px_16px_rgba(79,70,229,0.4)]",
    borderActive: "border-[#4F46E5] ring-2 ring-indigo-400/60 shadow-[0_0_25px_rgba(79,70,229,0.25)] bg-indigo-500/5",
    borderHover: "hover:border-[#4F46E5] hover:shadow-[0_6px_20px_rgba(79,70,229,0.15)]",
    accentText: "text-indigo-700 dark:text-indigo-400 font-black",
    buttonActive: "bg-[#4F46E5] text-white font-black shadow-[0_2px_10px_rgba(79,70,229,0.3)]",
    glowDot: "#4F46E5",
    tag: "All",
  }
};

function getCategoryStyle(cat) {
  return CATEGORY_CONFIG[cat] || CATEGORY_CONFIG["All"];
}

const VIEWPORT_DIMENSIONS = {
  "16:9": { width: 1366, height: 768, label: "16:9 Widescreen (1366×768)" },
  "4:3": { width: 1024, height: 768, label: "4:3 Classic (1024×768)" },
  "a4-p": { width: 794, height: 1123, label: "A4 Portrait (794×1123)" },
  "a4-l": { width: 1123, height: 794, label: "A4 Landscape (1123×794)" },
};

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

function extractMetadata(htmlText) {
  if (!htmlText) return { title: "", slideCount: 0 };
  const titleMatch = htmlText.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  const title = titleMatch ? titleMatch[1].trim() : "";

  // Count slides
  const slideRegex = /class=["'][^"']*\b(slide|slide-shell)\b[^"']*["']/gi;
  const slideMatches = htmlText.match(slideRegex) || [];
  let slideCount = slideMatches.length;

  if (slideCount === 0) {
    const sectionMatches = htmlText.match(/<section\b[^>]*>/gi) || [];
    slideCount = sectionMatches.length;
  }

  return { title, slideCount: Math.max(1, slideCount) };
}

function buildEmptyPreview() {
  return `<!doctype html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
      html, body { height: 100%; margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #94a3b8; }
      .empty { height: 100%; display: grid; place-items: center; text-align: center; padding: 24px; box-sizing: border-box; }
      .title { margin: 0 0 10px; font-size: 26px; font-weight: 800; color: #f8fafc; }
      .copy { margin: 0 auto; font-size: 16px; line-height: 1.6; max-width: 520px; color: #94a3b8; }
      .badge { display: inline-block; padding: 6px 14px; background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #818cf8; border-radius: 20px; font-size: 13px; font-weight: 700; margin-bottom: 15px; }
    </style>
  </head>
  <body>
    <div class="empty">
      <div>
        <div class="badge">Live Slide Deck Preview</div>
        <p class="title">No Content Loaded Yet</p>
        <p class="copy">Upload an HTML file, paste raw code in the Editor tab, or pick a sample template from the gallery to inspect your presentation live.</p>
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
  const previewStageRef = useRef(null);
  const previewScaleShellRef = useRef(null);
  const fullscreenStageRef = useRef(null);
  const fullscreenScaleShellRef = useRef(null);
  const pillsContainerRef = useRef(null);

  const scrollPills = (direction) => {
    if (pillsContainerRef.current) {
      const amount = 250;
      pillsContainerRef.current.scrollBy({ left: direction === 'left' ? -amount : amount, behavior: 'smooth' });
    }
  };

  // General State
  const [theme, setTheme] = useState(() => localStorage.getItem("hcs-theme") || "dark");
  const [inputMode, setInputMode] = useState("upload"); // "upload" | "editor" | "templates"
  const [backendStatus, setBackendStatus] = useState("checking"); // "online" | "offline" | "checking"

  // Input Data State
  const [file, setFile] = useState(null);
  const [rawHtml, setRawHtml] = useState("");
  const [customFilename, setCustomFilename] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [editorSearch, setEditorSearch] = useState("");
  const [editorSearchIndex, setEditorSearchIndex] = useState(-1);
  const textareaRef = useRef(null);
  const [activeTemplateId, setActiveTemplateId] = useState(null);
  const [backendSamples, setBackendSamples] = useState([]);
  const [isLoadingSamples, setIsLoadingSamples] = useState(false);
  const [loadingSampleId, setLoadingSampleId] = useState(null);
  const [sampleSearch, setSampleSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [presetViewMode, setPresetViewMode] = useState(() => localStorage.getItem("hcs-preset-view") || "grid"); // "grid" | "list" | "compact"
  const [sortBy, setSortBy] = useState(() => localStorage.getItem("hcs-preset-sort-by") || "name"); // "name" | "category" | "size" | "type"
  const [sortOrder, setSortOrder] = useState(() => localStorage.getItem("hcs-preset-sort-order") || "asc"); // "asc" | "desc"
  const [isSortOpen, setIsSortOpen] = useState(false);
  const sortMenuRef = useRef(null);

  useEffect(() => {
    localStorage.setItem("hcs-preset-view", presetViewMode);
  }, [presetViewMode]);

  useEffect(() => {
    localStorage.setItem("hcs-preset-sort-by", sortBy);
  }, [sortBy]);

  useEffect(() => {
    localStorage.setItem("hcs-preset-sort-order", sortOrder);
  }, [sortOrder]);

  // Click outside to close sort dropdown
  useEffect(() => {
    function handleClickOutside(e) {
      if (sortMenuRef.current && !sortMenuRef.current.contains(e.target)) {
        setIsSortOpen(false);
      }
    }
    if (isSortOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isSortOpen]);

  // Fetch Sample Files dynamically from backend
  useEffect(() => {
    let isMounted = true;
    async function fetchSamples() {
      try {
        setIsLoadingSamples(true);
        const res = await fetch(`${API_BASE}/samples`, { method: "GET" });
        if (res.ok && isMounted) {
          const data = await res.json();
          setBackendSamples(data.samples || []);
        }
      } catch {
        // Fallback silently to client starters
      } finally {
        if (isMounted) setIsLoadingSamples(false);
      }
    }
    fetchSamples();
    return () => {
      isMounted = false;
    };
  }, [backendStatus]);

  // Combined Presets Catalog
  const allTemplates = useMemo(() => {
    const starters = SAMPLE_TEMPLATES.map((t) => ({
      ...t,
      isStarter: true,
      category: "Built-in Starters",
    }));
    return [...starters, ...backendSamples];
  }, [backendSamples]);

  // Unique Categories
  const sampleCategories = useMemo(() => {
    const cats = new Set(allTemplates.map((t) => t.category || "General"));
    return ["All", ...Array.from(cats)];
  }, [allTemplates]);

  // Filtered & Sorted Templates
  const filteredTemplates = useMemo(() => {
    const list = allTemplates.filter((t) => {
      const matchCat = selectedCategory === "All" || (t.category || "General") === selectedCategory;
      const q = sampleSearch.toLowerCase().trim();
      const matchSearch =
        !q ||
        (t.title && t.title.toLowerCase().includes(q)) ||
        (t.filename && t.filename.toLowerCase().includes(q)) ||
        (t.category && t.category.toLowerCase().includes(q));
      return matchCat && matchSearch;
    });

    // Sort list
    return list.sort((a, b) => {
      let comparison = 0;
      if (sortBy === "name") {
        const nameA = (a.title || a.filename || "").toLowerCase();
        const nameB = (b.title || b.filename || "").toLowerCase();
        comparison = nameA.localeCompare(nameB);
      } else if (sortBy === "category") {
        const catA = (a.category || "General").toLowerCase();
        const catB = (b.category || "General").toLowerCase();
        comparison = catA.localeCompare(catB);
        if (comparison === 0) {
          comparison = (a.title || a.filename || "").localeCompare(b.title || b.filename || "");
        }
      } else if (sortBy === "size") {
        const sizeA = Number(a.size) || 0;
        const sizeB = Number(b.size) || 0;
        comparison = sizeA - sizeB;
      } else if (sortBy === "date") {
        const dateA = Number(a.modified_at) || 0;
        const dateB = Number(b.modified_at) || 0;
        comparison = dateA - dateB;
      } else if (sortBy === "type") {
        const typeA = a.isStarter ? "Starter" : "Preset";
        const typeB = b.isStarter ? "Starter" : "Preset";
        comparison = typeA.localeCompare(typeB);
      }

      return sortOrder === "asc" ? comparison : -comparison;
    });
  }, [allTemplates, selectedCategory, sampleSearch, sortBy, sortOrder]);

  // Preview & Viewport State
  const [previewSrcDoc, setPreviewSrcDoc] = useState(buildEmptyPreview());
  const [previewViewport, setPreviewViewport] = useState("16:9");
  const [previewZoom, setPreviewZoom] = useState("fit");
  const [previewTheme, setPreviewTheme] = useState("dark");
  const [previewScale, setPreviewScale] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Conversion Engine State
  const [status, setStatus] = useState("ready");
  const [message, setMessage] = useState("Select an HTML file or paste code to begin.");
  const [activeConversion, setActiveConversion] = useState(null); // "pdf" | "pptx" | "both"
  const [conversionPhase, setConversionPhase] = useState(1);
  const [progress, setProgress] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // History & Toast State
  const [history, setHistory] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("hcs-history") || "[]");
    } catch {
      return [];
    }
  });
  const [toasts, setToasts] = useState([]);

  // Apply Theme
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    localStorage.setItem("hcs-theme", theme);
  }, [theme]);

  // Save History
  useEffect(() => {
    localStorage.setItem("hcs-history", JSON.stringify(history));
  }, [history]);

  // Toast Notification Dispatcher
  function addToast(msg, type = "info") {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, msg, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3800);
  }

  // Periodic Backend Health Check
  useEffect(() => {
    let isMounted = true;
    async function pingHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`, { method: "GET", cache: "no-store" });
        if (isMounted) {
          setBackendStatus(res.ok ? "online" : "offline");
        }
      } catch {
        if (isMounted) setBackendStatus("offline");
      }
    }

    pingHealth();
    const interval = setInterval(pingHealth, 12000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (progressTimerRef.current) clearInterval(progressTimerRef.current);
    };
  }, []);

  // Calculate extracted metadata
  const currentMetadata = useMemo(() => {
    const content = inputMode === "upload" ? previewSrcDoc : rawHtml;
    return extractMetadata(content);
  }, [inputMode, previewSrcDoc, rawHtml]);

  // Check if current input has content to convert
  const hasContent = useMemo(() => {
    if (inputMode === "upload") {
      return !!file && (file.name.toLowerCase().endsWith(".html") || file.name.toLowerCase().endsWith(".htm"));
    }
    return rawHtml.trim().length > 0;
  }, [inputMode, file, rawHtml]);

  // Fit and scale preview
  function updatePreviewScale() {
    const stage = isFullscreen ? fullscreenStageRef.current : previewStageRef.current;
    const shell = isFullscreen ? fullscreenScaleShellRef.current : previewScaleShellRef.current;
    if (!stage || !shell) return;

    const dim = VIEWPORT_DIMENSIONS[previewViewport] || VIEWPORT_DIMENSIONS["16:9"];
    shell.style.width = `${dim.width}px`;
    shell.style.height = `${dim.height}px`;

    let scale = 1;
    if (previewZoom === "fit") {
      const scaleX = (stage.clientWidth - 32) / dim.width;
      const scaleY = (stage.clientHeight - 32) / dim.height;
      scale = Math.min(scaleX, scaleY);
    } else {
      scale = Number(previewZoom) || 1;
    }

    const safeScale = Math.max(scale, 0.05);
    shell.style.transform = `translate(-50%, -50%) scale(${safeScale})`;
    setPreviewScale(safeScale);
  }

  useEffect(() => {
    updatePreviewScale();
    window.addEventListener("resize", updatePreviewScale);
    return () => window.removeEventListener("resize", updatePreviewScale);
  }, [previewViewport, previewZoom, isFullscreen]);

  useEffect(() => {
    const timer = setTimeout(updatePreviewScale, 100);
    return () => clearTimeout(timer);
  }, [previewSrcDoc, isFullscreen]);

  // Keyboard shortcut listener
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === "Escape" && isFullscreen) {
        setIsFullscreen(false);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && hasContent && status !== "working") {
        e.preventDefault();
        convert("pdf");
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isFullscreen, hasContent, status]);

  // Load selected template (supports built-in starters & backend sample files)
  async function handleSelectTemplate(tpl) {
    const tplKey = tpl.id || tpl.filename;
    setActiveTemplateId(tplKey);
    setLoadingSampleId(tplKey);

    try {
      let htmlContent = tpl.html;
      if (!htmlContent && tpl.filename) {
        const res = await fetch(`${API_BASE}/samples/${encodeURIComponent(tpl.filename)}`);
        if (!res.ok) throw new Error("Could not load sample file from backend.");
        const data = await res.json();
        htmlContent = data.html;
      }

      setRawHtml(htmlContent);
      setPreviewSrcDoc(injectPreviewBase(htmlContent));
      const cleanStem = (tpl.filename || tpl.title || "Preset").replace(/\.(html|htm)$/i, "");
      setCustomFilename(cleanStem);
      setFile(null);
      setStatus("ready");
      setMessage(`Template "${tpl.title || tpl.filename}" loaded. Ready to convert.`);
      addToast(`Loaded preset: ${tpl.title || tpl.filename}`, "success");
    } catch (err) {
      setStatus("error");
      setMessage(`Failed to load preset: ${err.message}`);
      addToast(`Error loading preset: ${err.message}`, "error");
    } finally {
      setLoadingSampleId(null);
    }
  }

  // Handle file selection
  function handleFileSelected(nextFile) {
    if (!nextFile) return;

    if (!nextFile.name.toLowerCase().endsWith(".html") && !nextFile.name.toLowerCase().endsWith(".htm")) {
      setStatus("error");
      setMessage("Only .html or .htm files are supported.");
      addToast("Invalid file format. Please upload an HTML file.", "error");
      return;
    }

    setFile(nextFile);
    setResult(null);
    setError(null);
    setProgress(0);
    setElapsedSeconds(0);
    setActiveConversion(null);
    setActiveTemplateId(null);

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target.result;
      setPreviewSrcDoc(injectPreviewBase(text));
      setRawHtml(text);
    };
    reader.onerror = () => {
      setStatus("error");
      setMessage("Failed to read the selected file.");
    };
    reader.readAsText(nextFile);

    setStatus("ready");
    setMessage("File loaded. Ready to convert.");
    addToast(`Loaded ${nextFile.name} (${formatBytes(nextFile.size)})`, "success");
  }

  // Handle raw code update
  function handleRawHtmlChange(val) {
    setRawHtml(val);
    setPreviewSrcDoc(injectPreviewBase(val));
    if (status === "error") setStatus("ready");
    setEditorSearchIndex(-1); // Reset search index when code changes
  }

  // Handle editor search
  function handleEditorSearch(e) {
    if (e) e.preventDefault();
    if (!editorSearch || !textareaRef.current) return;
    const text = rawHtml.toLowerCase();
    const query = editorSearch.toLowerCase();
    
    let startIndex = editorSearchIndex + 1;
    let index = text.indexOf(query, startIndex);
    
    if (index === -1) {
      index = text.indexOf(query, 0); // wrap around
    }
    
    if (index !== -1) {
      setEditorSearchIndex(index);
      textareaRef.current.focus();
      textareaRef.current.setSelectionRange(index, index + query.length);
      // Basic manual scroll estimation
      const linesBefore = text.substring(0, index).split('\n').length;
      const lineHeight = 22; // rough guess
      textareaRef.current.scrollTop = Math.max(0, (linesBefore - 3) * lineHeight);
    } else {
      addToast(`"${editorSearch}" not found in HTML.`, "warning");
    }
  }

  // Multi-phase progress simulator
  function startProgress() {
    if (progressTimerRef.current) clearInterval(progressTimerRef.current);
    conversionStartedAtRef.current = Date.now();
    setElapsedSeconds(0);
    setProgress(2);
    setConversionPhase(1);

    progressTimerRef.current = setInterval(() => {
      const elapsed = Date.now() - conversionStartedAtRef.current;
      setElapsedSeconds(Math.floor(elapsed / 1000));

      if (elapsed < 3000) {
        setConversionPhase(1); // Parsing
        setProgress(Math.min(25, Math.floor(elapsed / 120)));
      } else if (elapsed < 12000) {
        setConversionPhase(2); // Chromium Rendering
        setProgress(25 + Math.min(45, Math.floor((elapsed - 3000) / 200)));
      } else if (elapsed < 24000) {
        setConversionPhase(3); // Slide Extraction
        setProgress(70 + Math.min(24, Math.floor((elapsed - 12000) / 500)));
      } else {
        setConversionPhase(4); // Packaging
        setProgress(95);
      }
    }, 250);
  }

  function finishProgress(success = true) {
    if (progressTimerRef.current) clearInterval(progressTimerRef.current);
    progressTimerRef.current = null;
    if (conversionStartedAtRef.current) {
      setElapsedSeconds(Math.floor((Date.now() - conversionStartedAtRef.current) / 1000));
    }
    setProgress(success ? 100 : 0);
    if (success) setConversionPhase(4);
  }

  // Core Conversion Function
  async function convert(type) {
    if (!hasContent) {
      setStatus("error");
      setMessage("Please provide valid HTML content first.");
      addToast("No HTML content to convert.", "error");
      return;
    }

    if (backendStatus === "offline") {
      setStatus("error");
      setMessage(`Backend server is currently offline at ${API_BASE}. Please start the backend server.`);
      addToast("Backend offline. Please start the Python backend.", "error");
      return;
    }

    setStatus("working");
    setActiveConversion(type);
    setError(null);
    setResult(null);
    setMessage(
      type === "both"
        ? "Generating both PDF and PPTX decks..."
        : type === "pdf"
        ? "Rendering pixel-perfect PDF document..."
        : "Generating editable PPTX presentation..."
    );
    startProgress();

    try {
      if (type === "both") {
        // Execute PDF then PPTX sequentially
        const pdfResult = await performSingleConversion("pdf");
        const pptxResult = await performSingleConversion("pptx");

        finishProgress(true);
        setActiveConversion(null);
        setStatus("success");
        setMessage("Both PDF and PPTX generated successfully!");
        setResult({
          type: "both",
          outputName: `${pdfResult.outputName} & ${pptxResult.outputName}`,
          pdfResult,
          pptxResult,
        });
        addToast("Dual PDF & PPTX conversion completed!", "success");
      } else {
        const convResult = await performSingleConversion(type);
        finishProgress(true);
        setActiveConversion(null);
        setStatus("success");
        setMessage(`${type.toUpperCase()} generated successfully.`);
        setResult(convResult);
        addToast(`${type.toUpperCase()} ready for download.`, "success");
      }
    } catch (err) {
      finishProgress(false);
      setActiveConversion(null);
      setStatus("error");
      setError(err.message || String(err));
      setMessage("Conversion failed. Please check backend logs.");
      addToast(`Error: ${err.message || "Conversion failed"}`, "error");
    }
  }

  async function performSingleConversion(type) {
    let response;
    const baseName = customFilename.trim() || (file ? file.name.replace(/\.(html|htm)$/i, "") : "presentation");
    const targetFilename = `${baseName}.${type}`;

    if (inputMode === "upload" && file) {
      const formData = new FormData();
      formData.append("file", file);
      response = await fetch(`${API_BASE}/convert/${type}/file`, {
        method: "POST",
        body: formData,
      });
    } else {
      // Use raw HTML JSON payload
      const htmlPayload = rawHtml || previewSrcDoc;
      response = await fetch(`${API_BASE}/convert/${type}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          html: htmlPayload,
          filename: targetFilename,
        }),
      });
    }

    let data;
    try {
      data = await response.json();
    } catch {
      data = {};
    }

    if (!response.ok) {
      throw new Error(data.detail || `Server returned HTTP ${response.status}`);
    }

    const downloadUrl = data.download_url;
    const outputPath = data.pdf_file || data.pptx_file || "";
    const outputName = data.output_file_name || getFileNameFromPath(outputPath) || targetFilename;

    // Log to conversion history
    const historyItem = {
      id: Date.now() + Math.random(),
      name: outputName,
      type: type.toUpperCase(),
      downloadUrl,
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      timestamp: Date.now(),
    };
    setHistory((prev) => [historyItem, ...prev.slice(0, 19)]);

    return { type, outputName, downloadUrl, outputPath };
  }

  function handleCopyDownloadUrl(url) {
    if (!url) return;
    navigator.clipboard.writeText(url);
    addToast("Download link copied to clipboard!", "success");
  }

  function handleClearHistory() {
    setHistory([]);
    addToast("Export history cleared.", "info");
  }

  function handleOpenInNewTab() {
    const blob = new Blob([previewSrcDoc], { type: "text/html" });
    const blobUrl = URL.createObjectURL(blob);
    window.open(blobUrl, "_blank");
  }

  function handleResetAll() {
    setFile(null);
    setRawHtml("");
    setActiveTemplateId(null);
    setCustomFilename("");
    setPreviewSrcDoc(buildEmptyPreview());
    setResult(null);
    setError(null);
    setStatus("ready");
    setMessage("Workspace reset. Select a file or template to begin.");
    if (inputRef.current) inputRef.current.value = "";
    addToast("Workspace reset.", "info");
  }

  const isWorking = status === "working";

  return (
    <main className="relative min-h-screen px-4 py-5 sm:px-6 lg:px-8 lg:py-7 overflow-x-hidden">
      {/* Magic UI Background Elements */}
      <div className="magic-dot-grid" />
      <div className="magic-ambient-glow-1" />
      <div className="magic-ambient-glow-2" />

      <div className="relative z-10 mx-auto flex w-full max-w-7xl flex-col gap-6">
        {/* Top Navbar */}
        <header className="top-navbar">
          <div className="brand-badge">
            <div className="flex-shrink-0 cursor-pointer hover:scale-105 transition-all duration-300 shadow-[0_0_24px_rgba(99,102,241,0.45)] rounded-[13px]">
              <StudioLogo size={44} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="brand-title shiny-text">HTML Converter Studio</span>
                <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-primary/15 text-primary border border-primary/30">
                  v2.0 Magic
                </span>
              </div>
              <div className="brand-subtitle">Enterprise Slide Deck & PDF Generator</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Backend Health Status */}
            <div
              className="health-pill"
              title={
                backendStatus === "online"
                  ? `Connected to FastAPI backend at ${API_BASE}`
                  : "Backend disconnected. Run Start_Server.bat or start uvicorn."
              }
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  backendStatus === "online" ? "bg-success animate-pulse-glow" : backendStatus === "offline" ? "bg-danger" : "bg-warning"
                }`}
              />
              <span>{backendStatus === "online" ? "Backend Online" : "Backend Offline"}</span>
            </div>

            {/* Reset Workspace Button */}
            {(file || rawHtml) && (
              <button
                type="button"
                onClick={handleResetAll}
                className="action-icon-btn"
                title="Clear Workspace & Reset"
              >
                <Trash2 size={16} />
              </button>
            )}

            {/* Theme Toggle */}
            <button
              type="button"
              onClick={() => setTheme((curr) => (curr === "dark" ? "light" : "dark"))}
              className="action-icon-btn"
              title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
            >
              {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </button>
          </div>
        </header>

        {/* Main 2-Column Workstation Layout */}
        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr] items-start">
          {/* Left Column: Input Panel & Configuration */}
          <div className="flex flex-col gap-5 min-w-0 animate-fade-in-up">
            <div className="glass-card rounded-[2rem] p-5 sm:p-6">
              {/* Tab Navigation */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cardBorder pb-4">
                <div className="tab-switcher">
                  <button
                    type="button"
                    onClick={() => setInputMode("upload")}
                    className={`tab-btn ${inputMode === "upload" ? "active" : ""}`}
                  >
                    <UploadCloud size={16} />
                    File Upload
                  </button>
                  <button
                    type="button"
                    onClick={() => setInputMode("editor")}
                    className={`tab-btn ${inputMode === "editor" ? "active" : ""}`}
                  >
                    <Code2 size={16} />
                    HTML Editor
                  </button>
                  <button
                    type="button"
                    onClick={() => setInputMode("templates")}
                    className={`tab-btn ${inputMode === "templates" ? "active" : ""}`}
                  >
                    <LayoutTemplate size={16} />
                    Presets
                  </button>
                </div>

                {/* Detected Stats Badge */}
                {hasContent && (
                  <div className="flex items-center gap-2">
                    <span className="file-pill">
                      <Layers size={13} />
                      {currentMetadata.slideCount} {currentMetadata.slideCount === 1 ? "Slide" : "Slides"}
                    </span>
                  </div>
                )}
              </div>

              {/* Mode 1: File Upload */}
              {inputMode === "upload" && (
                <div className="mt-5">
                  <div
                    onDragOver={(e) => {
                      e.preventDefault();
                      setIsDragging(true);
                    }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={(e) => {
                      e.preventDefault();
                      setIsDragging(false);
                      handleFileSelected(e.dataTransfer.files?.[0]);
                    }}
                    className={`upload-zone upload-grid ${isDragging ? "dragging" : ""}`}
                  >
                    <div className="upload-icon">
                      <FileCode2 size={38} />
                    </div>
                    <h3 className="mt-4 text-base font-extrabold text-mainText">Drop your HTML Presentation here</h3>
                    <p className="mt-1 max-w-sm text-xs text-mutedText">
                      Accepts standard HTML5 presentation decks (.html, .htm). Zero server upload — fully local.
                    </p>
                    <button
                      type="button"
                      onClick={() => inputRef.current?.click()}
                      className="primary-button mt-4 rounded-xl px-5 py-2.5 text-xs font-bold"
                    >
                      Browse Files
                    </button>
                    <input
                      ref={inputRef}
                      type="file"
                      accept=".html,.htm"
                      className="hidden"
                      onChange={(e) => handleFileSelected(e.target.files?.[0])}
                    />
                  </div>

                  {file && (
                    <div className="file-info-card border-primary ring-2 ring-primary/40 shadow-[0_0_25px_rgba(99,102,241,0.25)] bg-gradient-to-r from-primary/10 via-transparent to-primary/5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="file-icon bg-primary/20 text-primary border border-primary/30 p-2.5 rounded-xl">
                            <FileText size={22} />
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <div className="font-black text-mainText text-sm truncate">{file.name}</div>
                              <span className="shimmer-active-badge bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                Ready
                              </span>
                            </div>
                            <div className="text-xs text-mutedText mt-0.5 font-medium">
                              {formatBytes(file.size)} • Last modified{" "}
                              {new Date(file.lastModified).toLocaleDateString()}
                            </div>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={() => {
                            setFile(null);
                            setPreviewSrcDoc(buildEmptyPreview());
                            if (inputRef.current) inputRef.current.value = "";
                          }}
                          className="action-icon-btn hover:text-danger hover:border-danger/40"
                          title="Remove File"
                        >
                          <X size={15} />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Mode 2: Live HTML Code Editor */}
              {inputMode === "editor" && (
                <div className="mt-5 flex flex-col gap-3">
                  <div className="code-editor-wrap">
                    <div className="code-editor-toolbar">
                      <div className="flex items-center gap-2">
                        <Code2 size={15} />
                        <span>Raw HTML Code</span>
                      </div>
                      <div className="flex items-center gap-3 text-xs">
                        <form onSubmit={handleEditorSearch} className="flex items-center bg-card-soft rounded border border-cardBorder overflow-hidden">
                           <input 
                             type="text" 
                             value={editorSearch} 
                             onChange={e => { setEditorSearch(e.target.value); setEditorSearchIndex(-1); }} 
                             placeholder="Search code..." 
                             className="bg-transparent text-[11px] font-medium text-mainText px-2 py-1 outline-none w-28 sm:w-36" 
                           />
                           <button type="submit" className="px-1.5 py-1 text-mutedText hover:text-primary border-l border-cardBorder bg-background" title="Find Next">
                             <Search size={11} />
                           </button>
                        </form>
                        <span className="hidden sm:inline">{rawHtml.split("\n").length} Lines</span>
                        <span className="hidden sm:inline">{rawHtml.length} Chars</span>
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(rawHtml);
                            addToast("Code copied to clipboard!", "info");
                          }}
                          className="hover:text-mainText text-mutedText"
                          title="Copy HTML"
                        >
                          <Copy size={14} />
                        </button>
                      </div>
                    </div>
                    <textarea
                      ref={textareaRef}
                      value={rawHtml}
                      onChange={(e) => handleRawHtmlChange(e.target.value)}
                      placeholder="<!-- Paste or edit your raw HTML slide markup here... -->&#10;<section class='slide'>&#10;  <h1>Slide Title</h1>&#10;</section>"
                      className="code-editor-textarea"
                      spellCheck={false}
                    />
                  </div>
                </div>
              )}

              {/* Mode 3: Presets Gallery */}
              {inputMode === "templates" && (
                <div className="mt-5">
                  {/* Category Pills Bar */}
                  <div className="flex items-center mb-3 w-full">
                    <button
                      type="button"
                      onClick={() => scrollPills('left')}
                      className="flex-shrink-0 action-icon-btn mr-2"
                      style={{ width: '1.8rem', height: '1.8rem', borderRadius: '50%' }}
                      title="Scroll Left"
                    >
                      <ChevronLeft size={16} />
                    </button>
                    
                    <div className="category-pills-bar flex-1 m-0" ref={pillsContainerRef}>
                      {sampleCategories.map((cat) => {
                        const isCatSelected = selectedCategory === cat;
                        const catStyle = getCategoryStyle(cat);

                        return (
                          <button
                            key={cat}
                            type="button"
                            onClick={() => setSelectedCategory(cat)}
                            className={`category-pill-btn transition-all duration-200 ${
                              isCatSelected
                                ? `${catStyle.pillActive} border-transparent scale-[1.03]`
                                : "hover:border-cardBorder"
                            }`}
                          >
                            {cat}
                            <span className="text-[10px] opacity-80 font-bold">
                              (
                              {cat === "All"
                                ? allTemplates.length
                                : allTemplates.filter((t) => (t.category || "General") === cat).length}
                              )
                            </span>
                          </button>
                        );
                      })}
                    </div>

                    <button
                      type="button"
                      onClick={() => scrollPills('right')}
                      className="flex-shrink-0 action-icon-btn ml-2"
                      style={{ width: '1.8rem', height: '1.8rem', borderRadius: '50%' }}
                      title="Scroll Right"
                    >
                      <ChevronRight size={16} />
                    </button>
                  </div>

                  {/* Search Bar & View Mode Switcher */}
                  <div className="flex items-center gap-2 mb-3.5">
                    <div className="template-search-wrap flex-1 m-0">
                      <Search
                        size={15}
                        className="absolute left-3 top-1/2 -translate-y-1/2 text-mutedText pointer-events-none"
                      />
                      <input
                        type="text"
                        value={sampleSearch}
                        onChange={(e) => setSampleSearch(e.target.value)}
                        placeholder="Search presets by name or topic (e.g. Meity, Architecture, EY)..."
                        className="template-search-input"
                      />
                      {sampleSearch && (
                        <button
                          type="button"
                          onClick={() => setSampleSearch("")}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-mutedText hover:text-mainText"
                        >
                          <X size={14} />
                        </button>
                      )}
                    </div>

                    {/* Windows-style Sort Dropdown */}
                    <div className="relative flex-shrink-0" ref={sortMenuRef}>
                      <button
                        type="button"
                        onClick={() => setIsSortOpen(!isSortOpen)}
                        className={`flex items-center gap-1.5 px-3 rounded-xl border text-xs font-black transition-all ${
                          isSortOpen
                            ? "bg-primary text-white border-primary shadow-sm"
                            : "bg-card-soft text-mutedText hover:text-mainText border-cardBorder hover:bg-card-highlight"
                        }`}
                        style={{ height: "2.35rem" }}
                        title="Sort Presets"
                      >
                        <ArrowUpDown size={14} />
                        <span className="hidden sm:inline">Sort</span>
                        <ChevronDown size={13} className={`transition-transform duration-200 ${isSortOpen ? "rotate-180" : ""}`} />
                      </button>

                      {isSortOpen && (
                        <div className="sort-dropdown-menu">
                          <div className="px-3 py-1.5 text-[10px] font-black uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center justify-between">
                            <span>Sort By</span>
                            <span className="text-[9px] font-bold text-primary">Field</span>
                          </div>

                          <div className="space-y-0.5">
                            {[
                              { id: "name", label: "Name", hint: "A-Z" },
                              { id: "category", label: "Category", hint: "Group" },
                              { id: "date", label: "Date modified", hint: "Timestamp" },
                              { id: "size", label: "File Size", hint: "KB/MB" },
                              { id: "type", label: "Preset Type", hint: "Type" },
                            ].map((opt) => {
                              const isCur = sortBy === opt.id;
                              return (
                                <button
                                  key={opt.id}
                                  type="button"
                                  onClick={() => { setSortBy(opt.id); setIsSortOpen(false); }}
                                  className={`sort-menu-item ${isCur ? "active" : ""}`}
                                >
                                  <span className="font-bold flex items-center gap-2">
                                    {opt.label}
                                  </span>
                                  {isCur ? (
                                    <span className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center">
                                      <Check size={12} className="stroke-[3] text-white" />
                                    </span>
                                  ) : (
                                    <span className="text-[10px] opacity-50 font-semibold">{opt.hint}</span>
                                  )}
                                </button>
                              );
                            })}
                          </div>

                          <div className="my-1.5 border-t border-slate-200 dark:border-slate-800" />

                          <div className="px-3 py-1.5 text-[10px] font-black uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center justify-between">
                            <span>Order</span>
                            <span className="text-[9px] font-bold text-primary">Direction</span>
                          </div>

                          <div className="space-y-0.5">
                            {[
                              { id: "asc", label: "Ascending", desc: "A to Z • Oldest" },
                              { id: "desc", label: "Descending", desc: "Z to A • Newest" },
                            ].map((ord) => {
                              const isCur = sortOrder === ord.id;
                              return (
                                <button
                                  key={ord.id}
                                  type="button"
                                  onClick={() => { setSortOrder(ord.id); setIsSortOpen(false); }}
                                  className={`sort-menu-item ${isCur ? "active" : ""}`}
                                >
                                  <span className="font-bold flex flex-col items-start text-left">
                                    <span>{ord.label}</span>
                                    <span className={`text-[10px] font-medium ${isCur ? "text-white/80" : "text-slate-500 dark:text-slate-400"}`}>
                                      {ord.desc}
                                    </span>
                                  </span>
                                  {isCur && (
                                    <span className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center">
                                      <Check size={12} className="stroke-[3] text-white" />
                                    </span>
                                  )}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Windows-style View Mode Switcher */}
                    <div className="flex items-center px-1 bg-card-soft rounded-xl border border-cardBorder gap-0.5 flex-shrink-0" style={{ height: "2.35rem" }}>
                      <button
                        type="button"
                        onClick={() => setPresetViewMode("grid")}
                        className={`p-1.5 rounded-lg transition-all ${
                          presetViewMode === "grid"
                            ? "bg-primary text-white shadow-sm"
                            : "text-mutedText hover:text-mainText hover:bg-card-highlight"
                        }`}
                        title="Boxes / Large Cards View"
                      >
                        <LayoutGrid size={15} />
                      </button>

                      <button
                        type="button"
                        onClick={() => setPresetViewMode("compact")}
                        className={`p-1.5 rounded-lg transition-all ${
                          presetViewMode === "compact"
                            ? "bg-primary text-white shadow-sm"
                            : "text-mutedText hover:text-mainText hover:bg-card-highlight"
                        }`}
                        title="Tiles View (Compact Cards)"
                      >
                        <Columns size={15} />
                      </button>

                      <button
                        type="button"
                        onClick={() => setPresetViewMode("list")}
                        className={`p-1.5 rounded-lg transition-all ${
                          presetViewMode === "list"
                            ? "bg-primary text-white shadow-sm"
                            : "text-mutedText hover:text-mainText hover:bg-card-highlight"
                        }`}
                        title="Details / List View"
                      >
                        <List size={15} />
                      </button>
                    </div>
                  </div>

                  {/* Templates Content Rendering */}
                  {isLoadingSamples && backendSamples.length === 0 ? (
                    <div className="py-12 text-center text-xs text-mutedText flex items-center justify-center gap-2">
                      <Loader2 className="animate-spin" size={16} />
                      <span>Loading presentation templates...</span>
                    </div>
                  ) : filteredTemplates.length === 0 ? (
                    <div className="py-12 text-center text-xs text-mutedText">
                      No templates match your search criteria.
                    </div>
                  ) : presetViewMode === "list" ? (
                    /* View Mode 1: List / Details View */
                    <div className="template-list-wrap">
                      {filteredTemplates.map((tpl) => {
                        const tplKey = tpl.id || tpl.filename;
                        const isSelected = activeTemplateId === tplKey;
                        const isLoadingThis = loadingSampleId === tplKey;
                        const catStyle = getCategoryStyle(tpl.category);

                        return (
                          <div
                            key={tplKey}
                            onClick={() => !isLoadingThis && handleSelectTemplate(tpl)}
                            className={`template-list-row ${
                              isSelected
                                ? `${catStyle.borderActive} scale-[1.01]`
                                : `${catStyle.borderHover}`
                            }`}
                          >
                            <div className="flex items-center gap-3 min-w-0 flex-1">
                              <div className="flex-shrink-0">
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider ${catStyle.badge}`}>
                                  {tpl.category || "General"}
                                </span>
                              </div>
                              <div className="min-w-0 flex-1">
                                <h4 className="template-card-title truncate">
                                  {tpl.title || tpl.filename}
                                </h4>
                                {tpl.description && (
                                  <p className="template-card-desc truncate text-xs">{tpl.description}</p>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center gap-3 flex-shrink-0">
                              {tpl.date && (
                                <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 hidden sm:inline">
                                  {tpl.date}
                                </span>
                              )}
                              {tpl.size && (
                                <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 hidden sm:inline">
                                  {formatBytes(tpl.size)}
                                </span>
                              )}
                              {isSelected ? (
                                <span className={`px-2.5 py-1 rounded-lg text-xs font-black flex items-center gap-1.5 ${catStyle.buttonActive}`}>
                                  <Check size={13} className="stroke-[3]" /> Active
                                </span>
                              ) : (
                                <button
                                  type="button"
                                  className={`text-xs font-black flex items-center gap-1 transition-colors ${catStyle.accentText} hover:underline`}
                                >
                                  {isLoadingThis ? (
                                    <>
                                      <Loader2 className="animate-spin" size={12} /> Loading...
                                    </>
                                  ) : (
                                    <>
                                      Load <Play size={10} className="fill-current" />
                                    </>
                                  )}
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : presetViewMode === "compact" ? (
                    /* View Mode 2: Compact Tiles View */
                    <div className="template-tiles-grid">
                      {filteredTemplates.map((tpl) => {
                        const tplKey = tpl.id || tpl.filename;
                        const isSelected = activeTemplateId === tplKey;
                        const isLoadingThis = loadingSampleId === tplKey;
                        const catStyle = getCategoryStyle(tpl.category);

                        return (
                          <div
                            key={tplKey}
                            onClick={() => !isLoadingThis && handleSelectTemplate(tpl)}
                            className={`template-tile-card ${
                              isSelected
                                ? `${catStyle.borderActive} scale-[1.02]`
                                : `${catStyle.borderHover}`
                            }`}
                          >
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-1 mb-1">
                                <span className={`px-1.5 py-0.5 rounded text-[9px] font-black uppercase ${catStyle.badge}`}>
                                  {tpl.category || "General"}
                                </span>
                              </div>
                              <h4 className="template-card-title truncate text-xs font-black">
                                {tpl.title || tpl.filename}
                              </h4>
                              {tpl.date && (
                                <span className="text-[9px] font-bold text-slate-500 dark:text-slate-400 block mt-0.5">
                                  {tpl.date}
                                </span>
                              )}
                            </div>

                            <div className="flex-shrink-0 ml-2">
                              {isSelected ? (
                                <span className="w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center font-bold text-xs">
                                  <Check size={13} className="stroke-[3]" />
                                </span>
                              ) : (
                                <span className={`text-xs font-black ${catStyle.accentText}`}>
                                  {isLoadingThis ? (
                                    <Loader2 className="animate-spin" size={12} />
                                  ) : (
                                    <Play size={11} className="fill-current" />
                                  )}
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    /* View Mode 3: Grid Boxes View (Default) */
                    <div className="template-grid">
                      {filteredTemplates.map((tpl) => {
                        const tplKey = tpl.id || tpl.filename;
                        const isSelected = activeTemplateId === tplKey;
                        const isLoadingThis = loadingSampleId === tplKey;
                        const catStyle = getCategoryStyle(tpl.category);

                        return (
                          <div
                            key={tplKey}
                            onClick={() => !isLoadingThis && handleSelectTemplate(tpl)}
                            className={`template-card relative overflow-hidden transition-all duration-300 ${
                              isSelected
                                ? `${catStyle.borderActive} scale-[1.02]`
                                : `${catStyle.borderHover} hover:-translate-y-1`
                            }`}
                          >
                            {/* Selected Card Ambient Color Halo */}
                            {isSelected && (
                              <div
                                className="absolute -top-12 -right-12 w-32 h-32 rounded-full blur-2xl opacity-40 pointer-events-none"
                                style={{ backgroundColor: catStyle.glowDot ? undefined : 'var(--primary)' }}
                              />
                            )}

                            <div>
                              <div className="flex items-center justify-between gap-1 mb-2.5">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider ${catStyle.badge}`}>
                                    {tpl.category || "General"}
                                  </span>
                                  {isSelected && (
                                    <span className="shimmer-active-badge bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                      Loaded
                                    </span>
                                  )}
                                </div>
                                <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 dark:text-slate-400">
                                  {tpl.date && <span>{tpl.date}</span>}
                                  {tpl.date && tpl.size && <span>•</span>}
                                  {tpl.size && <span>{formatBytes(tpl.size)}</span>}
                                </div>
                              </div>
                              <h4 className="template-card-title line-clamp-2">
                                {tpl.title || tpl.filename}
                              </h4>
                              {tpl.description && (
                                <p className="template-card-desc mt-1 line-clamp-2">{tpl.description}</p>
                              )}
                            </div>

                            <div className="template-card-footer">
                              <span className="template-card-type flex items-center gap-1">
                                {tpl.isStarter ? "Starter" : "Preset"}
                              </span>

                              {isSelected ? (
                                <span className={`px-2.5 py-1 rounded-lg text-xs font-black flex items-center gap-1.5 ${catStyle.buttonActive}`}>
                                  <Check size={13} className="stroke-[3]" /> Active
                                </span>
                              ) : (
                                <span className={`text-xs font-black flex items-center gap-1 transition-colors ${catStyle.accentText} hover:underline`}>
                                  {isLoadingThis ? (
                                    <>
                                      <Loader2 className="animate-spin" size={12} /> Loading...
                                    </>
                                  ) : (
                                    <>
                                      Load Preset <Play size={11} className="fill-current" />
                                    </>
                                  )}
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Optional Output Filename Override */}
              <div className="mt-5 border-t border-cardBorder pt-4">
                <label className="block text-xs font-bold uppercase tracking-wider text-mutedText mb-1.5">
                  Custom Output Filename (Optional)
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={customFilename}
                    onChange={(e) => setCustomFilename(e.target.value)}
                    placeholder={
                      file
                        ? file.name.replace(/\.(html|htm)$/i, "")
                        : currentMetadata.title || "My_Presentation"
                    }
                    className="w-full rounded-xl border border-cardBorder bg-card-soft px-3.5 py-2 text-xs font-medium text-mainText outline-none focus:border-accent"
                  />
                </div>
              </div>
            </div>

            {/* Session Conversion History / Download Center */}
            <div className="glass-card rounded-[2rem] p-5 sm:p-6">
              <div className="flex items-center justify-between mb-3 border-b border-cardBorder pb-3">
                <div className="flex items-center gap-2">
                  <Layers size={16} className="text-secondary" />
                  <h3 className="font-extrabold text-sm text-mainText">Recent Session Exports</h3>
                </div>
                {history.length > 0 && (
                  <button
                    type="button"
                    onClick={handleClearHistory}
                    className="text-xs font-bold text-mutedText hover:text-danger flex items-center gap-1"
                  >
                    <Trash2 size={12} /> Clear
                  </button>
                )}
              </div>

              {history.length === 0 ? (
                <div className="py-6 text-center text-xs text-mutedText">
                  No exports in this session yet. Convert a file to see your downloads here.
                </div>
              ) : (
                <div className="flex flex-col gap-2 max-h-60 overflow-y-auto pr-1">
                  {history.map((item) => (
                    <div key={item.id} className="history-item">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <span
                          className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-md ${
                            item.type === "PDF"
                              ? "bg-primary/20 text-primary border border-primary/30"
                              : "bg-secondary/20 text-secondary border border-secondary/30"
                          }`}
                        >
                          {item.type}
                        </span>
                        <div className="min-w-0">
                          <div className="text-xs font-bold text-mainText truncate">{item.name}</div>
                          <div className="text-[10px] text-mutedText">{item.time}</div>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <button
                          type="button"
                          onClick={() => handleCopyDownloadUrl(item.downloadUrl)}
                          className="action-icon-btn"
                          style={{ width: "1.8rem", height: "1.8rem" }}
                          title="Copy Download URL"
                        >
                          <Copy size={12} />
                        </button>
                        <a
                          href={item.downloadUrl}
                          className="action-icon-btn text-success"
                          style={{ width: "1.8rem", height: "1.8rem" }}
                          title="Download File"
                        >
                          <ArrowDownToLine size={13} />
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>

          {/* Right Column: Live Viewport Preview & Export History */}
          <div className="flex flex-col gap-5 min-w-0 animate-fade-in-up" style={{ animationDelay: '0.1s', animationFillMode: 'both' }}>
            {/* Live Interactive Preview Card */}
            <div className="preview-card-ui glass-card magic-border-card transition-all duration-300">
              {/* Preview Toolbar */}
              <div className="preview-toolbar-ui">
                <div className="flex items-center gap-2">
                  <Eye size={16} className="text-primary" />
                  <span className="text-xs font-extrabold text-mainText">Multi-Viewport Preview</span>
                </div>

                <div className="flex items-center gap-2">
                  {/* Aspect Ratio Selector */}
                  <select
                    value={previewViewport}
                    onChange={(e) => setPreviewViewport(e.target.value)}
                    className="preview-aspect-select"
                    title="Select Viewport Aspect Ratio"
                  >
                    <option value="16:9">16:9 Presentation</option>
                    <option value="4:3">4:3 Standard</option>
                    <option value="a4-p">A4 Portrait</option>
                    <option value="a4-l">A4 Landscape</option>
                  </select>

                  {/* Zoom Controls */}
                  <select
                    value={previewZoom}
                    onChange={(e) => setPreviewZoom(e.target.value)}
                    className="preview-aspect-select"
                    title="Preview Zoom"
                  >
                    <option value="fit">Auto Fit</option>
                    <option value="0.5">50%</option>
                    <option value="0.75">75%</option>
                    <option value="1.0">100%</option>
                    <option value="1.25">125%</option>
                  </select>

                  {/* Frame Theme Switcher */}
                  <button
                    type="button"
                    onClick={() =>
                      setPreviewTheme((t) => (t === "dark" ? "light" : t === "light" ? "grid" : "dark"))
                    }
                    className="action-icon-btn"
                    title={`Stage Background: ${previewTheme}`}
                  >
                    <Layout size={14} />
                  </button>

                  {/* Open in New Tab */}
                  <button
                    type="button"
                    onClick={handleOpenInNewTab}
                    className="action-icon-btn"
                    title="Open Fullscreen in New Browser Tab"
                  >
                    <ExternalLink size={14} />
                  </button>

                  {/* Modal Fullscreen Preview */}
                  <button
                    type="button"
                    onClick={() => setIsFullscreen(true)}
                    className="action-icon-btn"
                    title="Expand Fullscreen"
                  >
                    <Maximize2 size={14} />
                  </button>
                </div>
              </div>

              {/* Viewport Frame Stage */}
              <div
                ref={previewStageRef}
                className={`preview-stage-container theme-${previewTheme}`}
              >
                <div ref={previewScaleShellRef} className="preview-scale-shell-ui">
                  <iframe
                    title="Live Presentation Preview"
                    srcDoc={previewSrcDoc}
                    sandbox="allow-scripts allow-forms allow-popups allow-modals allow-downloads"
                    onLoad={updatePreviewScale}
                  />
                </div>
                <div className="preview-hint-ui">
                  {VIEWPORT_DIMENSIONS[previewViewport]?.label.split(" ")[0]} • Scale: {Math.round(previewScale * 100)}%
                </div>
              </div>
            </div>

            {/* Conversion Controls Deck */}
            <div className="glass-card rounded-[2rem] p-5 sm:p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-black text-base text-mainText">Export Actions</h3>
                  <p className="text-xs text-mutedText">Select target export format.</p>
                </div>
                <div className="text-xs font-bold text-mutedText">
                  Shortcut: <kbd className="rounded bg-card-soft px-1.5 py-0.5 border border-border">Ctrl+Enter</kbd>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                {/* PDF Button */}
                <button
                  type="button"
                  disabled={!hasContent || isWorking}
                  onClick={() => convert("pdf")}
                  className="convert-button pdf"
                >
                  {isWorking && activeConversion === "pdf" ? (
                    <Loader2 className="animate-spin flex-shrink-0" size={17} />
                  ) : (
                    <FileText size={17} className="flex-shrink-0" />
                  )}
                  <span className="whitespace-nowrap">{isWorking && activeConversion === "pdf" ? "Exporting..." : "Convert PDF"}</span>
                </button>

                {/* PPTX Button */}
                <button
                  type="button"
                  disabled={!hasContent || isWorking}
                  onClick={() => convert("pptx")}
                  className="convert-button pptx"
                >
                  {isWorking && activeConversion === "pptx" ? (
                    <Loader2 className="animate-spin flex-shrink-0" size={17} />
                  ) : (
                    <Presentation size={17} className="flex-shrink-0" />
                  )}
                  <span className="whitespace-nowrap">{isWorking && activeConversion === "pptx" ? "Exporting..." : "Convert PPTX"}</span>
                </button>

                {/* Dual Convert Both Button */}
                <button
                  type="button"
                  disabled={!hasContent || isWorking}
                  onClick={() => convert("both")}
                  className="convert-button both magic-shine"
                >
                  {isWorking && activeConversion === "both" ? (
                    <Loader2 className="animate-spin flex-shrink-0" size={17} />
                  ) : (
                    <Sparkles size={17} className="flex-shrink-0" />
                  )}
                  <span className="whitespace-nowrap">{isWorking && activeConversion === "both" ? "Converting..." : "Export Both"}</span>
                </button>
              </div>

              {/* Multi-Phase Progress Box */}
              {isWorking && (
                <div className="conversion-progress-box">
                  <div className="flex items-center justify-between text-xs font-bold text-mutedText mb-2">
                    <span>{message}</span>
                    <span>{progress}%</span>
                  </div>

                  <div className="progress-track-ui mb-4">
                    <div className="progress-bar-ui" style={{ width: `${progress}%` }} />
                  </div>

                  {/* 4 Conversion Phases */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-cardBorder">
                    <div
                      className={`phase-step ${
                        conversionPhase === 1 ? "active" : conversionPhase > 1 ? "completed" : ""
                      }`}
                    >
                      <div className="phase-circle">{conversionPhase > 1 ? "✓" : "1"}</div>
                      <span>DOM Parsing</span>
                    </div>

                    <div
                      className={`phase-step ${
                        conversionPhase === 2 ? "active" : conversionPhase > 2 ? "completed" : ""
                      }`}
                    >
                      <div className="phase-circle">{conversionPhase > 2 ? "✓" : "2"}</div>
                      <span>Rendering</span>
                    </div>

                    <div
                      className={`phase-step ${
                        conversionPhase === 3 ? "active" : conversionPhase > 3 ? "completed" : ""
                      }`}
                    >
                      <div className="phase-circle">{conversionPhase > 3 ? "✓" : "3"}</div>
                      <span>Rasterization</span>
                    </div>

                    <div
                      className={`phase-step ${
                        conversionPhase === 4 ? "active" : conversionPhase > 4 ? "completed" : ""
                      }`}
                    >
                      <div className="phase-circle">{progress === 100 ? "✓" : "4"}</div>
                      <span>Packaging</span>
                    </div>
                  </div>

                  <div className="mt-3 text-right text-[11px] font-semibold text-mutedText">
                    Elapsed: {elapsedSeconds}s
                  </div>
                </div>
              )}
            </div>

            {/* Status & Error Message Box */}
            <div
              className={`status-card ${
                status === "success"
                  ? "status-success"
                  : status === "error"
                  ? "status-error"
                  : status === "working"
                  ? "status-working"
                  : "status-ready"
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  {status === "success" && <CheckCircle2 size={20} />}
                  {status === "error" && <XCircle size={20} />}
                  {status === "working" && <Loader2 className="animate-spin" size={20} />}
                  {status === "ready" && <ShieldCheck size={20} />}
                </div>
                <div className="min-w-0 flex-1">
                  <h3>Conversion Status</h3>
                  <p>{message}</p>
                  {error && <pre>{error}</pre>}
                </div>
              </div>
            </div>

            {/* Result Download Box */}
            {result && (
              <div className="glass-card rounded-[2rem] p-5 sm:p-6 border-success/40 bg-success/5">
                <div className="flex items-start gap-4">
                  <div className="success-tile">
                    <CheckCircle2 size={24} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-base font-black text-mainText">Export Completed Successfully!</h3>
                    <p className="mt-0.5 text-xs text-mutedText truncate">{result.outputName}</p>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {result.type === "both" ? (
                        <>
                          <a href={result.pdfResult.downloadUrl} className="download-button">
                            <ArrowDownToLine size={16} />
                            Download PDF
                          </a>
                          <a href={result.pptxResult.downloadUrl} className="download-button bg-secondary">
                            <ArrowDownToLine size={16} />
                            Download PPTX
                          </a>
                        </>
                      ) : (
                        <a href={result.downloadUrl} className="download-button">
                          <ArrowDownToLine size={16} />
                          Download {result.type.toUpperCase()}
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Fullscreen Preview Modal */}
      {isFullscreen && (
        <div className="fullscreen-modal-overlay">
          <div className="fullscreen-modal-header">
            <div className="flex items-center gap-3">
              <Eye size={18} className="text-primary" />
              <span className="font-extrabold text-sm text-white">
                Fullscreen Presentation Preview ({VIEWPORT_DIMENSIONS[previewViewport]?.label})
              </span>
            </div>

            <div className="flex items-center gap-3">
              <select
                value={previewViewport}
                onChange={(e) => setPreviewViewport(e.target.value)}
                className="preview-aspect-select"
              >
                <option value="16:9">16:9 Presentation</option>
                <option value="4:3">4:3 Standard</option>
                <option value="a4-p">A4 Portrait</option>
                <option value="a4-l">A4 Landscape</option>
              </select>

              <button
                type="button"
                onClick={() => setIsFullscreen(false)}
                className="action-icon-btn text-white"
                title="Close Fullscreen (Esc)"
              >
                <Minimize2 size={16} />
              </button>
            </div>
          </div>

          <div
            ref={fullscreenStageRef}
            className={`fullscreen-modal-body theme-${previewTheme}`}
          >
            <div ref={fullscreenScaleShellRef} className="preview-scale-shell-ui">
              <iframe
                title="Fullscreen Presentation Preview"
                srcDoc={previewSrcDoc}
                sandbox="allow-scripts allow-forms allow-popups allow-modals allow-downloads"
                onLoad={updatePreviewScale}
              />
            </div>
            {/* Conversion Controls Deck */}
            <div className="glass-card rounded-[2rem] p-5 sm:p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-black text-base text-mainText">Export Actions</h3>
                  <p className="text-xs text-mutedText">Select target export format.</p>
                </div>
                <div className="text-xs font-bold text-mutedText">
                  Shortcut: <kbd className="rounded bg-card-soft px-1.5 py-0.5 border border-border">Ctrl+Enter</kbd>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                {/* PDF Button */}
                <button
                  type="button"
                  disabled={!hasContent || isWorking}
                  onClick={() => convert("pdf")}
                  className="convert-button pdf"
                >
                  {isWorking && activeConversion === "pdf" ? (
                    <Loader2 className="animate-spin" size={17} />
                  ) : (
                    <FileText size={17} />
                  )}
                  <span>{isWorking && activeConversion === "pdf" ? "Exporting PDF..." : "Convert PDF"}</span>
                </button>

                {/* PPTX Button */}
                <button
                  type="button"
                  disabled={!hasContent || isWorking}
                  onClick={() => convert("pptx")}
                  className="convert-button pptx"
                >
                  {isWorking && activeConversion === "pptx" ? (
                    <Loader2 className="animate-spin" size={17} />
                  ) : (
                    <Presentation size={17} />
                  )}
                  <span>{isWorking && activeConversion === "pptx" ? "Exporting PPTX..." : "Convert PPTX"}</span>
                </button>

                {/* Dual Convert Both Button */}
                <button
                  type="button"
                  disabled={!hasContent || isWorking}
                  onClick={() => convert("both")}
                  className="convert-button both"
                >
                  {isWorking && activeConversion === "both" ? (
                    <Loader2 className="animate-spin" size={17} />
                  ) : (
                    <Sparkles size={17} />
                  )}
                  <span>{isWorking && activeConversion === "both" ? "Converting..." : "Export Both"}</span>
                </button>
              </div>

              {/* Multi-Phase Progress Box */}
              {isWorking && (
                <div className="conversion-progress-box">
                  <div className="flex items-center justify-between text-xs font-bold text-mutedText mb-2">
                    <span>{message}</span>
                    <span>{progress}%</span>
                  </div>

                  <div className="progress-track-ui mb-4">
                    <div className="progress-bar-ui" style={{ width: `${progress}%` }} />
                  </div>

                  {/* 4 Conversion Phases */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-cardBorder">
                    <div
                      className={`phase-step ${
                        conversionPhase === 1 ? "active" : conversionPhase > 1 ? "completed" : ""
                      }`}
                    >
                      <div className="phase-circle">{conversionPhase > 1 ? "✓" : "1"}</div>
                      <span>DOM Parsing</span>
                    </div>

                    <div
                      className={`phase-step ${
                        conversionPhase === 2 ? "active" : conversionPhase > 2 ? "completed" : ""
                      }`}
                    >
                      <div className="phase-circle">{conversionPhase > 2 ? "✓" : "2"}</div>
                      <span>Rendering</span>
                    </div>

                    <div
                      className={`phase-step ${
                        conversionPhase === 3 ? "active" : conversionPhase > 3 ? "completed" : ""
                      }`}
                    >
                      <div className="phase-circle">{conversionPhase > 3 ? "✓" : "3"}</div>
                      <span>Rasterization</span>
                    </div>

                    <div
                      className={`phase-step ${
                        conversionPhase === 4 ? "active" : conversionPhase > 4 ? "completed" : ""
                      }`}
                    >
                      <div className="phase-circle">{progress === 100 ? "✓" : "4"}</div>
                      <span>Packaging</span>
                    </div>
                  </div>

                  <div className="mt-3 text-right text-[11px] font-semibold text-mutedText">
                    Elapsed: {elapsedSeconds}s
                  </div>
                </div>
              )}
            </div>

            {/* Status & Error Message Box */}
            <div
              className={`status-card ${
                status === "success"
                  ? "status-success"
                  : status === "error"
                  ? "status-error"
                  : status === "working"
                  ? "status-working"
                  : "status-ready"
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  {status === "success" && <CheckCircle2 size={20} />}
                  {status === "error" && <XCircle size={20} />}
                  {status === "working" && <Loader2 className="animate-spin" size={20} />}
                  {status === "ready" && <ShieldCheck size={20} />}
                </div>
                <div className="min-w-0 flex-1">
                  <h3>Conversion Status</h3>
                  <p>{message}</p>
                  {error && <pre>{error}</pre>}
                </div>
              </div>
            </div>

            {/* Result Download Box */}
            {result && (
              <div className="glass-card rounded-[2rem] p-5 sm:p-6 border-success/40 bg-success/5">
                <div className="flex items-start gap-4">
                  <div className="success-tile">
                    <CheckCircle2 size={24} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-base font-black text-mainText">Export Completed Successfully!</h3>
                    <p className="mt-0.5 text-xs text-mutedText truncate">{result.outputName}</p>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {result.type === "both" ? (
                        <>
                          <a href={result.pdfResult.downloadUrl} className="download-button">
                            <ArrowDownToLine size={16} />
                            Download PDF
                          </a>
                          <a href={result.pptxResult.downloadUrl} className="download-button bg-secondary">
                            <ArrowDownToLine size={16} />
                            Download PPTX
                          </a>
                        </>
                      ) : (
                        <a href={result.downloadUrl} className="download-button">
                          <ArrowDownToLine size={16} />
                          Download {result.type.toUpperCase()}
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Toast Notification Container */}
      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className="toast-message">
            {t.type === "success" && <CheckCircle2 size={16} className="text-success" />}
            {t.type === "error" && <ShieldAlert size={16} className="text-danger" />}
            {t.type === "info" && <Sparkles size={16} className="text-primary" />}
            <span>{t.msg}</span>
          </div>
        ))}
      </div>
    </main>
  );
}
