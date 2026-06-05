import json
import re
import os
import sys
import http.client
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.messages import HumanMessage
from agents.state import AgentState
from agents.config import llm

def serper_search(query, num_results=10):
    """
    Uses Serper.dev to get real Google search results seamlessly.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        print("⚠️ Serper credentials missing in .env!")
        return []
        
    results = []
    try:
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({
          "q": query,
          "num": num_results
        })
        headers = {
          'X-API-KEY': api_key,
          'Content-Type': 'application/json'
        }
        conn.request("POST", "/search", payload, headers)
        res = conn.getresponse()
        data = res.read()
        json_data = json.loads(data.decode("utf-8"))
        
        # Parse organic results
        for item in json_data.get("organic", []):
            results.append({
                "title": item.get("title", ""),
                "href": item.get("link", ""),
                "body": item.get("snippet", ""),
            })
    except Exception as e:
        print(f"   ⚠️ Serper search failed: {e}")
        
    return results

async def scrape_urls_with_mcp(urls):
    """
    Connects to the local Browser MCP Server to scrape full job descriptions.
    """
    if not urls:
        return []
        
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_servers/browser_mcp.py"],
    )
    
    results = []
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                for url in urls:
                    try:
                        print(f"   🤖 MCP Client: Asking Browser Server to scrape -> {url}")
                        res = await session.call_tool("scrape_job_description", arguments={"url": url})
                        if res.content and len(res.content) > 0:
                            results.append({
                                "url": url, 
                                "full_text": res.content[0].text
                            })
                    except Exception as scrape_err:
                        print(f"   ⚠️ MCP Client failed to scrape {url}: {scrape_err}")
    except Exception as e:
        print(f"   🚨 Failed to connect to MCP Server: {e}")
        
    return results

def is_direct_job_url(url: str) -> bool:
    """
    Heuristics to determine if a URL points to a specific direct job description page,
    rather than a search results aggregator / search index page.
    """
    lowercase_url = url.lower()
    
    # 1. Common aggregator/listing index indicators to instantly reject
    aggregator_indicators = [
        "/q-", "/jobs-in-", "/l-", "indeed.com/q-", "indeed.com/l-", 
        "glassdoor.com/job/us-", "wellfound.com/role/", "wellfound.com/location/",
        "remoterocketship.com/us/jobs/", "linkedin.com/jobs/search",
        "linkedin.com/jobs/collections", "naukri.com/jobs-in", "naukri.com/software-developer-jobs",
        "glassdoor.com/job/browse"
    ]
    
    for indicator in aggregator_indicators:
        if indicator in lowercase_url:
            return False
            
    # 2. Known direct job page patterns (including Indian job boards)
    direct_patterns = [
        "linkedin.com/jobs/view/",
        "indeed.com/viewjob",
        "indeed.com/rc/clk",
        "in.indeed.com/viewjob",
        "in.indeed.com/rc/clk",
        "weworkremotely.com/remote-jobs/",
        "glassdoor.com/job-listing",
        "glassdoor.co.in/job-listing",
        "wellfound.com/jobs/",
        "naukri.com/job-listings",
        "instahyre.com/job/",
        "foundit.in/job/",
        "cutshort.io/jobs/",
        "upwork.com/jobs/",
        "lever.co",
        "greenhouse.io",
        "boards.greenhouse.io",
        "jobs.lever.co",
        "careers.",
        "jobs.",
        "/job/",
        "/jobs/",
        "/careers/"
    ]
    
    for pattern in direct_patterns:
        if pattern in lowercase_url:
            return True
            
    # 3. If the URL contains '/jobs/number' or similar, it's likely a direct job page
    if re.search(r'/jobs?/\d+', lowercase_url) or re.search(r'/job-/[a-z0-9]+', lowercase_url):
        return True
        
    return False

def is_high_signal_text(text: str) -> bool:
    """
    Checks if the scraped text contains actual job description details
    rather than a login wall, captcha, or redirect page.
    """
    if not text:
        return False
    lowercase_text = text.lower()
    
    # Check if we were blocked, redirected to login page, or hit access issues
    blocked_indicators = [
        "sign in", "login", "log in", "security check", "captcha", 
        "check your browser", "robot", "forbidden", "access denied", 
        "page not found", "error 403", "error 404", "failed to scrape"
    ]
    for indicator in blocked_indicators:
        if indicator in lowercase_text and len(lowercase_text) < 1500:
            return False
            
    # Check for presence of typical job description words
    job_keywords = ["experience", "requirement", "qualification", "responsibilities", "skills", "description", "apply", "candidate", "about the role"]
    matches = sum(1 for kw in job_keywords if kw in lowercase_text)
    if matches < 2:
        return False
        
    return True

def scout_node(state: AgentState):
    preferred_job = state.get('preferred_job', '').strip()
    locations = state.get('locations', '').strip()
    resume_summary = state.get('resume_summary', '')
    
    print(f"🕵️  ScoutAgent: Searching for '{preferred_job}' in [{locations}]...")
    
    # Build smart search queries using the user's preferred job + locations
    location_list = [loc.strip() for loc in locations.split(',') if loc.strip()]
    
    # Generate search variations to avoid niche title bottleneck
    clean_job = preferred_job.replace("Junior", "").replace("junior", "").replace("Senior", "").replace("senior", "").replace("Lead", "").replace("lead", "").strip()
    
    # Base search terms
    search_terms = [preferred_job, clean_job]
    
    # Expand to broader terms based on keyword matching
    lowercase_job = preferred_job.lower()
    if "generative ai" in lowercase_job or "genai" in lowercase_job or "ai" in lowercase_job:
        search_terms.extend(["AI Engineer", "Generative AI Engineer", "Python Developer", "Machine Learning Engineer"])
    elif "data" in lowercase_job:
        search_terms.extend(["Data Scientist", "Data Analyst", "Machine Learning Engineer"])
    elif "devops" in lowercase_job or "cloud" in lowercase_job:
        search_terms.extend(["DevOps Engineer", "Cloud Engineer", "Site Reliability Engineer"])
    elif "full stack" in lowercase_job or "software" in lowercase_job or "developer" in lowercase_job or "engineer" in lowercase_job:
        search_terms.extend(["Software Engineer", "Python Developer", "Full Stack Developer"])
        
    # Remove duplicates and empty items
    search_terms = list(dict.fromkeys([term.strip() for term in search_terms if term.strip()]))
    
    search_queries = []
    for term in search_terms[:3]: # Limit to top 3 search terms to prevent query explosion
        for location in location_list:
            # Check if the location is in India or remote to target local/remote India job postings
            is_india_or_local = any(loc in location.lower() for loc in ["kochi", "bangalore", "mumbai", "delhi", "hyderabad", "chennai", "pune", "india"])
            loc_suffix = f"{location} India" if (is_india_or_local and "india" not in location.lower()) else location
            
            # OPEN WEB QUERIES (highest priority — no site: restriction)
            search_queries.append(f'{term} jobs {loc_suffix} 2025')
            search_queries.append(f'{term} hiring {loc_suffix}')
        
        # Site-specific queries as supplementary sources
        search_queries.append(f'site:linkedin.com/jobs/view/ {term} India')
        search_queries.append(f'site:naukri.com {term}')
        
        # Remote search queries
        search_queries.append(f'{term} remote jobs India 2025')
        search_queries.append(f'site:weworkremotely.com/remote-jobs/ {term}')
        
    # Limit queries to 12 to balance coverage vs API cost
    search_queries = list(dict.fromkeys(search_queries))[:12]
    
    # LLM-optimized extra query
    if llm and resume_summary:
        query_prompt = f"""Given this Resume Summary: {resume_summary}
