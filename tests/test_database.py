"""
Database layer tests for Career-Pilot.
Tests init_db, insert_user, update_user_preferred_job, log_sent_job, 
get_sent_jobs, get_all_users, get_db_stats, and connection safety.
"""
import os
import sqlite3
import pytest
from unittest.mock import patch


class TestInitDb:
    """Tests for database initialization."""

    def test_init_db_creates_tables(self, tmp_path):
        """init_db() should create users and sent_jobs tables."""
        db_path = str(tmp_path / "test.db")
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)):
            from db.database import init_db
            init_db()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "users" in tables
        assert "sent_jobs" in tables

    def test_init_db_creates_indexes(self, tmp_path):
        """init_db() should create performance indexes."""
        db_path = str(tmp_path / "test.db")
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)):
            from db.database import init_db
            init_db()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "idx_sent_jobs_user_id" in indexes
        assert "idx_users_email" in indexes

    def test_init_db_idempotent(self, tmp_path):
        """Calling init_db() multiple times should not error."""
        db_path = str(tmp_path / "test.db")
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)):
            from db.database import init_db
            init_db()
            init_db()  # Second call should be safe


class TestInsertUser:
    """Tests for user insertion and upsert."""

    def test_insert_new_user(self, tmp_path):
        """insert_user() should create a new user and return user_id."""
        db_path = str(tmp_path / "test.db")
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)):
            from db.database import init_db, insert_user
            init_db()
            user_id = insert_user("test@example.com", "Kochi, Bangalore", "Resume text here")

        assert user_id is not None
        assert isinstance(user_id, int)
        assert user_id > 0

    def test_insert_user_upsert(self, tmp_path):
        """Inserting same email again should update, not duplicate."""
        db_path = str(tmp_path / "test.db")
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)):
            from db.database import init_db, insert_user
            init_db()
            id1 = insert_user("test@example.com", "Kochi", "Resume v1")
            id2 = insert_user("test@example.com", "Mumbai", "Resume v2")

        assert id1 == id2  # Same user, just updated

        # Verify the update
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT locations, resume_text FROM users WHERE email = ?", ("test@example.com",))
        row = cursor.fetchone()
        conn.close()

        assert row[0] == "Mumbai"
        assert row[1] == "Resume v2"

    def test_insert_multiple_users(self, tmp_path):
        """insert_user() with different emails creates separate records."""
        db_path = str(tmp_path / "test.db")
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)):
            from db.database import init_db, insert_user
            init_db()
            id1 = insert_user("alice@example.com", "Kochi", "Resume A")
            id2 = insert_user("bob@example.com", "Mumbai", "Resume B")

        assert id1 != id2


class TestUpdatePreferredJob:
    """Tests for updating user's preferred job."""

    def test_update_preferred_job(self, tmp_path):
        """update_user_preferred_job() should update the preferred_job field."""
        db_path = str(tmp_path / "test.db")
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)):
            from db.database import init_db, insert_user, update_user_preferred_job
            init_db()
            user_id = insert_user("test@example.com", "Kochi", "Resume")
            update_user_preferred_job(user_id, "Senior AI Engineer")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT preferred_job FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()[0]
        conn.close()

        assert result == "Senior AI Engineer"


class TestSentJobs:
    """Tests for job URL logging and retrieval."""

    def test_log_and_get_sent_jobs(self, tmp_path):
        """log_sent_job() should persist, get_sent_jobs() should retrieve."""
        db_path = str(tmp_path / "test.db")
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)):
            from db.database import init_db, insert_user, log_sent_job, get_sent_jobs
            init_db()
            user_id = insert_user("test@example.com", "Kochi", "Resume")
            
            log_sent_job(user_id, "https://linkedin.com/jobs/view/111")
            log_sent_job(user_id, "https://linkedin.com/jobs/view/222")
            
            jobs = get_sent_jobs(user_id)

        assert len(jobs) == 2
        assert "https://linkedin.com/jobs/view/111" in jobs
        assert "https://linkedin.com/jobs/view/222" in jobs

    def test_get_sent_jobs_empty(self, tmp_path):
        """get_sent_jobs() should return empty list for new user."""
        db_path = str(tmp_path / "test.db")
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)):
            from db.database import init_db, insert_user, get_sent_jobs
            init_db()
            user_id = insert_user("test@example.com", "Kochi", "Resume")
            jobs = get_sent_jobs(user_id)

        assert jobs == []

    def test_sent_jobs_user_isolation(self, tmp_path):
        """Jobs logged for one user should not appear for another."""
        db_path = str(tmp_path / "test.db")
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)):
            from db.database import init_db, insert_user, log_sent_job, get_sent_jobs
            init_db()
            uid1 = insert_user("alice@test.com", "Kochi", "Resume A")
            uid2 = insert_user("bob@test.com", "Mumbai", "Resume B")
            
            log_sent_job(uid1, "https://linkedin.com/jobs/view/111")
            
            alice_jobs = get_sent_jobs(uid1)
            bob_jobs = get_sent_jobs(uid2)

        assert len(alice_jobs) == 1
        assert len(bob_jobs) == 0


class TestGetAllUsers:
    """Tests for get_all_users()."""

    def test_get_all_users(self, tmp_path):
        """get_all_users() should return all registered users."""
        db_path = str(tmp_path / "test.db")
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)):
            from db.database import init_db, insert_user, get_all_users
            init_db()
            insert_user("alice@test.com", "Kochi", "Resume A")
            insert_user("bob@test.com", "Mumbai", "Resume B")
            
            users = get_all_users()

        assert len(users) == 2

    def test_get_all_users_empty(self, tmp_path):
        """get_all_users() should return empty list when no users exist."""
        db_path = str(tmp_path / "test.db")
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)):
            from db.database import init_db, get_all_users
            init_db()
            users = get_all_users()

        assert users == []


class TestGetDbStats:
    """Tests for get_db_stats()."""

    def test_get_db_stats(self, tmp_path):
        """get_db_stats() should return correct counts."""
        db_path = str(tmp_path / "test.db")
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)):
            from db.database import init_db, insert_user, log_sent_job, get_db_stats
            init_db()
            uid = insert_user("test@test.com", "Kochi", "Resume")
            log_sent_job(uid, "https://example.com/job/1")
            
            stats = get_db_stats()

        assert stats["status"] == "OK"
        assert stats["user_count"] == 1
        assert stats["sent_jobs_count"] == 1
