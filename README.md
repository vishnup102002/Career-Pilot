Markdown
---
title: Career Pilot
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Career-Pilot: Autonomous MCP & LangGraph Driven Job Intelligence Engine

[![Hugging Face Space](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Space-blue)](https://huggingface.co/spaces/Vishnuporkulath/career-pilot)
[![Python 3.11](https://img.shields.io/badge/python-3.11-green.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Career-Pilot** is an agentic, stateful ecosystem built on [LangGraph](https://github.com/langchain-ai/langgraph) and the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) to bridge the "Context Gap" in technical job hunting. Instead of sending low-quality bulk applications, Career-Pilot focuses on **High-Intent Alignment**: discovering targeted technical roles, performing deep semantic matching against a candidate's resume, drafting personalized job listings, and alerting the candidate directly via email with precise application targets.

The live application is hosted on Hugging Face Spaces: [Career-Pilot Live App](https://huggingface.co/spaces/Vishnuporkulath/career-pilot).

---

## 🗺️ System Architecture & Workflow

Career-Pilot orchestrates four distinct specialized agents within a stateful, cyclic workflow built on LangGraph. Here is the operational state graph:

```mermaid
graph TD
    Start((Start Onboarding / Daily Cron)) --> ResearchNode["📚 ResearchAgent<br/>(Analyze Resume & Ideal Role)"]
    ResearchNode --> ScoutNode["🕵️ ScoutAgent<br/>(Optimized Job Hunting Searches)"]
    ScoutNode --> MatchEngine["🧠 LLM Scoring Engine<br/>(Generous Profile Matching)"]
    MatchEngine --> WriterNode["✍️ WriterAgent<br/>(Format Personalized Email List)"]
    WriterNode --> AlertNode["🚨 AlertAgent<br/>(SendGrid Email & SQLite Dedup)"]
    AlertNode --> End((End Workflow))
    
    subgraph State Management [LangGraph TypedDict State]
        direction LR
        StateVar["• user_id<br/>• resume_summary<br/>• preferred_job<br/>• found_jobs<br/>• drafted_response<br/>• extracted_urls"]
    end
🛠️ Tech Stack & Key Files
Core Technologies
Stateful Orchestration: LangGraph (Dynamic multi-agent node transition and memory preservation).

Protocol Standard: Model Context Protocol (MCP) using fastmcp to interface tool-calling agents with browser runtimes.

LLM Backends: Dual client support for Google Gemini (gemini-2.0-flash) and Groq (llama-3.1-8b-instant) for speed and reliability.

Database Layer: Native SQLite database (data/career_pilot.db) to track user metadata and deduplicate previously sent listings.

Web UI: Modern responsive Glassmorphic dashboard built using FastAPI, HTML5, Vanilla CSS, and custom async JS.

Workspace Directory Structure
main.py: The primary LangGraph compiler defining the state graph and sequential execution edges.

api.py: FastAPI web router hosting the onboarding API endpoint, static views, and the universal APScheduler daily cron job.

agents/:

state.py: Defines the state dictionary (AgentState) containing user parameters, scraped jobs, and output emails.

config.py: Bootstraps LLM clients with dynamic switchovers based on API quotas.

research_agent.py: Holds the research_node which extracts technical credentials from uploaded resumes.

scout_agent.py: Holds the scout_node managing Google Serper.dev searches, filtering, and LLM matching.

writer_agent.py: Holds the writer_node structuring job match details into a personalized pitch.

alert_agent.py: Holds the alert_node sending email reports via SendGrid and logging target URLs to SQLite.

mcp_servers/:

browser_mcp.py: A custom FastMCP server running Playwright under the hood to perform deep client-side scraping for single-page applications (SPAs).

db/:

database.py: Manages SQL schema setups (init_db), new user insertions, preferred job logs, and duplicate exclusions.

🤖 Dynamic Agent Pipeline
1. The Research Agent
Reads the user's raw uploaded resume to run structured parsing. It generates a standardized technical DNA report highlighting core stacks (e.g., Python, RAG, Kubernetes), years of experience, and location constraints. It also infers the single best-fitting role (e.g. Junior AI Engineer, Staff Frontend Developer).

2. The Scout Agent & Custom Browser MCP
Flashes out multi-variant search queries matching the candidate's profile to retrieve organic listings across LinkedIn, Indeed, Naukri, and WeWorkRemotely.

Direct Job URL Filter: Uses advanced heuristics to reject generalized indexing pages, aggregators, or search queries, focusing strictly on target-rich job application links.

FastMCP Integration: Connects to the local browser_mcp.py running headless Playwright. It bypasses classic SPA rendering traps to extract inner page layout text.

LLM Score Matcher: Scores jobs out of 5 across role titles, location restrictions, required experience levels, education constraints, and skill overlaps. It returns listings with scoring >= 3/5.

3. The Writer Agent
Refines the matches, mapping their technical relevance directly to the candidate's resume history. It tags jobs with source platform markers (📍 via LinkedIn, 📍 via Indeed) and constructs a high-impact, short, bulleted catalog.

4. The Alert & Deduplication Agent
SendGrid Deliverability: Pushes the formatted listing catalog straight to the candidate's email address.

SQLite Memory Lock: Ensures that the same job is never suggested twice. Every dispatched URL is permanently indexed to prevent spamming.

📦 Local Setup & Deployment
Prerequisites
Python 3.11+

Node.js (for custom MCP integrations)

Playwright browsers

1. Clone & Set Up Directory
Bash
git clone [https://github.com/vishnup102002/Career-Pilot.git](https://github.com/vishnup102002/Career-Pilot.git)
cd Career-Pilot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium --with-deps
2. Configure Environment Variables
Create a .env file in the root directory:

Ini, TOML
# Central LLM Configurations
GOOGLE_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
USE_GEMINI=true   # Set to true to prioritize Gemini over Groq

# Search Engine Configuration
SERPER_API_KEY=your_serper_dev_api_key_here

# Delivery Config
SENDGRID_API_KEY=your_sendgrid_api_key_here
EMAIL_SENDER=sender_verified_email@domain.com
3. Initialize SQLite Schema
Bash
python db/database.py
4. Start the Application
Run the FastAPI application locally:

Bash
python api.py
Open your browser to http://127.0.0.1:8000 to access the onboarding page.

🌎 Deploying to Hugging Face Spaces (Docker SDK)
To build and deploy your own instance of Career-Pilot on Hugging Face Spaces:

Make sure your Space settings are configured to use the Docker SDK.

The custom Dockerfile handles python-3.11 environment setup, installs OS dependencies for Chromium, downloads Playwright runtimes, and launches Uvicorn on port 7860.

Add the environment secrets (GOOGLE_API_KEY, SERPER_API_KEY, SENDGRID_API_KEY, etc.) inside the Space settings console.

📈 Future Roadmap
[ ] Interactive Mock Interviews: Generate tailored mock technical questions based on the candidate's exact target roles.

[ ] Salary Intelligence: Integrate real-time market data to recommend optimum salary ranges during target job selection.

[ ] Cross-Platform HITL approvals: Support WhatsApp/Telegram callbacks to approve and edit drafts directly from standard chat applications.


---
