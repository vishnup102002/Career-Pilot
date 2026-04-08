from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# 1. State Definition
# This is the "shared memory" that gets passed between all agents
class AgentState(TypedDict):
    job_url: str
    job_description: str
    extracted_skills: str
    resume_matches: str
    drafted_response: str
    human_approval: str

# 2. Nodes (The functions/agents that do the work)
def scout_node(state: AgentState):
    print(f"🕵️  ScoutAgent: Scouting job at {state['job_url']}")
    # Here the LLM would connect to our Browser MCP! We mock it for now.
    return {
        "job_description": "Looking for an AI engineer with Python and LangGraph.", 
        "extracted_skills": "Python, LangGraph"
    }

def research_node(state: AgentState):
    print("📚 ResearchAgent: Querying ChromaDB for resume matches...")
    # Here the LLM would connect to our Research MCP!
    db_match = "- Built a multi-agent system using LangGraph and Python."
    return {"resume_matches": db_match}

def writer_node(state: AgentState):
    print("✍️  WriterAgent: Drafting the cover letter...")
    draft = f"I am a great fit for {state['extracted_skills']} because {state['resume_matches']}"
    return {"drafted_response": draft}

# 3. Graph Definition (Connecting the dots)
workflow = StateGraph(AgentState)

# Add our agents to the graph
workflow.add_node("scout", scout_node)
workflow.add_node("research", research_node)
workflow.add_node("writer", writer_node)

# Flow logic (How data moves from Agent to Agent)
workflow.add_edge(START, "scout")
workflow.add_edge("scout", "research")
workflow.add_edge("research", "writer")
workflow.add_edge("writer", END)

# Compile graph into a runnable application
app = workflow.compile()

if __name__ == "__main__":
    print("🚀 Starting Career-Pilot LangGraph...\n")
    # We kick off the graph by giving it the starting state
    final_state = app.invoke({"job_url": "https://wellfound.com/job/123-ai-engineer"})
    
    print("\n--- Final Output ---")
    print("Final State Dictionary contains:", final_state.keys())
    print("Draft:", final_state["drafted_response"])
