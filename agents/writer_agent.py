import logging
from langchain_core.messages import HumanMessage
from agents.state import AgentState
from agents.config import llm

logger = logging.getLogger("career_pilot.writer")

def writer_node(state: AgentState):
    found_jobs = state.get('found_jobs', '').strip()
    
    if not found_jobs or "NO STRICT MATCHES FOUND TODAY" in found_jobs:
        logger.info("✍️  WriterAgent: No jobs found. Skipping formatting.")
        return {"drafted_response": "NO STRICT MATCHES FOUND TODAY. We couldn't find any jobs that strictly match your profile (experience level, skills, and locations) today. We will check again tomorrow morning!"}

    logger.info("✍️  WriterAgent: Formatting the final dispatch...")
    prompt = f"""
    You MUST format the jobs below into a clean, professional email-friendly message.
    
    - Use ultra-short bullet points.
    - Make it sound like an elite AI recruiter exclusively hunted these down for them based on their custom resume.
    - CRITICAL: You MUST flawlessly copy/paste the 'Apply Here' URLs exactly as provided. DO NOT alter, wrap in markdown, or truncate the links!
    - For each job, include the source platform tag (e.g., 📍 via LinkedIn, 📍 via Indeed, 📍 via Naukri) next to the job title to show credibility.
    - NO introductory or concluding paragraphs whatsoever. Just list the jobs.
    - Exclude placeholders or generic recruiter text.
    
    Jobs to format:
    {found_jobs}
    """
    response = llm.invoke([HumanMessage(content=prompt)]) if llm else type('obj', (object,), {'content': 'Here are your jobs!'})()
    return {"drafted_response": response.content}
