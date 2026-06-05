from fastapi import FastAPI, UploadFile, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import shutil
import PyPDF2
import os

from main import career_pilot_graph
from db.database import init_db, insert_user, get_sent_jobs, get_all_users
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager

def run_daily_hunt():
    """
    This is the CRON task that loops through all registered users and finds them jobs every morning!
    """
    print("\n⏰ [CRON JOB STARTED] Executing Morning Universal Agent Hunting...")
    users = get_all_users()
    for user in users:
        user_id, email, preferred_job, locations, resume_text = user
        previously_sent = get_sent_jobs(user_id)
        
        print(f"-> Hunting for User: {email} | Locations: {locations}")
        
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
        except Exception as e:
            print(f"❌ Graph crashed for user {email}:", e)
    
    print("[CRON JOB COMPLETED]\n")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Database on boot
    init_db()
    
    # Initialize the Cron Scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_hunt, 'cron', hour=9, minute=0, timezone='Asia/Kolkata') # Runs daily at 9:00 AM IST
    scheduler.start()
    print("⏰ APScheduler Cron Job Armed for 9:00 AM IST daily!")
    
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
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

@app.get("/api/debug")
async def debug_pipeline():
    """
    Diagnostic endpoint to test every stage of the pipeline.
    Hit this to see exactly where things break on HF Spaces.
    """
    import json as json_mod
    from agents.scout_agent import serper_search, is_direct_job_url
    from agents.config import llm as configured_llm
    
    results = {
        "env_vars": {},
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
        "LLM_TYPE": str(type(configured_llm).__name__) if configured_llm else "None"
    }
    
    # 2. Test Serper - raw HTTP call to see actual response
    try:
        import http.client
        import json as json_lib
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json_lib.dumps({"q": "AI Engineer jobs India", "num": 3, "gl": "in", "hl": "en"})
        headers = {'X-API-KEY': os.getenv("SERPER_API_KEY", ""), 'Content-Type': 'application/json'}
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
    
    # 3. Test URL filter on real results
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
    
    # 4. Test LLM
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
        results["serper_test"].get("status") == "OK" and
        results["llm_test"].get("status") == "OK"
    )
    results["overall"] = "ALL_SYSTEMS_GO" if all_ok else "ISSUES_DETECTED"
    
    return results

def run_onboarding_workflow(resume_path: str, email: str, locations: str):
    """
    Fires immediately when the user uploads a resume strictly for onboarding.
    """
    print("\n-------------------------------------------")
    print(f"🚀 [NEW USER ONBOARDING] Triggering First Scout!")
    print(f"   Locations: {locations}")
    print("-------------------------------------------\n")
    
    resume_text = ""
    try:
        with open(resume_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    resume_text += text
    except Exception as e:
        print("Failed to read PDF:", e)
        return
        
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
        print("❌ LangGraph workflow crashed:", str(e))
    
    print("\n[ONBOARDING COMPLETED]\n")

@app.post("/api/initialize")
async def initialize_pipeline(
    background_tasks: BackgroundTasks,
    resume: UploadFile,
    email: str = Form(...),
    locations: str = Form(...)
):
    if not os.path.exists("data"):
        os.makedirs("data")
        
    file_location = f"data/{resume.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(resume.file, buffer)
        
    # Kickoff the LangGraph agent in the background so the UI doesn't crash!
    background_tasks.add_task(run_onboarding_workflow, file_location, email, locations)
    
    return {"message": "Agents Dispatched Successfully!"}

if __name__ == "__main__":
    import uvicorn
    print("\n===========================================")
    print("Starting FastAPI Autonomous Recruiter Server...")
    print("Open your browser to: http://127.0.0.1:8000")
    print("===========================================\n")
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
