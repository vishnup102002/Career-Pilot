import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from agents.state import AgentState
from db.database import log_sent_job

def alert_node(state: AgentState):
    print("\n🚨 AlertAgent: Dispatching Email Notification...")
    
    draft = state.get('drafted_response', '')
    
    # Guard: If no draft or no matches, skip email entirely
    if not draft or not draft.strip() or "NO STRICT MATCHES FOUND TODAY" in draft:
        print("⚠️ AlertAgent: No jobs to send (draft is empty or no matches). Skipping email.")
        return {"human_approval": "skipped_no_matches"}

    target_email = state.get("email_address", "").strip()
    if not target_email:
        print("❌ AlertAgent: No target email address in state!")
        return {"human_approval": "email_config_error"}

    email_sent = False

    # ── METHOD 1: Gmail SMTP (free, reliable, uses Google App Password) ──
    gmail_sender = os.getenv("EMAIL_SENDER", "").strip()
    gmail_password = os.getenv("EMAIL_PASSWORD", "").strip()
    
    if gmail_sender and gmail_password:
        print(f"   📧 Sending via Gmail SMTP...")
        print(f"   📧 From: {gmail_sender}")
        print(f"   📧 To: {target_email}")
        print(f"   📧 Draft length: {len(draft)} chars")
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Career-Pilot 🚀 Your Daily Agentic Job Hunt"
            msg["From"] = f"Career-Pilot <{gmail_sender}>"
            msg["To"] = target_email
            
            # Plain text version
            msg.attach(MIMEText(draft, "plain"))
            
            # HTML version (makes links clickable in email)
            html_draft = draft.replace("\n", "<br>")
            # Make URLs clickable
            import re
            html_draft = re.sub(
                r'(https?://[^\s<>]+)',
                r'<a href="\1">\1</a>',
                html_draft
            )
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2563eb;">🚀 Career-Pilot: Your Daily Job Hunt</h2>
                    <hr style="border: 1px solid #e5e7eb;">
                    <div style="margin-top: 16px;">
                        {html_draft}
                    </div>
                    <hr style="border: 1px solid #e5e7eb; margin-top: 24px;">
                    <p style="font-size: 12px; color: #9ca3af;">
                        Sent by Career-Pilot AI Agent • Your autonomous job hunter
                    </p>
                </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(html_body, "html"))
            
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(gmail_sender, gmail_password)
                server.sendmail(gmail_sender, target_email, msg.as_string())
            
            print("   ✅ Gmail SMTP: Email sent successfully!")
            email_sent = True
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"   ❌ Gmail Auth Failed: {e}")
            print(f"   💡 Fix: Generate a new App Password at https://myaccount.google.com/apppasswords")
        except smtplib.SMTPRecipientsRefused as e:
            print(f"   ❌ Recipient refused: {e}")
        except smtplib.SMTPException as e:
            print(f"   ❌ Gmail SMTP error: {e}")
        except Exception as e:
            print(f"   ❌ Gmail unexpected error: {type(e).__name__}: {e}")
    
    # ── METHOD 2: SendGrid API (fallback if Gmail not configured) ──
    if not email_sent:
        api_key = os.getenv("SENDGRID_API_KEY", "").strip()
        sender = gmail_sender or os.getenv("EMAIL_SENDER", "").strip()
        
        if api_key and sender:
            print(f"   📧 Falling back to SendGrid API...")
            try:
                import requests
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
                
                response = requests.post(url, headers=headers, json=data, timeout=30)
                print(f"   📧 SendGrid HTTP Status: {response.status_code}")
                
                if response.status_code >= 400:
                    print(f"   ❌ SendGrid Error: {response.text}")
                    if response.status_code == 403:
                        print(f"   💡 Your SendGrid trial may have expired. Gmail SMTP is the primary method now.")
                else:
                    print("   ✅ SendGrid: Email sent successfully!")
                    email_sent = True
                    
            except Exception as e:
                print(f"   ❌ SendGrid failed: {e}")
        
        if not email_sent and not gmail_password:
            print("❌ AlertAgent: No email method available!")
            print("   💡 Set EMAIL_SENDER and EMAIL_PASSWORD (Google App Password) in your secrets")
    
    # ONLY log sent jobs AFTER email succeeds (prevents false dedup)
    if email_sent:
        for job_url in state.get('extracted_urls', []):
            log_sent_job(state['user_id'], job_url)
        print(f"   💽 Logged {len(state.get('extracted_urls', []))} job URLs as sent (dedup for tomorrow)")
    else:
        print("   ⚠️ Skipping job dedup logging since email failed — will retry these jobs next run")
        
    return {"human_approval": "alerted" if email_sent else "email_failed"}
