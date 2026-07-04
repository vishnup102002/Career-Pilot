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

def serper_search(query, num_results=10, time_filter="qdr:m"):
    """
    Uses Serper.dev to get real Google search results.
    time_filter: 'qdr:d' (past day), 'qdr:w' (past week), 'qdr:m' (past month), None (all time)
    """
    api_key = os.getenv("SERPER_API_KEY", "").strip()
    if not api_key:
        print("⚠️ Serper credentials missing in .env!")
        return []
        
    results = []
    try:
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload_dict = {
          "q": query,
          "num": num_results,
          "gl": "in",
          "hl": "en"
        }
        # Add time-based filter to get only recent results
        if time_filter:
            payload_dict["tbs"] = time_filter
        
        payload = json.dumps(payload_dict)
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
                "date": item.get("date", ""),
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

def _is_stale_job(result: dict) -> bool:
    """
    Detect stale/expired job postings from snippet text or metadata.
    Returns True if the job appears old or expired.
    """
    text = (result.get('body', '') + ' ' + result.get('title', '') + ' ' + result.get('date', '')).lower()
    
    # Expired/closed indicators
    stale_indicators = [
        "no longer accepting", "this job has expired", "position filled",
        "position closed", "application closed", "job closed",
        "no longer available", "listing has expired",
    ]
    for indicator in stale_indicators:
        if indicator in text:
            return True
    
    # Old date indicators (more than ~2 months old)
    old_date_patterns = [
        r'\b(\d+)\+?\s*years?\s*ago\b',
        r'\b([3-9]|1[0-2])\+?\s*months?\s*ago\b',  # 3+ months ago
    ]
    for pattern in old_date_patterns:
        match = re.search(pattern, text)
        if match:
            return True
    
    return False

def _is_stale_job_content(text: str) -> bool:
    """
    Check if the full scraped content indicates the job is expired, filled, or closed.
    """
    if not text:
        return False
    lowercase_text = text.lower()
    
    expired_indicators = [
        "no longer accepting applications",
        "this job has expired",
        "position has been filled",
        "job is closed",
        "no longer accepting",
        "job posting has been removed",
        "not accepting applications",
        "page not found",
        "404 error",
        "unable to load this page",
        "job is no longer active",
        "unable to load the page",
        "job posting is no longer available",
    ]
    for indicator in expired_indicators:
        if indicator in lowercase_text:
            return True
            
    return False

