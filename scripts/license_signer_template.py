#!/usr/bin/env python3
"""
Scry License Signer - Owner's Private Key Tool (TEMPLATE)

This is a TEMPLATE for the tool YOU (the owner) use to generate license keys.
The actual 'license_signer.py' containing your PRIVATE KEY is git-ignored
for security.

USAGE:
1. Copy this file to 'license_signer.py' (if it doesn't exist)
2. Insert your PRIVATE KEY in the variable below
3. Run: python license_signer.py <challenge> 
"""

import sys
import os
import base64
import argparse

# Try to import cryptography
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("ERROR: cryptography package required. Install with: pip install cryptography")
    sys.exit(1)


# =============================================================================
# PRIVATE KEY - THIS IS YOUR SECRET - KEEP IT SAFE!
# =============================================================================
# PASTE YOUR PRIVATE KEY PEM HERE
PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
paste_your_private_key_here
-----END PRIVATE KEY-----"""


def load_private_key():
    """Load the embedded private key."""
    try:
        return serialization.load_pem_private_key(
            PRIVATE_KEY_PEM.encode(),
            password=None,
            backend=default_backend()
        )
    except Exception as e:
        print(f"Error loading private key: {e}")
        print("Did you replace the placeholder PRIVATE_KEY_PEM with your actual key?")
        sys.exit(1)


def sign_challenge(challenge: str) -> str:
    """
    Sign a challenge to generate a license key.
    
    Args:
        challenge: The challenge string from the software
        
    Returns:
        The license key (base64-encoded signature)
    """
    private_key = load_private_key()
    
    signature = private_key.sign(
        challenge.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    return base64.urlsafe_b64encode(signature).decode()


def cli_mode():
    """Command-line interface for signing challenges."""
    parser = argparse.ArgumentParser(
        description="Sign a challenge to generate a Scry license key"
    )
    parser.add_argument(
        "challenge",
        nargs="?",
        help="The challenge string to sign"
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Run as a local web server for easy access"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8888,
        help="Port for web server (default: 8888)"
    )
    
    args = parser.parse_args()
    
    if args.server:
        run_web_server(args.port)
    elif args.challenge:
        try:
            license_key = sign_challenge(args.challenge)
            print(f"\n✓ License Key Generated!\n")
            print(f"License Key:\n{license_key}")
        except Exception as e:
            print(f"✗ Error: {e}")
            sys.exit(1)
    else:
        # Interactive mode
        print("\n🔐 Scry License Signer (Template)")
        print("=" * 50)
        print("Enter the challenge from the software:\n")
        
        try:
            challenge = input("Challenge: ").strip()
            if not challenge:
                print("No challenge provided.")
                sys.exit(1)
            
            license_key = sign_challenge(challenge)
            print(f"\n✓ License Key:\n{license_key}")
            
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)


def run_web_server(port: int):
    """
    Run a simple web server for signing challenges.
    
    This allows you to sign challenges from your phone or any device.
    """
    try:
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import urllib.parse
        import json
    except ImportError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    class SignerHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/" or self.path.startswith("/?"):
                # Parse query parameters
                parsed = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed.query)
                challenge = params.get("challenge", [""])[0]
                license_key = ""
                error = ""
                
                if challenge:
                    try:
                        license_key = sign_challenge(challenge)
                    except Exception as e:
                        error = str(e)
                
                # Return HTML page
                html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scry License Signer</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            max-width: 500px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #fff;
            text-align: center;
            margin-bottom: 30px;
            font-size: 1.8em;
        }}
        .emoji {{ font-size: 1.5em; }}
        label {{
            display: block;
            color: #a0a0a0;
            margin-bottom: 8px;
            font-size: 0.9em;
        }}
        textarea, input {{
            width: 100%;
            padding: 15px;
            border: 2px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            margin-bottom: 20px;
            resize: vertical;
        }}
        textarea:focus, input:focus {{
            outline: none;
            border-color: #6366f1;
        }}
        button {{
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            border: none;
            border-radius: 12px;
            color: #fff;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(99, 102, 241, 0.4);
        }}
        .result {{
            margin-top: 20px;
            padding: 20px;
            background: rgba(34, 197, 94, 0.2);
            border: 2px solid #22c55e;
            border-radius: 12px;
        }}
        .result.error {{
            background: rgba(239, 68, 68, 0.2);
            border-color: #ef4444;
        }}
        .result h3 {{
            color: #22c55e;
            margin-bottom: 10px;
        }}
        .result.error h3 {{
            color: #ef4444;
        }}
        .result pre {{
            color: #fff;
            word-break: break-all;
            white-space: pre-wrap;
            font-size: 12px;
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
        }}
        .copy-btn {{
            margin-top: 10px;
            padding: 10px 20px;
            font-size: 0.9em;
            background: rgba(255,255,255,0.1);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1><span class="emoji">🔐</span> Scry License Signer</h1>
        
        <form method="GET" action="/">
            <label for="challenge">Challenge Code from Software:</label>
            <textarea 
                name="challenge" 
                id="challenge" 
                rows="3" 
                placeholder="Paste the challenge code here..."
            >{challenge}</textarea>
            
            <button type="submit">🔑 Generate License Key</button>
        </form>
        
        {"" if not license_key and not error else f'''
        <div class="result {"error" if error else ""}">
            <h3>{"❌ Error" if error else "✓ License Key Generated"}</h3>
            {f"<p style='color:#fff'>{error}</p>" if error else f'''
            <pre id="license-key">{license_key}</pre>
            <button class="copy-btn" onclick="copyKey()">📋 Copy to Clipboard</button>
            '''}
        </div>
        '''}
    </div>
    
    <script>
        function copyKey() {{
            const key = document.getElementById('license-key').textContent;
            navigator.clipboard.writeText(key).then(() => {{
                alert('License key copied!');
            }});
        }}
    </script>
</body>
</html>"""
                
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(html.encode())
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            print(f"[{self.log_date_time_string()}] {args[0]}")
    
    print(f"\n🔐 Scry License Signer - Web Server")
    print(f"=" * 50)
    print(f"Server running at: http://localhost:{port}")
    print(f"Access from your phone using your computer's IP address")
    print(f"\nPress Ctrl+C to stop\n")
    
    try:
        server = HTTPServer(("0.0.0.0", port), SignerHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    cli_mode()
