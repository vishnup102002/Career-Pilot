import logging
import os
import re
import time
import shutil

import PyPDF2
from fastapi import FastAPI, UploadFile, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from main import career_pilot_graph
from db.database import init_db, insert_user, get_sent_jobs, get_all_users, get_db_stats, DATA_DIR, DB_PATH
from agents.config import check_llm_health
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager

# ── Structured Logging Setup ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("career_pilot.api")

# ── Constants ──
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf", ".txt"}
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
START_TIME = time.time()


def run_daily_hunt():
    """
    This is the CRON task that loops through all registered users and finds them jobs every morning!
    """
    logger.info("⏰ [CRON JOB STARTED] Executing Morning Universal Agent Hunting...")
    users = get_all_users()
    
    if not users:
        logger.warning("   ⚠️ No registered users found in database!")
        logger.info("   📁 DB Path: %s", DB_PATH)
        logger.info("   💡 Users must onboard via /api/initialize first.")
        logger.info("[CRON JOB COMPLETED]")
        return
    
    logger.info("   👥 Found %d registered user(s)", len(users))
    
    for user in users:
        user_id, email, preferred_job, locations, resume_text = user
        previously_sent = get_sent_jobs(user_id)
        
        logger.info("-> Hunting for User: %s | Job: %s | Locations: %s", email, preferred_job, locations)
        logger.info("   Previously sent: %d job URLs", len(previously_sent))
        
        initial_state = {
            "user_id": user_id,
            "email_address": email,
            "preferred_job": preferred_job,
            "locations": locations,
            "resume_text": resume_text,
            "previously_sent_jobs": previously_sent,
            "job_url": "" 
        }
        try:
            career_pilot_graph.invoke(initial_state)
            logger.info("   ✅ Pipeline completed for %s", email)
        except Exception as e:
            logger.exception("   ❌ Graph crashed for user %s: %s", email, e)
    
    logger.info("[CRON JOB COMPLETED]")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Database on boot
    init_db()
    
    # Initialize the Cron Scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_hunt, 'cron', hour=9, minute=0, timezone='Asia/Kolkata') # Runs daily at 9:00 AM IST
    scheduler.start()
    logger.info("⏰ APScheduler Cron Job Armed for 9:00 AM IST daily!")
    
    yield
    scheduler.shutdown()

