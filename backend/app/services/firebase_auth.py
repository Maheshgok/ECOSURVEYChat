"""
Firebase Authentication Service - NO SERVICE ACCOUNT NEEDED
Verifies Firebase ID tokens using Google's public keys
"""

from typing import Optional
import jwt
import requests
from datetime import datetime
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend
from app.core.settings import settings


class FirebaseAuthService:
    """Firebase authentication service using public key verification"""
    
    GOOGLE_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
    _certs_cache = None
    _certs_expiry = None
    
    @classmethod
    def _get_public_keys(cls):
        """Fetch Google's public keys for token verification"""
        now = datetime.now()
        
        # Use cached certs if still valid
        if cls._certs_cache and cls._certs_expiry and now < cls._certs_expiry:
            return cls._certs_cache
        
        # Fetch new certs (X.509 certificates)
        response = requests.get(cls.GOOGLE_CERTS_URL)
        response.raise_for_status()
        
        # Convert X.509 certificates to public keys
        certs_dict = response.json()
        public_keys = {}
        
        for kid, cert_str in certs_dict.items():
            # Load the X.509 certificate and extract public key
            cert = load_pem_x509_certificate(cert_str.encode(), default_backend())
            public_keys[kid] = cert.public_key()
        
        cls._certs_cache = public_keys
        
        # Cache for 1 hour (Google recommends checking cache-control header)
        cache_control = response.headers.get('cache-control', '')
        if 'max-age=' in cache_control:
            max_age = int(cache_control.split('max-age=')[1].split(',')[0])
            from datetime import timedelta
            cls._certs_expiry = now + timedelta(seconds=max_age)
        
        return cls._certs_cache
    
    @classmethod
    async def verify_token(cls, token: str) -> Optional[dict]:
        """
        Verify Firebase ID token using Google's public keys
        
        Args:
            token: Firebase ID token from client
            
        Returns:
            Decoded token dict with user info, or None if invalid
        """
        try:
            # Get the public keys
            public_keys = cls._get_public_keys()
            
            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get('kid')
            
            if not kid or kid not in public_keys:
                print(f"Invalid token: key ID '{kid}' not found")
                return None
            
            # Verify the token with the public key
            decoded = jwt.decode(
                token,
                public_keys[kid],
                algorithms=['RS256'],
                audience=settings.FIREBASE_PROJECT_ID,
                issuer=f'https://securetoken.google.com/{settings.FIREBASE_PROJECT_ID}'
            )
            
            # Extract user info
            return {
                'uid': decoded.get('sub'),  # 'sub' is the user ID
                'email': decoded.get('email'),
                'email_verified': decoded.get('email_verified', False),
                'name': decoded.get('name'),
                'picture': decoded.get('picture'),
                'firebase_user': decoded
            }
            
        except jwt.ExpiredSignatureError:
            print("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            print(f"Invalid token: {e}")
            return None
        except Exception as e:
            print(f"Error verifying token: {e}")
            return None


# Global instance
firebase_service = FirebaseAuthService()
