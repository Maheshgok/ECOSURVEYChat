"""
Economic Survey Practitioner Chat v1.2
FastAPI application entry point
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
import traceback

from app.core.settings import settings
from app.core.database import init_db, SessionLocal
from app.api import health, auth, chat

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle app startup and shutdown"""
    # Startup
    try:
        logger.info("Starting Economic Survey Practitioner Chat v1.2")
        # Skip table creation in production (Supabase schema already exists)
        if settings.ENVIRONMENT != "production":
            try:
                init_db()
                logger.info("Database initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize database: {e} (continuing without DB)")
                traceback.print_exc(file=sys.stderr)
        else:
            logger.info("Production mode: skipping auto-migration (using existing Supabase schema)")
        
        logger.info("App ready and running")
        yield
    except Exception as e:
        logger.error(f"Error in lifespan startup: {e}")
        traceback.print_exc(file=sys.stderr)
        raise
    finally:
        # Shutdown
        logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title="Economic Survey Practitioner Chat v1.2",
    description="Evidence-grounded chat application for Economic Survey analysis",
    version="1.2.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - welcome message"""
    return {
        "name": "Economic Survey Practitioner Chat",
        "version": "1.2.0",
        "status": "running",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
