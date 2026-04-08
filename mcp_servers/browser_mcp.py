import asyncio
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright

# Initialize the MCP Server. 
# FastMCP handles all the complex JSON-RPC standardisation underneath!
mcp = FastMCP("ScoutBrowser")

@mcp.tool()
async def scrape_job_description(url: str) -> str:
    """
    Scrapes the visible text of a job posting URL.
    The LangGraph agent will use this tool to see the page text,
    then use its intelligence to extract 'Must-Have' and 'Nice-to-Have' skills.
    """
    async with async_playwright() as p:
        # Launch Chromium headless browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # We wait until the DOM is loaded; quicker than waiting for all images.
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            
            # Many job boards (like Wellfound) are single-page apps (SPAs).
            # We sleep lightly to let client-side React/Vue finish rendering.
            await asyncio.sleep(2)
            
            # Extract plain text from the webpage body
            content = await page.evaluate("document.body.innerText")
            
            # Return up to 10k characters so we don't overwhelm the LLM context window
            return content[:10000]
            
        except Exception as e:
            return f"Failed to scrape {url}. Error: {str(e)}"
        
        finally:
            await browser.close()

if __name__ == "__main__":
    print("Starting Scout Browser MCP Server...")
    mcp.run()
