import os
import requests
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
        sender = os.getenv("EMAIL_SENDER", "").strip()
        api_key = os.getenv("SENDGRID_API_KEY", "").strip()
        target_email = state.get("email_address", sender).strip()
        
        if sender and api_key:
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "personalizations": [{"to": [{"email": target_email}]}],
                "from": {"email": sender, "name": "Career-Pilot"},
                "subject": "Career-Pilot 🚀 Your Daily Agentic Job Hunt",
                "content": [{"type": "text/plain", "value": draft}]
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            print("✅ SendGrid API Alert Fired Successfully!")
        else:
            print("⚠️ Skipping Email Notification: Missing SENDGRID_API_KEY")
    except Exception as e:
        print("❌ SendGrid API Email failed:", str(e))
        
    return {"human_approval": "alerted"}
