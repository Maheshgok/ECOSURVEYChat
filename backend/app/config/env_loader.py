"""
Deployment Configuration Loader
Selects adapters based on deployment target (GCP, Azure, Private Cloud)
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DeploymentConfig:
    """Manages deployment-specific configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Load deployment configuration
        
        Priority (highest to lowest):
        1. Environment variables (DEPLOYMENT_TARGET, AUTH_PROVIDER, etc.)
        2. deployment.yaml file
        3. Default values (GCP/Firebase)
        """
        self.config_path = config_path or os.getenv('DEPLOYMENT_CONFIG_PATH')
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment"""
        
        # Start with defaults (GCP/Firebase - zero config)
        config = {
            'deployment': {
                'target': 'gcp',
                'environment': 'production',
            },
            'auth': {
                'provider': 'firebase',
                'project_id': os.getenv('FIREBASE_PROJECT_ID'),
            },
            'sessions': {
                'provider': 'firestore',
                'ttl_seconds': 3600,
            },
            'vectors': {
                'provider': 'pinecone',
                'index_name': os.getenv('PINECONE_INDEX_NAME', 'economic-survey-2026'),
            },
            'observability': {
                'metrics_enabled': True,
                'logging_level': 'INFO',
                'feature_flags_enabled': False,
            }
        }
        
        # Try to load from YAML file
        if self.config_path and Path(self.config_path).exists():
            try:
                with open(self.config_path, 'r') as f:
                    yaml_config = yaml.safe_load(f)
                    config = self._merge_configs(config, yaml_config)
                logger.info(f"Loaded config from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")
        
        # Override with environment variables
        config = self._apply_env_overrides(config)
        
        return config
    
    def _merge_configs(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dicts"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def _apply_env_overrides(self, config: Dict) -> Dict:
        """Apply environment variable overrides"""
        
        # Deployment target
        if os.getenv('DEPLOYMENT_TARGET'):
            config['deployment']['target'] = os.getenv('DEPLOYMENT_TARGET')
        
        # Auth provider
        if os.getenv('AUTH_PROVIDER'):
            config['auth']['provider'] = os.getenv('AUTH_PROVIDER')
        
        # Azure AD specific
        if os.getenv('AZURE_TENANT_ID'):
            config['auth']['tenant_id'] = os.getenv('AZURE_TENANT_ID')
        if os.getenv('AZURE_CLIENT_ID'):
            config['auth']['client_id'] = os.getenv('AZURE_CLIENT_ID')
        
        # Session storage
        if os.getenv('SESSION_PROVIDER'):
            config['sessions']['provider'] = os.getenv('SESSION_PROVIDER')
        
        # Redis (if configured)
        if os.getenv('REDIS_HOST'):
            config['sessions']['redis_host'] = os.getenv('REDIS_HOST')
            config['sessions']['redis_port'] = os.getenv('REDIS_PORT', '6379')
            config['sessions']['redis_password'] = os.getenv('REDIS_PASSWORD')
        
        # Vector DB
        if os.getenv('VECTOR_PROVIDER'):
            config['vectors']['provider'] = os.getenv('VECTOR_PROVIDER')
        
        return config
    
    def get(self, *keys, default=None):
        """Get nested config value"""
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def get_deployment_target(self) -> str:
        """Get deployment target (gcp, azure, private)"""
        return self.get('deployment', 'target', default='gcp')
    
    def get_auth_provider(self) -> str:
        """Get auth provider (firebase, azure_ad, custom_jwt)"""
        return self.get('auth', 'provider', default='firebase')
    
    def get_session_provider(self) -> str:
        """Get session provider (firestore, cosmosdb, redis, postgres)"""
        return self.get('sessions', 'provider', default='firestore')
    
    def get_vector_provider(self) -> str:
        """Get vector provider (pinecone, azure_ai_search)"""
        return self.get('vectors', 'provider', default='pinecone')
    
    def is_metrics_enabled(self) -> bool:
        """Check if metrics collection is enabled"""
        return self.get('observability', 'metrics_enabled', default=True)
    
    def is_feature_flags_enabled(self) -> bool:
        """Check if feature flags are enabled"""
        return self.get('observability', 'feature_flags_enabled', default=False)


# Global instance
deployment_config = DeploymentConfig()


def get_config() -> DeploymentConfig:
    """Get global deployment config instance"""
    return deployment_config
