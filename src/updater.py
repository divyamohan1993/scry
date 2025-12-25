import os
import sys
import subprocess
import requests
import logging
from .config import VERSION_CHECK_URL, LATEST_RELEASE_URL
from .version import VERSION

logger = logging.getLogger("Updater")

def is_frozen():
    """Check if running as a compiled exe."""
    return getattr(sys, 'frozen', False)

def get_remote_version():
    """Fetch the version string from the remote repo."""
    try:
        response = requests.get(VERSION_CHECK_URL, timeout=10)
        if response.status_code == 200:
            # Parse the text to find VERSION = "x.y.z"
            # We assume the file is simple python.
            for line in response.text.splitlines():
                if line.strip().startswith("VERSION"):
                    # Extract string between quotes
                    parts = line.split('"')
                    if len(parts) >= 2:
                        return parts[1]
                    parts = line.split("'")
                    if len(parts) >= 2:
                        return parts[1]
        else:
            logger.warning(f"Failed to fetch version: Status {response.status_code}")
    except Exception as e:
        logger.error(f"Error checking remote version: {e}")
    return None

def update_source_code():
    """
    Performs a git pull and restarts the script.
    Returns True if update was performed and restart initiated.
    """
    logger.info("Checking for updates via Git...")
    try:
        # Check if git is available
        subprocess.check_call(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Fetch origin
        subprocess.check_call(["git", "fetch", "origin"])

        # Check if behind
        status = subprocess.check_output(["git", "status", "-uno"]).decode()
        if "Your branch is up to date" in status:
            logger.info("Source code is up to date.")
            return False

        logger.info("New code found. Pulling changes...")
        subprocess.check_call(["git", "pull"])

        # dependency check
        if os.path.exists("requirements.txt"):
            logger.info("Updating dependencies...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

        logger.info("Restarting application...")
        restart_application()
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Git update failed: {e}")
    except FileNotFoundError:
        logger.warning("Git not found. Skipping source update.")
    return False

def update_binary(remote_ver):
    """
    Downloads the new binary and schedules a replacement.
    """
    logger.info(f"Updating binary from {VERSION} to {remote_ver}...")
    try:
        response = requests.get(LATEST_RELEASE_URL, stream=True, timeout=30)
        if response.status_code != 200:
            logger.error("Failed to download release.")
            return False

        new_exe_name = "Scry_new.exe"
        with open(new_exe_name, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info("Download complete. Scheduling restart...")

        # Create a transient batch script to handle the swap
        # We need a delay to allow this process to exit.
        current_exe = sys.executable

        # The script:
        # 1. Wait 3 seconds
        # 2. Move /Y Scry_new.exe -> current_exe
        # 3. Start current_exe
        # 4. Delete self

        updater_script = "update_swap.bat"
        with open(updater_script, "w") as bat:
            bat.write("@echo off\n")
            bat.write("timeout /t 3 /nobreak >nul\n")
            bat.write(f'move /y "{new_exe_name}" "{current_exe}" >nul\n')
            bat.write(f'start "" "{current_exe}"\n')
            bat.write(f'del "{updater_script}"\n')

        # Launch the batch script silently
        subprocess.Popen(updater_script, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

        sys.exit(0)

    except Exception as e:
        logger.error(f"Binary update failed: {e}")
        return False

def restart_application():
    """Restarts the current python script."""
    logger.info("Restarting...")

    # On Windows, os.execv can be finicky with open file handles,
    # but subprocess + sys.exit is safer for a clean restart.

    # If running as python script
    cmd = [sys.executable] + sys.argv

    if is_frozen():
        # Should be handled by update_binary's batch script usually,
        # but if we just want to restart same exe:
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        # Running as python script
        # If launched by 'pythonw', sys.executable is pythonw.exe
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)

    sys.exit(0)

def check_and_update():
    """
    Main entry point for updates.
    """
    logger.info(f"Current Version: {VERSION}")
    
    if is_frozen():
        # Binary Update Logic
        remote_ver = get_remote_version()
        if remote_ver and remote_ver > VERSION:
            logger.info(f"Update available: {remote_ver}")
            update_binary(remote_ver)
        else:
            logger.info("No binary update available.")
    else:
        # Source Update Logic
        # We use git check first
        if os.path.exists(".git"):
            update_source_code()
        else:
            logger.debug("Not a git repo, skipping git update check.")
