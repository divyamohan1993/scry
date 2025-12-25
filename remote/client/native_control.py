"""
Scry Remote - Native Control Helper

This is a standalone Python script that runs on the user's machine
to execute mouse and keyboard commands received from the web client.

Since browsers cannot directly control the OS mouse/keyboard,
this helper bridges that gap using native automation libraries.

Usage:
1. Install: pip install pyautogui keyboard websockets
2. Run: python native_control.py
3. When prompted, enter your session token from the web client

The helper connects to the Scry Remote server and receives commands
to execute on the local machine.
"""

import asyncio
import json
import time
import random
import sys
import argparse
from typing import Optional

try:
    import pyautogui
    import keyboard
    import websockets
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install pyautogui keyboard websockets")
    sys.exit(1)


# Safety settings
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.01


class NativeController:
    """
    Executes mouse and keyboard commands on the local system.
    """
    
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self.is_running = True
        
    async def execute(self, command: dict) -> bool:
        """Execute a command and return success status."""
        try:
            cmd_type = command.get("type")
            
            if cmd_type == "composite":
                # Execute sequence
                for sub_cmd in command.get("commands", []):
                    await self.execute(sub_cmd)
                    delay = command.get("delay_between_ms", 100) / 1000
                    await asyncio.sleep(delay)
                return True
                
            elif cmd_type == "mouse_move":
                await self._move_mouse(command)
                
            elif cmd_type == "mouse_click":
                await self._click(command)
                
            elif cmd_type == "type_text":
                await self._type_text(command)
                
            elif cmd_type == "key_press":
                await self._key_press(command)
                
            else:
                print(f"Unknown command type: {cmd_type}")
                return False
                
            return True
            
        except Exception as e:
            print(f"Command execution error: {e}")
            return False
    
    async def _move_mouse(self, cmd: dict):
        """Move mouse to position with human-like movement."""
        x = int(cmd.get("x", 0.5) * self.screen_width)
        y = int(cmd.get("y", 0.5) * self.screen_height)
        duration = cmd.get("duration_ms", 500) / 1000
        
        if cmd.get("human_like", True):
            # Use easing for natural movement
            pyautogui.moveTo(
                x, y,
                duration=duration,
                tween=pyautogui.easeOutQuad
            )
        else:
            pyautogui.moveTo(x, y, duration=duration)
    
    async def _click(self, cmd: dict):
        """Click at position."""
        x = int(cmd.get("x", 0.5) * self.screen_width)
        y = int(cmd.get("y", 0.5) * self.screen_height)
        button = cmd.get("button", "left")
        
        if cmd.get("move_first", True):
            duration = cmd.get("duration_ms", 500) / 1000
            pyautogui.moveTo(
                x, y,
                duration=duration,
                tween=pyautogui.easeOutQuad
            )
        
        # Small random delay before click (human behavior)
        await asyncio.sleep(random.uniform(0.05, 0.15))
        
        pyautogui.click(x, y, button=button)
    
    async def _type_text(self, cmd: dict):
        """Type text with human-like timing."""
        text = cmd.get("text", "")
        wpm_min = cmd.get("wpm_min", 40)
        wpm_max = cmd.get("wpm_max", 80)
        
        # Calculate base delay
        avg_wpm = (wpm_min + wpm_max) / 2
        chars_per_minute = avg_wpm * 5
        base_delay = 60 / chars_per_minute
        
        for char in text:
            # Variable inter-key delay
            delay = base_delay * random.uniform(0.5, 1.5)
            
            # Type the character
            if char == '\n':
                keyboard.press_and_release('enter')
            else:
                keyboard.write(char)
            
            await asyncio.sleep(delay)
            
            # Occasional longer pause (thinking)
            if random.random() < 0.02:
                await asyncio.sleep(random.uniform(0.3, 1.0))
    
    async def _key_press(self, cmd: dict):
        """Press a key or key combination."""
        key = cmd.get("key", "")
        
        # Handle common key names
        key_map = {
            "enter": "enter",
            "return": "enter",
            "tab": "tab",
            "backspace": "backspace",
            "delete": "delete",
            "escape": "esc",
            "space": "space",
        }
        
        mapped_key = key_map.get(key.lower(), key)
        keyboard.press_and_release(mapped_key)


class NativeClient:
    """
    WebSocket client that receives commands from Scry Remote server.
    """
    
    def __init__(self, server_url: str, session_token: str):
        self.server_url = server_url
        self.session_token = session_token
        self.controller = NativeController()
        self.is_connected = False
        
    async def connect(self):
        """Connect to server and start receiving commands."""
        ws_url = f"{self.server_url}/native/ws?token={self.session_token}"
        
        print(f"Connecting to {self.server_url}...")
        
        async with websockets.connect(ws_url) as ws:
            self.is_connected = True
            print("✓ Connected! Waiting for commands...")
            print("  (Move mouse to screen corner to abort)")
            print("")
            
            try:
                async for message in ws:
                    data = json.loads(message)
                    
                    if data.get("type") == "command":
                        print(f"→ Executing: {data.get('action', 'unknown')}")
                        
                        command = data.get("command", {})
                        success = await self.controller.execute(command)
                        
                        # Send acknowledgment
                        await ws.send(json.dumps({
                            "type": "ack",
                            "command_id": data.get("id"),
                            "success": success,
                        }))
                        
                    elif data.get("type") == "ping":
                        await ws.send(json.dumps({"type": "pong"}))
                        
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
            except KeyboardInterrupt:
                print("\nDisconnecting...")
            finally:
                self.is_connected = False


def get_session_token() -> str:
    """Get session token from user."""
    print("")
    print("=" * 50)
    print("  SCRY REMOTE - NATIVE CONTROL HELPER")
    print("=" * 50)
    print("")
    print("This helper enables full mouse/keyboard control.")
    print("")
    print("To get your session token:")
    print("  1. Open Scry Remote in your browser")
    print("  2. Start screen sharing")
    print("  3. Click 'Copy Session Token' button")
    print("")
    
    token = input("Enter session token: ").strip()
    return token


def main():
    parser = argparse.ArgumentParser(description="Scry Remote Native Control Helper")
    parser.add_argument(
        "--server",
        default="wss://scry.dmj.one",
        help="Server WebSocket URL"
    )
    parser.add_argument(
        "--token",
        help="Session token (will prompt if not provided)"
    )
    
    args = parser.parse_args()
    
    token = args.token or get_session_token()
    
    if not token:
        print("No session token provided. Exiting.")
        sys.exit(1)
    
    client = NativeClient(args.server, token)
    
    try:
        asyncio.run(client.connect())
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
