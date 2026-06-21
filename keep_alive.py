import os
import sys
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DEFAULT_HF_URL = "https://vishnuporkulath-career-pilot.hf.space"

def ping_url(url: str):
    """
    Pings the specified URL to keep the Hugging Face Space active.
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📡 Sending keep-alive request to: {url}")
    try:
        # Send a GET request with a reasonable timeout
        response = requests.get(url, timeout=30)
        status = response.status_code
        if 200 <= status < 300:
            print(f"   🟢 Success! Status Code: {status}")
            return True
        else:
            print(f"   ⚠️ Warning: Received status code {status}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   🔴 Error: Failed to reach the server. Details: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Career-Pilot Hugging Face Space Keep-Alive Utility")
    parser.add_argument("--url", type=str, help="Target URL to ping. Defaults to APP_URL env var or Hugging Face Space URL.")
    parser.add_argument("--daemon", action="store_true", help="Run as a persistent daemon in the background using APScheduler.")
    parser.add_argument("--interval", type=int, default=30, help="Interval in minutes for daemon ping. Default: 30 minutes.")
    parser.add_argument("--morning-only", action="store_true", help="In daemon mode, only run once every morning (at 08:45 AM IST) instead of intervals.")
    args = parser.parse_args()

    # Determine target URL: CLI argument > APP_URL env variable > default HF space URL
    target_url = args.url or os.getenv("APP_URL") or DEFAULT_HF_URL
    
    # Run immediate ping
    success = ping_url(target_url)

    if args.daemon:
        print(f"⏰ Starting in daemon mode...")
        try:
            from apscheduler.schedulers.blocking import BlockingScheduler
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.triggers.interval import IntervalTrigger
        except ImportError:
            print("❌ Error: APScheduler is required for daemon mode. Run: pip install apscheduler")
            sys.exit(1)

        scheduler = BlockingScheduler()

        if args.morning_only:
            # Set up cron for 8:45 AM IST daily (03:15 AM UTC)
            # APScheduler supports timezone-aware schedules
            trigger = CronTrigger(hour=8, minute=45, timezone="Asia/Kolkata")
            scheduler.add_job(
                ping_url, 
                trigger=trigger, 
                args=[target_url],
                name="morning_keep_alive"
            )
            print("📅 Scheduled to ping once every morning at 08:45 AM IST.")
        else:
            # Set up interval ping
            trigger = IntervalTrigger(minutes=args.interval)
            scheduler.add_job(
                ping_url, 
                trigger=trigger, 
                args=[target_url],
                name="interval_keep_alive"
            )
            print(f"📅 Scheduled to ping every {args.interval} minutes.")

        print("Press Ctrl+C to stop the scheduler.")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("\n👋 Scheduler stopped.")
            
if __name__ == "__main__":
    main()
