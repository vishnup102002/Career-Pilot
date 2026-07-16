"""
Agent unit tests for Career-Pilot.
Tests individual agent nodes, URL filtering, signal detection, and stale job detection.
"""
import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── URL Filtering Tests ──

class TestIsDirectJobUrl:
    """Tests for the is_direct_job_url() heuristic filter."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from agents.scout_agent import is_direct_job_url
        self.is_direct = is_direct_job_url

    # Positive cases (should return True)
    @pytest.mark.parametrize("url", [
        "https://linkedin.com/jobs/view/1234567890",
        "https://www.linkedin.com/jobs/view/ai-engineer-at-google-12345",
        "https://indeed.com/viewjob?jk=abc123def456",
        "https://in.indeed.com/viewjob?jk=abc123",
        "https://weworkremotely.com/remote-jobs/acme-ai-engineer",
        "https://boards.greenhouse.io/acme/jobs/12345",
        "https://jobs.lever.co/acme/abc-123-def",
        "https://glassdoor.com/job-listing/ai-engineer-1234",
        "https://naukri.com/job-listings-ai-engineer-xyz-company",
        "https://instahyre.com/job/123456",
        "https://careers.google.com/jobs/results/12345",
    ])
    def test_accepts_direct_job_urls(self, url):
        assert self.is_direct(url) is True, f"Should accept: {url}"

    # Negative cases (should return False — aggregator/listing pages)
    @pytest.mark.parametrize("url", [
        "https://linkedin.com/jobs/search?keywords=AI",
        "https://linkedin.com/jobs/collections/recommended",
        "https://linkedin.com/jobs/artificial-intelligence-jobs-kochi",
        "https://indeed.com/q-ai-engineer-l-bangalore-jobs.html",
        "https://indeed.com/q-generative-ai-jobs.html",
        "https://glassdoor.co.in/job/us-ai-engineer",
        "https://naukri.com/ai-engineer-jobs",
        "https://naukri.com/jobs-in-bangalore",
        "https://wellfound.com/role/software-engineer",
        "https://www.ambitionbox.com/jobs/ai-engineer",
        "https://internshala.com/jobs/ai-engineer",
    ])
    def test_rejects_aggregator_urls(self, url):
        assert self.is_direct(url) is False, f"Should reject: {url}"


class TestIsHighSignalText:
    """Tests for the is_high_signal_text() quality filter."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from agents.scout_agent import is_high_signal_text
        self.is_signal = is_high_signal_text

    def test_valid_job_description(self):
        text = """
        About the Role: We are looking for a Junior AI Engineer.
        Requirements: Python, PyTorch, 0-2 years experience.
        Responsibilities: Build ML pipelines, deploy models.
        Skills: Deep learning, NLP, computer vision.
        Apply now to join our team!
        """
        assert self.is_signal(text) is True

    def test_login_wall(self):
        text = "Sign in to continue. Please login to view this job."
        assert self.is_signal(text) is False

    def test_captcha_page(self):
        text = "Security check. Please verify you are not a robot."
        assert self.is_signal(text) is False

    def test_empty_text(self):
        assert self.is_signal("") is False
        assert self.is_signal(None) is False

    def test_insufficient_keywords(self):
        text = "Welcome to our company. We make great products."
        assert self.is_signal(text) is False


