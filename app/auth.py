"""
Simple guest-token authentication using JWT (HS256).

No user database is required – the token itself carries the identity.
The secret key is read from the environment (falls back to a default for dev).
"""

import os
import time
import uuid
import logging
from typing import Any, Dict

import jwt
from fastapi import HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production-please")
_ALGORITHM = "HS256"
_TTL_SECONDS = 60 * 60 * 24  # 24 hours


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = _TTL_SECONDS
    sub: str


def create_guest_token() -> Dict[str, Any]:
    """Mint a new guest JWT token."""
    subject = f"guest:{uuid.uuid4()}"
    now = int(time.time())
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + _TTL_SECONDS,
        "role": "guest",
    }
    token = jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)
    logger.debug("JWT issued: sub=%s", subject)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": _TTL_SECONDS,
        "sub": subject,
    }


def verify_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.
    Raises HTTP 401 on any failure.
    """
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Request a new one via POST /auth/guest.")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")
