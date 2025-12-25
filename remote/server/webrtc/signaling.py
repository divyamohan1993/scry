"""
Scry Remote - WebRTC Signaling Server

Handles WebRTC connection establishment and SDP/ICE exchange.
Uses aiortc for Python-based WebRTC support.
"""

import asyncio
import json
from typing import Dict, Optional
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import JSONResponse
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.contrib.media import MediaRelay
from loguru import logger

from ..auth.google_sso import get_current_user
from ..auth.session import SessionManager
from .track_processor import FrameProcessor

router = APIRouter()

# Global state
peer_connections: Dict[str, RTCPeerConnection] = {}
frame_processors: Dict[str, FrameProcessor] = {}
media_relay = MediaRelay()

# Session manager (injected from main.py)
_session_manager: Optional[SessionManager] = None


def set_session_manager(manager: SessionManager):
    """Set the session manager (called from main.py)."""
    global _session_manager
    _session_manager = manager


def get_session_manager() -> SessionManager:
    """Get the session manager."""
    if _session_manager is None:
        raise RuntimeError("Session manager not initialized")
    return _session_manager


async def cleanup_peer_connection(session_id: str):
    """Clean up a peer connection and its resources."""
    if session_id in peer_connections:
        pc = peer_connections.pop(session_id)
        try:
            await pc.close()
        except Exception as e:
            logger.error(f"Error closing peer connection: {e}")
    
    if session_id in frame_processors:
        processor = frame_processors.pop(session_id)
        await processor.stop()
    
    logger.info(f"Cleaned up WebRTC resources for session {session_id[:8]}...")


# =============================================================================
# REST ENDPOINTS FOR SIGNALING
# =============================================================================

@router.post("/offer")
async def handle_offer(
    request_data: dict,
    user: dict = Depends(get_current_user),
):
    """
    Handle WebRTC offer from client.
    
    Client sends SDP offer, server creates answer.
    """
    session_manager = get_session_manager()
    email = user["email"]
    
    # Get or create session
    session = await session_manager.create_session(email)
    session_id = session.session_id
    
    # Clean up existing connection if any
    await cleanup_peer_connection(session_id)
    
    # Create new peer connection
    pc = RTCPeerConnection()
    peer_connections[session_id] = pc
    
    # Create frame processor for this session
    frame_processor = FrameProcessor(session_id, session_manager)
    frame_processors[session_id] = frame_processor
    
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"Connection state: {pc.connectionState} for {email}")
        if pc.connectionState in ["failed", "closed", "disconnected"]:
            await cleanup_peer_connection(session_id)
            await session_manager.update_session(session_id, is_streaming=False)
    
    @pc.on("track")
    def on_track(track):
        logger.info(f"Track received: {track.kind} from {email}")
        if track.kind == "video":
            # Start processing video frames
            relayed_track = media_relay.subscribe(track)
            asyncio.create_task(frame_processor.start(relayed_track))
            asyncio.create_task(
                session_manager.update_session(session_id, is_streaming=True)
            )
    
    @pc.on("datachannel")
    def on_datachannel(channel):
        logger.info(f"Data channel opened: {channel.label}")
        frame_processor.set_data_channel(channel)
    
    # Set remote description (offer)
    offer = RTCSessionDescription(
        sdp=request_data["sdp"],
        type=request_data["type"],
    )
    await pc.setRemoteDescription(offer)
    
    # Create and set local description (answer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    
    logger.info(f"Created WebRTC answer for {email}")
    
    return {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
        "session_id": session_id,
    }


@router.post("/ice-candidate")
async def handle_ice_candidate(
    request_data: dict,
    user: dict = Depends(get_current_user),
):
    """Handle ICE candidate from client."""
    session_manager = get_session_manager()
    email = user["email"]
    session_id = session_manager.get_session_id(email)
    
    if not session_id or session_id not in peer_connections:
        raise HTTPException(status_code=400, detail="No active session")
    
    pc = peer_connections[session_id]
    
    candidate_data = request_data.get("candidate")
    if candidate_data:
        candidate = RTCIceCandidate(
            sdpMid=candidate_data.get("sdpMid"),
            sdpMLineIndex=candidate_data.get("sdpMLineIndex"),
            candidate=candidate_data.get("candidate"),
        )
        await pc.addIceCandidate(candidate)
        logger.debug(f"Added ICE candidate for {email}")
    
    return {"status": "ok"}


@router.post("/disconnect")
async def handle_disconnect(user: dict = Depends(get_current_user)):
    """Handle client disconnect request."""
    session_manager = get_session_manager()
    email = user["email"]
    session_id = session_manager.get_session_id(email)
    
    if session_id:
        await cleanup_peer_connection(session_id)
        await session_manager.end_session(session_id)
        logger.info(f"Client disconnected: {email}")
    
    return {"status": "disconnected"}


# =============================================================================
# WEBSOCKET SIGNALING (ALTERNATIVE)
# =============================================================================

@router.websocket("/ws")
async def websocket_signaling(websocket: WebSocket):
    """
    WebSocket-based signaling for real-time communication.
    
    Protocol:
    - Client sends: {"type": "auth", "token": "..."}
    - Client sends: {"type": "offer", "sdp": "...", "type": "offer"}
    - Server sends: {"type": "answer", "sdp": "...", "type": "answer"}
    - Client/Server sends: {"type": "ice", "candidate": {...}}
    - Server sends: {"type": "command", ...}
    """
    await websocket.accept()
    
    session_id: Optional[str] = None
    email: Optional[str] = None
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "auth":
                # Authenticate via session token
                # In practice, verify the token from the session cookie
                email = data.get("email")
                if email:
                    session_manager = get_session_manager()
                    session = await session_manager.create_session(email)
                    session_id = session.session_id
                    await websocket.send_json({"type": "auth_ok", "session_id": session_id})
                    logger.info(f"WebSocket authenticated: {email}")
                else:
                    await websocket.send_json({"type": "error", "message": "Invalid auth"})
            
            elif msg_type == "offer" and session_id:
                # Handle WebRTC offer
                await cleanup_peer_connection(session_id)
                
                session_manager = get_session_manager()
                pc = RTCPeerConnection()
                peer_connections[session_id] = pc
                
                frame_processor = FrameProcessor(session_id, session_manager, websocket)
                frame_processors[session_id] = frame_processor
                
                @pc.on("track")
                def on_track(track):
                    if track.kind == "video":
                        relayed_track = media_relay.subscribe(track)
                        asyncio.create_task(frame_processor.start(relayed_track))
                        asyncio.create_task(
                            session_manager.update_session(session_id, is_streaming=True)
                        )
                
                offer = RTCSessionDescription(sdp=data["sdp"], type="offer")
                await pc.setRemoteDescription(offer)
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                
                await websocket.send_json({
                    "type": "answer",
                    "sdp": pc.localDescription.sdp,
                })
            
            elif msg_type == "ice" and session_id:
                # Handle ICE candidate
                if session_id in peer_connections:
                    pc = peer_connections[session_id]
                    candidate_data = data.get("candidate")
                    if candidate_data:
                        candidate = RTCIceCandidate(
                            sdpMid=candidate_data.get("sdpMid"),
                            sdpMLineIndex=candidate_data.get("sdpMLineIndex"),
                            candidate=candidate_data.get("candidate"),
                        )
                        await pc.addIceCandidate(candidate)
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {email or 'unknown'}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if session_id:
            await cleanup_peer_connection(session_id)
