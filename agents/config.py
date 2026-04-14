import os
from dotenv import load_dotenv

load_dotenv()

# Centralize the LLM instantiation
# Using Groq as primary (free, reliable, no quota issues)
# Switch to Gemini by setting USE_GEMINI=true in .env when quota resets
llm = None

use_gemini = os.getenv("USE_GEMINI", "false").lower() == "true"

if use_gemini and os.getenv("GOOGLE_API_KEY"):
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    print("🧠 LLM: Gemini 2.0 Flash loaded!")

if llm is None and os.getenv("GROQ_API_KEY"):
    from langchain_groq import ChatGroq
    llm = ChatGroq(model="llama-3.1-8b-instant")
    print("🧠 LLM: Groq Llama 3.1 8B loaded!")

if llm is None:
    print("❌ No LLM configured! Add GROQ_API_KEY or GOOGLE_API_KEY to .env")
