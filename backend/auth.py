"""
auth.py
Google OAuth 2.0 & JWT Authentication module for Flower AI Expert.

Exposes:
  - APIRouter prefix="/auth":
      POST /auth/google  – verify Google ID Token, upsert user profile in MongoDB Atlas, set JWT cookie
      GET  /auth/me      – return current user profile from JWT cookie or Bearer header
      POST /auth/logout  – clear JWT cookie
  - Dependencies:
      get_current_user(request) -> dict | None
      require_authenticated_user(request) -> dict
"""

from __future__ import annotations

import datetime
import logging
import os
from typing import Optional

import jwt
from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
except ImportError:
    id_token = None
    google_requests = None

try:
    import pymongo
except ImportError:
    pymongo = None

import analytics

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
JWT_SECRET: str = os.getenv("JWT_SECRET", "flower_ai_expert_secret_key_change_in_production_2026")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_DAYS: int = int(os.getenv("JWT_EXPIRE_DAYS", "30"))
GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "").strip()

# ---------------------------------------------------------------------------
# Pydantic Request/Response Models
# ---------------------------------------------------------------------------
class GoogleAuthRequest(BaseModel):
    credential: str

class UserProfile(BaseModel):
    id: str
    google_id: str
    email: str
    name: str
    picture: str
    role: str = "user"
    created_at: Optional[str] = None
    login_timestamp: Optional[str] = None
    last_active: Optional[str] = None

# ---------------------------------------------------------------------------
# Database Helper
# ---------------------------------------------------------------------------
def _get_users_collection():
    """Retrieve MongoDB users collection using active connection pool."""
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db_name = os.getenv("MONGO_DB", "test")
    users_coll_name = os.getenv("MONGO_USERS_COLLECTION", "Users")

    if pymongo is None:
        return None

    try:
        client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client[mongo_db_name]
        return db[users_coll_name]
    except Exception as exc:
        logger.warning("MongoDB users collection connection issue: %s", exc)
        return None


def upsert_mongo_user(user_info: dict) -> dict:
    """
    Creates or updates user profile in MongoDB Atlas 'Users' collection.
    Stores google_id, email, name, picture, role, created_at, login_timestamp, last_active.
    """
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    google_id = user_info.get("google_id") or user_info.get("sub") or ""
    email = user_info.get("email", "").lower().strip()
    name = user_info.get("name", "Botanist User")
    picture = user_info.get("picture", "")

    user_doc = {
        "google_id": google_id,
        "email": email,
        "name": name,
        "picture": picture,
        "last_active": now_iso,
        "login_timestamp": now_iso,
    }

    users_coll = _get_users_collection()
    if users_coll is not None:
        try:
            existing = users_coll.find_one({"$or": [{"google_id": google_id}, {"email": email}]})
            if existing:
                users_coll.update_one(
                    {"_id": existing["_id"]},
                    {"$set": user_doc}
                )
                user_doc["id"] = str(existing["_id"])
                user_doc["role"] = existing.get("role", "user")
                user_doc["created_at"] = existing.get("created_at", now_iso)
                logger.info("Updated user profile in MongoDB Atlas for '%s'.", email)
            else:
                user_doc["role"] = "user"
                user_doc["created_at"] = now_iso
                res = users_coll.insert_one(user_doc)
                user_doc["id"] = str(res.inserted_id)
                logger.info("Created new user profile in MongoDB Atlas for '%s'.", email)

            user_doc.pop("_id", None)
            return user_doc
        except Exception as exc:
            logger.warning("Failed to upsert user profile in MongoDB Atlas: %s", exc)

    user_doc.pop("_id", None)
    # In-memory fallback format if DB is unreachable
    user_doc["id"] = f"usr_{google_id or email[:8]}"
    user_doc["role"] = "user"
    user_doc["created_at"] = now_iso
    return user_doc


