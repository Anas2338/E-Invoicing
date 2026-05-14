"""
AI-Agent Automation Service - FastAPI entry point.

Usage:
    uv run python main.py

Starts the FastAPI server on port 8002 (configurable via PORT env var).
"""
import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
    )
