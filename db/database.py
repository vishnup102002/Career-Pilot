import sqlite3
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger("career_pilot.database")

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
        logger.info("✅ Using HF Storage Bucket at %s (from HF_BUCKET_PATH)", bucket_path)
        return bucket_path

    # 2. On HF Spaces — check for mounted Storage Buckets or persistent storage
    if os.getenv("SPACE_ID"):
        persistent_dir = "/data"
        if _test_writable(persistent_dir):
            logger.info("✅ HF Spaces persistent storage detected at %s", persistent_dir)
            return persistent_dir
        else:
            logger.warning("⚠️ HF Spaces: /data is NOT writable!")
            logger.warning("   → Mount a Storage Bucket: Space Settings > Storage Buckets > Mount a bucket")
            logger.warning("   → Or set HF_BUCKET_PATH secret to the mounted bucket path")
            logger.warning("   → Falling back to ephemeral storage (DB WILL BE LOST on restart)")

    # 3. Local 'data' directory (for local development)
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

    # 4. Fallback to /tmp/data (ephemeral)
    tmp_dir = "/tmp/data"
    os.makedirs(tmp_dir, exist_ok=True)
    logger.warning("⚠️ Using ephemeral /tmp/data — database WILL be lost on restart!")
    return tmp_dir

DATA_DIR = get_data_dir()
DB_PATH = os.path.join(DATA_DIR, "career_pilot.db")


@contextmanager
def get_db_connection():
    """
    Context manager for safe SQLite connections.
    Ensures connections are always closed, even on errors.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db_connection() as conn:
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
        
        # Performance indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sent_jobs_user_id ON sent_jobs(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        
        conn.commit()
        
        # Diagnostic: show how many users are persisted
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
    
    logger.info("📁 SQLite DB at: %s", DB_PATH)
    logger.info("   → %d registered user(s) in database", user_count)

def insert_user(email: str, locations: str, resume_text: str):
    with get_db_connection() as conn:
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
    logger.info("💾 User saved: %s (id=%d)", email, user_id)
    return user_id

def update_user_preferred_job(user_id: int, preferred_job: str):
    """Called by the ResearchAgent after it detects the best job role from CV."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET preferred_job = ? WHERE id = ?", (preferred_job, user_id))
        conn.commit()

def log_sent_job(user_id: int, job_url: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sent_jobs (user_id, job_url) VALUES (?, ?)", (user_id, job_url))
        conn.commit()

def get_sent_jobs(user_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT job_url FROM sent_jobs WHERE user_id = ?", (user_id,))
        jobs = [row[0] for row in cursor.fetchall()]
    return jobs

def get_all_users():
    """ Used by the morning Cron Job to loop through everything """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, preferred_job, locations, resume_text FROM users")
        users = cursor.fetchall()
    return users

def get_db_stats() -> dict:
    """Returns database statistics for the /api/health endpoint."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM sent_jobs")
            sent_count = cursor.fetchone()[0]
        return {
            "status": "OK",
            "db_path": DB_PATH,
            "user_count": user_count,
            "sent_jobs_count": sent_count,
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e), "db_path": DB_PATH}


if __name__ == "__main__":
    init_db()