def scrape_url_via_jina(url: str, retries=1) -> str:
    """
    Scrapes the text/markdown content of a job page using Jina Reader API.
    Uses a 15-second timeout and retries once on timeout.
    """
    import requests
    import time
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/plain"
    }
    jina_key = os.getenv("JINA_API_KEY", "").strip()
    if jina_key:
        headers["Authorization"] = f"Bearer {jina_key}"
        
    for attempt in range(retries + 1):
        try:
            resp = requests.get(jina_url, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.text
            else:
                print(f"      ⚠️ Jina Reader returned status {resp.status_code} for {url}")
        except requests.exceptions.Timeout:
            print(f"      ⚠️ Jina Reader timeout on {url} (Attempt {attempt+1}/{retries+1})")
            if attempt < retries:
                time.sleep(2)  # Wait before retrying
        except Exception as e:
            print(f"      ⚠️ Jina Reader failed to scrape {url}: {e}")
            break
            
    return ""

def scrape_via_apify(urls: list, token: str) -> dict:
    """
    Uses Apify's RAG Web Browser actor to scrape the URLs.
    Extremely reliable for scraping LinkedIn and Indeed because it uses rotating residential proxies.
    """
    import requests
    import time
    
    results = {}
    if not urls:
        return results
        
    print(f"   🤖 Apify: Starting scraping for {len(urls)} URLs...")
    try:
        # Run apify/rag-web-browser
        run_url = f"https://api.apify.com/v2/acts/apify~rag-web-browser/runs?token={token}"
        payload = {
            "startUrls": [{"url": url} for url in urls],
            "maxPagesPerCrawl": len(urls),
            "dynamicContentWaitSecs": 2,
        }
        
        resp = requests.post(run_url, json=payload, timeout=20)
        if resp.status_code != 201:
            print(f"   ⚠️ Apify actor start failed: {resp.status_code} {resp.text}")
            return results
            
        run_data = resp.json().get("data", {})
        run_id = run_data.get("id")
        dataset_id = run_data.get("defaultDatasetId")
        
        print(f"   🤖 Apify: Run ID {run_id} started. Waiting for completion...")
        
        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={token}"
        start_time = time.time()
        completed = False
        
        # Poll for completion (up to 60 seconds)
        while time.time() - start_time < 60:
            time.sleep(4)
            status_resp = requests.get(status_url, timeout=10)
            if status_resp.status_code == 200:
                status = status_resp.json().get("data", {}).get("status")
                if status in ["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"]:
                    if status == "SUCCEEDED":
                        completed = True
                    break
        
        if completed:
            items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={token}"
            items_resp = requests.get(items_url, timeout=15)
            if items_resp.status_code == 200:
                for item in items_resp.json():
                    url = item.get("url")
                    text = item.get("text", "") or item.get("markdown", "")
                    if url and text:
                        results[url] = text
                print(f"   ✅ Apify: Successfully scraped {len(results)} pages!")
            else:
                print(f"   ⚠️ Apify: Failed to fetch dataset ({items_resp.status_code})")
        else:
            print("   ⚠️ Apify: Scraping timed out or failed.")
            
    except Exception as e:
        print(f"   ❌ Apify API call failed: {e}")
        
    return results

def scrape_multiple_urls(urls: list) -> dict:
    """
    Scrapes multiple URLs concurrently.
    Uses Apify if APIFY_API_TOKEN is configured in environment, otherwise falls back to Jina Reader.
    """
    from concurrent.futures import ThreadPoolExecutor
    
    apify_token = os.getenv("APIFY_API_TOKEN", "").strip()
    if apify_token:
        print("   🔑 APIFY_API_TOKEN secret detected. Running premium scraper...")
        return scrape_via_apify(urls, apify_token)
        
    print("   ℹ️ No APIFY_API_TOKEN detected. Using free Jina Reader...")
    results = {}
    if not urls:
        return results
        
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_url = {executor.submit(scrape_url_via_jina, url): url for url in urls}
        for future in future_to_url:
            url = future_to_url[future]
            try:
                data = future.result()
                if data and data.strip():
                    results[url] = data
            except Exception as e:
                print(f"      ⚠️ Thread failure for {url}: {e}")
    return results

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
            # Use past-month filter for site-specific queries, past-week for open web
            is_site_query = query.startswith('site:')
            time_filter = "qdr:m" if is_site_query else "qdr:w"
            
            results = serper_search(query, num_results=10, time_filter=time_filter)
            new_count = 0
            stale_count = 0
            for r in results:
                url = r.get('href', '')
                if url and url not in seen_urls:
                    # Filter out stale/expired jobs
                    if _is_stale_job(r):
                        stale_count += 1
                        continue
                    seen_urls.add(url)
                    all_results.append(r)
                    new_count += 1
            stale_msg = f", {stale_count} stale filtered" if stale_count else ""
            print(f"   ✅ '{query}': {len(results)} results ({new_count} new{stale_msg})")
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

    # Perform deep scraping of the top candidate URLs using Jina Reader
    candidates_to_scrape = scraped_data[:8]
    urls_to_scrape = [c.get('href') for c in candidates_to_scrape if c.get('href')]
    
    print(f"🕵️  ScoutAgent: Deep scraping {len(urls_to_scrape)} top job URLs using Jina Reader...")
    scraped_contents = scrape_multiple_urls(urls_to_scrape)
    
    final_job_data = []
    for data in candidates_to_scrape:
        url = data.get('href')
        full_text = scraped_contents.get(url, "").strip()
        
        # If we got the full text, perform deep validation for expiry and load issues
        if full_text:
            if _is_stale_job_content(full_text):
                print(f"   ❌ Rejected (Expired/Closed in Full Text): {data.get('title', '')[:50]} -> {url[:50]}")
                continue
            
            final_job_data.append({
                "title": data.get('title'),
                "href": url,
                "text_source": "jina_reader",
                "content": full_text[:6000] # Cap text to avoid context overload
            })
            print(f"   ℹ️ Scraped full text: {data.get('title', '')[:50]} -> {url[:50]}")
        else:
            # Fallback to Serper snippet if scraping failed
            final_job_data.append({
                "title": data.get('title'),
                "href": url,
                "text_source": "serper_snippet",
                "content": data.get('body')
            })
            print(f"   ℹ️ Fallback to snippet: {data.get('title', '')[:50]} -> {url[:50]}")
            
    print(f"   📊 Sending {len(final_job_data)} candidate jobs to LLM for matching")

    scraped_text = json.dumps(final_job_data, indent=2)

    print("🕵️  ScoutAgent: Matching search results against Resume + Preferences...")
    prompt = f"""
    You are a STRICT AI Job Matcher. Find ONLY jobs that genuinely match this candidate's profile.
    
    USER PROFILE: 
    {resume_summary}
    
    USER PREFERENCES:
    - Preferred Job Role: {preferred_job}
    - Preferred Locations: {locations}
    
    LIVE SEARCH JOB RESULTS:
    {scraped_text[:15000]}
    
    Previously Sent Jobs (DO NOT suggest these URLs again):
    {state.get('previously_sent_jobs', [])}
    
    Task: Find the top 1 to 5 jobs that STRICTLY MATCH this user's profile.
    
    ═══ MANDATORY REJECTION RULES (apply these FIRST) ═══
    
    IMMEDIATELY REJECT any job that:
    1. ❌ STALE/EXPIRED: Contains phrases like "no longer accepting", "X year(s) ago", "position filled", "closed", "expired", "0 applicants" with old dates. Only include jobs that appear RECENTLY POSTED (within the last 30 days).
    2. ❌ EXPERIENCE MISMATCH: If the user is a fresher/junior (0-1 years), REJECT jobs requiring 3+ years of experience. If the user has 2-4 years, REJECT jobs requiring 7+ years. Experience level MUST be compatible.
    3. ❌ SENIOR ROLE MISMATCH: REJECT "Senior", "Staff", "Principal", "Lead", "Architect", "Manager" level roles for fresher/junior candidates.
    
    ═══ EVALUATION CRITERIA (score remaining jobs out of 5) ═══
    
    1. JOB ROLE MATCH: Title must be related to "{preferred_job}" or a closely adjacent field.
    2. LOCATION MATCH: Must be in {locations}, or remote. If unclear, assume match.
    3. EXPERIENCE MATCH: User's experience level must fit. For freshers: 0-1 year roles only. For juniors: 0-2 year roles.
    4. SKILL MATCH: User should possess at least 60% of core skills mentioned.
    5. FRESHNESS: Job must appear to be recently posted (not months/years old).
    
    SCORING:
    - 5/5 criteria = STRONG MATCH (always include)
    - 4/5 criteria = GOOD MATCH (include)
    - 3/5 criteria = WEAK MATCH (only include if fewer than 2 strong matches)
    - 0-2/5 criteria = REJECT
    
    QUALITY OVER QUANTITY: It is BETTER to return 2 excellent matches than 5 mediocre ones.
    
    If ZERO jobs pass 3+ criteria, reply with EXACTLY: "NO STRICT MATCHES FOUND TODAY."
    
    CRITICAL URL RULE: Copy the EXACT 'href' URL from the JSON data. DO NOT modify or fabricate URLs!
    
    Format matches EXACTLY like this:
    1. [Job Title] at [Company] — [Location]
       Match Score: [e.g., 85%]
       Experience Required: [e.g., 0-2 years / Fresher / Not specified]
       Why it's a match: [Specific skills from their resume that align + experience fit]
       Apply Here: [EXACT 'href' URL from the JSON data]
    """
    
    response = llm.invoke([HumanMessage(content=prompt)]) if llm else type('obj', (object,), {'content': '1. AI Engineer at Acme'})()
    
    # Extract URLs so we can save them in SQLite for deduction tomorrow
    urls = re.findall(r'(https?://[^\s\)]+)', response.content)
    # Clean trailing punctuation from URLs
    urls = [url.rstrip('.,;:!?)') for url in urls]
    
    print(f"   🎯 LLM matched {len(urls)} job URLs")
    
    return {"found_jobs": response.content, "extracted_urls": urls}
