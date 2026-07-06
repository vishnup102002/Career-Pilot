import os
import html
import smtplib
import re
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from agents.state import AgentState
from db.database import log_sent_job

logger = logging.getLogger("career_pilot.alert")

def _sanitize_for_html(text: str) -> str:
    """
    Sanitize draft text for safe HTML email embedding.
    Escapes HTML entities but preserves line breaks and URLs.
    """
    # Escape all HTML entities first
    safe_text = html.escape(text)
    # Convert newlines to <br> tags
    safe_text = safe_text.replace("\n", "<br>")
    # Convert URLs back to clickable links (after escaping, they're safe)
    safe_text = re.sub(r'(https?://[^\s<>&]+)', r'<a href="\1">\1</a>', safe_text)
    return safe_text

def _send_via_sendgrid(sender, target_email, draft, api_key):
    """Send email via SendGrid HTTPS API (works on HF Spaces, port 443)."""
    import requests
    
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Build HTML version with sanitized content and clickable links
    html_draft = _sanitize_for_html(draft)
    html_body = f"""<html><body style="font-family:Arial,sans-serif;line-height:1.6;color:#333;">
    <div style="max-width:600px;margin:0 auto;padding:20px;">
    <h2 style="color:#2563eb;">🚀 Career-Pilot: Your Daily Job Hunt</h2>
    <hr style="border:1px solid #e5e7eb;">{html_draft}
    <hr style="border:1px solid #e5e7eb;margin-top:24px;">
    <p style="font-size:12px;color:#9ca3af;">Sent by Career-Pilot AI Agent</p>
    </div></body></html>"""
    
    data = {
        "personalizations": [{"to": [{"email": target_email}]}],
        "from": {"email": sender, "name": "Career-Pilot"},
        "subject": "Career-Pilot 🚀 Your Daily Agentic Job Hunt",
        "content": [
            {"type": "text/plain", "value": draft},
            {"type": "text/html", "value": html_body}
        ]
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=30)
    logger.info("   📧 SendGrid HTTP Status: %d", response.status_code)
    
    if response.status_code >= 400:
        logger.error("   ❌ SendGrid Error: %s", response.text)
        if response.status_code == 403:
            logger.error("   💡 Sender not verified OR trial expired. Verify sender at SendGrid Dashboard.")
        elif response.status_code == 401:
            logger.error("   💡 API key invalid. Check SENDGRID_API_KEY secret.")
        return False
    
    logger.info("   ✅ SendGrid: Email sent successfully!")
    return True

def _send_via_resend(target_email, draft, api_key):
    """Send email via Resend HTTPS API (works on HF Spaces, port 443)."""
    import requests
    
    html_draft = _sanitize_for_html(draft)
    
    response = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "from": "Career-Pilot <onboarding@resend.dev>",
            "to": [target_email],
            "subject": "Career-Pilot 🚀 Your Daily Agentic Job Hunt",
            "html": html_draft,
            "text": draft
        },
        timeout=30
    )
    logger.info("   📧 Resend HTTP Status: %d", response.status_code)
    if response.status_code >= 400:
        logger.error("   ❌ Resend Error: %s", response.text)
        return False
    logger.info("   ✅ Resend: Email sent successfully!")
    return True

