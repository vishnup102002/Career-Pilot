from typing import TypedDict

class AgentState(TypedDict):
    user_id: int               # Persist Memory Identity
    email_address: str
    preferred_job: str         # User's desired job role
    locations: str             # Comma-separated preferred locations
    resume_text: str  
    resume_summary: str 
    previously_sent_jobs: list # LangGraph Deduplication
    found_jobs: str     
    drafted_response: str
    extracted_urls: list       # Found URLs to save back to SQLite
