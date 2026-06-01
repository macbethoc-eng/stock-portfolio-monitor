"""
Stock Portfolio Monitor - FastAPI Application Entry Point.

Run with: python -m src.main
Or:       uvicorn src.main:app --reload --port 8765
"""
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path

from .router import router


app = FastAPI(
    title="Stock Portfolio Monitor",
    description="Track your stock portfolio with live PnL",
    version="1.0.0"
)

# Mount static files
STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include API routes
app.include_router(router)


@app.get("/")
def root():
    """Redirect to the dashboard."""
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}


def main():
    """Run the application."""
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8765,
        reload=True
    )


if __name__ == "__main__":
    main()