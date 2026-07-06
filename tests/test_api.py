"""
API endpoint tests for Career-Pilot.
Tests health check, index page, static files, and /api/initialize validation.
"""
import os
import sys
import io
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    """Create a test client with a temporary database."""
    db_path = str(tmp_path / "test.db")
    data_dir = str(tmp_path)
    
    with patch("db.database.DB_PATH", db_path), \
         patch("db.database.DATA_DIR", data_dir), \
         patch("api.DB_PATH", db_path), \
         patch("api.DATA_DIR", data_dir):
        from api import app
        with TestClient(app) as c:
            yield c


class TestIndexPage:
    """Tests for GET / endpoint."""

    def test_get_index_returns_html(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Career-Pilot" in response.text


class TestHealthEndpoint:
    """Tests for GET /api/health endpoint."""

    def test_health_returns_200(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_returns_json_structure(self, client):
        response = client.get("/api/health")
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "healthy"
        assert "uptime_seconds" in data
        assert "database" in data
        assert "llm" in data
        assert "env" in data

    def test_health_database_status(self, client):
        response = client.get("/api/health")
        data = response.json()
        
        db_status = data["database"]
        assert "status" in db_status
        assert "user_count" in db_status


class TestStaticFiles:
    """Tests for static file serving."""

    def test_robots_txt(self, client):
        response = client.get("/robots.txt")
        assert response.status_code == 200

    def test_sitemap_xml(self, client):
        response = client.get("/sitemap.xml")
        assert response.status_code == 200


class TestInitializeEndpoint:
    """Tests for POST /api/initialize validation."""

    def test_missing_resume(self, client):
        """Should return 422 when resume file is missing."""
        response = client.post(
            "/api/initialize",
            data={"email": "test@example.com", "locations": "Kochi"},
        )
        assert response.status_code == 422

    def test_invalid_email_format(self, client, sample_pdf_bytes):
        """Should return 400 for invalid email format."""
        response = client.post(
            "/api/initialize",
            data={"email": "not-an-email", "locations": "Kochi"},
            files={"resume": ("test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()

    def test_empty_locations(self, client, sample_pdf_bytes):
        """Should return 400 for empty locations."""
        response = client.post(
            "/api/initialize",
            data={"email": "test@example.com", "locations": " "},
            files={"resume": ("test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 400

    def test_invalid_file_type(self, client):
        """Should return 400 for non-PDF/TXT file."""
        fake_docx = b"fake docx content"
        response = client.post(
            "/api/initialize",
            data={"email": "test@example.com", "locations": "Kochi"},
            files={"resume": ("test.docx", io.BytesIO(fake_docx), "application/vnd.openxmlformats")},
        )
        assert response.status_code == 400
        assert "file type" in response.json()["detail"].lower()

    def test_empty_file(self, client):
        """Should return 400 for empty file."""
        response = client.post(
            "/api/initialize",
            data={"email": "test@example.com", "locations": "Kochi"},
            files={"resume": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
        )
        assert response.status_code == 400

    @patch("api.run_onboarding_workflow")
    def test_valid_upload_succeeds(self, mock_workflow, client, sample_pdf_bytes):
        """Should return 200 for valid upload and trigger background task."""
        response = client.post(
            "/api/initialize",
            data={"email": "test@example.com", "locations": "Kochi, Bangalore"},
            files={"resume": ("resume.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Dispatched" in data["message"]

    def test_oversized_file(self, client):
        """Should return 413 for files over 10MB."""
        # Create a file just over 10MB
        huge_content = b"x" * (10 * 1024 * 1024 + 1)
        response = client.post(
            "/api/initialize",
            data={"email": "test@example.com", "locations": "Kochi"},
            files={"resume": ("huge.pdf", io.BytesIO(huge_content), "application/pdf")},
        )
        assert response.status_code == 413
