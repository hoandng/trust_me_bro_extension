from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import analyze
from app.core.logging import setup_logging
from app.core.config import settings

setup_logging()

app = FastAPI(title="FactCheck API", version="1.0.0")

if settings.allowed_origins:
    origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(analyze.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
