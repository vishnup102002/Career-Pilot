import os
import smtplib
from email.mime.text import MIMEText
from agents.state import AgentState
from db.database import log_sent_job

def alert_node(state: AgentState):
    print("\n🚨 AlertAgent: Dispatching Email Notification...")
    
    draft = state.get('drafted_response', '')
    
    # Log sent jobs to SQLite so we NEVER send them tomorrow morning!
    for url in state.get('extracted_urls', []):
        log_sent_job(state['user_id'], url)
    print("💽 Deduplication: Logged sent job URLs to SQLite database!")

    # Email Notification
    try:
        sender = os.getenv("EMAIL_SENDER")
        password = os.getenv("EMAIL_PASSWORD")
        target_email = state.get("email_address", sender).strip()
        
        if sender and password:
            msg = MIMEText(f"{draft}")
            msg['Subject'] = 'Career-Pilot 🚀 Your Daily Agentic Job Hunt'
            msg['From'] = sender
            msg['To'] = target_email
            
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(sender, password)
            server.send_message(msg)
            server.quit()
            print("✅ Email Alert Fired Successfully!")
        else:
            print("⚠️ Skipping Email Notification: Missing .env keys")
    except Exception as e:
        print("❌ SMTP Email failed:", str(e))
        
    return {"human_approval": "alerted"}
