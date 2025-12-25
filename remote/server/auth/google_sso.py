"""
Scry Remote - Google SSO Authentication

Implements Google OAuth 2.0 for secure authentication.
"""

import secrets
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from jose import jwt, JWTError
from loguru import logger
import httpx

from ..config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    OAUTH_REDIRECT_URI,
    SECRET_KEY,
    SESSION_TIMEOUT,
    ALLOWED_EMAILS,
    DOMAIN,
)

router = APIRouter()

# Initialize OAuth client
oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
        "prompt": "select_account",
    },
)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(seconds=SESSION_TIMEOUT))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


def is_email_allowed(email: str) -> bool:
    """Check if email is in the allowed list (supports wildcards)."""
    if not ALLOWED_EMAILS:
        # No whitelist = allow all
        return True
    
    email_lower = email.lower()
    for pattern in ALLOWED_EMAILS:
        pattern_lower = pattern.lower()
        if pattern_lower.startswith("*@"):
            # Wildcard domain match
            domain = pattern_lower[2:]
            if email_lower.endswith(f"@{domain}"):
                return True
        elif email_lower == pattern_lower:
            # Exact match
            return True
    
    return False


async def get_current_user(request: Request) -> dict:
    """
    Dependency to get the current authenticated user.
    Raises 401 if not authenticated.
    """
    user = request.session.get("user")
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify the token is still valid
    token = request.session.get("access_token")
    if token and not verify_token(token):
        request.session.clear()
        raise HTTPException(status_code=401, detail="Session expired")
    
    return user


async def get_optional_user(request: Request) -> Optional[dict]:
    """
    Dependency to get the current user if authenticated, None otherwise.
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


# =============================================================================
# ROUTES
# =============================================================================

@router.get("/login")
async def login(request: Request):
    """Initiate Google OAuth login flow."""
    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    
    logger.info("Initiating Google OAuth login...")
    
    return await oauth.google.authorize_redirect(
        request,
        OAUTH_REDIRECT_URI,
        state=state,
    )


@router.get("/callback")
async def callback(request: Request):
    """Handle OAuth callback from Google."""
    # Verify state
    state = request.query_params.get("state")
    stored_state = request.session.get("oauth_state")
    
    if not state or state != stored_state:
        logger.warning("OAuth state mismatch - possible CSRF attack")
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    try:
        # Exchange code for token
        token = await oauth.google.authorize_access_token(request)
        
        # Get user info
        user_info = token.get("userinfo")
        if not user_info:
            # Fetch from userinfo endpoint if not in token
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {token['access_token']}"},
                )
                user_info = resp.json()
        
        email = user_info.get("email", "")
        name = user_info.get("name", "")
        picture = user_info.get("picture", "")
        
        logger.info(f"OAuth callback for user: {email}")
        
        # Check if email is allowed
        if not is_email_allowed(email):
            logger.warning(f"Email not in whitelist: {email}")
            raise HTTPException(
                status_code=403,
                detail="Access denied. Your email is not authorized."
            )
        
        # Create session
        user = {
            "email": email,
            "name": name,
            "picture": picture,
            "authenticated_at": datetime.utcnow().isoformat(),
        }
        
        access_token = create_access_token({"sub": email, "name": name})
        
        request.session["user"] = user
        request.session["access_token"] = access_token
        request.session.pop("oauth_state", None)
        
        logger.info(f"User authenticated: {email}")
        
        return RedirectResponse(url="/", status_code=302)
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@router.get("/logout")
async def logout(request: Request):
    """Log out the current user."""
    user = request.session.get("user")
    if user:
        logger.info(f"User logged out: {user.get('email')}")
    
    request.session.clear()
    
    return RedirectResponse(url="/auth/login", status_code=302)


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user information."""
    return user


@router.get("/check")
async def check_auth(request: Request):
    """Check if user is authenticated (for client-side checks)."""
    user = request.session.get("user")
    return {
        "authenticated": user is not None,
        "user": user,
    }
