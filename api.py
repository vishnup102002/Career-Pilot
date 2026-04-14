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
    scheduler.add_job(run_daily_hunt, 'cron', hour=9, minute=0) # Runs daily at 9:00 AM
    scheduler.start()
    print("⏰ APScheduler Cron Job Armed for 9:00 AM daily!")
    
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
    if not os.path.exists("db"):
        os.makedirs("db")
        
    file_location = f"db/{resume.filename}"
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
