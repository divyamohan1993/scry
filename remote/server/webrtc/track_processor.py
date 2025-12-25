"""
Scry Remote - Track Processor

Extracts frames from WebRTC video track and sends them to Scry for analysis.
Receives control commands and forwards them to the client.
"""

import asyncio
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timedelta
import io

from PIL import Image
import numpy as np
from aiortc import MediaStreamTrack
from aiortc.mediastreams import MediaStreamError
from loguru import logger

if TYPE_CHECKING:
    from fastapi import WebSocket
    from ..auth.session import SessionManager

from ..config import FRAME_INTERVAL_MS, FRAME_QUALITY
from ..scry_adapter.adapter import ScryAdapter


class FrameProcessor:
    """
    Processes video frames from WebRTC stream.
    
    - Extracts frames at configurable intervals
    - Sends frames to Scry for AI analysis
    - Receives control commands and forwards to client
    """
    
    def __init__(
        self,
        session_id: str,
        session_manager: "SessionManager",
        websocket: Optional["WebSocket"] = None,
    ):
        self.session_id = session_id
        self.session_manager = session_manager
        self.websocket = websocket
        self.data_channel = None
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_frame_time: Optional[datetime] = None
        self._frame_interval = timedelta(milliseconds=FRAME_INTERVAL_MS)
        
        # Scry adapter for AI analysis
        self.scry_adapter = ScryAdapter()
        
        # Frame statistics
        self.frames_processed = 0
        self.last_analysis_result = None
    
    def set_data_channel(self, channel):
        """Set the WebRTC data channel for sending commands."""
        self.data_channel = channel
        logger.info(f"Data channel set for session {self.session_id[:8]}...")
    
    async def start(self, track: MediaStreamTrack):
        """Start processing frames from the video track."""
        if self._running:
            logger.warning(f"Frame processor already running for {self.session_id[:8]}...")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._process_track(track))
        logger.info(f"Started frame processing for session {self.session_id[:8]}...")
    
    async def stop(self):
        """Stop frame processing."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info(f"Stopped frame processing for session {self.session_id[:8]}...")
    
    async def _process_track(self, track: MediaStreamTrack):
        """Main processing loop for video frames."""
        try:
            while self._running:
                try:
                    # Receive frame from track
                    frame = await track.recv()
                    
                    # Throttle frame processing
                    now = datetime.utcnow()
                    if self._last_frame_time:
                        elapsed = now - self._last_frame_time
                        if elapsed < self._frame_interval:
                            continue
                    
                    self._last_frame_time = now
                    
                    # Convert frame to PIL Image
                    image = self._frame_to_pil(frame)
                    if image is None:
                        continue
                    
                    self.frames_processed += 1
                    await self.session_manager.increment_frame_count(self.session_id)
                    
                    # Analyze frame with Scry
                    result = await self._analyze_frame(image)
                    
                    if result and result.get("action"):
                        # Send control command to client
                        await self._send_command(result)
                
                except MediaStreamError:
                    logger.info(f"Media stream ended for session {self.session_id[:8]}...")
                    break
                except Exception as e:
                    logger.error(f"Frame processing error: {e}")
                    await asyncio.sleep(0.1)
        
        finally:
            self._running = False
    
    def _frame_to_pil(self, frame) -> Optional[Image.Image]:
        """Convert aiortc VideoFrame to PIL Image."""
        try:
            # Convert to numpy array (RGB format)
            img = frame.to_ndarray(format="rgb24")
            return Image.fromarray(img)
        except Exception as e:
            logger.error(f"Frame conversion error: {e}")
            return None
    
    async def _analyze_frame(self, image: Image.Image) -> Optional[dict]:
        """
        Send frame to Scry for analysis.
        
        Returns control commands if action is needed.
        """
        try:
            result = await self.scry_adapter.analyze_image(image)
            
            if result:
                self.last_analysis_result = result
                logger.debug(f"Analysis result: {result.get('type', 'unknown')}")
            
            return result
        
        except Exception as e:
            logger.error(f"Scry analysis error: {e}")
            return None
    
    async def _send_command(self, command: dict):
        """Send control command to client."""
        try:
            # Add session and timestamp
            command["session_id"] = self.session_id
            command["timestamp"] = datetime.utcnow().isoformat()
            
            await self.session_manager.increment_command_count(self.session_id)
            
            # Send via WebSocket (if available)
            if self.websocket:
                await self.websocket.send_json({
                    "type": "command",
                    **command,
                })
                logger.info(f"Sent command via WebSocket: {command.get('action')}")
            
            # Send via Data Channel (if available)
            elif self.data_channel and self.data_channel.readyState == "open":
                import json
                self.data_channel.send(json.dumps({
                    "type": "command",
                    **command,
                }))
                logger.info(f"Sent command via DataChannel: {command.get('action')}")
            
            else:
                logger.warning("No channel available to send command")
        
        except Exception as e:
            logger.error(f"Error sending command: {e}")


class ScreenCaptureTrack(MediaStreamTrack):
    """
    Custom MediaStreamTrack for screen capture.
    
    Used when we need to send frames back to the client for debugging.
    """
    
    kind = "video"
    
    def __init__(self):
        super().__init__()
        self._timestamp = 0
        self._frame = None
    
    def set_frame(self, image: Image.Image):
        """Set the next frame to send."""
        from av import VideoFrame
        
        frame = VideoFrame.from_ndarray(
            np.array(image),
            format="rgb24",
        )
        frame.pts = self._timestamp
        frame.time_base = "1/30"
        self._timestamp += 1
        self._frame = frame
    
    async def recv(self):
        """Receive the next frame."""
        if self._frame:
            frame = self._frame
            self._frame = None
            return frame
        
        # Return empty frame if none available
        await asyncio.sleep(1/30)
        return await self.recv()
