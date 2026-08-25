export const SAMPLE_TEMPLATES = [
  {
    id: "executive-pitch",
    title: "Executive Business Pitch",
    description: "3-slide executive deck with cover, key metrics, and strategic pillars.",
    category: "Presentation",
    slidesCount: 3,
    html: `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Executive Strategy Deck</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; }
    body { background: #0f172a; color: #f8fafc; }
    .deck { display: flex; flex-direction: column; gap: 40px; padding: 40px; align-items: center; }
    .slide {
      width: 1366px;
      height: 768px;
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
      border-radius: 20px;
      padding: 60px 80px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
      border: 1px solid rgba(255, 255, 255, 0.1);
      position: relative;
      overflow: hidden;
      page-break-after: always;
    }
    .slide::before {
      content: "";
      position: absolute;
      top: -100px;
      right: -100px;
      width: 400px;
      height: 400px;
      background: radial-gradient(circle, rgba(99, 102, 241, 0.25) 0%, transparent 70%);
      pointer-events: none;
    }
    .header-tag {
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 2px;
      text-transform: uppercase;
      color: #38bdf8;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    h1 { font-size: 54px; font-weight: 800; line-height: 1.1; color: #ffffff; margin-top: 15px; }
    h2 { font-size: 38px; font-weight: 700; color: #ffffff; }
    .subtitle { font-size: 22px; color: #94a3b8; margin-top: 15px; max-width: 800px; line-height: 1.5; }
    .hero-badge {
      display: inline-block;
      padding: 8px 18px;
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.4);
      color: #38bdf8;
      border-radius: 30px;
      font-size: 16px;
      font-weight: 600;
    }
    .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-top: 40px; }
    .card {
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      padding: 30px;
      backdrop-filter: blur(10px);
    }
    .card h3 { font-size: 22px; color: #f8fafc; margin-bottom: 12px; }
    .card p { font-size: 16px; color: #94a3b8; line-height: 1.6; }
    .stat-num { font-size: 48px; font-weight: 800; color: #38bdf8; margin-bottom: 8px; }
    .footer-bar { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 20px; color: #64748b; font-size: 14px; }
  </style>
</head>
<body>
  <div class="deck">
    <!-- Slide 1: Cover -->
    <section class="slide">
      <div>
        <span class="hero-badge">Confidential • Strategic Blueprint 2026</span>
        <h1 style="margin-top: 30px;">Next-Gen Enterprise Cloud & AI Acceleration</h1>
        <p class="subtitle">Scaling digital capabilities, driving automation, and establishing resilient cloud architecture for global operations.</p>
      </div>
      <div class="footer-bar">
        <span>Global Strategy & Technology Advisory</span>
        <span>Slide 01 / 03</span>
      </div>
    </section>

    <!-- Slide 2: Key Metrics -->
    <section class="slide">
      <div>
        <div class="header-tag">Impact Metrics</div>
        <h2 style="margin-top: 10px;">Demonstrated Performance at Scale</h2>
        <p class="subtitle">Key operational achievements following modern platform migration.</p>
        <div class="grid-3">
          <div class="card">
            <div class="stat-num">99.99%</div>
            <h3>Platform Uptime</h3>
            <p>Achieved enterprise-grade high availability across 4 global multi-region deployments.</p>
          </div>
          <div class="card">
            <div class="stat-num">4.8x</div>
            <h3>Deployment Speed</h3>
            <p>Accelerated release cycles from monthly deployments to automated continuous delivery.</p>
          </div>
          <div class="card">
            <div class="stat-num">38%</div>
            <h3>Cost Optimization</h3>
            <p>Reduced infrastructure overhead via automated autoscaling and serverless compute.</p>
          </div>
        </div>
      </div>
      <div class="footer-bar">
        <span>Operational Excellence KPIs</span>
        <span>Slide 02 / 03</span>
      </div>
    </section>

    <!-- Slide 3: Strategic Pillars -->
    <section class="slide">
      <div>
        <div class="header-tag">Roadmap Pillars</div>
        <h2 style="margin-top: 10px;">Three Core Transformation Tracks</h2>
        <p class="subtitle">Actionable milestones structured across technology, people, and governance.</p>
        <div class="grid-3">
          <div class="card">
            <h3>1. Intelligent Automation</h3>
            <p>Embedding AI copilot agents and workflow orchestration across core business pipelines.</p>
          </div>
          <div class="card">
            <h3>2. Zero-Trust Security</h3>
            <p>Unified identity federation, dynamic role-based access, and real-time audit logging.</p>
          </div>
          <div class="card">
            <h3>3. Data Mesh Fabric</h3>
            <p>Democratized data access with centralized governance and real-time analytics engines.</p>
          </div>
        </div>
      </div>
      <div class="footer-bar">
        <span>Target Operating Model</span>
        <span>Slide 03 / 03</span>
      </div>
    </section>
  </div>
</body>
</html>`
  },
  {
    id: "architecture-flow",
    title: "System Architecture & Data Flow",
    description: "Single 16:9 landscape architecture diagram slide with step pipelines.",
    category: "Architecture",
    slidesCount: 1,
    html: `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Architecture Flow Diagram</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; }
    body { background: #0b0f19; color: #f1f5f9; }
    .slide {
      width: 1366px;
      height: 768px;
      background: radial-gradient(circle at 10% 20%, #1e1e38 0%, #0b0f19 80%);
      padding: 50px 70px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      position: relative;
    }
    .badge {
      display: inline-block;
      padding: 6px 14px;
      border-radius: 20px;
      background: rgba(168, 85, 247, 0.2);
      border: 1px solid rgba(168, 85, 247, 0.4);
      color: #c084fc;
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    h1 { font-size: 36px; font-weight: 800; color: #ffffff; margin-top: 12px; }
    .subtitle { font-size: 16px; color: #94a3b8; margin-top: 6px; }
    .pipeline {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin: 30px 0;
    }
    .node {
      flex: 1;
      background: rgba(26, 32, 53, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
    }
    .node-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
    .node-num {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: #6366f1;
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 800;
    }
    .node h3 { font-size: 17px; font-weight: 700; color: #f8fafc; }
    .node p { font-size: 13px; color: #94a3b8; line-height: 1.5; }
    .node-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }
    .node-tag {
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.06);
      color: #cbd5e1;
    }
    .arrow { font-size: 24px; color: #6366f1; font-weight: bold; }
    .footer { display: flex; justify-content: space-between; color: #64748b; font-size: 13px; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 15px; }
  </style>
</head>
<body>
  <div class="slide">
    <div>
      <span class="badge">Architecture Specification</span>
      <h1>End-to-End HTML Document Conversion Pipeline</h1>
      <p class="subtitle">Distributed headless Chromium rendering, DOM rasterization, and vector PDF/PPTX packaging pipeline.</p>
    </div>

    <div class="pipeline">
      <div class="node">
        <div class="node-header">
          <div class="node-num">1</div>
          <h3>DOM Ingestion</h3>
        </div>
        <p>Parses HTML structure, extracts slide tags, normalizes viewport width and viewport meta tags.</p>
        <div class="node-tags">
          <span class="node-tag">HTML5</span>
          <span class="node-tag">BeautifulSoup</span>
        </div>
      </div>

      <div class="arrow">➔</div>

      <div class="node" style="border-color: rgba(99, 102, 241, 0.4);">
        <div class="node-header">
          <div class="node-num" style="background:#8b5cf6;">2</div>
          <h3>Chromium Engine</h3>
        </div>
        <p>Launches headless Playwright browser, enforces high-DPI scaling (2.0x), and evaluates dynamic scripts.</p>
        <div class="node-tags">
          <span class="node-tag">Playwright</span>
          <span class="node-tag">Proactor Async</span>
        </div>
      </div>

      <div class="arrow">➔</div>

      <div class="node">
        <div class="node-header">
          <div class="node-num" style="background:#06b6d4;">3</div>
          <h3>Slide Rasterizer</h3>
        </div>
        <p>Captures pixel-perfect screenshots of distinct slide elements with zero margin clipping.</p>
        <div class="node-tags">
          <span class="node-tag">Parallel Workers</span>
          <span class="node-tag">PNG Buffers</span>
        </div>
      </div>

      <div class="arrow">➔</div>

      <div class="node" style="border-color: rgba(16, 185, 129, 0.4);">
        <div class="node-header">
          <div class="node-num" style="background:#10b981;">4</div>
          <h3>Package Exporter</h3>
        </div>
        <p>Assembles vector PDF pages via ReportLab or builds editable PowerPoint presentation deck (.pptx).</p>
        <div class="node-tags">
          <span class="node-tag">python-pptx</span>
          <span class="node-tag">ReportLab</span>
        </div>
      </div>
    </div>

    <div class="footer">
      <span>Unified Conversion Engine v2.0</span>
      <span>16:9 Standard Resolution (1366x768)</span>
    </div>
  </div>
</body>
</html>`
  },
  {
    id: "kpi-dashboard",
    title: "Executive KPI & Performance Matrix",
    description: "High-contrast corporate dashboard slide with KPIs, charts, and milestones.",
    category: "Dashboard",
    slidesCount: 1,
    html: `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Q3 Executive Performance Dashboard</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; }
    body { background: #0a0e1a; color: #f8fafc; }
    .slide {
      width: 1366px;
      height: 768px;
      background: #0f172a;
      padding: 48px 64px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .top-bar { display: flex; justify-content: space-between; align-items: flex-start; }
    h1 { font-size: 34px; font-weight: 800; color: #ffffff; }
    .date-badge { background: #1e293b; border: 1px solid #334155; padding: 8px 16px; border-radius: 8px; font-size: 14px; font-weight: 600; color: #94a3b8; }
    .kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 24px 0; }
    .kpi-box {
      background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 14px;
      padding: 22px;
    }
    .kpi-label { font-size: 13px; color: #94a3b8; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px; }
    .kpi-val { font-size: 36px; font-weight: 900; color: #ffffff; margin: 8px 0 4px; }
    .kpi-change { font-size: 13px; font-weight: 700; color: #10b981; display: flex; align-items: center; gap: 4px; }
    .kpi-change.up { color: #10b981; }
    .kpi-change.down { color: #f43f5e; }
    .main-content { display: grid; grid-template-columns: 1.4fr 1fr; gap: 24px; }
    .section-box {
      background: #1e293b;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 14px;
      padding: 24px;
    }
    .section-title { font-size: 16px; font-weight: 700; color: #f8fafc; margin-bottom: 16px; }
    .bar-item { margin-bottom: 14px; }
    .bar-label { display: flex; justify-content: space-between; font-size: 13px; color: #cbd5e1; margin-bottom: 6px; font-weight: 600; }
    .bar-track { height: 10px; background: #334155; border-radius: 999px; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 999px; }
    .footer { display: flex; justify-content: space-between; font-size: 13px; color: #64748b; border-top: 1px solid #1e293b; padding-top: 14px; }
  </style>
</head>
<body>
  <div class="slide">
    <div class="top-bar">
      <div>
        <h1>Q3 2026 Executive Performance Dashboard</h1>
        <p style="color: #94a3b8; margin-top: 4px; font-size: 15px;">Consolidated business metrics across enterprise transformation initiatives.</p>
      </div>
      <div class="date-badge">Reporting Period: Q3 FY26</div>
    </div>

    <div class="kpi-row">
      <div class="kpi-box">
        <div class="kpi-label">Annual Recurring Revenue</div>
        <div class="kpi-val">$48.2M</div>
        <div class="kpi-change up">▲ +24.6% YoY</div>
      </div>
      <div class="kpi-box">
        <div class="kpi-label">Customer Retention</div>
        <div class="kpi-val">97.4%</div>
        <div class="kpi-change up">▲ +1.8% vs Plan</div>
      </div>
      <div class="kpi-box">
        <div class="kpi-label">Net Promoter Score</div>
        <div class="kpi-val">+72</div>
        <div class="kpi-change up">▲ Top Decile</div>
      </div>
      <div class="kpi-box">
        <div class="kpi-label">Avg. Service Latency</div>
        <div class="kpi-val">18ms</div>
        <div class="kpi-change up">▼ -32% Reduction</div>
      </div>
    </div>

    <div class="main-content">
      <div class="section-box">
        <div class="section-title">Strategic Goal Completion Rates</div>
        <div class="bar-item">
          <div class="bar-label"><span>Cloud Infrastructure Modernization</span><span>94%</span></div>
          <div class="bar-track"><div class="bar-fill" style="width: 94%; background: #6366f1;"></div></div>
        </div>
        <div class="bar-item">
          <div class="bar-label"><span>Enterprise Security & Compliance Alignment</span><span>88%</span></div>
          <div class="bar-track"><div class="bar-fill" style="width: 88%; background: #38bdf8;"></div></div>
        </div>
        <div class="bar-item">
          <div class="bar-label"><span>AI Workflow Automation Integration</span><span>76%</span></div>
          <div class="bar-track"><div class="bar-fill" style="width: 76%; background: #10b981;"></div></div>
        </div>
      </div>

      <div class="section-box">
        <div class="section-title">Key Highlights</div>
        <ul style="list-style: none; font-size: 14px; color: #cbd5e1; line-height: 1.8;">
          <li>✓ Complete zero-downtime migration of primary database clusters.</li>
          <li>✓ Onboarded 14 new global tier-1 enterprise customers.</li>
          <li>✓ Achieved SOC2 Type II and ISO 27001 renewal certifications.</li>
        </ul>
      </div>
    </div>

    <div class="footer">
      <span>Enterprise Performance Operations</span>
      <span>Confidential • Internal Distribution Only</span>
    </div>
  </div>
</body>
</html>`
  }
];