class TestIsStaleJob:
    """Tests for stale/expired job detection."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from agents.scout_agent import _is_stale_job, _is_stale_job_content
        self.is_stale = _is_stale_job
        self.is_stale_content = _is_stale_job_content

    def test_expired_job(self):
        result = {"title": "AI Engineer", "body": "This job has expired", "date": ""}
        assert self.is_stale(result) is True

    def test_position_filled(self):
        result = {"title": "AI Engineer", "body": "Position filled", "date": ""}
        assert self.is_stale(result) is True

    def test_old_job_months(self):
        result = {"title": "AI Engineer", "body": "Posted 6 months ago", "date": ""}
        assert self.is_stale(result) is True

    def test_fresh_job(self):
        result = {"title": "AI Engineer", "body": "Apply now for this exciting role", "date": "2 days ago"}
        assert self.is_stale(result) is False

    def test_stale_content_expired(self):
        text = "This job posting is no longer available. Please check other openings."
        assert self.is_stale_content(text) is True

    def test_stale_content_not_accepting(self):
        text = "This position is no longer accepting applications."
        assert self.is_stale_content(text) is True

    def test_stale_content_valid(self):
        text = "We are hiring! Apply today for our AI Engineer position."
        assert self.is_stale_content(text) is False

    def test_stale_content_empty(self):
        assert self.is_stale_content("") is False
        assert self.is_stale_content(None) is False


# ── Research Agent Tests ──

class TestResearchNode:
    """Tests for the research_node agent."""

    def test_research_node_parses_json(self, tmp_path):
        """research_node should parse LLM JSON and return summary + preferred_job."""
        db_path = str(tmp_path / "test.db")
        
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='{"summary": "Fresher with Python skills.", "preferred_job": "Junior AI Developer"}'
        )
        
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)), \
             patch("agents.research_agent.llm", mock_llm):
            from db.database import init_db
            from agents.research_agent import research_node
            init_db()
            
            state = {
                "user_id": None,
                "resume_text": "Python developer with LangChain experience.",
            }
            result = research_node(state)

        assert result["resume_summary"] == "Fresher with Python skills."
        assert result["preferred_job"] == "Junior AI Developer"

    def test_research_node_handles_markdown_fences(self, tmp_path):
        """research_node should strip markdown code fences from LLM response."""
        db_path = str(tmp_path / "test.db")
        
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='```json\n{"summary": "Test summary", "preferred_job": "Data Engineer"}\n```'
        )
        
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)), \
             patch("agents.research_agent.llm", mock_llm):
            from db.database import init_db
            from agents.research_agent import research_node
            init_db()
            
            state = {"user_id": None, "resume_text": "SQL, Spark, Python"}
            result = research_node(state)

        assert result["preferred_job"] == "Data Engineer"

    def test_research_node_fallback_on_invalid_json(self, tmp_path):
        """research_node should gracefully fallback when LLM returns garbage."""
        db_path = str(tmp_path / "test.db")
        
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="This is not JSON at all")
        
        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)), \
             patch("agents.research_agent.llm", mock_llm):
            from db.database import init_db
            from agents.research_agent import research_node
            init_db()
            
            state = {"user_id": None, "resume_text": "Some resume"}
            result = research_node(state)

        assert result["preferred_job"] == "Software Developer"  # Fallback
        assert "This is not JSON" in result["resume_summary"]


# ── Writer Agent Tests ──

class TestWriterNode:
    """Tests for the writer_node agent."""

    def test_writer_skips_no_matches(self):
        """writer_node should skip formatting when no matches found."""
        from agents.writer_agent import writer_node
        
        state = {"found_jobs": "NO STRICT MATCHES FOUND TODAY."}
        result = writer_node(state)

        assert "NO STRICT MATCHES FOUND TODAY" in result["drafted_response"]

    def test_writer_skips_empty_jobs(self):
        """writer_node should skip formatting when found_jobs is empty."""
        from agents.writer_agent import writer_node
        
        state = {"found_jobs": ""}
        result = writer_node(state)

        assert "NO STRICT MATCHES FOUND TODAY" in result["drafted_response"]

    def test_writer_formats_jobs(self):
        """writer_node should invoke LLM to format jobs when matches exist."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Formatted job listing here")
        
        with patch("agents.writer_agent.llm", mock_llm):
            from agents.writer_agent import writer_node
            state = {"found_jobs": "1. AI Engineer at Acme — Remote\n   Apply Here: https://example.com/job/1"}
            result = writer_node(state)

        assert result["drafted_response"] == "Formatted job listing here"
        mock_llm.invoke.assert_called_once()


# ── Alert Agent Tests ──

class TestAlertNode:
    """Tests for the alert_node agent."""

    def test_alert_skips_no_matches(self):
        """alert_node should skip when draft contains NO STRICT MATCHES."""
        from agents.alert_agent import alert_node
        
        state = {
            "drafted_response": "NO STRICT MATCHES FOUND TODAY.",
            "email_address": "test@example.com",
            "extracted_urls": [],
        }
        result = alert_node(state)
        assert result["human_approval"] == "skipped_no_matches"

    def test_alert_skips_empty_draft(self):
        """alert_node should skip when draft is empty."""
        from agents.alert_agent import alert_node
        
        state = {
            "drafted_response": "",
            "email_address": "test@example.com",
            "extracted_urls": [],
        }
        result = alert_node(state)
        assert result["human_approval"] == "skipped_no_matches"

    def test_alert_skips_missing_email(self):
        """alert_node should error when no email address provided."""
        from agents.alert_agent import alert_node
        
        state = {
            "drafted_response": "Here are your jobs!",
            "email_address": "",
            "extracted_urls": [],
        }
        result = alert_node(state)
        assert result["human_approval"] == "email_config_error"

    @patch.dict(os.environ, {"SENDGRID_API_KEY": "", "RESEND_API_KEY": "", "EMAIL_PASSWORD": "", "EMAIL_SENDER": ""})
    def test_alert_all_methods_fail(self):
        """alert_node should report failure when no email method is configured."""
        from agents.alert_agent import alert_node
        
        state = {
            "drafted_response": "Here are your matched jobs!",
            "email_address": "test@example.com",
            "user_id": 1,
            "extracted_urls": ["https://example.com/job/1"],
        }
        result = alert_node(state)
        assert result["human_approval"] == "email_failed"


