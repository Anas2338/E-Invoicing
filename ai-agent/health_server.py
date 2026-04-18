"""
Simple HTTP health server for Hugging Face Spaces status verification.
Runs alongside the AI agent to provide health endpoint on port 7860.
"""
import logging
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import threading

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent Health Server")


@app.get("/")
@app.get("/health")
def health_check():
    """
    Health check endpoint for Hugging Face Spaces.
    Verifies agent heartbeat file is recent.
    """
    heartbeat_file = Path("/tmp/agent_heartbeat.txt")

    if not heartbeat_file.exists():
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": "Agent heartbeat file not found"
            }
        )

    # Check if heartbeat is recent (within last 10 minutes)
    heartbeat_time = datetime.fromtimestamp(heartbeat_file.stat().st_mtime)
    age = datetime.now() - heartbeat_time

    if age > timedelta(minutes=10):
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": f"Agent heartbeat is stale ({age.total_seconds():.0f}s old)"
            }
        )

    return {
        "status": "healthy",
        "message": "AI Agent is running",
        "last_heartbeat": heartbeat_time.isoformat(),
        "heartbeat_age_seconds": age.total_seconds()
    }


def run_health_server():
    """Run health server in background thread."""
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")


def start_health_server_thread():
    """Start health server in a daemon thread."""
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()
    logger.info("Health server started on port 7860")
