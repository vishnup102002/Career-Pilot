"""
Shared pytest fixtures for Career-Pilot test suite.
"""
import os
import sys
import json
import sqlite3
import tempfile
import pytest
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Sample Data ──

SAMPLE_RESUME_TEXT = """
VISHNU P
B.Tech Computer Science, Government Engineering College Thrissur
Email: test@example.com | Phone: +91-9876543210
Location: Kochi, Kerala, India

SKILLS:
- Python, JavaScript, TypeScript
- LangChain, LangGraph, Hugging Face, PyTorch
- React.js, FastAPI, Flask
- SQL, MongoDB, ChromaDB
- Docker, Git, Linux
- Machine Learning, NLP, RAG Pipelines

EXPERIENCE:
- AI Intern at TechCorp (3 months) - Built RAG pipeline using LangChain
- Freelance Web Developer (6 months) - Built React dashboards

EDUCATION:
- B.Tech in Computer Science (2024) - GPA: 8.5/10

PROJECTS:
- Career-Pilot: AI-powered job hunting agent using LangGraph
- ChatBot: Fine-tuned LLM for customer support
"""

SAMPLE_STATE = {
    "user_id": 1,
    "email_address": "test@example.com",
    "preferred_job": "Junior AI Engineer",
    "locations": "Kochi, Bangalore, Remote",
    "resume_text": SAMPLE_RESUME_TEXT,
    "resume_summary": "Recent B.Tech graduate with Python, LangChain, PyTorch skills. Fresher with 3 months AI internship.",
    "previously_sent_jobs": [],
    "found_jobs": "",
    "drafted_response": "",
    "extracted_urls": [],
}

SAMPLE_FOUND_JOBS = """1. Junior AI Developer at CognitiveLabs — Remote
   Match Score: 90%
   Experience Required: 0-2 years
   Why it's a match: Python, LangChain, PyTorch align perfectly with fresher profile.
   Apply Here: https://linkedin.com/jobs/view/1111111

2. AI Engineer Intern at DataCorp — Bangalore
   Match Score: 85%
   Experience Required: Fresher
   Why it's a match: RAG pipeline experience directly relevant.
   Apply Here: https://linkedin.com/jobs/view/2222222
"""


# ── Fixtures ──

@pytest.fixture
def mock_llm():
    """Returns a mocked LLM that gives predictable responses."""
    llm_mock = MagicMock()
    llm_mock.invoke.return_value = MagicMock(
        content='{"summary": "Fresher B.Tech graduate with Python, LangChain, PyTorch skills.", "preferred_job": "Junior AI Engineer"}'
    )
    return llm_mock


@pytest.fixture
def temp_db(tmp_path):
    """Creates a temporary SQLite database for testing."""
    db_path = str(tmp_path / "test_career_pilot.db")
    
    with patch("db.database.DB_PATH", db_path), \
         patch("db.database.DATA_DIR", str(tmp_path)):
        from db.database import init_db
        init_db()
        yield db_path


@pytest.fixture
def sample_state():
    """Returns a copy of the sample agent state."""
    return SAMPLE_STATE.copy()


@pytest.fixture
def sample_state_with_jobs(sample_state):
    """Returns a sample state with found jobs populated."""
    state = sample_state.copy()
    state["found_jobs"] = SAMPLE_FOUND_JOBS
    state["extracted_urls"] = [
        "https://linkedin.com/jobs/view/1111111",
        "https://linkedin.com/jobs/view/2222222",
    ]
    return state


@pytest.fixture
def sample_pdf_bytes():
    """Returns minimal valid PDF bytes for testing upload."""
    # Minimal valid PDF content
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test Resume) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer << /Size 5 /Root 1 0 R >>
startxref
312
%%EOF"""
