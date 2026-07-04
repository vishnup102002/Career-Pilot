import sqlite3
import os

def get_data_dir():
    """
    Determine the best writable data directory.
    Priority:
    1. HF_BUCKET_PATH env var (if user specifies a custom mount path)
    2. HF Storage Bucket mounted under /data (auto-detected)
    3. /data persistent storage (HF Spaces legacy)
    4. ./data (local development)
    5. /tmp/data (ephemeral fallback)
    """
    def _test_writable(path):
        """Test if a directory is writable."""
        try:
            os.makedirs(path, exist_ok=True)
            test_file = os.path.join(path, ".write_test")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return True
        except (PermissionError, OSError):
            return False

    # 1. Explicit bucket path from env var
    bucket_path = os.getenv("HF_BUCKET_PATH", "").strip()
    if bucket_path and _test_writable(bucket_path):
        print(f"✅ Using HF Storage Bucket at {bucket_path} (from HF_BUCKET_PATH)")
        return bucket_path

    # 2. On HF Spaces — check for mounted Storage Buckets or persistent storage
    if os.getenv("SPACE_ID"):
        # Check /data for any mounted bucket or persistent storage
        persistent_dir = "/data"
        if _test_writable(persistent_dir):
            print(f"✅ HF Spaces persistent storage detected at {persistent_dir}")
            return persistent_dir
        else:
            print("⚠️ HF Spaces: /data is NOT writable!")
            print("   → Mount a Storage Bucket: Space Settings > Storage Buckets > Mount a bucket")
            print("   → Or set HF_BUCKET_PATH secret to the mounted bucket path")
            print("   → Falling back to ephemeral storage (DB WILL BE LOST on restart)")

    # 2. Local 'data' directory (for local development)
    local_dir = os.path.abspath("data")
    try:
        os.makedirs(local_dir, exist_ok=True)
        test_file = os.path.join(local_dir, ".test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return local_dir
    except (PermissionError, OSError):
        pass

    # 3. Fallback to /tmp/data (ephemeral)
    tmp_dir = "/tmp/data"
    os.makedirs(tmp_dir, exist_ok=True)
    print(f"⚠️ Using ephemeral /tmp/data — database WILL be lost on restart!")
    return tmp_dir

DATA_DIR = get_data_dir()
DB_PATH = os.path.join(DATA_DIR, "career_pilot.db")

def init_db():
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
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    
    # Diagnostic: show how many users are persisted
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    conn.close()
    
    print(f"📁 SQLite DB at: {DB_PATH}")
    print(f"   → {user_count} registered user(s) in database")

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
    print(f"💾 User saved: {email} (id={user_id})")
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
