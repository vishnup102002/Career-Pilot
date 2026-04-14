import json
import re
import os
import http.client
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

def scout_node(state: AgentState):
    preferred_job = state.get('preferred_job', '').strip()
    locations = state.get('locations', '').strip()
    resume_summary = state.get('resume_summary', '')
    
    print(f"🕵️  ScoutAgent: Searching for '{preferred_job}' in [{locations}]...")
    
    # Build smart search queries using the user's preferred job + locations
    location_list = [loc.strip() for loc in locations.split(',') if loc.strip()]
    
    # Generate search variations combining job role with each location
    search_queries = []
    
    for location in location_list:
        search_queries.append(f"{preferred_job} jobs {location} apply")
    
    # Add remote/general query
    search_queries.append(f"{preferred_job} jobs remote apply 2025 2026")
    
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
    
    scraped_data = all_results
    print(f"   📊 Total unique results aggregated: {len(scraped_data)}")

    if len(scraped_data) == 0:
        print("⚠️ ScoutAgent: No results from Serper. Skipping LLM matching.")
        return {"found_jobs": "NO STRICT MATCHES FOUND TODAY. The job search returned zero results. Please try again later.", "extracted_urls": []}

    scraped_text = json.dumps(scraped_data, indent=2)

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
    3. EXPERIENCE MATCH: If the job requires minimum years of experience (e.g., "2+ years") and the User is a fresher or intern, you MUST instantly reject it.
    4. EDUCATION MATCH: If the job requires a specific Degree and the User's profile does not state they have it, reject it.
    5. SKILL MATCH: The User must possess the core mandatory capabilities from the job description.
    
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
