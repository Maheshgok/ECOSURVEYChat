"""
Adapter interfaces for cloud-agnostic deployment
Enables plug-and-play across GCP, Azure, and private clouds
"""

from .auth import AuthAdapter, get_auth_adapter
from .sessions import SessionAdapter, get_session_adapter
from .vectors import VectorAdapter, get_vector_adapter

__all__ = [
    'AuthAdapter',
    'SessionAdapter', 
    'VectorAdapter',
    'get_auth_adapter',
    'get_session_adapter',
    'get_vector_adapter',
]
