import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from agents.state import AgentState
from agents.config import llm
from db.database import update_user_preferred_job

logger = logging.getLogger("career_pilot.research")

def research_node(state: AgentState):
    logger.info("📚 ResearchAgent: Reading the uploaded Resume...")
    messages = [
        SystemMessage(content="""You are an elite Technical Recruiter. Read this resume text and respond in EXACTLY this JSON format, nothing else:
{
    "summary": "A 4-sentence summary identifying: 1) Their EXACT Years of Experience (e.g. fresher, intern, 5 years). 2) Their Highest Education (e.g. none, Bachelor's). 3) Their location. 4) Their core technical skills.",
    "preferred_job": "The single BEST fitting job title for this person based on their skills and experience level (e.g. 'Junior AI Developer', 'Frontend Engineer', 'Data Analyst Intern'). Be specific and include seniority level."
}
Reply with ONLY valid JSON. No markdown, no code fences, no extra text."""),
        HumanMessage(content=state.get('resume_text', 'No resume text')[:4000]) 
    ]
    response = llm.invoke(messages) if llm else type('obj', (object,), {'content': '{"summary": "Expert Developer", "preferred_job": "Software Developer"}'})()
    
    # Parse the JSON response from Gemini
    try:
        raw = response.content.strip()
        # Strip markdown code fences if the model wraps it
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(raw)
        summary = parsed.get("summary", response.content)
        preferred_job = parsed.get("preferred_job", "Software Developer")
    except (json.JSONDecodeError, Exception) as e:
        # Fallback: use the raw response as summary
        logger.warning("Failed to parse LLM JSON response: %s", e)
        summary = response.content
        preferred_job = "Software Developer"
    
    # Save the AI-detected job role to the database for the daily cron job
    user_id = state.get("user_id")
    if user_id:
        update_user_preferred_job(user_id, preferred_job)
    
    logger.info("   -> Skills analyzed successfully!")
    logger.info("   -> AI-detected best job role: %s", preferred_job)
    return {"resume_summary": summary, "preferred_job": preferred_job}
