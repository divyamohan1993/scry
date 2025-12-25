"""
Scry Remote - Session Management

Handles tracking of active WebRTC sessions and user connections.
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import uuid

from loguru import logger


@dataclass
class UserSession:
    """Represents an active user session."""
    session_id: str
    email: str
    created_at: datetime
    last_activity: datetime
    webrtc_peer_id: Optional[str] = None
    is_streaming: bool = False
    frame_count: int = 0
    command_count: int = 0
    
    def touch(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() > self.last_activity + timedelta(seconds=timeout_seconds)


class SessionManager:
    """
    Manages active user sessions.
    
    Thread-safe session tracking with automatic cleanup.
    """
    
    def __init__(self, max_sessions: int = 10):
        self._sessions: Dict[str, UserSession] = {}
        self._email_to_session: Dict[str, str] = {}
        self._max_sessions = max_sessions
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
    
    @property
    def active_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)
    
    async def create_session(self, email: str) -> UserSession:
        """
        Create a new session for a user.
        
        If user already has a session, returns existing one.
        If at max capacity, raises ValueError.
        """
        async with self._lock:
            # Check if user already has a session
            if email in self._email_to_session:
                session_id = self._email_to_session[email]
                if session_id in self._sessions:
                    session = self._sessions[session_id]
                    session.touch()
                    logger.debug(f"Returning existing session for {email}")
                    return session
            
            # Check capacity
            if len(self._sessions) >= self._max_sessions:
                # Try to clean up expired sessions first
                await self._cleanup_expired_unlocked()
                
                if len(self._sessions) >= self._max_sessions:
                    raise ValueError("Maximum session limit reached")
            
            # Create new session
            session_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            session = UserSession(
                session_id=session_id,
                email=email,
                created_at=now,
                last_activity=now,
            )
            
            self._sessions[session_id] = session
            self._email_to_session[email] = session_id
            
            logger.info(f"Created session {session_id[:8]}... for {email}")
            
            return session
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get a session by ID."""
        async with self._lock:
            return self._sessions.get(session_id)
    
    def get_session_id(self, email: str) -> Optional[str]:
        """Get session ID for an email."""
        return self._email_to_session.get(email)
    
    def is_connected(self, email: str) -> bool:
        """Check if user has an active streaming connection."""
        session_id = self._email_to_session.get(email)
        if not session_id:
            return False
        session = self._sessions.get(session_id)
        return session.is_streaming if session else False
    
    async def update_session(
        self,
        session_id: str,
        webrtc_peer_id: Optional[str] = None,
        is_streaming: Optional[bool] = None,
    ):
        """Update session state."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.touch()
                if webrtc_peer_id is not None:
                    session.webrtc_peer_id = webrtc_peer_id
                if is_streaming is not None:
                    session.is_streaming = is_streaming
    
    async def increment_frame_count(self, session_id: str):
        """Increment frame count for a session."""
        session = self._sessions.get(session_id)
        if session:
            session.frame_count += 1
            session.touch()
    
    async def increment_command_count(self, session_id: str):
        """Increment command count for a session."""
        session = self._sessions.get(session_id)
        if session:
            session.command_count += 1
    
    async def end_session(self, session_id: str):
        """End and remove a session."""
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                self._email_to_session.pop(session.email, None)
                logger.info(f"Ended session {session_id[:8]}... for {session.email}")
    
    async def end_session_by_email(self, email: str):
        """End session for a user by email."""
        session_id = self._email_to_session.get(email)
        if session_id:
            await self.end_session(session_id)
    
    async def _cleanup_expired_unlocked(self, timeout_seconds: int = 3600):
        """Clean up expired sessions (must hold lock)."""
        expired = [
            sid for sid, s in self._sessions.items()
            if s.is_expired(timeout_seconds)
        ]
        
        for session_id in expired:
            session = self._sessions.pop(session_id, None)
            if session:
                self._email_to_session.pop(session.email, None)
                logger.info(f"Cleaned up expired session for {session.email}")
    
    async def cleanup_expired(self, timeout_seconds: int = 3600):
        """Clean up expired sessions."""
        async with self._lock:
            await self._cleanup_expired_unlocked(timeout_seconds)
    
    async def cleanup_all(self):
        """Clean up all sessions (for shutdown)."""
        async with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            self._email_to_session.clear()
            logger.info(f"Cleaned up {count} sessions")
    
    def get_all_sessions(self) -> Dict[str, dict]:
        """Get all sessions (for admin/monitoring)."""
        return {
            sid: {
                "email": s.email,
                "created_at": s.created_at.isoformat(),
                "last_activity": s.last_activity.isoformat(),
                "is_streaming": s.is_streaming,
                "frame_count": s.frame_count,
                "command_count": s.command_count,
            }
            for sid, s in self._sessions.items()
        }
