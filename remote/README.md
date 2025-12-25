# 🌐 Scry Remote - Screen Streaming & Control Framework

> **Modular framework for remote screen streaming and AI-powered control**

This framework enables users to stream their screen via a web browser to a Scry server, which analyzes the stream using AI and sends back control commands (mouse movements, clicks, typing).

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER'S BROWSER                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  WebRTC Client (JavaScript)                                      │   │
│  │  - Captures screen via getDisplayMedia()                         │   │
│  │  - Streams video to server via WebRTC                            │   │
│  │  - Receives control commands from server                         │   │
│  │  - Executes mouse/keyboard simulation locally                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ WebRTC + WebSocket
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       SCRY REMOTE SERVER (Ubuntu VM)                    │
│                          scry.dmj.one                                   │
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │
│  │  FastAPI        │  │  SSO Auth       │  │  WebRTC/Signaling       │ │
│  │  (HTTPS:443)    │──│  (Google OAuth) │──│  Server (aiortc)        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘ │
│           │                                            │                │
│           │                                            │                │
│           ▼                                            ▼                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    FRAME PROCESSOR                               │   │
│  │  - Extracts frames from WebRTC video stream                      │   │
│  │  - Sends frames to Scry Adapter (subprocess or API)              │   │
│  │  - Receives control commands from Scry                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│           │                                                             │
│           │ STDIN/STDOUT (JSON Protocol)                               │
│           ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    SCRY ADAPTER                                  │   │
│  │  - Wrapper around existing Scry software                         │   │
│  │  - Receives PIL Image, returns control commands                  │   │
│  │  - NO MODIFICATIONS to core Scry code                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Features

- **🔐 SSO Authentication** - Google OAuth via scry.dmj.one
- **📺 WebRTC Streaming** - Low-latency screen capture via browser
- **🤖 AI Analysis** - Uses existing Scry/Gemini for screen analysis
- **🖱️ Remote Control** - Mouse movements, clicks, and typing sent back to browser
- **🔌 Modular Design** - Completely separate from core Scry software
- **☁️ Cloud Ready** - Designed for GCloud Ubuntu VM deployment

---

## 📁 Directory Structure

```
remote/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .env.example              # Environment configuration template
│
├── server/                   # Backend server components
│   ├── __init__.py
│   ├── main.py               # FastAPI application entry point
│   ├── config.py             # Server configuration
│   ├── auth/                 # Authentication module
│   │   ├── __init__.py
│   │   ├── google_sso.py     # Google OAuth implementation
│   │   └── session.py        # Session management
│   ├── webrtc/               # WebRTC handling
│   │   ├── __init__.py
│   │   ├── signaling.py      # WebRTC signaling server
│   │   └── track_processor.py # Frame extraction from video
│   ├── scry_adapter/         # Adapter to existing Scry
│   │   ├── __init__.py
│   │   └── adapter.py        # Scry integration layer
│   └── control/              # Remote control commands
│       ├── __init__.py
│       └── commands.py       # Mouse/keyboard command protocol
│
├── client/                   # Frontend web client
│   ├── index.html            # Main entry point
│   ├── css/
│   │   └── styles.css        # Styling
│   └── js/
│       ├── app.js            # Main application logic
│       ├── auth.js           # SSO authentication
│       ├── webrtc.js         # WebRTC client
│       └── control.js        # Receiving and executing commands
│
└── deploy/                   # Deployment scripts
    ├── install.sh            # Ubuntu setup script
    ├── nginx.conf            # Nginx reverse proxy config
    ├── scry-remote.service   # Systemd service file
    └── ssl-setup.sh          # Let's Encrypt SSL setup
```

---

## 🛠️ Installation

### Prerequisites

- Ubuntu 20.04+ (GCloud VM recommended)
- Python 3.10+
- Nginx
- Domain configured (scry.dmj.one → VM IP)

### Quick Setup

```bash
cd remote/deploy
chmod +x install.sh
sudo ./install.sh
```

### Manual Setup

1. **Clone and install dependencies**:
```bash
cd remote
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your Google OAuth credentials and Gemini API key
```

3. **Run server**:
```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

---

## ⚙️ Configuration

All configuration is via environment variables (`.env` file):

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | ✅ |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret | ✅ |
| `GEMINI_API_KEY` | Gemini API Key (for Scry) | ✅ |
| `SECRET_KEY` | JWT signing key | ✅ |
| `DOMAIN` | Your domain (e.g., scry.dmj.one) | ✅ |
| `ALLOWED_EMAILS` | Comma-separated allowed email patterns | ❌ |
| `FRAME_INTERVAL_MS` | Screenshot interval (default: 500) | ❌ |

---

## 🔒 Security

- All traffic over HTTPS (Let's Encrypt)
- Google OAuth SSO for authentication
- JWT tokens for session management
- Optional email whitelist for access control
- No credentials stored on client

---

## 📜 License

MIT License - Same as Scry
