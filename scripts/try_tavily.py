import asyncio
import sys
import os

# Change working directory to backend so pydantic-settings can find .env
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.chdir(backend_dir)
sys.path.append(backend_dir)

from app.services.tavily_service import TavilySearchService
from app.schemas.internal import AnalysisContext

async def main():
    query = "Latest news on artificial intelligence"
    if len(sys.argv) > 1:
        query = sys.argv[1]
        
    print(f"Checking tavily for: '{query}'")
    
    # The TavilySearchService will automatically read from app.core.config.settings
    service = TavilySearchService()
    ctx = AnalysisContext(text=query, search_queries=[query], lang="en")
    
    result = await service.check(ctx)
    await service.aclose()
    
    print(f"Status: {result.status}")
    if result.error:
        print(f"Error: {result.error}")
        
    if result.status == "ok":
        print(f"Found {len(result.sources)} sources:")
        for i, source in enumerate(result.sources, 1):
            print(f"{i}. Publisher: {source.publisher}")
            print(f"   Title: {source.title}")
            print(f"   Snippet: {source.snippet}")
            print(f"   URL: {source.url}\n")
    elif result.status == "empty":
        print("No results found.")

if __name__ == "__main__":
    asyncio.run(main())
