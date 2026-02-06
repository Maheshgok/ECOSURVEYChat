"""
Economic Survey Practitioner Chat v2.0 (Multi-Cloud Edition)
FastAPI application entry point with adapter pattern
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
import traceback
import os

from app.core.settings import settings
from app.core.env_loader import get_deployment_config
from app.adapters import (
    get_auth_adapter,
    get_session_adapter,
    get_vector_adapter,
)
from app.api import health, auth, chat, rag_chat_v2
from app.observability import get_metrics, get_feature_flags

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


# Global adapters (initialized at startup)
auth_adapter = None
session_adapter = None
vector_adapter = None


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle app startup and shutdown"""
    global auth_adapter, session_adapter, vector_adapter
    
    # Startup
    deployment_target = os.getenv('DEPLOYMENT_TARGET', 'gcp')
    logger.info(f"Starting Economic Survey Chat v2.0 - Deployment: {deployment_target}")
    
    # Load deployment config
    config = get_deployment_config()
    logger.info(f"Auth: {config.auth.provider}, Sessions: {config.sessions.provider}, Vectors: {config.vectors.provider}")
    
    # Initialize adapters
    try:
        auth_adapter = get_auth_adapter()
        session_adapter = get_session_adapter()
        vector_adapter = get_vector_adapter()
        
        # Store in app state for dependency injection
        app.state.auth_adapter = auth_adapter
        app.state.session_adapter = session_adapter
        app.state.vector_adapter = vector_adapter
        app.state.metrics = get_metrics()
        app.state.feature_flags = get_feature_flags()
        
        logger.info("✓ Adapters initialized successfully")
        logger.info("✓ Observability layer active")
        logger.info("✓ App ready and running")
    except Exception as e:
        logger.error(f"STARTUP ERROR: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    logger.info(f"Session metrics: {get_metrics().get_stats()}")


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
