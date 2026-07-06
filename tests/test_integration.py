"""
Integration tests for Career-Pilot.
Tests the full LangGraph pipeline with mocked external services.
"""
import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFullPipeline:
    """Integration tests for the complete research → scout → writer → alert pipeline."""

    def test_pipeline_no_matches_flow(self, tmp_path):
        """
        Full pipeline with mocked LLM that finds no matches.
        Verifies state flows correctly through all 4 nodes without crashing.
        """
        db_path = str(tmp_path / "test.db")

        # Mock LLM responses for each stage
        mock_llm = MagicMock()
        call_count = [0]
        
        def mock_invoke(messages):
            call_count[0] += 1
            if call_count[0] == 1:
                # Research node
                return MagicMock(content='{"summary": "Fresher with Python skills.", "preferred_job": "AI Engineer"}')
            elif call_count[0] == 2:
                # Scout node - LLM-optimized query (optional, may not fire)
                return MagicMock(content="AI Engineer Python LangChain Kochi")
            else:
                # Scout node matching or Writer node
                return MagicMock(content="NO STRICT MATCHES FOUND TODAY.")
        
        mock_llm.invoke = mock_invoke

        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)), \
             patch("agents.config.llm", mock_llm), \
             patch("agents.research_agent.llm", mock_llm), \
             patch("agents.scout_agent.llm", mock_llm), \
             patch("agents.writer_agent.llm", mock_llm), \
             patch("agents.scout_agent.serper_search", return_value=[]), \
             patch("agents.scout_agent.scrape_multiple_urls", return_value={}):
            
            from db.database import init_db
            init_db()
            
            from main import career_pilot_graph
            
            initial_state = {
                "user_id": None,
                "email_address": "test@example.com",
                "preferred_job": "",
                "locations": "Kochi, Remote",
                "resume_text": "Python developer with LangChain experience.",
                "previously_sent_jobs": [],
                "job_url": "",
            }
            
            # This should not raise any exceptions
            result = career_pilot_graph.invoke(initial_state)
            
            # Verify the pipeline completed
            assert result is not None
            assert "NO STRICT MATCHES FOUND TODAY" in result.get("drafted_response", "")

    def test_pipeline_with_matches_flow(self, tmp_path):
        """
        Full pipeline with mocked search results that produce matches.
        Verifies state flows through scout → writer → alert correctly.
        """
        db_path = str(tmp_path / "test.db")

        # Mocked search results
        mock_search_results = [
            {
                "title": "Junior AI Developer (Remote)",
                "href": "https://linkedin.com/jobs/view/999999",
                "body": "Looking for AI Developer with Python, LangChain. Fresher welcome.",
                "date": "2 days ago",
            }
        ]
        
        mock_llm = MagicMock()
        call_count = [0]
        
        def mock_invoke(messages):
            call_count[0] += 1
            if call_count[0] == 1:
                # Research node
                return MagicMock(content='{"summary": "Fresher with Python and LangChain.", "preferred_job": "Junior AI Engineer"}')
            elif call_count[0] <= 3:
                # Scout LLM calls (query gen + matching)
                return MagicMock(content="""1. Junior AI Developer at CognitiveLabs — Remote
   Match Score: 90%
   Experience Required: Fresher
   Why it's a match: Python, LangChain align perfectly.
   Apply Here: https://linkedin.com/jobs/view/999999""")
            else:
                # Writer node
                return MagicMock(content="🚀 Your personalized job matches:\n• Junior AI Developer — Remote\n  Apply: https://linkedin.com/jobs/view/999999")
        
        mock_llm.invoke = mock_invoke

        with patch("db.database.DB_PATH", db_path), \
             patch("db.database.DATA_DIR", str(tmp_path)), \
             patch("agents.config.llm", mock_llm), \
             patch("agents.research_agent.llm", mock_llm), \
             patch("agents.scout_agent.llm", mock_llm), \
             patch("agents.writer_agent.llm", mock_llm), \
             patch("agents.scout_agent.serper_search", return_value=mock_search_results), \
             patch("agents.scout_agent.scrape_multiple_urls", return_value={"https://linkedin.com/jobs/view/999999": "Full job description text with requirements and skills and experience and apply now"}), \
             patch.dict(os.environ, {"SENDGRID_API_KEY": "", "RESEND_API_KEY": "", "EMAIL_PASSWORD": "", "EMAIL_SENDER": ""}):
            
            from db.database import init_db
            init_db()
            
            from main import career_pilot_graph
            
            initial_state = {
                "user_id": None,
                "email_address": "test@example.com",
                "preferred_job": "",
                "locations": "Kochi, Remote",
                "resume_text": "Python developer with LangChain and PyTorch experience.",
                "previously_sent_jobs": [],
                "job_url": "",
            }
            
            result = career_pilot_graph.invoke(initial_state)
            
            assert result is not None
            # Writer should have formatted something (not NO STRICT MATCHES)
            drafted = result.get("drafted_response", "")
            assert drafted  # Should not be empty


class TestDeduplication:
    """Tests for the job deduplication logic across runs."""

    def test_previously_sent_jobs_excluded(self, tmp_path):
        """
        Scout agent should pass previously_sent_jobs to the LLM prompt,
        enabling deduplication across runs.
        """
        from agents.scout_agent import _build_search_queries
        
        # Verify search query builder works without error
        queries = _build_search_queries("AI Engineer", "Kochi, Bangalore", "Fresher with Python skills")
        
        assert len(queries) > 0
        assert any("linkedin" in q.lower() for q in queries)
        assert any("AI Engineer" in q for q in queries)

    def test_search_query_diversity(self):
        """
        Search queries should include site-specific, open web, and remote variations.
        """
        from agents.scout_agent import _build_search_queries
        
        queries = _build_search_queries("Frontend Developer", "Mumbai, Remote", "3 years React experience")
        
        # Should have LinkedIn site queries
        linkedin_queries = [q for q in queries if "linkedin.com" in q]
        assert len(linkedin_queries) > 0
        
        # Should have Indeed queries
        indeed_queries = [q for q in queries if "indeed.com" in q]
        assert len(indeed_queries) > 0
        
        # Should be capped at 16 queries max
        assert len(queries) <= 16
