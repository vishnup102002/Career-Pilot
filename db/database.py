import sqlite3
import os

DB_PATH = "db/career_pilot.db"

def init_db():
    if not os.path.exists("db"):
        os.makedirs("db")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users Table saves the profile permanently
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        preferred_job TEXT NOT NULL DEFAULT '',
        locations TEXT NOT NULL DEFAULT '',
        resume_text TEXT NOT NULL
    )
    ''')
    
    # Sent Jobs Table links previously dispatched URLs to users so we don't spam 
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sent_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        job_url TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("📁 SQLite DB Initialized natively at `db/career_pilot.db`!")

def insert_user(email: str, locations: str, resume_text: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # If the user uploads again, we update their profile to the latest version
    cursor.execute('''
    INSERT INTO users (email, locations, resume_text) 
    VALUES (?, ?, ?)
    ON CONFLICT(email) DO UPDATE SET 
        locations=excluded.locations,
        resume_text=excluded.resume_text
    ''', (email, locations, resume_text))
    
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    user_id = cursor.fetchone()[0]
    
    conn.commit()
    conn.close()
    return user_id

def update_user_preferred_job(user_id: int, preferred_job: str):
    """Called by the ResearchAgent after it detects the best job role from CV."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET preferred_job = ? WHERE id = ?", (preferred_job, user_id))
    conn.commit()
    conn.close()

def log_sent_job(user_id: int, job_url: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sent_jobs (user_id, job_url) VALUES (?, ?)", (user_id, job_url))
    conn.commit()
    conn.close()

def get_sent_jobs(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT job_url FROM sent_jobs WHERE user_id = ?", (user_id,))
    jobs = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jobs

def get_all_users():
    """ Used by the morning Cron Job to loop through everything """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, preferred_job, locations, resume_text FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

if __name__ == "__main__":
    init_db()
