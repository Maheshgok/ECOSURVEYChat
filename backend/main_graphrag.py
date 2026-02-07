"""
FastAPI main entry point for GraphRAG backend
Separate deployment from standard RAG
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
import os

from app.api import graphrag
from app.core.env_loader import load_environment

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting GraphRAG backend...")
    
    # Load environment
    env_config = load_environment()
    logger.info(f"Environment: {env_config['environment']}")
    logger.info(f"Pinecone Index: {os.getenv('PINECONE_INDEX_NAME', 'ecosurvey-facts')}")
    
    # Validate required environment variables
    required_vars = [
        'PINECONE_API_KEY',
        'OPENAI_API_KEY',
        'FIREBASE_PROJECT_ID'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        raise RuntimeError(f"Missing environment variables: {missing_vars}")
    
    logger.info("GraphRAG backend started successfully")
    
    yield
    
    logger.info("Shutting down GraphRAG backend...")


# Create FastAPI app
app = FastAPI(
    title="EcoSurvey GraphRAG API",
    description="Structured fact-based RAG with explainable reasoning",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://research.edgechurn.ai",
        "https://edgechurn.ai",
        "https://watch-mail-trial.web.app",
        "http://localhost:5173",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    graphrag.router,
    prefix="/api",
    tags=["GraphRAG"]
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "graphrag",
        "version": "1.0.0",
        "pinecone_index": os.getenv('PINECONE_INDEX_NAME', 'ecosurvey-facts')
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "EcoSurvey GraphRAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    
    uvicorn.run(
        "main_graphrag:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development"
    )