def _send_via_gmail_smtp(sender, target_email, draft, password):
    """Send email via Gmail SMTP (for local dev only — blocked on HF Spaces)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Career-Pilot 🚀 Your Daily Agentic Job Hunt"
    msg["From"] = f"Career-Pilot <{sender}>"
    msg["To"] = target_email
    msg.attach(MIMEText(draft, "plain"))
    
    html_draft = _sanitize_for_html(draft)
    html_body = f"""<html><body style="font-family:Arial,sans-serif;line-height:1.6;color:#333;">
    <div style="max-width:600px;margin:0 auto;padding:20px;">
    <h2 style="color:#2563eb;">🚀 Career-Pilot: Your Daily Job Hunt</h2>
    <hr style="border:1px solid #e5e7eb;">{html_draft}
    <hr style="border:1px solid #e5e7eb;margin-top:24px;">
    <p style="font-size:12px;color:#9ca3af;">Sent by Career-Pilot AI Agent</p>
    </div></body></html>"""
    msg.attach(MIMEText(html_body, "html"))
    
    # Short timeout — SMTP ports are blocked on HF Spaces
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
        server.login(sender, password)
        server.sendmail(sender, target_email, msg.as_string())
    
    logger.info("   ✅ Gmail SMTP: Email sent successfully!")
    return True

def alert_node(state: AgentState):
    logger.info("🚨 AlertAgent: Dispatching Email Notification...")
    
    draft = state.get('drafted_response', '')
    
    # Guard: If no draft or no matches, skip email entirely
    if not draft or not draft.strip() or "NO STRICT MATCHES FOUND TODAY" in draft:
        logger.warning("⚠️ AlertAgent: No jobs to send. Skipping email.")
        return {"human_approval": "skipped_no_matches"}

    target_email = state.get("email_address", "").strip()
    if not target_email:
        logger.error("❌ AlertAgent: No target email address!")
        return {"human_approval": "email_config_error"}

    sender = os.getenv("EMAIL_SENDER", "").strip()
    logger.info("   📧 From: %s", sender)
    logger.info("   📧 To: %s", target_email)
    logger.info("   📧 Draft length: %d chars", len(draft))

    email_sent = False

    # ── METHOD 1: SendGrid HTTPS API (works on HF Spaces) ──
    sendgrid_key = os.getenv("SENDGRID_API_KEY", "").strip()
    if not email_sent and sendgrid_key and sender:
        logger.info("   📧 Trying SendGrid API...")
        try:
            email_sent = _send_via_sendgrid(sender, target_email, draft, sendgrid_key)
        except Exception as e:
            logger.error("   ❌ SendGrid failed: %s: %s", type(e).__name__, e)

    # ── METHOD 2: Resend HTTPS API (works on HF Spaces) ──
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    if not email_sent and resend_key:
        logger.info("   📧 Trying Resend API...")
        try:
            email_sent = _send_via_resend(target_email, draft, resend_key)
        except Exception as e:
            logger.error("   ❌ Resend failed: %s: %s", type(e).__name__, e)

    # ── METHOD 3: Gmail SMTP (local dev only — ports blocked on HF Spaces) ──
    gmail_password = os.getenv("EMAIL_PASSWORD", "").strip()
    if not email_sent and gmail_password and sender:
        logger.info("   📧 Trying Gmail SMTP (may timeout on HF Spaces)...")
        try:
            email_sent = _send_via_gmail_smtp(sender, target_email, draft, gmail_password)
        except smtplib.SMTPAuthenticationError:
            logger.error("   ❌ Gmail auth failed. Regenerate App Password at https://myaccount.google.com/apppasswords")
        except (TimeoutError, OSError, ConnectionRefusedError) as e:
            logger.error("   ❌ Gmail SMTP blocked (port 465 not reachable): %s", e)
            logger.error("   💡 SMTP ports are blocked on HF Spaces. Use SendGrid or Resend instead.")
        except Exception as e:
            logger.error("   ❌ Gmail error: %s: %s", type(e).__name__, e)

    if not email_sent:
        logger.error("   🚫 ALL EMAIL METHODS FAILED!")
        logger.error("   💡 Options: 1) SendGrid  2) Resend  3) Gmail SMTP (local only)")

    # ONLY log sent jobs AFTER email succeeds
    if email_sent:
        for job_url in state.get('extracted_urls', []):
            log_sent_job(state['user_id'], job_url)
        logger.info("   💽 Logged %d job URLs as sent", len(state.get('extracted_urls', [])))
    else:
        logger.warning("   ⚠️ Skipping dedup logging — will retry these jobs next run")
        
    return {"human_approval": "alerted" if email_sent else "email_failed"}
