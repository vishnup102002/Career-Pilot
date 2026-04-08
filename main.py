import os
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
from typing import TypedDict
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()
if os.getenv("GROQ_API_KEY"):
    llm = ChatGroq(model="llama-3.1-8b-instant")
else:
    llm = None

class AgentState(TypedDict):
    job_url: str
    whatsapp_number: str
    email_address: str
    resume_text: str  # Dynamically passed from API parsing
    job_description: str
    extracted_skills: str
    resume_matches: str
    drafted_response: str
    human_approval: str

def scout_node(state: AgentState):
    print(f"🕵️  ScoutAgent: Scouting job at {state['job_url']}")
    job_desc = "We are looking for a Software Engineer proficient in Python, React, and building highly scalable backend architectures."
    messages = [
        SystemMessage(content="You are a Technical Scout. Extract the Must-Have and Nice-to-Have skills from the job description. Return ONLY a comma-separated list of skills."),
        HumanMessage(content=job_desc)
    ]
    response = llm.invoke(messages) if llm else type('obj', (object,), {'content': 'Python, React'})()
    return {"job_description": job_desc, "extracted_skills": response.content}

def research_node(state: AgentState):
    print("📚 ResearchAgent: Reading the uploaded Resume...")
    # Analyzing the dynamic resume text uploaded by the Web UI
    messages = [
        SystemMessage(content="You are a Research Assistant. Read this resume text and summarize it into 2 bullet points highlighting their best skills for engineering."),
        HumanMessage(content=state.get('resume_text', 'No resume text')[:4000]) 
    ]
    response = llm.invoke(messages) if llm else type('obj', (object,), {'content': 'Great Dev'})()
    return {"resume_matches": response.content}

def writer_node(state: AgentState):
    print("✍️  WriterAgent: Drafting the cover letter...")
    prompt = f"""
    Write a short 'Why I am a good fit' message (max 3 sentences).
    Required Skills: {state['extracted_skills']}
    My Resume Summary: {state['resume_matches']}
    Be direct.
    """
    response = llm.invoke([HumanMessage(content=prompt)]) if llm else type('obj', (object,), {'content': 'I am hired!'})()
    return {"drafted_response": response.content}

def alert_node(state: AgentState):
    print("\n🚨 AlertAgent: Dispatching WhatsApp and Email Communications...")
    
    # 1. WhatsApp Dispatch via Twilio
    try:
        tw_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
        twilio_number = os.getenv("TWILIO_PHONE_NUMBER", "whatsapp:+14155238886")
        
        # Format the user's inputted number
        target = state.get("whatsapp_number", "").strip()
        if not target.startswith("whatsapp:"):
            if not target.startswith("+"): target = "+" + target
            target = "whatsapp:" + target
            
        tw_client.messages.create(
            body=f"Career-Pilot Orchestrator:\n\nWe successfully drafted an application for the job you provided!\n\nCover Letter Draft:\n{state['drafted_response']}",
            from_=twilio_number,
            to=target
        )
        print("✅ WhatsApp Alert Fired Successfully!")
    except Exception as e:
        print("❌ Twilio Alert failed (check Keys):", str(e))
        
    # 2. Email Dispatch via SMTP
    try:
        sender = os.getenv("EMAIL_SENDER")
        password = os.getenv("EMAIL_PASSWORD")
        target_email = state.get("email_address", sender).strip()
        
        if sender and password:
            msg = MIMEText(f"Agentic Pipeline Complete.\n\nCover Letter Draft:\n{state['drafted_response']}\n\nBest,\nYour Personal AI")
            msg['Subject'] = 'Career-Pilot 🚀 Auto-Job Output'
            msg['From'] = sender
            msg['To'] = target_email
            
            # For Gmail, you *MUST* use an App Password generated from Google Security Settings
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(sender, password)
            server.send_message(msg)
            server.quit()
            print("✅ Email Alert Fired Successfully!")
        else:
            print("⚠️ Skipping Email Notification: Set EMAIL_SENDER and EMAIL_PASSWORD in .env")
    except Exception as e:
        print("❌ SMTP Email failed (check App Password):", str(e))
        
    return {"human_approval": "alerted"}


workflow = StateGraph(AgentState)
workflow.add_node("scout", scout_node)
workflow.add_node("research", research_node)
workflow.add_node("writer", writer_node)
workflow.add_node("alert", alert_node)

workflow.add_edge(START, "scout")
workflow.add_edge("scout", "research")
workflow.add_edge("research", "writer")
workflow.add_edge("writer", "alert")
workflow.add_edge("alert", END)

career_pilot_graph = workflow.compile()
