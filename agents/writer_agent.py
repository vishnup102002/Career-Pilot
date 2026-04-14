from langchain_core.messages import HumanMessage
from agents.state import AgentState
from agents.config import llm

def writer_node(state: AgentState):
    print("✍️  WriterAgent: Formatting the final dispatch...")
    prompt = f"""
    You MUST format the jobs below into a clean, professional email-friendly message.
    
    - Use ultra-short bullet points.
    - Make it sound like an elite AI recruiter exclusively hunted these down for them based on their custom resume.
    - CRITICAL: You MUST flawlessly copy/paste the 'Apply Here' URLs exactly as provided. DO NOT alter, wrap in markdown, or truncate the links!
    - For each job, include the source platform tag (e.g., 📍 via LinkedIn, 📍 via Indeed, 📍 via Naukri) next to the job title to show credibility.
    - NO introductory or concluding paragraphs whatsoever. Just list the jobs.
    - Exclude placeholders or generic recruiter text.
    
    Jobs to format:
    {state.get('found_jobs', 'No jobs')}
    """
    response = llm.invoke([HumanMessage(content=prompt)]) if llm else type('obj', (object,), {'content': 'Here are your jobs!'})()
    return {"drafted_response": response.content}