The user wants: {preferred_job} jobs in {locations}.
Write ONE highly optimized 5-6 word search query combining their skills with the job role.
If the user is a junior or fresher, include 'junior' or 'entry level'.
Reply with ONLY the query string, nothing else. No quotes."""
        try:
            extra_query = llm.invoke([HumanMessage(content=query_prompt)]).content.strip().replace('"', '')
            search_queries.append(extra_query)
            print(f"   -> LLM-optimized query: {extra_query}")
        except Exception as e:
            print(f"   ⚠️ LLM query generation failed: {e}")
    
    print(f"🌐 ScoutAgent: Executing {len(search_queries)} targeted Google searches...")
    
    all_results = []
    seen_urls = set()
    
    for query in search_queries:
        try:
            results = serper_search(query, num_results=10)
            for r in results:
                url = r.get('href', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)
            print(f"   ✅ '{query}': {len(results)} results")
        except Exception as e:
            print(f"   ⚠️ Search failed for '{query}': {e}")
            continue
    
    print(f"   🔍 Serper returned: {len(all_results)} total unique results")
    
    # Filter Serper results to prioritize direct job description URLs
    direct_job_results = [r for r in all_results if is_direct_job_url(r.get('href', ''))]
    
    # Smart fallback: if the filter drops >70% of results, it's being too aggressive — skip it
    if direct_job_results and len(direct_job_results) >= len(all_results) * 0.3:
        scraped_data = direct_job_results
        print(f"   📊 After URL filter: {len(scraped_data)} direct job listings (from {len(all_results)} total)")
    else:
        scraped_data = all_results
        if direct_job_results:
            print(f"   ⚠️ URL filter too aggressive ({len(direct_job_results)}/{len(all_results)} passed). Using all results.")
        else:
            print(f"   ⚠️ No direct job URLs matched heuristics. Using all {len(all_results)} results.")

    if len(scraped_data) == 0:
        print("⚠️ ScoutAgent: No results from Serper. Skipping LLM matching.")
        print(f"   📊 DIAGNOSTIC: {len(search_queries)} queries executed, {len(all_results)} total results, 0 after filtering")
        return {"found_jobs": "NO STRICT MATCHES FOUND TODAY. The job search returned zero results. Please try again later.", "extracted_urls": []}

    # Extract top 5 URLs for deep scraping via MCP Client
    top_urls = [data.get('href') for data in scraped_data[:5] if data.get('href')]
    
    print(f"🕵️  ScoutAgent: Booting MCP Browser Server to deep-read top {len(top_urls)} jobs...")
    try:
        deep_scraped = asyncio.run(scrape_urls_with_mcp(top_urls))
    except Exception as e:
        print(f"   ⚠️ MCP invocation error: {e}")
        deep_scraped = []

    # Build final list of job descriptions.
    # If deep scraping succeeded and returned high-signal text, use it.
    # Otherwise, fallback to the Serper Google snippet.
    final_job_data = []
    for data in scraped_data[:8]:
        url = data.get('href')
        # Check if we have deep-scraped text for this URL
        deep_match = next((item for item in deep_scraped if item['url'] == url), None)
        
        if deep_match and is_high_signal_text(deep_match['full_text']):
            final_job_data.append({
                "title": data.get('title'),
                "href": url,
                "text_source": "mcp_deep_scrape",
                "content": deep_match['full_text'][:4000] # Limit size to avoid LLM context bloat
            })
            print(f"   ✅ Using FULL deep-scraped text for: {url}")
        else:
            final_job_data.append({
                "title": data.get('title'),
                "href": url,
                "text_source": "serper_snippet",
                "content": data.get('body')
            })
            if deep_match:
                print(f"   ⚠️ Scraped text for {url} looks like a login wall or captcha. Falling back to Serper Google snippet.")
            else:
                print(f"   ℹ️ Using Serper snippet for: {url}")
    
    print(f"   📊 Sending {len(final_job_data)} candidates to LLM for matching")

    scraped_text = json.dumps(final_job_data, indent=2)

    print("🕵️  ScoutAgent: Matching search results against Resume + Preferences...")
    prompt = f"""
    You are a precise AI Job Matcher. Your job is to find the BEST matches between a user's profile and live job results.
    
    USER PROFILE: 
    {resume_summary}
    
    USER PREFERENCES:
    - Preferred Job Role: {preferred_job}
    - Preferred Locations: {locations}
    
    LIVE SEARCH JOB RESULTS:
    {scraped_text[:12000]}
    
    Previously Sent Jobs (DO NOT suggest these URLs again):
    {state.get('previously_sent_jobs', [])}
    
    Task: Find the top 1 to 5 jobs that are the BEST MATCH for this user.
    
    EVALUATION CRITERIA (score each job out of 5):
    1. JOB ROLE MATCH: The job title/description should be related to "{preferred_job}" or closely adjacent fields. Adjacent roles (e.g., ML Engineer for an AI Engineer candidate) are acceptable.
    2. LOCATION MATCH: The job should be in one of these locations: {locations}, or be a remote position. If location is unclear from the snippet, still include the job.
    3. EXPERIENCE MATCH: The user's experience level should reasonably fit the job requirements. For junior/fresher candidates, jobs requiring 0-2 years experience ARE valid matches. If the snippet does not specify experience requirements, do NOT reject the job.
    4. EDUCATION MATCH: Only reject if the job explicitly requires a degree the user clearly lacks.
    5. SKILL MATCH: The user should possess most of the core technical skills mentioned in the job description.
    
    SCORING:
    - Jobs passing 4-5 criteria = STRONG MATCH (include these)
    - Jobs passing 3 criteria = POSSIBLE MATCH (include these if fewer than 3 strong matches exist)
    - Jobs passing 0-2 criteria = REJECT
    
    IMPORTANT: When the search snippet is short (Serper snippet), be GENEROUS with your evaluation. A snippet saying "AI Engineer - Bangalore" with no other details should be treated as a possible match if role and location fit.
    
    If NO jobs pass at least 3 criteria, reply with EXACTLY: "NO STRICT MATCHES FOUND TODAY."
    
    CRITICAL URL RULE: You MUST copy the EXACT 'href' URL from the JSON data. DO NOT modify, shorten, or fabricate any URL!
    
    Format matches EXACTLY like this:
    1. [Job Title] at [Company] — [Location]
       Match Score: [e.g., 85%]
       Why it's a match: [Brief explanation of how their skills, experience, and location align]
       Apply Here: [EXACT 'href' URL from the JSON data]
    """
    
    response = llm.invoke([HumanMessage(content=prompt)]) if llm else type('obj', (object,), {'content': '1. AI Engineer at Acme'})()
    
    # Extract URLs so we can save them in SQLite for deduction tomorrow
    urls = re.findall(r'(https?://[^\s]+)', response.content)
    
    return {"found_jobs": response.content, "extracted_urls": urls}
