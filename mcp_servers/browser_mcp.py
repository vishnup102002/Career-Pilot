import asyncio
import os
import requests
import json
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright

# Initialize the MCP Server
mcp = FastMCP("ScoutBrowser")

def scrape_via_apify(url: str, token: str) -> str:
    """
    Scrapes a single job URL using Apify's premium RAG Web Browser actor.
    """
    import time
    try:
        run_url = f"https://api.apify.com/v2/acts/apify~rag-web-browser/runs?token={token}"
        payload = {
            "startUrls": [{"url": url}],
            "maxPagesPerCrawl": 1,
            "dynamicContentWaitSecs": 2,
        }
        resp = requests.post(run_url, json=payload, timeout=20)
        if resp.status_code == 201:
            run_data = resp.json().get("data", {})
            run_id = run_data.get("id")
            dataset_id = run_data.get("defaultDatasetId")
            
            # Poll for completion (up to 45 seconds)
            status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={token}"
            start_time = time.time()
            while time.time() - start_time < 45:
                time.sleep(2)
                status_resp = requests.get(status_url, timeout=10)
                if status_resp.status_code == 200:
                    status = status_resp.json().get("data", {}).get("status")
                    if status == "SUCCEEDED":
                        items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={token}"
                        items_resp = requests.get(items_url, timeout=15)
                        if items_resp.status_code == 200:
                            items = items_resp.json()
                            if items:
                                return items[0].get("text", "") or items[0].get("markdown", "")
                        break
                    elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                        break
    except Exception as e:
        print(f"   ⚠️ MCP Apify failed: {e}")
    return ""

def scrape_multiple_via_apify(urls: list, token: str) -> dict:
    """
    Scrapes a list of job URLs in a single batch run using Apify's premium RAG Web Browser actor.
    Prevents concurrency/credit limits by using only one run for all URLs.
    """
    import time
    results = {}
    try:
        run_url = f"https://api.apify.com/v2/acts/apify~rag-web-browser/runs?token={token}"
        payload = {
            "startUrls": [{"url": url} for url in urls],
            "maxPagesPerCrawl": len(urls),
            "dynamicContentWaitSecs": 2,
        }
        resp = requests.post(run_url, json=payload, timeout=20)
        if resp.status_code == 201:
            run_data = resp.json().get("data", {})
            run_id = run_data.get("id")
            dataset_id = run_data.get("defaultDatasetId")
            
            print(f"   🤖 MCP Server (Apify Batch): Run ID {run_id} started for {len(urls)} URLs. Polling...")
            
            # Poll for completion (up to 60 seconds)
            status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={token}"
            start_time = time.time()
            completed = False
            while time.time() - start_time < 60:
                time.sleep(3)
                status_resp = requests.get(status_url, timeout=10)
                if status_resp.status_code == 200:
                    status = status_resp.json().get("data", {}).get("status")
                    if status == "SUCCEEDED":
                        completed = True
                        break
                    elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
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
                    print(f"   ✅ MCP Server (Apify Batch): Scraped {len(results)} pages successfully.")
    except Exception as e:
        print(f"   ⚠️ MCP Apify Batch failed: {e}")
    return results

def scrape_via_jina(url: str, retries=1) -> str:
    """
    Scrapes a job page using Jina Reader API.
    """
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
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
            else:
                print(f"   ⚠️ MCP Jina failed: {e}")
    return ""

@mcp.tool()
async def scrape_job_description(url: str) -> str:
    """
    Scrapes the visible text of a job posting URL.
    Encapsulates premium Apify (if token available), free Jina Reader (with retries), 
    and local Playwright fallback.
    """
    # 1. Try Premium Apify Scraper
    apify_token = os.getenv("APIFY_API_TOKEN", "").strip()
    if apify_token:
        print(f"   🤖 MCP Server: Scraping via Apify Premium -> {url}")
        content = scrape_via_apify(url, apify_token)
        if content and content.strip():
            return content
            
    # 2. Try Standard Jina Reader
    print(f"   🤖 MCP Server: Scraping via Jina Reader -> {url}")
    content = scrape_via_jina(url)
    if content and content.strip():
        return content
        
    # 3. Fallback to Local Playwright
    print(f"   🤖 MCP Server: Falling back to local Playwright browser -> {url}")
    async with async_playwright() as p:
        # Launch Chromium headless browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            content = await page.evaluate("document.body.innerText")
            return content[:10000]
        except Exception as e:
            return f"Failed to scrape {url}. Error: {str(e)}"
        finally:
            await browser.close()

@mcp.tool()
async def scrape_multiple_job_descriptions(urls: list) -> str:
    """
    Scrapes a list of job posting URLs.
    Supports single-batch premium Apify scraping, and falls back to concurrent Jina/Playwright.
    Returns a JSON string mapping each URL to its scraped content.
    """
    results = {}
    apify_token = os.getenv("APIFY_API_TOKEN", "").strip()
    
    # 1. Try Apify Batch (highly efficient, uses 1 run)
    if apify_token:
        print(f"   🤖 MCP Server: Scraping {len(urls)} URLs via Apify Batch...")
        results = scrape_multiple_via_apify(urls, apify_token)
        if len(results) == len(urls):
            return json.dumps(results)

    # 2. Fallback to Jina Reader or Playwright for remaining URLs
    remaining_urls = [url for url in urls if url not in results]
    if not remaining_urls:
        return json.dumps(results)
        
    print(f"   🤖 MCP Server: Scraping remaining {len(remaining_urls)} URLs via fallback...")
    
    async def scrape_one_fallback(url):
        content = scrape_via_jina(url)
        if content and content.strip():
            return url, content
            
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(2)
                content = await page.evaluate("document.body.innerText")
                await browser.close()
                if content and content.strip():
                    return url, content[:10000]
        except Exception as e:
            print(f"   ⚠️ MCP Server Playwright fallback failed for {url}: {e}")
        return url, ""

    tasks = [scrape_one_fallback(url) for url in remaining_urls]
    completed = await asyncio.gather(*tasks)
    
    for url, text in completed:
        if text:
            results[url] = text
            
    return json.dumps(results)

if __name__ == "__main__":
    print("Starting Scout Browser MCP Server...")
    mcp.run()