# ── HTML Sanitization Tests ──

class TestHtmlSanitization:
    """Tests for email HTML injection prevention."""

    def test_sanitize_escapes_html(self):
        from agents.alert_agent import _sanitize_for_html
        
        malicious = '<script>alert("xss")</script>'
        result = _sanitize_for_html(malicious)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_sanitize_preserves_urls(self):
        from agents.alert_agent import _sanitize_for_html
        
        text = "Apply here: https://linkedin.com/jobs/view/123"
        result = _sanitize_for_html(text)
        assert 'href="https://linkedin.com/jobs/view/123"' in result

    def test_sanitize_converts_newlines(self):
        from agents.alert_agent import _sanitize_for_html
        
        text = "Line 1\nLine 2"
        result = _sanitize_for_html(text)
        assert "<br>" in result


# ── Scout Agent Experience & Cleaning Tests ──

class TestScoutExperienceHandling:
    """Tests for scraped markdown boilerplate cleaning and experience mismatch detection."""

    def test_clean_scraped_markdown_strips_boilerplate(self):
        from agents.scout_agent import _clean_scraped_markdown

        raw_markdown = """
        [Skip to main content](https://linkedin.com)
        Sign in
        Join now
        Email or phone
        Password
        By clicking Continue to join or sign in, you agree to User Agreement and Privacy Policy.

        DigitalXNode hiring AI/ML Engineer in Kochi, Kerala, India

        Join a growing AI team in Kochi and work on cutting-edge Generative AI.
        **Experience**3–10 Years (flexible for exceptional candidates up to 12 years)

        Key Responsibilities
        * Design and deploy LLM-based applications
        * Build RAG pipelines

        Required Skills
        * Python, FastAPI, PyTorch

        Mid-Senior level

        Intelligence Specialist jobs 315 open jobs
        Scientist jobs 2,584 open jobs
        User Agreement Cookie Policy Copyright Policy
        العربية Deutsch Français
        """

        cleaned = _clean_scraped_markdown(raw_markdown)

        # Verify boilerplate noise is stripped
        assert "Sign in" not in cleaned
        assert "Join now" not in cleaned
        assert "Email or phone" not in cleaned
        assert "Intelligence Specialist jobs" not in cleaned
        assert "User Agreement Cookie Policy" not in cleaned

        # Verify core content and experience requirements survive
        assert "DigitalXNode hiring AI/ML Engineer" in cleaned
        assert "**Experience**3–10 Years" in cleaned
        assert "Key Responsibilities" in cleaned
        assert "Mid-Senior level" in cleaned

    def test_extract_experience_requirement(self):
        from agents.scout_agent import _extract_experience_requirement

        # Range pattern with en-dash
        text1 = "Join a team. **Experience**3–10 Years (flexible)"
        assert _extract_experience_requirement(text1) == "3-10 Years"

        # Explicit plus pattern
        text2 = "Looking for a developer. Experience: 5+ years with Python."
        assert _extract_experience_requirement(text2) == "5+ years"

        # Seniority level fallback
        text3 = "Role: Senior ML Engineer\nSeniority level: Mid-Senior level"
        assert _extract_experience_requirement(text3) == "Mid-Senior level"

        # Fresher
        text4 = "Entry Level position for freshers."
        assert _extract_experience_requirement(text4).lower() in ["fresher", "entry level", "entry-level"]

        # Missing experience
        text5 = "We are hiring a Python Engineer for our Kochi office."
        assert _extract_experience_requirement(text5) == "Not specified"

    def test_is_experience_mismatch(self):
        from agents.scout_agent import _is_experience_mismatch

        fresher_resume = "Recent B.Tech graduate with Python, RAG projects. No professional experience (fresher), looking for entry-level positions."

        # Rejects 3-10 years for fresher candidate
        assert _is_experience_mismatch("3-10 Years", fresher_resume) is True

        # Rejects 5+ years for fresher candidate
        assert _is_experience_mismatch("5+ years", fresher_resume) is True

        # Rejects Mid-Senior level for fresher candidate
        assert _is_experience_mismatch("Mid-Senior level", fresher_resume) is True

        # Accepts 0-2 years for fresher candidate
        assert _is_experience_mismatch("0-2 Years", fresher_resume) is False

        # Accepts Fresher for fresher candidate
        assert _is_experience_mismatch("Fresher", fresher_resume) is False

        # Accepts Not specified (delegated to LLM scoring)
        assert _is_experience_mismatch("Not specified", fresher_resume) is False

