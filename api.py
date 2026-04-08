from fastapi import FastAPI, UploadFile, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import shutil
import PyPDF2

# Import the actual LangGraph logic!
from main import career_pilot_graph

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

def run_agentic_workflow(resume_path: str, email: str, whatsapp: str):
    """
    This background task ties everything together: UI -> API -> PDF Parse -> LangGraph -> WhatsApp/Email
    """
    print("\n-------------------------------------------")
    print(f"🚀 [BACKGROUND AGENT STARTED]")
    print("-------------------------------------------\n")
    
    # 1. Parse the injected Resume
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
        
    # 2. Invoke the massive LangGraph Orchestration
    # It will hit the Scout -> Research -> Writer -> Alert nodes and trigger external APIs
    try:
        initial_state = {
            "job_url": "https://company.com/cool-job",
            "whatsapp_number": whatsapp,
            "email_address": email,
            "resume_text": resume_text
        }
        # Run it natively
        career_pilot_graph.invoke(initial_state)
    except Exception as e:
        print("❌ LangGraph workflow crashed:", str(e))
    
    print("\n[BACKGROUND AGENT COMPLETED]\n")

@app.post("/api/initialize")
async def initialize_pipeline(
    background_tasks: BackgroundTasks,
    resume: UploadFile,
    email: str = Form(...),
    whatsapp: str = Form(...)
):
    # Save the file temporarily
    file_location = f"db/{resume.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(resume.file, buffer)
        
    # Run the brain asynchronously
    background_tasks.add_task(run_agentic_workflow, file_location, email, whatsapp)
    
    return {"message": "Agents Dispatched Successfully!"}

if __name__ == "__main__":
    import uvicorn
    print("\n===========================================")
    print("Starting FastAPI Backend Server...")
    print("Open your browser to: http://127.0.0.1:8000")
    print("===========================================\n")
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
