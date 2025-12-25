"""
Scry Remote - FastAPI Main Application

Entry point for the Scry Remote server.
Handles HTTP routes, WebSocket signaling, and coordinates all modules.
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from loguru import logger

from .config import (
    DOMAIN,
    SECRET_KEY,
    STATIC_DIR,
    DEBUG_MODE,
    LOG_LEVEL,
    MAX_SESSIONS,
)
from .auth.google_sso import router as auth_router, get_current_user
from .auth.session import SessionManager
from .webrtc.signaling import router as webrtc_router
from .control.commands import router as control_router

# Configure logging
logger.remove()
logger.add(
    "logs/scry_remote_{time}.log",
    rotation="10 MB",
    retention="7 days",
    level=LOG_LEVEL,
)
if DEBUG_MODE:
    logger.add(lambda msg: print(msg, end=""), level="DEBUG")

# Session manager for tracking active connections
session_manager = SessionManager(max_sessions=MAX_SESSIONS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    logger.info("🚀 Scry Remote starting up...")
    logger.info(f"📡 Domain: {DOMAIN}")
    logger.info(f"🔧 Debug mode: {DEBUG_MODE}")
    logger.info(f"👥 Max sessions: {MAX_SESSIONS}")
    
    yield
    
    logger.info("👋 Scry Remote shutting down...")
    await session_manager.cleanup_all()


# Create FastAPI app
app = FastAPI(
    title="Scry Remote",
    description="Remote screen streaming and AI-powered control system",
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="scry_session",
    max_age=3600,
    same_site="lax",
    https_only=not DEBUG_MODE,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"https://{DOMAIN}", "http://localhost:8000"] if not DEBUG_MODE else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(webrtc_router, prefix="/rtc", tags=["WebRTC"])
app.include_router(control_router, prefix="/control", tags=["Control"])

# Serve static files (client)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# =============================================================================
# ROUTES
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main page. Redirects to login if not authenticated."""
    user = request.session.get("user")
    
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Serve the main client page
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head><title>Scry Remote</title></head>
    <body>
        <h1>Welcome to Scry Remote</h1>
        <p>Authenticated as: {email}</p>
        <p>Client files not found. Please check installation.</p>
        <a href="/auth/logout">Logout</a>
    </body>
    </html>
    """.format(email=user.get("email", "Unknown")))


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers."""
    return {
        "status": "healthy",
        "active_sessions": session_manager.active_count,
        "max_sessions": MAX_SESSIONS,
    }


@app.get("/api/session/info")
async def session_info(user: dict = Depends(get_current_user)):
    """Get current session information."""
    return {
        "user": user,
        "session_id": session_manager.get_session_id(user["email"]),
        "connected": session_manager.is_connected(user["email"]),
    }


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: HTTPException):
    """Redirect to login on 401."""
    return RedirectResponse(url="/auth/login", status_code=302)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 page."""
    return HTMLResponse(
        content="<h1>404 - Not Found</h1><a href='/'>Go Home</a>",
        status_code=404,
    )


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run the server directly."""
    import uvicorn
    
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG_MODE,
        log_level=LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