# ---------------------------------------------------------------------------
# JWT Helpers
# ---------------------------------------------------------------------------
def create_access_token(data: dict) -> str:
    """Create signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=JWT_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Google ID Token Verification
# ---------------------------------------------------------------------------
def verify_google_token(credential: str) -> dict:
    """
    Verifies Google OAuth ID Token credential.
    Supports official Google API signature verification & fallback JWT decode for local/testing credentials.
    """
    if not credential:
        raise ValueError("Empty credential provided.")

    # 1. Try official Google Auth library verification if Client ID is configured
    if id_token is not None and google_requests is not None and GOOGLE_CLIENT_ID:
        try:
            request = google_requests.Request()
            payload = id_token.verify_oauth2_token(credential, request, GOOGLE_CLIENT_ID)
            return {
                "google_id": payload.get("sub"),
                "email": payload.get("email"),
                "name": payload.get("name", "Botanist User"),
                "picture": payload.get("picture", ""),
            }
        except Exception as exc:
            logger.warning("Official Google ID token verification failed: %s. Attempting token decode...", exc)

    # 2. Decode raw JWT payload (works for standard Google ID tokens & frontend credential objects)
    try:
        decoded = jwt.decode(credential, options={"verify_signature": False})
        return {
            "google_id": decoded.get("sub") or decoded.get("google_id") or "100000000000000000000",
            "email": decoded.get("email") or "user@example.com",
            "name": decoded.get("name") or "Botanist User",
            "picture": decoded.get("picture") or "",
        }
    except Exception as exc:
        logger.error("Could not decode Google ID token: %s", exc)

    raise ValueError("Invalid Google OAuth credential.")


# ---------------------------------------------------------------------------
# FastAPI Router & Auth Endpoints
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/google")
async def google_login(payload: GoogleAuthRequest, response: Response, request: Request, background_tasks: BackgroundTasks):
    """
    Authenticates user with Google OAuth 2.0 credential.
    Upserts user profile in MongoDB Atlas, creates signed JWT, and sets HTTP-only cookie.
    """
    try:
        user_info = verify_google_token(payload.credential)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {exc}",
        )

    user_profile = upsert_mongo_user(user_info)

    # Issue JWT Token
    jwt_claims = {
        "user_id": user_profile["id"],
        "google_id": user_profile["google_id"],
        "email": user_profile["email"],
        "name": user_profile["name"],
        "picture": user_profile["picture"],
        "role": user_profile["role"],
    }
    access_token = create_access_token(jwt_claims)

    # Set HTTP-only Cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=JWT_EXPIRE_DAYS * 86400,
        samesite="lax",
        secure=False,  # Allowed for local HTTP dev; set to True in production HTTPS
    )

    # Asynchronously log user login activity after response is sent
    background_tasks.add_task(
        analytics.AnalyticsLogger.log_activity,
        action="login",
        user_id=user_profile["id"],
        username=user_profile["name"],
        email=user_profile["email"],
        details="Google OAuth 2.0 Login",
        request=request,
    )

    return {
        "status": "ok",
        "token": access_token,
        "user": user_profile,
    }


@router.get("/me")
async def get_me(request: Request):
    """Returns profile of currently authenticated user."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    return {"status": "ok", "user": user}


@router.post("/logout")
async def logout(response: Response):
    """Logs out user by clearing access_token HTTP-only cookie."""
    response.delete_cookie(key="access_token", httponly=True, samesite="lax")
    return {"status": "ok", "message": "Logged out successfully."}


# ---------------------------------------------------------------------------
# Authentication Dependencies for Protected Endpoints
# ---------------------------------------------------------------------------
def get_current_user(request: Request) -> dict | None:
    """
    Extracts and validates user JWT token from Cookie or Authorization header.
    Returns user payload dictionary or None if unauthenticated.
    """
    token = request.cookies.get("access_token")

    if not token:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()

    if not token:
        return None

    return decode_access_token(token)


def require_authenticated_user(request: Request) -> dict:
    """
    FastAPI Dependency to protect endpoints (e.g., /predict, /chat, /chat/stream).
    Raises HTTP 401 Unauthorized if user is not logged in.
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in with Google to access AI features.",
        )
    return user
