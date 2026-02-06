"""
Economic Survey Practitioner Chat v2.0 (Multi-Cloud Edition)
FastAPI application entry point
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
import traceback
import os

from app.core.settings import settings
from app.api import health, auth, chat, rag_chat_v2

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle app startup and shutdown"""
    # Startup
    deployment_target = os.getenv('DEPLOYMENT_TARGET', 'gcp')
    logger.info(f"Starting Economic Survey Chat v2.0 - Deployment: {deployment_target}")
    logger.info("App ready and running (Pinecone + Firebase mode)")
    yield
    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title="Economic Survey Practitioner Chat v2.0 - Multi-Cloud",
    description="Evidence-grounded chat with Firebase/Azure AD/Custom JWT + Firestore/CosmosDB/Postgres",
    version="2.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_origin_regex=r"https://.*\.netlify\.app",  # Allow all Netlify preview/production URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (only Pinecone-based routes)
app.include_router(health.router, prefix="/api", tags=["Health"])
# app.include_router(auth.router, prefix="/api", tags=["Authentication"])  # Disabled - requires database
# app.include_router(chat.router, prefix="/api", tags=["Chat"])  # Disabled - requires database
# Firebase forwards full path: /chatbot/ecosurveybudget2026/api/rag-chat-v2
# So we need /api prefix here to match /api/rag-chat-v2
app.include_router(rag_chat_v2.router, prefix="/chatbot/ecosurveybudget2026/api", tags=["RAG Chat v2 - Advanced"])


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
