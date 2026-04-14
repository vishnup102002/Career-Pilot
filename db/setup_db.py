import sqlite3
import chromadb
import os

def setup_sqlite():
    print("Setting up SQLite for job tracking...")
    # SQLite helps us track state (which jobs we've seen, scraped, or applied to)
    os.makedirs("db", exist_ok=True)
    conn = sqlite3.connect("db/jobs.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            job_title TEXT,
            url TEXT,
            status TEXT, -- 'discovered', 'researched', 'drafted', 'applied'
            must_have_skills TEXT,
            nice_to_have_skills TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("SQLite database ready at db/jobs.db")

def setup_chroma():
    print("Setting up ChromaDB for Resume storage...")
    # Chroma is a local vector database. 
    # persistent_client saves embedded vectors to a local folder
    client = chromadb.PersistentClient(path="db/resume_chroma")
    
    # Collections are like tables in traditional databases
    collection = client.get_or_create_collection(name="resume_bullets")
    
    # We will embed some dummy resume bullet points.
    documents = [
        "Built a multi-agent system using LangGraph and Python to automate workflows.",
        "Used Model Context Protocol (MCP) to allow agents to interact with Playwright.",
        "Experienced in React, Next.js, and TypeScript for Frontend development.",
        "Set up vector databases like ChromaDB and Pinecone for Retrieval-Augmented Generation.",
        "Created an end-to-end Python backend using FastAPI and SQLite."
    ]
    
    # Each document needs a unique ID
    ids = [f"bullet_{i}" for i in range(len(documents))]
    
    # Upsert automatically runs the document through an embedding model (like all-MiniLM-L6-v2)
    # and stores it locally for fast semantic search
    collection.upsert(
        documents=documents,
        ids=ids
    )
    print(f"Added {len(documents)} resume bullet points to ChromaDB.")

if __name__ == "__main__":
    print("Initializing databases...")
    setup_sqlite()
    setup_chroma()
