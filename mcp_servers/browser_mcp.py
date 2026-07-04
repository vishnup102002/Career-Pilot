import asyncio
import os
import requests
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

if __name__ == "__main__":
    print("Starting Scout Browser MCP Server...")
    mcp.run()
