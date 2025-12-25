"""
Scry Remote - Control Commands

Defines the protocol for control commands sent to the client.
Also provides REST endpoints for manual control and testing.
"""

from typing import Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from loguru import logger

from ..auth.google_sso import get_current_user
from ..auth.session import SessionManager

router = APIRouter()


# =============================================================================
# COMMAND PROTOCOL
# =============================================================================

class CommandType(str, Enum):
    """Types of control commands."""
    MOUSE_MOVE = "mouse_move"
    MOUSE_CLICK = "mouse_click"
    MOUSE_DOUBLE_CLICK = "mouse_double_click"
    MOUSE_SCROLL = "mouse_scroll"
    KEY_PRESS = "key_press"
    KEY_SEQUENCE = "key_sequence"
    TYPE_TEXT = "type_text"
    COMPOSITE = "composite"  # Multiple commands in sequence


@dataclass
class MouseMoveCommand:
    """Move mouse to position."""
    type: str = CommandType.MOUSE_MOVE.value
    x: float = 0.0  # Normalized 0-1
    y: float = 0.0  # Normalized 0-1
    duration_ms: int = 500  # Movement duration
    human_like: bool = True  # Use human-like movement
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MouseClickCommand:
    """Click at position."""
    type: str = CommandType.MOUSE_CLICK.value
    x: float = 0.0  # Normalized 0-1
    y: float = 0.0  # Normalized 0-1
    button: str = "left"  # left, right, middle
    move_first: bool = True  # Move to position before clicking
    duration_ms: int = 500  # Movement duration
    human_like: bool = True
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TypeTextCommand:
    """Type text with human-like typing."""
    type: str = CommandType.TYPE_TEXT.value
    text: str = ""
    wpm_min: int = 40  # Minimum words per minute
    wpm_max: int = 80  # Maximum words per minute
    make_mistakes: bool = True  # Simulate typing errors
    click_first: bool = False  # Click at position before typing
    x: float = 0.0  # Click position (if click_first)
    y: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class KeyPressCommand:
    """Press a key or key combination."""
    type: str = CommandType.KEY_PRESS.value
    key: str = ""  # Key name (e.g., "enter", "tab", "ctrl+a")
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CompositeCommand:
    """Multiple commands to execute in sequence."""
    type: str = CommandType.COMPOSITE.value
    commands: List[dict] = None
    delay_between_ms: int = 100
    
    def __post_init__(self):
        if self.commands is None:
            self.commands = []
    
    def add_command(self, cmd):
        if hasattr(cmd, 'to_dict'):
            self.commands.append(cmd.to_dict())
        else:
            self.commands.append(cmd)
    
    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# COMMAND BUILDER
# =============================================================================

class CommandBuilder:
    """
    Builds control commands from Scry analysis results.
    
    Translates AI analysis into executable commands.
    """
    
    @staticmethod
    def from_analysis(result: dict) -> Optional[dict]:
        """
        Build command from Scry analysis result.
        
        Args:
            result: Dict with 'type', 'action', 'x', 'y', 'text', etc.
        
        Returns:
            Command dict ready to send to client
        """
        if not result or not result.get("action"):
            return None
        
        action = result["action"]
        
        if action == "click":
            # MCQ - click on answer
            cmd = MouseClickCommand(
                x=result.get("x", 0.5),
                y=result.get("y", 0.5),
                button="left",
                move_first=True,
                human_like=True,
            )
            return {
                "action": "click",
                "command": cmd.to_dict(),
                "answer_text": result.get("answer_text"),
                "question": result.get("question"),
            }
        
        elif action == "type":
            # DESCRIPTIVE - click on text area and type
            composite = CompositeCommand()
            
            # First click on the text area
            click_cmd = MouseClickCommand(
                x=result.get("x", 0.5),
                y=result.get("y", 0.5),
                button="left",
                human_like=True,
            )
            composite.add_command(click_cmd)
            
            # Then type the answer
            type_cmd = TypeTextCommand(
                text=result.get("text", ""),
                wpm_min=40,
                wpm_max=80,
                make_mistakes=True,
            )
            composite.add_command(type_cmd)
            
            return {
                "action": "type",
                "command": composite.to_dict(),
                "answer_text": result.get("text"),
                "question": result.get("question"),
                "marks": result.get("marks"),
            }
        
        return None


# =============================================================================
# REST ENDPOINTS
# =============================================================================

class ManualClickRequest(BaseModel):
    """Request model for manual click."""
    x: float
    y: float


class ManualTypeRequest(BaseModel):
    """Request model for manual typing."""
    text: str
    x: Optional[float] = None
    y: Optional[float] = None


# Session manager (injected)
_session_manager: Optional[SessionManager] = None


def set_session_manager(manager: SessionManager):
    """Set the session manager."""
    global _session_manager
    _session_manager = manager


@router.post("/click")
async def manual_click(
    request: ManualClickRequest,
    user: dict = Depends(get_current_user),
):
    """Send a manual click command."""
    if not _session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    
    email = user["email"]
    session_id = _session_manager.get_session_id(email)
    
    if not session_id:
        raise HTTPException(status_code=400, detail="No active session")
    
    cmd = MouseClickCommand(x=request.x, y=request.y)
    
    # Get frame processor to send command
    from ..webrtc.signaling import frame_processors
    
    if session_id in frame_processors:
        processor = frame_processors[session_id]
        await processor._send_command({
            "action": "click",
            "command": cmd.to_dict(),
        })
        return {"status": "sent"}
    
    raise HTTPException(status_code=400, detail="Session not streaming")


@router.post("/type")
async def manual_type(
    request: ManualTypeRequest,
    user: dict = Depends(get_current_user),
):
    """Send a manual type command."""
    if not _session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    
    email = user["email"]
    session_id = _session_manager.get_session_id(email)
    
    if not session_id:
        raise HTTPException(status_code=400, detail="No active session")
    
    composite = CompositeCommand()
    
    # Add click if position specified
    if request.x is not None and request.y is not None:
        click_cmd = MouseClickCommand(x=request.x, y=request.y)
        composite.add_command(click_cmd)
    
    type_cmd = TypeTextCommand(text=request.text)
    composite.add_command(type_cmd)
    
    # Get frame processor to send command
    from ..webrtc.signaling import frame_processors
    
    if session_id in frame_processors:
        processor = frame_processors[session_id]
        await processor._send_command({
            "action": "type",
            "command": composite.to_dict(),
        })
        return {"status": "sent"}
    
    raise HTTPException(status_code=400, detail="Session not streaming")


@router.get("/status")
async def get_control_status(user: dict = Depends(get_current_user)):
    """Get control status for current session."""
    if not _session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    
    email = user["email"]
    session_id = _session_manager.get_session_id(email)
    
    if not session_id:
        return {"connected": False}
    
    session = await _session_manager.get_session(session_id)
    if not session:
        return {"connected": False}
    
    from ..webrtc.signaling import frame_processors
    
    processor = frame_processors.get(session_id)
    
    return {
        "connected": session.is_streaming,
        "frames_processed": processor.frames_processed if processor else 0,
        "last_analysis": processor.last_analysis_result if processor else None,
        "command_count": session.command_count,
    }
