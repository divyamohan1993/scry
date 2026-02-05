"""
Secure API Key Manager for Scry

This module provides secure, machine-bound API key storage that:
1. Encrypts API keys using machine-specific fingerprints
2. Binds keys to the installation path (copying invalidates the key)
3. Handles all encryption/decryption transparently

Security Model:
- Key derivation uses: Machine ID + CPU info + Installation Path + Salt
- Copying the project folder invalidates the encrypted key
- Even the .env file's encrypted value is useless on another machine
"""

import base64
import hashlib
import json
import os
import platform
import subprocess
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple


class SecureKeyManager:
    """
    Manages secure, machine-bound API key encryption and storage.
    
    The encryption key is derived from:
    1. Machine UUID (unique to the hardware)
    2. CPU information
    3. Installation path (project location)
    4. A unique installation ID (generated once, stored in hidden file)
    
    This ensures that:
    - Copying the project folder to another machine won't work
    - Copying the project folder to another location won't work
    - The encrypted key is useless without the exact same environment
    """
    
    # File to store the installation-specific salt
    INSTALLATION_ID_FILE = ".scry_installation"
    # Prefix to identify encrypted keys
    ENCRYPTED_PREFIX = "SCRY_ENC_V1:"
    
    def __init__(self, base_dir: str):
        """
        Initialize the secure key manager.
        
        Args:
            base_dir: The base directory of the project (where .env is located)
        """
        self.base_dir = os.path.abspath(base_dir)
        # Normalize path on Windows to ensure consistent drive letter casing
        if platform.system() == "Windows" and len(self.base_dir) >= 2 and self.base_dir[1] == ':':
            self.base_dir = self.base_dir[0].upper() + self.base_dir[1:]
        self.installation_id_path = os.path.join(self.base_dir, self.INSTALLATION_ID_FILE)
        self._fernet = None
        self._key_valid = False
    
    def _get_machine_id(self) -> str:
        """Get a unique identifier for this machine."""
        machine_id_parts = []
        
        # 1. Use uuid.getnode() for MAC address (partial hardware ID)
        mac = uuid.getnode()
        machine_id_parts.append(f"mac:{mac}")
        
        # 2. Get machine name
        machine_id_parts.append(f"node:{platform.node()}")
        
        # 3. Get CPU info (platform provides limited but consistent info)
        machine_id_parts.append(f"proc:{platform.processor()}")
        machine_id_parts.append(f"arch:{platform.machine()}")
        
        # 4. Windows-specific: Get MachineGuid from registry (most stable identifier)
        if platform.system() == "Windows":
            try:
                import winreg
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Cryptography"
                ) as key:
                    machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
                    machine_id_parts.append(f"wguid:{machine_guid}")
            except Exception:
                pass
            
            # NOTE: Disk serial lookup removed - it's unreliable across restarts
            # as wmic can return serials in different orders or formats
        
        # 5. Linux/Mac: Try to read machine-id
        elif platform.system() == "Linux":
            try:
                with open("/etc/machine-id", "r") as f:
                    machine_id_parts.append(f"mid:{f.read().strip()}")
            except Exception:
                pass
        
        elif platform.system() == "Darwin":  # macOS
            try:
                result = subprocess.run(
                    ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if "IOPlatformUUID" in line:
                            uuid_val = line.split('"')[-2]
                            machine_id_parts.append(f"muuid:{uuid_val}")
                            break
            except Exception:
                pass
        
        return "|".join(machine_id_parts)
    
    def _get_installation_id(self) -> str:
        """
        Get or create a unique installation ID.
        
        This ID is generated once when the project is first set up
        and stored in a hidden file. If the file is missing, a new
        ID is generated, which will invalidate any existing encrypted keys.
        """
        if os.path.exists(self.installation_id_path):
            try:
                with open(self.installation_id_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("id", "")
            except Exception:
                pass
        
        # Generate new installation ID
        new_id = hashlib.sha256(
            f"{uuid.uuid4()}-{time.time_ns()}".encode()
        ).hexdigest()
        
        self._save_installation_id(new_id)
        return new_id
    
    def _save_installation_id(self, installation_id: str) -> bool:
        """Save the installation ID to the hidden file."""
        try:
            data = {
                "id": installation_id,
                "created": time.time(),
                "path": self.base_dir
            }
            with open(self.installation_id_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            
            # On Windows, make the file hidden
            if platform.system() == "Windows":
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(
                        self.installation_id_path, 0x02  # FILE_ATTRIBUTE_HIDDEN
                    )
                except Exception:
                    pass
            
            return True
        except Exception as e:
            print(f"[SecureKeyManager] Warning: Could not save installation ID: {e}")
            return False
    
    def _derive_key(self) -> bytes:
        """
        Derive the encryption key from machine-specific data.
        
        The key is derived from:
        1. Machine ID (hardware fingerprint)
        2. Installation path (prevents copy-paste attacks)
        3. Installation ID (unique salt per installation)
        """
        machine_id = self._get_machine_id()
        installation_id = self._get_installation_id()
        
        # Combine all components
        key_material = f"{machine_id}|{self.base_dir}|{installation_id}"
        
        # Derive a 32-byte key using SHA-256
        key_hash = hashlib.sha256(key_material.encode()).digest()
        
        # Fernet requires a URL-safe base64-encoded 32-byte key
        return base64.urlsafe_b64encode(key_hash)
    
    def _get_fernet(self):
        """Get or create the Fernet encryption instance."""
        if self._fernet is None:
            try:
                from cryptography.fernet import Fernet
                key = self._derive_key()
                self._fernet = Fernet(key)
                self._key_valid = True
            except ImportError:
                raise ImportError(
                    "cryptography package is required. Install with: pip install cryptography"
                )
        return self._fernet
    
    def encrypt_key(self, plain_key: str) -> str:
        """
        Encrypt an API key for secure storage.
        
        Args:
            plain_key: The plain-text API key
            
        Returns:
            Encrypted key string with prefix
        """
        if not plain_key:
            return ""
        
        fernet = self._get_fernet()
        encrypted = fernet.encrypt(plain_key.encode())
        return f"{self.ENCRYPTED_PREFIX}{encrypted.decode()}"
    
    def decrypt_key(self, encrypted_key: str) -> Optional[str]:
        """
        Decrypt an API key.
        
        Args:
            encrypted_key: The encrypted key string (with or without prefix)
            
        Returns:
            The plain-text API key, or None if decryption fails
        """
        if not encrypted_key:
            return None
        
        # Check if key is encrypted
        if not encrypted_key.startswith(self.ENCRYPTED_PREFIX):
            # Not encrypted, return as-is (for backward compatibility)
            return encrypted_key
        
        # Remove prefix
        encrypted_data = encrypted_key[len(self.ENCRYPTED_PREFIX):]
        
        try:
            fernet = self._get_fernet()
            decrypted = fernet.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            # Decryption failed - key is invalid for this machine/path
            return None
    
    def is_encrypted(self, key_value: str) -> bool:
        """Check if a key value is in encrypted format."""
        return key_value.startswith(self.ENCRYPTED_PREFIX) if key_value else False
    
    def get_decrypted_api_key(self, env_value: str) -> Tuple[Optional[str], bool]:
        """
        Get the decrypted API key from an environment value.
        
        Args:
            env_value: The value from the environment/config
            
        Returns:
            Tuple of (decrypted_key, was_encrypted)
            - decrypted_key: The plain text key, or None if decryption failed
            - was_encrypted: True if the value was encrypted
        """
        if not env_value:
            return None, False
        
        if self.is_encrypted(env_value):
            decrypted = self.decrypt_key(env_value)
            return decrypted, True
        else:
            return env_value, False
    
    def migrate_plain_key_to_encrypted(self, env_path: str, key_name: str = "GEMINI_API_KEY") -> bool:
        """
        Migrate a plain-text API key in .env to encrypted format.
        
        Args:
            env_path: Path to the .env file
            key_name: Name of the key to migrate
            
        Returns:
            True if migration was successful
        """
        if not os.path.exists(env_path):
            return False
        
        try:
            # Read current content
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            modified = False
            new_lines = []
            
            for line in lines:
                stripped = line.strip()
                if stripped.startswith(f"{key_name}="):
                    # Extract the current value
                    value = stripped.split("=", 1)[1].strip()
                    
                    # Skip if already encrypted or placeholder
                    if self.is_encrypted(value) or not value or value == "YOUR_GEMINI_API_KEY_HERE":
                        new_lines.append(line)
                        continue
                    
                    # Encrypt the key
                    encrypted = self.encrypt_key(value)
                    new_lines.append(f"{key_name}={encrypted}\n")
                    modified = True
                else:
                    new_lines.append(line)
            
            if modified:
                with open(env_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                return True
            
            return False
            
        except Exception as e:
            print(f"[SecureKeyManager] Error migrating key: {e}")
            return False
    
    def validate_installation(self) -> Tuple[bool, str]:
        """
        Validate that this installation is properly configured.
        
        Returns:
            Tuple of (is_valid, message)
        """
        # Check if installation ID exists and path matches
        if not os.path.exists(self.installation_id_path):
            return False, "Installation not initialized. Keys need to be re-entered."
        
        try:
            with open(self.installation_id_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            stored_path = data.get("path", "")
            if stored_path and stored_path != self.base_dir:
                return False, (
                    f"Installation path mismatch. "
                    f"Expected: {stored_path}, Got: {self.base_dir}. "
                    f"API keys need to be re-entered."
                )
            
            return True, "Installation valid."
            
        except Exception as e:
            return False, f"Installation validation error: {e}"
    
    def reset_installation(self) -> bool:
        """
        Reset the installation (invalidates all encrypted keys).
        
        This should be called when the user wants to re-enter their keys
        or when migrating the installation.
        """
        try:
            if os.path.exists(self.installation_id_path):
                os.remove(self.installation_id_path)
            self._fernet = None
            self._key_valid = False
            return True
        except Exception as e:
            print(f"[SecureKeyManager] Error resetting installation: {e}")
            return False


# Convenience functions for module-level access
_manager_instance: Optional[SecureKeyManager] = None


def get_manager(base_dir: Optional[str] = None) -> SecureKeyManager:
    """Get or create the global SecureKeyManager instance."""
    global _manager_instance
    
    if _manager_instance is None:
        if base_dir is None:
            # Default to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _manager_instance = SecureKeyManager(base_dir)
    
    return _manager_instance


def encrypt_api_key(plain_key: str, base_dir: Optional[str] = None) -> str:
    """Encrypt an API key."""
    return get_manager(base_dir).encrypt_key(plain_key)


def decrypt_api_key(encrypted_key: str, base_dir: Optional[str] = None) -> Optional[str]:
    """Decrypt an API key."""
    return get_manager(base_dir).decrypt_key(encrypted_key)


def migrate_env_keys(env_path: str, base_dir: Optional[str] = None) -> bool:
    """Migrate plain-text API keys in .env to encrypted format."""
    return get_manager(base_dir).migrate_plain_key_to_encrypted(env_path)


def is_key_encrypted(key_value: str) -> bool:
    """Check if a key value is encrypted."""
    return key_value.startswith(SecureKeyManager.ENCRYPTED_PREFIX) if key_value else False
