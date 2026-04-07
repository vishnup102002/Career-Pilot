This is a high-signal project for your 2026 portfolio. It demonstrates that you understand Model Context Protocol (MCP), Stateful Agents (LangGraph), and the ethical balance of Human-in-the-Loop AI.
Below is a professional README.md designed to impress a CTO at a company like Alchemyst AI. It positions you not as a "spammer," but as an AI Orchestrator.

Career-Pilot: MCP-Driven Agentic Job Intelligence
Career-Pilot is an agentic ecosystem designed to solve the "Context Gap" in technical job hunting. Instead of blind automation, it uses the Model Context Protocol (MCP) to orchestrate deep research, resume alignment, and human-in-the-loop application drafting across platforms like Wellfound, LinkedIn, and Instahyre.
核心 (Core) Philosophy
In the 2026 recruitment landscape, "Auto-Appliers" are filtered out. Career-Pilot focuses on High-Intent Alignment:
1. Discover: Scouts roles matching specific tech stacks (e.g., Python, RAG, LangGraph).
2. Research: Scrapes company engineering blogs and recent news via MCP.
3. Draft: Generates hyper-personalized "Why us?" responses based on technical synergy.
4. Human-Check: Pings the user via WhatsApp/Slack for a final review before submission.

🛠 Tech Stack
* Orchestration: LangGraph (Stateful Multi-Agent Workflows)
* Protocol: Model Context Protocol (MCP)
* Agents: * ScoutAgent: Playwright-based browser MCP for live job scraping.
    * ResearchAgent: Specialized MCP server for analyzing GitHub repos and Tech Blogs.
    * WriterAgent: LLM-driven (Claude 3.5/GPT-4o) alignment engine.
* Database: SQLite (Job tracking) & ChromaDB (Vectorized Resume/Experience)
* Human-in-the-Loop: WhatsApp/Telegram API for approval triggers.

🚀 Key Features & MCP Servers
1. The Browser-MCP Server
Provides a standardized interface for the agent to navigate modern SPAs (Single Page Applications) like Wellfound without triggering bot-detection.
* Tools: Maps_to_job, extract_requirements, detect_application_fields.
2. The Context-Research MCP
A dedicated server that takes a company URL and returns a "Technical DNA" report.
* Tools: fetch_engineering_stack, summarize_recent_funding, match_resume_to_role.
3. The Approval Loop (HITL)
Prevents "Bot-Banning" by requiring a manual signature. The agent sends a JSON payload to the user:
"Vishnu, I found a GenAI lead role at Teal India. They use Llama-Index (which you used in Project X). Here is the drafted response. [Approve / Edit / Skip]"

📦 Installation & Setup
1. Clone the Project: Bash  git clone https://github.com/your-username/career-pilot-mcp.git
2. cd career-pilot-mcp
3.    
4. Install Dependencies: Bash  pip install mcp langgraph playwright
5. playwright install chromium
6.    
7. Configure MCP Servers: Add your server configurations to your local MCP settings file (e.g., claude_desktop_config.json).
8. Initialize the Agent: Python  python main.py --focus "AI Engineer" --location "Remote, Bengaluru"
9.    

🛡 Ethical Considerations & Anti-Bot Strategy
* No Headless Spam: The system operates with randomized delays and human-like scrolling.
* Privacy First: Resume data is stored locally; only job-specific metadata is sent to the LLM for drafting.
* Quality > Quantity: Optimized to find the top 5 daily matches rather than 100 random ones.

📈 Future Roadmap
* [ ] Interview Simulator: Use the ResearchAgent to generate 10 mock interview questions based on the company's specific tech stack.
* [ ] Salary Intelligence: Integrate real-time market data to suggest optimal salary ranges during the application phase.

How to explain this in your next interview:
"I built Career-Pilot because I saw a flaw in how AI was being used for job hunting. Most tools just spam; I wanted to build an Intelligence Agent. I used MCP to give the LLM 'eyes' into company culture and 'hands' to navigate complex job boards. It’s a study in stateful orchestration (LangGraph) and building AI that works with humans, not instead of them."

Next Step for you: Create a new GitHub repo with this README. Then, start by building the first MCP Tool that can read a Wellfound job description and return a list of "Must-Have" vs "Nice-to-Have" skills.
Want the Python boilerplate for that first "Scout" MCP tool?
