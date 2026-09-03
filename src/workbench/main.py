"""Main entry point for Sovereign On-Prem Agentic AI Workbench FastAPI backend."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from workbench.api.routes import router
from workbench.models.ollama_client import get_ollama_client
from workbench.models.registry import get_model_registry
from workbench.tools.base import WORKSPACE_ROOT

# Load environment variables
load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("workbench.server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("Initializing Sovereign Workbench Backend...")
    registry = get_model_registry()
    logger.info(f"Loaded {len(registry.list_models())} models from registry: {[m.name for m in registry.list_models()]}")

    client = get_ollama_client()
    if await client.is_server_ready():
        logger.info(f"Ollama server connected at {client.host}")
        try:
            await client.ensure_router_resident()
            logger.info("Router classifier model resident check passed.")
        except Exception as e:
            logger.warning(f"Could not pin router on startup: {e}")
    else:
        logger.warning(f"Ollama server at {client.host} is not currently responding. Ensure 'ollama serve' is running.")

    yield
    logger.info("Shutting down Sovereign Workbench Backend...")


app = FastAPI(
    title="Sovereign On-Prem Agentic AI Workbench",
    description="Self-hosted, air-gapped agentic AI system for confidential industrial knowledge work.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for local client access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(router)

# Mount static web UI assets
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Mount uploads directory for previewing uploaded documents & drawings
uploads_dir = WORKSPACE_ROOT / "data" / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.get("/", summary="Web Application Console")
async def serve_ui():
    """Serves the main single-page engineering workbench console."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Sovereign Workbench API running. UI under /static/index.html"}


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("WORKBENCH_HOST", "127.0.0.1")
    port = int(os.getenv("WORKBENCH_PORT", "8000"))
    uvicorn.run("workbench.main:app", host=host, port=port, reload=True)
