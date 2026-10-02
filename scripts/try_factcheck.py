import asyncio
import sys
import os

# Change working directory to backend so pydantic-settings can find .env
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.chdir(backend_dir)
sys.path.append(backend_dir)

from app.services.factcheck_service import FactCheckService
from app.schemas.internal import AnalysisContext

async def main():
    claim_text = "Donald Trump won the 2020 election"
    if len(sys.argv) > 1:
        claim_text = sys.argv[1]
        
    print(f"Checking claim: '{claim_text}'")
    
    # The FactCheckService will automatically read from app.core.config.settings
    service = FactCheckService()
    ctx = AnalysisContext(text=claim_text, claim=claim_text, lang="en")
    
    result = await service.check(ctx)
    await service.aclose()
    
    print(f"Status: {result.status}")
    if result.error:
        print(f"Error: {result.error}")
        
    if result.status == "ok":
        print(f"Found {len(result.sources)} sources:")
        for i, source in enumerate(result.sources, 1):
            print(f"{i}. Publisher: {source.publisher}")
            print(f"   Rating: {source.snippet} -> Stance: {source.stance}")
            print(f"   Title: {source.title}")
            print(f"   URL: {source.url}\n")
    elif result.status == "empty":
        print("No fact checks found.")

if __name__ == "__main__":
    asyncio.run(main())
