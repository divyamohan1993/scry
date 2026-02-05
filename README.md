# 🔮 Scry

![Scry CI](https://github.com/divyamohan1993/scry/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-active-success)

> **Scry** (/skraɪ/) — *"To see, to reveal, to divine hidden knowledge."*
>
> An advanced, AI-powered screen analysis and response system designed for **OFFENSIVE SECURITY** and **EDUCATIONAL PURPOSES**.

<p align="center">
  <em>"Scry sees all."</em>
</p>

---

## ⚠️ Disclaimer & Legal Warning

> [!IMPORTANT]
> **OFFENSIVE SECURITY TOOL / EDUCATIONAL PURPOSE ONLY**
>
> This software is strictly for **educational purposes** and **authorized security testing**. It demonstrates how screen reading, OCR, and AI response automation can be used in simulated environments.
>
> **Unethical or illegal use of this software is prohibited.**
> The developers assume **no liability** and are not responsible for any misuse or damage caused by this program. By using this software, you agree to these terms.

---

## 🚀 Features

-   **🔮 Divine Vision**: Gazes at screens and divines answers using AI
-   **👻 Stealth Mode**: Runs silently in the background with minimal footprint
-   **🧠 AI-Powered**: Utilizes **Google Gemini (Flash Models)** for high-speed, accurate analysis
-   **👁️ OCR Redundancy**: Hybrid approach using both AI Vision and Tesseract OCR
-   **🎯 Automated Response**: Intelligent mouse movement and human-like typing simulation
-   **📋 Clipboard Streaming**: Stream clipboard content character-by-character with customizable hotkey
-   **🔐 Integrity Verification**: Built-in SHA256 integrity checks to prevent tampering

## 📋 Table of Contents

-   [Installation](#-installation)
-   [Usage](#-usage)
-   [Configuration](#-configuration)
-   [Development](#-development)
-   [Security](#-security)
-   [Contributing](#-contributing)

## 🛠 Installation

### Prerequisites

-   Windows 10/11
-   **Python 3.10+** (that's it!)
-   Tesseract-OCR (Optional, for redundancy)

### Setup & Usage

**True One-Click Deployment** — No setup required!

1. Download or clone this repository
2. **Double-click `Scry.vbs`** (silent) or `scry.bat` (with console)
3. The Control Panel opens in your browser
4. Click **Start** — everything installs automatically!

That's it! On a fresh machine, clicking Start will:
- ✅ Create a virtual environment
- ✅ Install all Python dependencies
- ✅ Create a default `.env` configuration
- ✅ Launch the application

### 🕹️ Control Center (Scripts)

| Script | Description |
| :--- | :--- |
| **`Scry.vbs`** | **The Main Launcher (Silent)**. Double-click to start — no console window appears. Auto-installs Python if missing! |
| **`scripts/scry.bat`** | **Developer Launcher**. Same as above but shows console output for debugging. |
| **`scripts/package.bat`** | **Create Distribution Package**. Creates a clean zip file for sharing to other computers. |
| **`scripts/stop.bat`** | **Force Stop**. Instantly terminates all running instances of Scry. |
| **`scripts/build.bat`** | **Build Executable**. Compiles Scry into a standalone .exe file. |

## 🎮 Usage

Scry operates in two modes:

### 1. Stealth Mode (Default)
Run `.\start.bat`. Scry will verify environment, check dependencies, and detach into the background.

### 2. Developer Mode
Set `DEVELOPER_MODE = True` in your `.env` file. Scry will run in the foreground with verbose logging.

## ⚙ Configuration

All configuration is managed via environment variables (`.env` file).

-   **Gemini API Key**: Stored with **machine-bound encryption** (see Security below).
-   **Hotkeys**: Configurable trigger keys for MCQ, descriptive modes, and clipboard streaming.
    - **Triple-Press Activation**: All hotkeys must be pressed **3 times consecutively** to trigger
    - Any other key pressed between the 3 presses resets the count
    - No time limit between presses (can be seconds or minutes apart)
-   **Clipboard Streaming**: Press the clipboard hotkey 3x (default: `ccc`) to type out clipboard content character-by-character.
    - **Controls during streaming**: `Backspace` = Pause/Resume, `9` = Stop, `→` = Speed Up
-   **Behavior**: Toggle typing simulation, mouse speed, and logging levels.

See `.env.example` for all available options.

## 🔐 API Key Security

Scry uses **machine-bound encryption** to protect your API key:

### How It Works
- When you enter your Gemini API key, it is **immediately encrypted** using a unique fingerprint derived from:
  - Machine hardware identifiers (CPU, disk serial, MAC address)
  - The exact installation path of the project
  - A unique installation ID generated on first run

### What This Means
- ✅ Your API key is **never stored in plain text** after first setup
- ✅ **Copying the project folder** to another location **invalidates** the key
- ✅ **Moving to another machine** also **invalidates** the key
- ✅ Even if someone steals your `.env` file, the encrypted key is **useless** without your exact setup

### If Your Key Is Invalidated
If you copy or move the project, you'll simply be prompted to re-enter your API key. This is a security feature, not a bug!

## 💻 Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
flake8 src/
bandit -r src/
```

## 📦 Shipping & Auto-Updates

Scry includes a built-in **Auto-Updater** and **CI/CD Pipeline**.

### 1. Automatic Updates
- **Source Mode**: If running from source, Scry periodically checks the GitHub repo. Changes pushed to `main` trigger automatic `git pull` and restart.
- **Binary Mode**: If deployed as an EXE, Scry checks the latest GitHub Release and upgrades itself seamlessly.

### 2. How to Ship a New Version
To deploy an update to all users:
1.  Edit `src/version.py` and bump the version string (e.g., `VERSION = "1.0.1"`).
2.  Push this change to the `main` branch.
3.  **GitHub Actions** will automatically:
    -   Detect the version change.
    -   Compile a new obfuscated `Scry.exe`.
    -   Create a new GitHub Release (e.g., `v1.0.1`).
    -   Upload the new EXE to the release.
4.  All active clients will detect the new release and download the update automatically.

## 🔐 Ephemeral Licensing System

Scry includes an optional **ephemeral licensing system** that requires a one-time license key for each session. This provides ultimate control over software distribution.

### How It Works

1. **On each startup**, the software generates a unique **Challenge Code**
2. You (the owner) **sign the challenge** with your private key to create a **License Key**
3. The user enters the License Key → Software verifies → Session starts
4. **When the software closes**, the license expires
5. On next run, a **new challenge** is generated → **new license key** needed

### Why This Is Secure

| Scenario | Result |
|:---------|:-------|
| Attacker has full source code | ❌ Can't generate license keys without private key |
| Attacker copies your license key | ❌ Useless - keys are one-time and session-specific |
| User shares software with others | ❌ Each session requires YOUR authorization |

### Setup (For Owner)

1. **Generate Keys** (one-time):
   ```bash
   python -m src.utils.license_manager generate-keys --output my_secret_keys
   ```

2. **Move the Private Key** out of the project to a secure location (like your personal device)

3. **Embed the Public Key** in `src/utils/license_manager.py` (already done if you used the built-in generator)

4. **Enable Licensing** in `.env`:
   ```
   REQUIRE_LICENSE=True
   ```

### Generating License Keys (For Owner)

When a user shows you their Challenge Code, you can generate a license key using:

**Option A: Command Line**
```bash
python license_signer.py <challenge>
```

**Option B: Mobile-Friendly Web Interface**
```bash
python license_signer.py --server --port 8888
# Access from any device at http://your-ip:8888
```

The web interface allows you to sign challenges from your phone!

## 🔒 Security

See [SECURITY.md](docs/SECURITY.md) for reporting vulnerabilities.

## 🤝 Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md).

---

<p align="center">
  <strong>🔮 Scry</strong> — <em>Divine your answers.</em>
  <br />
  Made with ❤️ by the Scry Team
  <br />
  A <a href="https://dmj.one">dmj.one</a> project
</p>
