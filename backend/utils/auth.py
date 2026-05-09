"""
Authentication utility functions for BudgetSense.
"""

import os
from datetime import datetime, timedelta
from flask import request

# Direct import - no conflicts
import jwt  # type: ignore

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')


def generate_access_token(user_id):
    """Generate JWT access token for user."""
    payload = {
        'user_id': str(user_id),
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=30)
    }
    
    try:
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')  # type: ignore
    except Exception:
        return None


def verify_token(token):
    """Verify JWT token and extract user_id."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])  # type: ignore
        return payload.get('user_id'), None
    except jwt.ExpiredSignatureError:  # type: ignore
        return None, "Token has expired"
    except jwt.InvalidTokenError:  # type: ignore
        return None, "Invalid token"
    except Exception as e:
        return None, f"Token verification failed: {str(e)}"


def get_user_id_from_request():
    """Extract user_id from Authorization header."""
    auth_header = request.headers.get('Authorization', '')
    
    # Convert Headers object to string
    if auth_header:
        auth_header = str(auth_header)
    else:
        return None
    
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:].strip()
    
    if not token:
        return None
    
    user_id, _ = verify_token(token)
    return user_id