app = FastAPI(
    title="Career-Pilot",
    description="AI Agentic Job Hunter — Autonomous job matching and email alerting",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/robots.txt")
async def get_robots():
    return FileResponse("static/robots.txt", media_type="text/plain")

@app.get("/sitemap.xml")
async def get_sitemap():
    return FileResponse("static/sitemap.xml", media_type="application/xml")

@app.get("/api/health")
async def health_check():
    """
    Production health check endpoint.
    Returns system status for monitoring, load balancers, and HF Spaces.
    """
    uptime_seconds = int(time.time() - START_TIME)
    
    return {
        "status": "healthy",
        "uptime_seconds": uptime_seconds,
        "database": get_db_stats(),
        "llm": check_llm_health(),
        "env": {
            "SERPER_API_KEY": bool(os.getenv("SERPER_API_KEY")),
            "SENDGRID_API_KEY": bool(os.getenv("SENDGRID_API_KEY")),
            "RESEND_API_KEY": bool(os.getenv("RESEND_API_KEY")),
            "EMAIL_SENDER": bool(os.getenv("EMAIL_SENDER")),
            "SPACE_ID": os.getenv("SPACE_ID", "local"),
        },
    }

@app.get("/api/debug")
async def debug_pipeline():
    """
    Diagnostic endpoint to test every stage of the pipeline.
    Hit this to see exactly where things break on HF Spaces.
    """
    import json as json_mod
    import sqlite3
    from agents.scout_agent import serper_search, is_direct_job_url
    from agents.config import llm as configured_llm
    
    results = {
        "env_vars": {},
        "database": {},
        "serper_test": {},
        "url_filter_test": {},
        "llm_test": {},
        "overall": "UNKNOWN"
    }
    
    # 1. Check env vars
    results["env_vars"] = {
        "SERPER_API_KEY": bool(os.getenv("SERPER_API_KEY")),
        "SERPER_KEY_PREFIX": os.getenv("SERPER_API_KEY", "")[:8] + "..." if os.getenv("SERPER_API_KEY") else "MISSING",
        "GROQ_API_KEY": bool(os.getenv("GROQ_API_KEY")),
        "GOOGLE_API_KEY": bool(os.getenv("GOOGLE_API_KEY")),
        "USE_GEMINI": os.getenv("USE_GEMINI", "false"),
        "LLM_LOADED": configured_llm is not None,
        "LLM_TYPE": str(type(configured_llm).__name__) if configured_llm else "None",
        "SENDGRID_API_KEY": bool(os.getenv("SENDGRID_API_KEY")),
        "SENDGRID_KEY_PREFIX": os.getenv("SENDGRID_API_KEY", "")[:8] + "..." if os.getenv("SENDGRID_API_KEY") else "MISSING",
        "EMAIL_SENDER": bool(os.getenv("EMAIL_SENDER")),
        "EMAIL_SENDER_VALUE": os.getenv("EMAIL_SENDER", ""),
        "SPACE_ID": os.getenv("SPACE_ID", "NOT_ON_HF"),
    }
    
    # 2. Database diagnostics
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM sent_jobs")
        sent_count = cursor.fetchone()[0]
        cursor.execute("SELECT id, email, preferred_job, locations FROM users")
        user_list = [{"id": r[0], "email": r[1], "preferred_job": r[2], "locations": r[3]} for r in cursor.fetchall()]
        conn.close()
        results["database"] = {
            "status": "OK",
            "db_path": DB_PATH,
            "data_dir": DATA_DIR,
            "user_count": user_count,
            "sent_jobs_count": sent_count,
            "users": user_list
        }
    except Exception as e:
        results["database"] = {"status": "ERROR", "error": str(e), "db_path": DB_PATH}
    
    # 3. Test Serper - raw HTTP call to see actual response
    try:
        import http.client
        import json as json_lib
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json_lib.dumps({"q": "AI Engineer jobs India", "num": 3, "gl": "in", "hl": "en"})
        headers = {'X-API-KEY': os.getenv("SERPER_API_KEY", "").strip(), 'Content-Type': 'application/json'}
        conn.request("POST", "/search", payload, headers)
        res = conn.getresponse()
        raw_data = res.read().decode("utf-8")
        raw_json = json_lib.loads(raw_data)
        
        organic = raw_json.get("organic", [])
        results["serper_test"] = {
            "status": "OK" if organic else "EMPTY",
            "http_status": res.status,
            "count": len(organic),
            "raw_keys": list(raw_json.keys()),
            "raw_snippet": raw_data[:500] if not organic else None,
            "sample": [{"title": r.get("title","")[:60], "url": r.get("link","")[:80]} for r in organic[:3]]
        }
    except Exception as e:
        results["serper_test"] = {"status": "ERROR", "error": str(e)}
    
    # 4. Test URL filter on real results
    if results["serper_test"].get("status") == "OK":
        try:
            site_results = serper_search("site:linkedin.com/jobs/view/ AI Engineer India", num_results=5)
            direct = [r for r in site_results if is_direct_job_url(r.get("href", ""))]
            results["url_filter_test"] = {
                "status": "OK",
                "site_query_count": len(site_results),
                "direct_after_filter": len(direct),
                "sample_direct": [{"title": r.get("title","")[:60], "url": r.get("href","")[:80]} for r in direct[:3]]
            }
        except Exception as e:
            results["url_filter_test"] = {"status": "ERROR", "error": str(e)}
    
    # 5. Test LLM
    if configured_llm:
        try:
            from langchain_core.messages import HumanMessage
            resp = configured_llm.invoke([HumanMessage(content="Reply with only the word: WORKING")])
            results["llm_test"] = {
                "status": "OK",
                "response": resp.content[:50]
            }
        except Exception as e:
            results["llm_test"] = {"status": "ERROR", "error": str(e)}
    else:
        results["llm_test"] = {"status": "NO_LLM", "error": "No LLM configured"}
    
    # Overall
    all_ok = (
        results["env_vars"]["SERPER_API_KEY"] and
        results["env_vars"]["LLM_LOADED"] and
        results["env_vars"]["SENDGRID_API_KEY"] and
        results["serper_test"].get("status") == "OK" and
        results["llm_test"].get("status") == "OK" and
        results["database"].get("status") == "OK"
    )
    results["overall"] = "ALL_SYSTEMS_GO" if all_ok else "ISSUES_DETECTED"
    
    return results

def run_onboarding_workflow(resume_path: str, email: str, locations: str):
    """
    Fires immediately when the user uploads a resume strictly for onboarding.
    """
    logger.info("🚀 [NEW USER ONBOARDING] Triggering First Scout!")
    logger.info("   Email: %s", email)
    logger.info("   Locations: %s", locations)
    
    resume_text = ""
    try:
        with open(resume_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    resume_text += text
    except Exception as e:
        logger.error("Failed to read PDF: %s", e)
        return
    
    if not resume_text.strip():
        logger.error("❌ Resume PDF was empty or unreadable!")
        return
    
    logger.info("   📄 Extracted %d chars from resume", len(resume_text))
        
    # Inject user into the permanent SQLite Database!
    user_id = insert_user(email, locations, resume_text)
    
    # Grab whatever jobs we have ALREADY sent them (none so far, but prevents bugs)
    previously_sent = get_sent_jobs(user_id)
    
    try:
        initial_state = {
            "user_id": user_id,
            "email_address": email,
            "preferred_job": "",
            "locations": locations,
            "resume_text": resume_text,
            "previously_sent_jobs": previously_sent,
            "job_url": ""
        }
        # Run Universal Orchestrator!
        career_pilot_graph.invoke(initial_state)
    except Exception as e:
        logger.exception("❌ LangGraph workflow crashed: %s", str(e))
    
    logger.info("[ONBOARDING COMPLETED]")

@app.post("/api/initialize")
async def initialize_pipeline(
    background_tasks: BackgroundTasks,
    resume: UploadFile,
    email: str = Form(...),
    locations: str = Form(...)
):
    # ── Input Validation ──
    
    # Validate email format
    email = email.strip()
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Invalid email address format.")
    
    # Validate locations
    locations = locations.strip()
    if not locations or len(locations) < 2:
        raise HTTPException(status_code=400, detail="Please provide at least one valid location.")
    if len(locations) > 500:
        raise HTTPException(status_code=400, detail="Locations text is too long (max 500 chars).")

    # Validate file extension
    filename = resume.filename or ""
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file_ext}'. Only {', '.join(ALLOWED_EXTENSIONS)} are allowed."
        )
    
    # Validate file size (read content to check)
    content = await resume.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(content)} bytes). Maximum size is {MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB."
        )
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    
    # Save the file
    file_location = os.path.join(DATA_DIR, filename)
    with open(file_location, "wb") as buffer:
        buffer.write(content)
        
    logger.info("📤 New upload: %s (%d bytes) from %s", filename, len(content), email)
    
    # Kickoff the LangGraph agent in the background so the UI doesn't crash!
    background_tasks.add_task(run_onboarding_workflow, file_location, email, locations)
    
    return {"message": "Agents Dispatched Successfully!"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI Autonomous Recruiter Server...")
    logger.info("Open your browser to: http://127.0.0.1:8000")
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
