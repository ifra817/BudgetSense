"""
Authentication utilities shared by route modules.
"""

from flask import current_app, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

TOKEN_SALT = "budgetsense-auth-token"
TOKEN_MAX_AGE_SECONDS = 86400


def _get_token_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_access_token(user_id):
    return _get_token_serializer().dumps({"user_id": str(user_id)}, salt=TOKEN_SALT)


def decode_access_token(token):
    try:
        payload = _get_token_serializer().loads(
            token,
            salt=TOKEN_SALT,
            max_age=TOKEN_MAX_AGE_SECONDS,
        )
    except (BadSignature, SignatureExpired):
        return None

    user_id = payload.get("user_id") if isinstance(payload, dict) else None
    if not user_id:
        return None

    return str(user_id)


def get_user_id_from_request():
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:].strip()
    if not token:
        return None

    return decode_access_token(token)
