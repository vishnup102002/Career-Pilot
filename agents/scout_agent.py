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
    api_key = os.getenv("SERPER_API_KEY", "").strip()
    if not api_key:
        print("⚠️ Serper credentials missing in .env!")
        return []
        
    results = []
    try:
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({
          "q": query,
          "num": num_results,
          "gl": "in",  # Force India results regardless of server location
          "hl": "en"   # English results
        })
        headers = {
          'X-API-KEY': api_key,
          'Content-Type': 'application/json'
        }
        conn.request("POST", "/search", payload, headers)
        res = conn.getresponse()
        status_code = res.status
        data = res.read()
        json_data = json.loads(data.decode("utf-8"))
        
        if status_code != 200:
            print(f"   ⚠️ Serper API returned status {status_code}: {json_data}")
            return []
        
        # Parse organic results
        for item in json_data.get("organic", []):
            results.append({
                "title": item.get("title", ""),
                "href": item.get("link", ""),
                "body": item.get("snippet", ""),
            })
        
        if not results:
            print(f"   ⚠️ Serper returned 0 organic results. Raw keys: {list(json_data.keys())}")
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
    Returns True ONLY for URLs that clearly point to a single job posting.
    """
    lowercase_url = url.lower()
    
    # 1. Aggressively reject known aggregator / listing index patterns
    aggregator_indicators = [
        # Indeed/LinkedIn listing pages
        "/q-", "/l-", "indeed.com/q-", "indeed.com/l-", 
        "q-generative", "q-ai", "q-junior", "q-software",
        "jobs.html", "-jobs.html", "-jobs?",
        # LinkedIn listing pages
        "linkedin.com/jobs/search", "linkedin.com/jobs/collections",
        "linkedin.com/jobs/artificial", "linkedin.com/jobs/ai-",
        "linkedin.com/jobs/software", "linkedin.com/jobs/machine",
        # Glassdoor/Wellfound listing pages
        "glassdoor.com/job/us-", "glassdoor.co.in/job/",
        "glassdoor.com/job/browse", "srch_",
        "wellfound.com/role/", "wellfound.com/location/",
        # Naukri listing pages 
        "naukri.com/jobs-in", "naukri.com/software-developer-jobs",
        "naukri.com/generative-ai-jobs", "naukri.com/ai-engineer-jobs",
        "naukri.com/machine-learning-jobs",
        # Other aggregators
        "remoterocketship.com/us/jobs/",
        "ambitionbox.com/jobs/", "internshala.com/jobs/",
        "hirist.tech/", "cybotrix.com/jobs/",
        # Generic search/results pages
        "jobs/results", "/about/careers/applications/jobs/results",
        "/work-from-home/"
    ]
    
    for indicator in aggregator_indicators:
        if indicator in lowercase_url:
            return False
    
    # Also reject if URL ends with a broad listing pattern
    if re.search(r'linkedin\.com/jobs/[a-z-]+-jobs-[a-z]+', lowercase_url):
        return False  # e.g. linkedin.com/jobs/artificial-intelligence-jobs-kochi
            
    # 2. Known DIRECT single-job page patterns (very specific)
    direct_patterns = [
        "linkedin.com/jobs/view/",
        "indeed.com/viewjob",
        "indeed.com/rc/clk",
        "in.indeed.com/viewjob",
        "in.indeed.com/rc/clk",
        "weworkremotely.com/remote-jobs/",
        "glassdoor.com/job-listing",
        "glassdoor.co.in/job-listing",
        "naukri.com/job-listings",
        "instahyre.com/job/",
        "foundit.in/job/",
        "cutshort.io/job/",
        "lever.co/",
        "greenhouse.io/",
        "boards.greenhouse.io/",
        "jobs.lever.co/",
        "getmereferred.com/job-listing/",
        "myworkdayjobs.com/",
        "smartrecruiters.com/",
        "jobvite.com/",
        "icims.com/",
    ]
    
    for pattern in direct_patterns:
        if pattern in lowercase_url:
            return True
            
    # 3. URL contains /job(s)/ID pattern — a specific job posting
    if re.search(r'/jobs?/\d+', lowercase_url) or re.search(r'/job-/[a-z0-9]+', lowercase_url):
        return True
    
    # 4. Company career pages with a specific job ID
    if re.search(r'careers?\..+/jobs?/.+', lowercase_url):
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

def _build_search_queries(preferred_job: str, locations: str, resume_summary: str) -> list:
    """
    Build a diverse set of search queries optimized for finding direct job postings.
    """
    location_list = [loc.strip() for loc in locations.split(',') if loc.strip()]
    
    # Generate search variations to avoid niche title bottleneck
    clean_job = re.sub(r'\b(junior|senior|lead|intern|fresher|entry.level)\b', '', preferred_job, flags=re.IGNORECASE).strip()
    clean_job = re.sub(r'\s+', ' ', clean_job)  # collapse whitespace
    
    # Base search terms
    search_terms = [preferred_job]
    if clean_job and clean_job.lower() != preferred_job.lower():
        search_terms.append(clean_job)
    
    # Expand to broader terms based on keyword matching
    lowercase_job = preferred_job.lower()
    if any(kw in lowercase_job for kw in ["generative ai", "genai", "ai engineer", "llm"]):
        search_terms.extend(["AI Engineer", "Generative AI Engineer", "Machine Learning Engineer", "Python Developer AI"])
    elif any(kw in lowercase_job for kw in ["machine learning", "ml engineer", "data scientist"]):
        search_terms.extend(["Machine Learning Engineer", "Data Scientist", "AI Engineer"])
    elif any(kw in lowercase_job for kw in ["data analyst", "data engineer", "analytics"]):
        search_terms.extend(["Data Analyst", "Data Engineer", "Business Analyst"])
    elif any(kw in lowercase_job for kw in ["devops", "cloud", "sre", "infrastructure"]):
        search_terms.extend(["DevOps Engineer", "Cloud Engineer", "Site Reliability Engineer"])
    elif any(kw in lowercase_job for kw in ["full stack", "fullstack", "mern", "mean"]):
        search_terms.extend(["Full Stack Developer", "Software Engineer", "Web Developer"])
    elif any(kw in lowercase_job for kw in ["frontend", "front end", "react", "angular", "vue"]):
        search_terms.extend(["Frontend Developer", "React Developer", "UI Developer"])
    elif any(kw in lowercase_job for kw in ["backend", "back end", "api", "microservices"]):
        search_terms.extend(["Backend Developer", "Software Engineer", "Python Developer"])
    elif any(kw in lowercase_job for kw in ["software", "developer", "engineer", "programmer"]):
        search_terms.extend(["Software Engineer", "Software Developer", "Python Developer"])
    elif any(kw in lowercase_job for kw in ["android", "ios", "mobile", "flutter", "react native"]):
        search_terms.extend(["Mobile Developer", "Android Developer", "Flutter Developer"])
    elif any(kw in lowercase_job for kw in ["cyber", "security", "penetration", "soc"]):
        search_terms.extend(["Cybersecurity Analyst", "Security Engineer", "SOC Analyst"])
    else:
        # Generic fallback — add "Developer" and "Engineer" variants
        search_terms.extend([f"{clean_job} Developer", f"{clean_job} Engineer"])
        
    # Remove duplicates while preserving order
    search_terms = list(dict.fromkeys([term.strip() for term in search_terms if term.strip()]))
    
    search_queries = []
    
    # PHASE 1: Site-specific direct job URL queries (highest signal)
    for term in search_terms[:4]:
        for location in location_list[:3]:
            is_india = any(loc in location.lower() for loc in [
                "kochi", "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad", 
                "chennai", "pune", "india", "noida", "gurgaon", "gurugram",
                "kolkata", "ahmedabad", "jaipur", "thiruvananthapuram", "trivandrum"
            ])
            loc_suffix = f"{location} India" if (is_india and "india" not in location.lower()) else location
            
            search_queries.append(f'site:linkedin.com/jobs/view/ {term} {loc_suffix}')
            search_queries.append(f'site:indeed.com/viewjob {term} {loc_suffix}')
        
        # Broader India-wide site queries
        search_queries.append(f'site:linkedin.com/jobs/view/ {term} India')
        search_queries.append(f'site:naukri.com/job-listings {term}')
    
    # PHASE 2: Remote job queries
    for term in search_terms[:2]:
        search_queries.append(f'site:linkedin.com/jobs/view/ {term} remote')
        search_queries.append(f'site:weworkremotely.com/remote-jobs/ {term}')
    
    # PHASE 3: Open web queries as fallback (broader coverage)
    from datetime import datetime
    current_year = datetime.now().year
    for term in search_terms[:3]:
        search_queries.append(f'{term} jobs India apply {current_year}')
        search_queries.append(f'{term} hiring India {current_year}')
    
    # PHASE 4: Naukri/Foundit specific (popular in India)
    for term in search_terms[:2]:
        search_queries.append(f'site:naukri.com {term} jobs')
        search_queries.append(f'site:foundit.in {term}')

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
    
    # Deduplicate and cap at 16 queries (balance coverage vs API cost)
    search_queries = list(dict.fromkeys(search_queries))[:16]
    
    return search_queries

def scout_node(state: AgentState):
    try:
        return _scout_node_inner(state)
    except Exception as e:
        print(f"🚨 ScoutAgent CRASHED: {e}")
        import traceback
        traceback.print_exc()
        return {"found_jobs": f"NO STRICT MATCHES FOUND TODAY. (Pipeline error: {str(e)[:100]})", "extracted_urls": []}

def _scout_node_inner(state: AgentState):
    preferred_job = state.get('preferred_job', '').strip()
    locations = state.get('locations', '').strip()
    resume_summary = state.get('resume_summary', '')
    
    print(f"🕵️  ScoutAgent: Searching for '{preferred_job}' in [{locations}]...")
    
    # Build optimized search queries
    search_queries = _build_search_queries(preferred_job, locations, resume_summary)
    
    print(f"🌐 ScoutAgent: Executing {len(search_queries)} targeted Google searches...")
    
    all_results = []
    seen_urls = set()
    
    for query in search_queries:
        try:
            results = serper_search(query, num_results=10)
            new_count = 0
            for r in results:
                url = r.get('href', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)
                    new_count += 1
            print(f"   ✅ '{query}': {len(results)} results ({new_count} new)")
        except Exception as e:
            print(f"   ⚠️ Search failed for '{query}': {e}")
            continue
    
    print(f"   🔍 Serper returned: {len(all_results)} total unique results")
    
    # Filter Serper results to prioritize direct job description URLs
    direct_job_results = [r for r in all_results if is_direct_job_url(r.get('href', ''))]
    rejected_results = [r for r in all_results if not is_direct_job_url(r.get('href', ''))]
    
    print(f"   📊 URL filter: {len(direct_job_results)} direct jobs, {len(rejected_results)} aggregator/listing pages rejected")
    if rejected_results:
        for r in rejected_results[:3]:
            print(f"      ❌ Rejected: {r.get('href', '')[:80]}")
    
    # Use direct job results if we have enough, otherwise fall back to all results
    if len(direct_job_results) >= 3:
        scraped_data = direct_job_results
        print(f"   ✅ Using {len(scraped_data)} direct job listings")
    elif direct_job_results:
        # We have some direct results but not enough — supplement with non-rejected results
        scraped_data = direct_job_results + rejected_results
        print(f"   ⚠️ Only {len(direct_job_results)} direct jobs found. Supplementing with all {len(scraped_data)} results.")
    else:
        scraped_data = all_results
        print(f"   ⚠️ No direct job URLs found. Using all {len(all_results)} results.")

    if len(scraped_data) == 0:
        print("⚠️ ScoutAgent: No results from Serper. Skipping LLM matching.")
        print(f"   📊 DIAGNOSTIC: {len(search_queries)} queries executed, {len(all_results)} total results, 0 after filtering")
        return {"found_jobs": "NO STRICT MATCHES FOUND TODAY. The job search returned zero results. Please try again later.", "extracted_urls": []}

    # Skip MCP deep scraping — use Serper snippets directly for speed and reliability
    # MCP Browser server crashes on HF Spaces due to Playwright/Chromium issues
    max_candidates = min(len(scraped_data), 12)
    print(f"🕵️  ScoutAgent: Using Serper snippets for top {max_candidates} jobs (skipping deep scrape for reliability)...")
    
    final_job_data = []
    for data in scraped_data[:max_candidates]:
        url = data.get('href')
        final_job_data.append({
            "title": data.get('title'),
            "href": url,
            "text_source": "serper_snippet",
            "content": data.get('body')
        })
        print(f"   ℹ️ {data.get('title', '')[:60]} -> {url[:70]}")
    
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
    {scraped_text[:15000]}
    
    Previously Sent Jobs (DO NOT suggest these URLs again):
    {state.get('previously_sent_jobs', [])}
    
    Task: Find the top 1 to 5 jobs that are the BEST MATCH for this user.
    
    EVALUATION CRITERIA (score each job out of 5):
    1. JOB ROLE MATCH: The job title/description should be related to "{preferred_job}" or closely adjacent fields. Adjacent roles (e.g., ML Engineer for an AI Engineer candidate, or Full Stack for a Backend candidate) are acceptable matches.
    2. LOCATION MATCH: The job should be in one of these locations: {locations}, or be a remote position. If location is unclear from the snippet, ASSUME it's a match.
    3. EXPERIENCE MATCH: The user's experience level should reasonably fit the job requirements. For junior/fresher candidates, jobs requiring 0-3 years experience ARE valid matches. If experience is not mentioned in the snippet, ASSUME it's a match.
    4. EDUCATION MATCH: Only reject if the job explicitly requires a degree the user clearly lacks. If not mentioned, ASSUME it's a match.
    5. SKILL MATCH: The user should possess most of the core technical skills mentioned. Partial overlap is acceptable.
    
    SCORING:
    - Jobs passing 4-5 criteria = STRONG MATCH (always include)
    - Jobs passing 3 criteria = POSSIBLE MATCH (include if fewer than 3 strong matches)
    - Jobs passing 0-2 criteria = REJECT
    
    IMPORTANT RULES:
    - When the search snippet is short, be GENEROUS. A snippet saying "AI Engineer - Bangalore" should be treated as a match if role and location fit.
    - PREFER direct job page URLs (linkedin.com/jobs/view/, indeed.com/viewjob, naukri.com/job-listings) over listing pages.
    - It is BETTER to include a borderline match than to return zero results.
    - If ZERO jobs pass 3+ criteria, LOWER your threshold to 2 and include the top 3 closest matches.
    
    If after all this you truly have ZERO viable results, reply with EXACTLY: "NO STRICT MATCHES FOUND TODAY."
    
    CRITICAL URL RULE: You MUST copy the EXACT 'href' URL from the JSON data. DO NOT modify, shorten, or fabricate any URL!
    
    Format matches EXACTLY like this:
    1. [Job Title] at [Company] — [Location]
       Match Score: [e.g., 85%]
       Why it's a match: [Brief explanation of how their skills, experience, and location align]
       Apply Here: [EXACT 'href' URL from the JSON data]
    """
    
    response = llm.invoke([HumanMessage(content=prompt)]) if llm else type('obj', (object,), {'content': '1. AI Engineer at Acme'})()
    
    # Extract URLs so we can save them in SQLite for deduction tomorrow
    urls = re.findall(r'(https?://[^\s\)]+)', response.content)
    # Clean trailing punctuation from URLs
    urls = [url.rstrip('.,;:!?)') for url in urls]
    
    print(f"   🎯 LLM matched {len(urls)} job URLs")
    
    return {"found_jobs": response.content, "extracted_urls": urls}
