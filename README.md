---
title: Career-Pilot
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# 🚀 Career-Pilot

[![Live App](https://img.shields.io/badge/🤗%20Hugging%20Face-Live%20App-FF9D00?style=for-the-badge&logo=huggingface&logoColor=white)](https://huggingface.co/spaces/Vishnuporkulath/career-pilot)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Stateful%20Agents-00C853?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **Career-Pilot** is an agentic, stateful ecosystem built on **LangGraph** and the **Model Context Protocol (MCP)** to bridge the "Context Gap" in technical job hunting. Instead of sending low-quality bulk applications, Career-Pilot focuses on **High-Intent Alignment**: discovering targeted technical roles, performing deep semantic matching against a candidate's resume, drafting personalized job listings, and alerting the candidate directly via email with precise application targets.

---

## 🚀 Key Value Proposition & Architecture Overview

Modern job hunting is bottlenecked by generic, high-volume applications that rarely convert. **Career-Pilot** bridges this gap:

- **High-Intent Targeting** — Discovers technical roles semantically aligned to the candidate's actual skills, not just keyword matches.
- **Autonomous Pipeline** — Four specialized LangGraph nodes run sequentially from resume parsing to email delivery with no manual steps.
- **Serverless Scraping** — A custom FastMCP browser server runs headless Playwright or premium Apify/Jina services client-side, bypassing SPA rendering traps without exposing infrastructure.

<div align="center">
  <br />
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 600" width="100%" height="100%">
    <defs>
      <style>
        .bg { fill: #05070d; rx: 8px; stroke: #0f172a; stroke-width: 2; }
        .header-title { font-family: 'Space Grotesk', 'Fira Code', monospace; font-size: 13px; fill: #38bdf8; font-weight: 700; letter-spacing: 1.5px; }
        .container-box { fill: rgba(15, 23, 42, 0.4); stroke: #1e293b; stroke-width: 1.5; rx: 8px; }
        .box { fill: #0f172a; stroke: #1e293b; stroke-width: 1.5; rx: 6px; }
        .box-active { fill: #0c1a2e; stroke: #38bdf8; stroke-width: 1.5; rx: 6px; }
        .box-mcp { fill: #082f25; stroke: #10b981; stroke-width: 1.5; rx: 6px; }
        .box-dedupe { fill: #2a1b08; stroke: #f59e0b; stroke-width: 1.5; rx: 6px; }
        .box-alert { fill: #220a11; stroke: #f43f5e; stroke-width: 1.5; rx: 6px; }
        .txt-title { font-family: 'Inter', sans-serif; font-size: 11px; fill: #f8fafc; font-weight: 700; }
        .txt-sub { font-family: 'JetBrains Mono', monospace; font-size: 9px; fill: #94a3b8; }
        .txt-mcp { font-family: 'JetBrains Mono', monospace; font-size: 9px; fill: #6ee7b7; }
        .line { stroke: #334155; stroke-width: 2; fill: none; stroke-dasharray: 4 4; }
        .status { font-family: 'JetBrains Mono', monospace; font-size: 10px; fill: #10b981; font-weight: 700; }
      </style>
      <filter id="glow-cyan" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="3" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
      <filter id="glow-green" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="3" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
      <filter id="glow-gold" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="3" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
    </defs>

    <!-- Background -->
    <rect width="1000" height="600" class="bg" />
    <text x="25" y="32" class="header-title">> CAREER-PILOT // END-TO-END AGENTIC PIPELINE ARCHITECTURE</text>

    <!-- Flow Paths -->
    <path id="path-top" d="M 160 90 L 230 90 M 370 90 L 440 90 M 580 90 L 650 90" class="line" />
    <path id="path-ingest" d="M 800 115 L 800 150 L 150 150 L 150 200" class="line" />
    <path id="path-agents" d="M 230 260 L 270 260 M 450 260 L 490 260 M 670 260 L 710 260" class="line" />
    <path id="path-mcp" d="M 360 310 L 360 410" class="line" />
    <path id="path-dedupe" d="M 800 310 L 800 450 L 690 450" class="line" />
    <path id="path-inbox" d="M 800 310 L 800 500" class="line" />

    <!-- 1. TOP ROW: INGESTION TIER -->
    <g transform="translate(25, 65)">
      <rect width="135" height="50" class="box" />
      <text x="12" y="20" class="txt-title">Candidate UI</text>
      <text x="12" y="35" class="txt-sub">Resume PDF / Prefs</text>
    </g>

    <g transform="translate(235, 65)">
      <rect width="135" height="50" class="box-active" />
      <text x="12" y="20" class="txt-title">FastAPI Router</text>
      <text x="12" y="35" class="txt-sub">PyPDF2 Parser</text>
    </g>

    <g transform="translate(445, 65)">
      <rect width="135" height="50" class="box" />
      <text x="12" y="20" class="txt-title">SQLite User DB</text>
      <text x="12" y="35" class="txt-sub">Candidate Profile</text>
    </g>

    <g transform="translate(655, 65)">
      <rect width="290" height="50" class="box-active" />
      <text x="14" y="20" class="txt-title">LangGraph State Machine</text>
      <text x="14" y="35" class="txt-sub">typed_state: AgentState Dict</text>
    </g>

    <!-- 2. MIDDLE CONTAINER: LANGGRAPH 4-AGENT PIPELINE -->
    <rect x="25" y="160" width="950" height="200" class="container-box" />
    <text x="40" y="185" class="header-title" font-size="10px" fill="#94a3b8">LANGGRAPH SEQUENTIAL AGENT PIPELINE</text>

    <!-- Agent 1: Research -->
    <g transform="translate(50, 200)">
      <rect width="180" height="120" class="box" />
      <text x="14" y="24" class="txt-title">1. RESEARCH NODE</text>
      <text x="14" y="48" class="txt-sub">• Resume Parsing</text>
      <text x="14" y="66" class="txt-sub">• Role Inference</text>
      <text x="14" y="84" class="txt-sub">• Skills Vectorizing</text>
      <text x="14" y="102" class="txt-sub">• Save Inferred Role</text>
    </g>

    <!-- Agent 2: Scout -->
    <g transform="translate(270, 200)">
      <rect width="180" height="120" class="box-active" />
      <text x="14" y="24" class="txt-title">2. SCOUT NODE</text>
      <text x="14" y="48" class="txt-sub">• Multi-query Serper</text>
      <text x="14" y="66" class="txt-sub">• Direct URL Filter</text>
      <text x="14" y="84" class="txt-sub">• FastMCP Scraping</text>
      <text x="14" y="102" class="txt-sub">• LLM Fit Score (≥3)</text>
    </g>

    <!-- Agent 3: Writer -->
    <g transform="translate(490, 200)">
      <rect width="180" height="120" class="box-active" />
      <text x="14" y="24" class="txt-title">3. WRITER NODE</text>
      <text x="14" y="48" class="txt-sub">• Resume-Job Match</text>
      <text x="14" y="66" class="txt-sub">• Source Tagging</text>
      <text x="14" y="84" class="txt-sub">• Alignment Bullet</text>
      <text x="14" y="102" class="txt-sub">• Pitch Drafting</text>
    </g>

    <!-- Agent 4: Alert -->
    <g transform="translate(710, 200)">
      <rect width="180" height="120" class="box-alert" />
      <text x="14" y="24" class="txt-title" fill="#f43f5e">4. ALERT NODE</text>
      <text x="14" y="48" class="txt-sub">• Dispatch Email</text>
      <text x="14" y="66" class="txt-sub">• SendGrid / Resend</text>
      <text x="14" y="84" class="txt-sub">• Log Dispatched URLs</text>
      <text x="14" y="102" class="txt-sub">• Complete Execution</text>
    </g>

    <!-- 3. BOTTOM TIER COMPONENTS -->
    <!-- FastMCP Server -->
    <g transform="translate(260, 410)">
      <rect width="200" height="80" class="box-mcp" />
      <text x="14" y="22" class="txt-title" fill="#10b981">MCP TOOL SERVER</text>
      <text x="14" y="42" class="txt-mcp">• Playwright Headless SPA</text>
      <text x="14" y="58" class="txt-mcp">• Jina Reader Markdown</text>
    </g>

    <!-- Deduplication Index -->
    <g transform="translate(490, 410)">
      <rect width="200" height="80" class="box-dedupe" />
      <text x="14" y="22" class="txt-title" fill="#f59e0b">PERSISTENT DEDUPE</text>
      <text x="14" y="42" class="txt-sub" fill="#fde68a">• SQLite sent_jobs Table</text>
      <text x="14" y="58" class="txt-sub" fill="#fde68a">• Zero Duplicate Guarantee</text>
    </g>

    <!-- User Inbox -->
    <g transform="translate(720, 500)">
      <rect width="160" height="45" class="box-alert" />
      <text x="14" y="20" class="txt-title" fill="#f43f5e">User Inbox Alert</text>
      <text x="14" y="34" class="txt-sub">Daily Job Digest Email</text>
    </g>

    <!-- 4. SMIL ANIMATED LIGHT PULSES -->
    <circle r="5" fill="#38bdf8" filter="url(#glow-cyan)">
      <animateMotion dur="3s" repeatCount="indefinite" path="M 160 90 L 230 90 M 370 90 L 440 90 M 580 90 L 650 90" />
    </circle>

    <circle r="6" fill="#38bdf8" filter="url(#glow-cyan)">
      <animateMotion dur="4s" repeatCount="indefinite" path="M 800 115 L 800 150 L 150 150 L 150 200 M 230 260 L 270 260 M 450 260 L 490 260 M 670 260 L 710 260" />
    </circle>

    <circle r="5" fill="#10b981" filter="url(#glow-green)">
      <animateMotion dur="2.2s" repeatCount="indefinite" path="M 360 310 L 360 410" />
    </circle>

    <circle r="5" fill="#f59e0b" filter="url(#glow-gold)">
      <animateMotion dur="2.5s" repeatCount="indefinite" path="M 800 310 L 800 450 L 690 450" />
    </circle>

    <circle r="5" fill="#f43f5e">
      <animateMotion dur="2s" repeatCount="indefinite" path="M 800 310 L 800 500" />
    </circle>

    <!-- 5. FOOTER TELEMETRY -->
    <line x1="25" y1="565" x2="975" y2="565" stroke="#1e293b" stroke-width="1" />
    <text x="25" y="582" class="status">● CRON: APSCHEDULER (9:00 AM IST)</text>
    <text x="360" y="582" class="status" fill="#38bdf8">LLM: GEMINI 2.0 FLASH ↔ GROQ LLAMA 3.1 8B</text>
    <text x="770" y="582" class="status" fill="#f59e0b">DEDUPE: SQLITE UNIQUE INDEX</text>
  </svg>
  <br />
</div>

---

## 🤖 Agent Pipeline & State Machine

Career-Pilot orchestrates four distinct specialized agents within a stateful workflow built on LangGraph. The pipeline passes a shared `AgentState` TypedDict containing candidate metadata, resume summaries, scraped listings, and dispatch status across all nodes.

### Agent Responsibilities

| Agent / Node | Role | Key Output / Action |
| :--- | :--- | :--- |
| **📚 Research Agent** (`research`) | Parses uploaded resume to extract a structured technical DNA report — core stacks, years of experience, location constraints, and best-fit role inference. Updates the user's inferred job role in SQLite database. | `resume_summary`, `preferred_job` |
| **🕵️ Scout Agent** (`scout`) | Generates multi-variant search queries against LinkedIn, Indeed, Naukri, and WeWorkRemotely; filters aggregator URLs; cleans markdown boilerplate; extracts experience requirements; pre-filters experience mismatches; runs headless Playwright scraping via FastMCP (with premium Jina/Apify options); and scores listings (score ≥ 3/5). | `found_jobs` (filtered match text), `extracted_urls` |
| **✍️ Writer Agent** (`writer`) | Maps job relevance to resume history; tags listings with source platform markers (📍 via LinkedIn, 📍 via Indeed); builds a high-impact bulleted catalog. | `drafted_response` |
| **🚨 Alert Agent** (`alert`) | Delivers the formatted catalog via SendGrid, Resend, or Gmail SMTP; permanently indexes dispatched URLs in SQLite on success to prevent duplicate alerts. | Email sent + `extracted_urls` logged in DB |

---

## 🛠️ System Architecture & Data Flow

Career-Pilot uses a decoupled, modular design divided into a **FastAPI server** (orchestrator + web UI) and a **LangGraph pipeline** (inference and agent execution engine).

```mermaid
sequenceDiagram
    autonumber
    actor User as Candidate
    participant Server as FastAPI Server / Cron
    participant DB as SQLite DB
    participant LG as LangGraph Pipeline
    participant MCP as Browser MCP (Playwright/Jina)
    participant Email as Email Service (SendGrid/Resend/SMTP)

    User->{Server}: Uploads resume + locations
    Server->>DB: Fetches previously sent job URLs (if any)
    DB->>Server: Returns URL exclusion list
    Server->>LG: Triggers graph execution with initial AgentState
    
    note over LG: [research Node]
    LG->>LG: Parses resume DNA & infers best-fit job role
    LG->>DB: Updates user's preferred job in DB
    
    note over LG: [scout Node]
    LG->>LG: Generates search queries & retrieves Serper results
    LG->>MCP: Requests deep SPA/page scraping for top URLs
    MCP->>LG: Returns full scraped text (Jina/Playwright)
    LG->>LG: Filters out stale jobs & scores matches (LLM) using URL exclusion list
    
    note over LG: [writer Node]
    LG->>LG: Formats matches into email catalog with source tags
    
    note over LG: [alert Node]
    LG->>Email: Dispatches personalized daily job catalog
    Email->>User: Delivers targeted job alert email
    LG->>DB: Permanently logs newly sent job URLs for deduplication
```

---

## 📂 Project Structure

```
.
├── main.py                    # LangGraph compiler — defines state graph and execution edges
├── api.py                     # FastAPI router — onboarding endpoint, static views, APScheduler cron
├── keep_alive.py              # Hugging Face Space Keep-Alive background utility
├── Dockerfile                 # Docker configuration for Hugging Face Spaces deployment
├── Procfile                   # Process file for Heroku/Render deployment
├── nixpacks.toml              # Nixpacks build configuration
├── requirements.txt           # Python project dependencies
├── agents/
│   ├── state.py               # AgentState TypedDict (user params, scraped jobs, output emails)
│   ├── config.py              # LLM client bootstrap with dynamic quota-based switchover
│   ├── research_agent.py      # research_node — extracts credentials & infers job role from resume
│   ├── scout_agent.py         # scout_node — query builder, Serper search, MCP scraper, boilerplate cleaning, LLM scoring
│   ├── writer_agent.py        # writer_node — structures job matches into personalized catalog
│   └── alert_agent.py         # alert_node — email dispatch (SendGrid / Resend / Gmail SMTP) + DB logger
├── mcp_servers/
│   └── browser_mcp.py         # FastMCP Server providing Playwright, Jina Reader & Apify batch scrapers
├── db/
│   └── database.py            # SQLite schema configuration, user management, and URL logging
├── evaluation/
│   ├── test_cases.json        # Mock scenarios for testing the matching engine
│   ├── eval_harness.py        # LLM-as-a-Judge benchmark scoring script
│   └── eval_report.md         # Generated benchmark evaluation results
├── tests/
│   ├── conftest.py            # Pytest fixtures and SQLite in-memory test DB setup
│   ├── test_agents.py         # Unit tests for Research, Scout, Writer & Alert nodes
│   ├── test_api.py            # Integration tests for FastAPI router & endpoint validation
│   ├── test_database.py       # Unit tests for SQLite database schema & CRUD helpers
│   └── test_integration.py    # End-to-end integration and URL deduplication test suite
├── static/
│   ├── index.html             # Glassmorphic onboarding page front-end
│   ├── app.js                 # Tag inputs, city autocomplete, and AJAX handler
│   ├── style.css              # Custom responsive glassmorphism styles and animations
│   ├── robots.txt             # Search engine crawler instructions
│   └── sitemap.xml            # Sitemap for SEO indexing
└── .github/
    └── workflows/
        └── keep_alive.yml     # GitHub Action scheduling keep-alive pings
```

---

## 📦 Local Installation & Configuration

### Prerequisites

- [Python 3.11+](https://www.python.org/)
- [Node.js](https://nodejs.org/) (for custom MCP integrations)
- [Playwright](https://playwright.dev/) browsers

### 1. Clone & Set Up

```bash
git clone https://github.com/vishnup102002/Career-Pilot.git
cd Career-Pilot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium --with-deps
```

### 2. Configure Environment Variables

Copy the provided secure environment template to `.env` and fill in your keys:

```bash
cp .env.example .env
```

### Environment Variables Details

| Variable | Required / Optional | Description |
|---|---|---|
| `GOOGLE_API_KEY` | Required (if `USE_GEMINI=true`) | Gemini API access key. Used for `gemini-2.0-flash`. |
| `GROQ_API_KEY` | Required (if no Gemini key) | Groq API access key. Falls back to `llama-3.1-8b-instant`. |
| `USE_GEMINI` | Optional (Default: `false`) | Prioritizes Gemini over Groq for processing when set to `true`. |
| `SERPER_API_KEY` | **Required** | Google Serper.dev API key to fetch organic Google search results. |
| `SENDGRID_API_KEY` | Optional | Transactional email delivery API key. |
| `EMAIL_SENDER` | Optional | Verified sender address for SendGrid/Gmail SMTP. |
| `RESEND_API_KEY` | Optional | Transactional email delivery key via Resend. |
| `EMAIL_PASSWORD` | Optional | App password generated for Gmail SMTP email dispatch (Local only). |
| `APIFY_API_TOKEN` | Optional | Apify token to use their premium RAG web browser actor for headless scraping. |
| `JINA_API_KEY` | Optional | Jina Reader token to speed up and authenticate web parsing. |

### 3. Initialize SQLite Schema

```bash
python db/database.py
```

### 4. Start the Application

```bash
python api.py
```

Open your browser to `http://127.0.0.1:8000` to access the onboarding page.

---

## 🏥 Production Health Check & Monitoring

Career-Pilot includes a production-grade diagnostic endpoint:
- **`GET /api/health`**: Returns real-time JSON report detailing system uptime, SQLite statistics (total users, logged emails), LLM connectivity status, and third-party environment credentials presence. Extremely useful for hosting platforms like Hugging Face Spaces or Uptime Kuma monitors.

---

## 🌎 Production Deployment & Hosting

### Deploying to Hugging Face Spaces (Docker SDK)

1. Configure your Space to use the **Docker SDK**.
2. The custom `Dockerfile` handles the Python 3.11 environment, installs OS dependencies for Chromium, downloads Playwright runtimes, and launches Uvicorn on port `7860`.
3. Add the environment secrets inside the Space settings console.
4. **Persistent Database Storage**: SQLite database persistent storage is fully supported on Hugging Face Spaces. Create a persistent storage mount at `/data` in Space Settings (Storage Buckets), or pass the path via `HF_BUCKET_PATH` env var to prevent data loss when the space restarts.

---

## 📡 Hugging Face Space Keep-Alive Utility

Since free Hugging Face Spaces go to sleep automatically after periods of inactivity (which pauses all internal schedulers/cron jobs), we provide a dedicated utility to keep the Space active or wake it up before the daily search cron triggers at 9:00 AM IST.

### Local Daemon Mode
You can run the keep-alive script locally as a daemon in the background:
```bash
# Ping the space every 30 minutes to prevent it from sleeping
python keep_alive.py --url https://your-space-name.hf.space --daemon --interval 30

# Alternatively, schedule it to run once every morning at 08:45 AM IST (to wake up the space for the 9:00 AM cron)
python keep_alive.py --url https://your-space-name.hf.space --daemon --morning-only
```

### GitHub Actions Workflow (Serverless / Recommended)
We have configured a GitHub Actions workflow in `.github/workflows/keep_alive.yml`. This workflow runs:
1. Every 6 hours to prevent the Hugging Face Space from entering deep sleep.
2. Specifically at 03:15 UTC (08:45 AM IST) to wake the Space up right before the morning cron triggers.

**Setup**:
1. Push this repository to GitHub.
2. Add your space direct URL (e.g. `https://vishnuporkulath-career-pilot.hf.space`) as a GitHub Repository Secret named `APP_URL`.

---

## 🧪 Quality Assurance, Tracing & Evaluation

### 1. LangSmith Integration (Automatic Agent Tracing)
Since `langsmith` is included in our dependencies and Career-Pilot uses standard LangChain/LangGraph model components, you can enable comprehensive state graph tracing simply by adding the following to your `.env` file:
```ini
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY="your-langsmith-api-key-here"
LANGCHAIN_PROJECT="career-pilot"
```

### 2. End-to-End Test Suite
We have implemented a comprehensive 81-test E2E test suite covering unit level, integration flows, SQLite database managers, safety controls (preventing email HTML injections), experience mismatch pre-filtering, and FastAPI routing.

To run the automated tests:
```bash
python -m pytest tests/ -v
```

To run with coverage reporting:
```bash
python -m pytest tests/ -v --cov=. --cov-report=term-missing
```

### 3. LLM-as-a-Judge Evaluation Suite
We have implemented a custom benchmark evaluation harness located under the `evaluation/` directory. It uses mock candidate scenarios and job postings to evaluate the scout matching agent's performance.

To run the evaluation:
```bash
python evaluation/eval_harness.py
```

The script will:
- Run the agent's matching algorithm on scenarios in `evaluation/test_cases.json`.
- Compute performance metrics: **Accuracy, Precision, Recall, and F1-Score**.
- Run an independent **LLM-as-a-Judge** to evaluate the factual correctness and quality of the agent's matching reasoning (scored 1-5).
- Print a diagnostic summary and save a markdown report to `evaluation/eval_report.md`.


---

## 📈 Future Roadmap

- [ ] **Interactive Mock Interviews** — Generate tailored technical questions based on the candidate's exact target roles.
- [ ] **Salary Intelligence** — Integrate real-time market data to recommend optimum salary ranges during job selection.
- [ ] **Cross-Platform HITL Approvals** — Support WhatsApp/Telegram callbacks to approve and edit drafts directly from chat.

---

## 📜 License

Licensed under the [MIT License](LICENSE). Created by **Vishnu P**.
