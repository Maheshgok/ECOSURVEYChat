"""
Application settings and configuration
Loaded from environment variables via pydantic-settings
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # =========================================================================
    # APPLICATION
    # =========================================================================
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, production
    LOG_LEVEL: str = "INFO"
    
    # =========================================================================
    # DATABASE
    # =========================================================================
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "survey_chat"
    DB_USER: str = "survey_user"
    DB_PASSWORD: str = "changeme"
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # =========================================================================
    # GOOGLE OAUTH
    # =========================================================================
    GOOGLE_CLIENT_ID: Optional[str] = None  # Optional for Phase 1 (required Phase 2+)
    GOOGLE_CLIENT_SECRET: Optional[str] = None  # Optional for Phase 1
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/callback"
    
    # =========================================================================
    # SECURITY
    # =========================================================================
    SESSION_SECRET: Optional[str] = "dev_session_secret_phase1_testing"  # Optional for Phase 1
    SERVER_SALT: Optional[str] = "dev_server_salt_phase1_testing"  # Optional for Phase 1
    SKIP_AUTH_FOR_TESTING: bool = False  # Set to True to disable auth for Phase 7 testing
    
    # =========================================================================
    # FIREBASE
    # =========================================================================
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None  # Path to service account JSON
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None  # Or inline JSON for serverless
    
    # =========================================================================
    # LLM API
    # =========================================================================
    LLM_PROVIDER: str = "openai"  # "openai" or "anthropic"
    LLM_MODEL: str = "gpt-4"
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    
    # =========================================================================
    # FRONTEND
    # =========================================================================
    FRONTEND_URL: str = "http://localhost:3000"
    FRONTEND_API_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    
    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        """Convert comma-separated origins to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # =========================================================================
    # GCP (Production)
    # =========================================================================
    GCP_PROJECT_ID: Optional[str] = None
    GCP_REGION: str = "us-central1"
    GCP_SERVICE_ACCOUNT_JSON: Optional[str] = None
    
    # =========================================================================
    # CONTEXT PACK & TOKEN BUDGETS
    # =========================================================================
    CONTEXT_BUDGET_TOKENS: int = 10000      # Global limit
    CONTEXT_QUOTA_CONVERSATION: int = 500   # Last 3 user + 3 assistant turns
    CONTEXT_QUOTA_CLAIMS: int = 1500        # Claim cards / topic briefs
    CONTEXT_QUOTA_NARRATIVE: int = 4000     # PDF nodes + supplements
    CONTEXT_QUOTA_DATA: int = 4000          # Dataset tables + indicator series
    SUPPLEMENT_QUOTA_PERCENT: int = 25      # Max supplement % of narrative quota
    
    # =========================================================================
    # INGESTION
    # =========================================================================
    INGESTION_MODE: str = "skip"  # "skip" or "strict"
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"  # Ignore extra fields from .env
    }


# Create global settings instance
settings = Settings()
