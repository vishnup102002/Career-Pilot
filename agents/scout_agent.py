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
            
    # 2. Known direct job page patterns
    direct_patterns = [
        "linkedin.com/jobs/view/",
        "indeed.com/viewjob",
        "indeed.com/rc/clk",
        "weworkremotely.com/remote-jobs/",
        "glassdoor.com/job-listing",
        "glassdoor.co.in/job-listing",
        "wellfound.com/jobs/",
        "naukri.com/job-listings",
        "upwork.com/jobs/",
        "lever.co",
        "greenhouse.io",
        "/job/",
        "/jobs/"
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
            
            # LinkedIn
            search_queries.append(f'site:linkedin.com/jobs/view/ {term} {loc_suffix}')
            # Indeed
            search_queries.append(f'site:indeed.com/viewjob {term} {loc_suffix}')
        
        # Remote search queries targeting India or globally
        search_queries.append(f'site:linkedin.com/jobs/view/ {term} remote India')
        search_queries.append(f'site:indeed.com/viewjob {term} remote India')
        search_queries.append(f'site:weworkremotely.com/remote-jobs/ {term}')
        
    # Limit queries to 8 to avoid rate limits / API cost explosion
    search_queries = list(dict.fromkeys(search_queries))[:8]
    
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
    
    # Filter Serper results to prioritize direct job description URLs
    direct_job_results = [r for r in all_results if is_direct_job_url(r.get('href', ''))]
    
    if direct_job_results:
        scraped_data = direct_job_results
        print(f"   📊 Aggregated {len(scraped_data)} direct job listings (filtered down from {len(all_results)} total results)")
    else:
        scraped_data = all_results
        print(f"   ⚠️ No direct job URLs matched heuristics. Falling back to all {len(all_results)} search results.")

    if len(scraped_data) == 0:
        print("⚠️ ScoutAgent: No results from Serper. Skipping LLM matching.")
        return {"found_jobs": "NO STRICT MATCHES FOUND TODAY. The job search returned zero results. Please try again later.", "extracted_urls": []}

    # Extract top 3 URLs for deep scraping via MCP Client
    top_urls = [data.get('href') for data in scraped_data[:3] if data.get('href')]
    
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
    for data in scraped_data[:3]:
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
                print(f"   ⚠️ Falling back to Serper Google snippet for: {url}")

    scraped_text = json.dumps(final_job_data, indent=2)

    print("🕵️  ScoutAgent: Matching Serper Google results against Resume + Preferences...")
    prompt = f"""
    You are a RUTHLESS, highly critical AI Job Matcher. DO NOT HALLUCINATE OR BE LENIENT.
    
    USER PROFILE: 
    {resume_summary}
    
    USER PREFERENCES:
    - Preferred Job Role: {preferred_job}
    - Preferred Locations: {locations}
    
    LIVE GOOGLE SEARCH JOB RESULTS:
    {scraped_text[:8000]}
    
    Previously Sent Jobs (DO NOT suggest these URLs again):
    {state.get('previously_sent_jobs', [])}
    
    Task: Find the top 1 to 5 jobs that are a PERFECT, STRICT MATCH for this user's resume AND preferences.
    
    YOUR STRICT EVALUATION RULES:
    1. JOB ROLE MATCH: The job title/description must closely match "{preferred_job}". Unrelated roles must be instantly rejected.
    2. LOCATION MATCH: The job must be in one of these locations: {locations}, or be a remote position.
    3. CRITICAL EXPERIENCE MATCH: The User's experience level MUST strictly match or exceed the job's minimum experience requirements. If the job requires more experience than the User currently possesses, you MUST instantly reject it. ZERO EXCEPTIONS. Do not ignore experience mismatch even if their skills align perfectly.
    4. EDUCATION MATCH: If the job requires a specific Degree and the User's profile does not state they have it, reject it.
    5. SKILL MATCH: The User MUST possess the core mandatory technical skills required by the job description.
    
    If NO jobs pass ALL 5 rules, you MUST simply reply: "NO STRICT MATCHES FOUND TODAY."
    
    CRITICAL URL RULE: You MUST copy the EXACT 'href' URL from the JSON data. DO NOT modify, shorten, or fabricate any URL!
    
    If you find perfect matches, format them EXACTLY like this:
    1. [Job Title] at [Company] — [Location]
       Match Score: [e.g., 95%]
       Why it's a match: [Explain how their skills, experience, and location preference align]
       Apply Here: [EXACT 'href' URL from the JSON data]
    """
    
    response = llm.invoke([HumanMessage(content=prompt)]) if llm else type('obj', (object,), {'content': '1. AI Engineer at Acme'})()
    
    # Extract URLs so we can save them in SQLite for deduction tomorrow
    urls = re.findall(r'(https?://[^\s]+)', response.content)
    
    return {"found_jobs": response.content, "extracted_urls": urls}
