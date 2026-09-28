from fastapi import FastAPI

from app.api.v1 import analyze
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title="FactCheck API", version="1.0.0")

app.include_router(analyze.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
