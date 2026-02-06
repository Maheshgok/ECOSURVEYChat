"""
Deployment Configuration
Environment-based adapter selection for cloud-agnostic deployment
"""

import os
from typing import Dict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DeploymentConfig:
    """Deployment configuration for different cloud environments"""
    name: str
    auth_provider: str
    session_storage: str
    vector_provider: str
    description: str


# Predefined deployment profiles
DEPLOYMENT_PROFILES = {
    'gcp': DeploymentConfig(
        name='gcp',
        auth_provider='firebase',
        session_storage='firestore',
        vector_provider='pinecone',
        description='Google Cloud Platform (Firebase + Firestore)'
    ),
    'azure': DeploymentConfig(
        name='azure',
        auth_provider='azure_ad',
        session_storage='cosmosdb',
        vector_provider='azure_ai_search',
        description='Microsoft Azure (Azure AD + Cosmos DB + AI Search)'
    ),
    'aws': DeploymentConfig(
        name='aws',
        auth_provider='custom_jwt',
        session_storage='postgres',
        vector_provider='pinecone',
        description='Amazon Web Services (Custom JWT + RDS Postgres + Pinecone)'
    ),
    'private': DeploymentConfig(
        name='private',
        auth_provider='custom_jwt',
        session_storage='postgres',
        vector_provider='pinecone',
        description='Private Cloud (Custom JWT + Postgres + Pinecone)'
    ),
    'hybrid_gcp_azure': DeploymentConfig(
        name='hybrid_gcp_azure',
        auth_provider='firebase',
        session_storage='cosmosdb',
        vector_provider='pinecone',
        description='Hybrid GCP/Azure (Firebase auth + Cosmos storage)'
    ),
}


def get_deployment_config() -> DeploymentConfig:
    """
    Get deployment configuration from environment
    
    Priority:
    1. DEPLOYMENT_PROFILE env var (gcp, azure, aws, private)
    2. Auto-detect based on cloud-specific env vars
    3. Default to GCP
    """
    profile_name = os.getenv('DEPLOYMENT_PROFILE', '').lower()
    
    # Use explicit profile if set
    if profile_name in DEPLOYMENT_PROFILES:
        config = DEPLOYMENT_PROFILES[profile_name]
        logger.info(f"Using deployment profile: {profile_name} - {config.description}")
        return config
    
    # Auto-detect based on environment variables
    if os.getenv('AZURE_TENANT_ID') and os.getenv('COSMOS_DB_URI'):
        logger.info("Auto-detected Azure environment")
        return DEPLOYMENT_PROFILES['azure']
    
    elif os.getenv('JWT_SECRET_KEY') and os.getenv('DATABASE_URL'):
        logger.info("Auto-detected private cloud environment (custom JWT + Postgres)")
        return DEPLOYMENT_PROFILES['private']
    
    else:
        logger.info("Using default GCP deployment profile")
        return DEPLOYMENT_PROFILES['gcp']


def get_environment_info() -> Dict:
    """Get current environment information for health checks"""
    config = get_deployment_config()
    
    return {
        'deployment_profile': config.name,
        'auth_provider': config.auth_provider,
        'session_storage': config.session_storage,
        'vector_provider': config.vector_provider,
        'description': config.description,
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'cloud_detected': _detect_cloud(),
    }


def _detect_cloud() -> str:
    """Detect which cloud we're running on"""
    # Google Cloud Run
    if os.getenv('K_SERVICE'):
        return 'gcp_cloud_run'
    
    # Azure Container Apps
    if os.getenv('CONTAINER_APP_NAME'):
        return 'azure_container_apps'
    
    # AWS (check for ECS or Lambda)
    if os.getenv('AWS_EXECUTION_ENV'):
        return 'aws'
    
    # Kubernetes
    if os.getenv('KUBERNETES_SERVICE_HOST'):
        return 'kubernetes'
    
    return 'local_or_private'
