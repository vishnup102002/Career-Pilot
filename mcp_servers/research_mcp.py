from mcp.server.fastmcp import FastMCP
import chromadb

mcp = FastMCP("ResearchBrowser")

@mcp.tool()
def search_resume_experience(query: str, n_results: int = 3) -> str:
    """
    Given a job requirement or target tech stack (e.g., "Python LangGraph experience"), 
    this tool queries the local ChromaDB vector store and returns the most relevant
    bullet points from the user's resume.
    """
    client = chromadb.PersistentClient(path="db/resume_chroma")
    
    try:
        collection = client.get_collection(name="resume_bullets")
    except Exception:
        return "Error: Resume collection not found. Please ensure 'db/setup_db.py' was run."
        
    # Performs a semantic search (using algorithms like Cosine Similarity) automatically!
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    if results and results.get("documents") and len(results["documents"][0]) > 0:
        formatted = "Found relevant resume experience:\n"
        for doc in results["documents"][0]:
            formatted += f"- {doc}\n"
        return formatted
        
    return "No strongly correlated experience found."

if __name__ == "__main__":
    print("Starting Research MCP Server...")
    # FastMCP automatically hosts the query function for any LLM client to use.
    mcp.run()
