import asyncio
import os
import sys
from dotenv import load_dotenv

backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.append(os.path.abspath(backend_path))
# Load .env before importing settings
load_dotenv(os.path.join(backend_path, '.env'))

from app.services.gemini_service import GeminiService
from app.schemas.response import Source

async def main():
    service = GeminiService()
    
    text = "The moon is made of green cheese according to a new study by NASA in 2024. Also, eating 50 apples a day cures all diseases."
    
    print("=== EXTRACT CLAIMS ===")
    extraction = await service.extract_claims(text)
    if extraction:
        print(f"Main Claim: {extraction.main_claim}")
        print(f"Queries: {extraction.search_queries}")
        print(f"Language: {extraction.detected_lang}")
        print(f"Is Checkable: {extraction.is_checkable}")
    else:
        print("Failed to extract claims.")
        
    print("\n=== ASSESS ===")
    claim = "Eating 50 apples a day cures all diseases."
    evidence = [
        Source(
            url="https://health.example.com/apples",
            title="Apples are good, but don't eat 50",
            snippet="Eating apples is healthy, but eating 50 a day can cause severe digestive issues. There is no evidence it cures all diseases."
        ),
        Source(
            url="https://nasa-fake.example.com/moon",
            title="Moon cheese",
            snippet="The moon is not made of green cheese."
        )
    ]
    
    assessment = await service.assess(text, claim, evidence)
    print(f"Verdict: {assessment.verdict}")
    print(f"Confidence: {assessment.confidence_score}")
    print(f"Explanation: {assessment.explanation}")
    print("Source Stances:")
    for s in assessment.source_stances:
        print(f" - {s.url} ({s.stance})")

if __name__ == "__main__":
    asyncio.run(main())
