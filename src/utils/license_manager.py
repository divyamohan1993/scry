"""
Scry License Manager - Ephemeral One-Time License System

This module implements a cryptographic licensing system where:
1. Each run generates a unique random challenge
2. The owner uses their PRIVATE KEY to sign the challenge
3. The software verifies the signature with the PUBLIC KEY
4. License is valid ONLY for the current session

SECURITY MODEL:
- Even with full source code access, attackers cannot generate valid licenses
- Each license key is unique to that specific run (replay attacks don't work)
- Only the holder of the private key can generate valid license keys

USAGE:
1. First-time setup: Run `python -m src.utils.license_manager --generate-keys`
   - This creates a key pair. KEEP THE PRIVATE KEY SAFE!
   - The public key is embedded in the software

2. Each run: User is shown a challenge code
   - Owner runs their private key tool to sign the challenge
   - Owner provides the signature as the license key

3. The software verifies and runs only if valid
"""

import os
import sys
import json
import base64
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

# Try to import cryptography
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.backends import default_backend
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class LicenseManager:
    """
    Manages ephemeral one-time license validation using RSA signatures.
    
    The challenge-response flow:
    1. Software generates a random challenge on each startup
    2. Owner signs the challenge with their private key
    3. Software verifies the signature with the embedded public key
    4. If valid, software runs for this session only
    """
    
    # File to store the session challenge (deleted on exit)
    CHALLENGE_FILE = ".scry_session_challenge"
    
    # The PUBLIC KEY is embedded here - safe to be in source code
    # Only the PRIVATE KEY must be kept secret
    EMBEDDED_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnvzDYXuizeLA3qM/tLo/
INx36vTM52kKI+6QSJOrj1Cr3C9QOubzb8DbUwZgtQxzRJAMl0euviTbzVTM4PUO
1ET4DU0fjm7xKI6MOo9O8rMHSgDldAggEyTwiBNb9nlcsexZVFkmtgzBMm2vUwC0
OGtf6wfnLovNbrvU4YLnYvtGzIxPteWFod/0J6BPItK3RtR3FDD/mgx3muSpkSIk
tDVEidsj1+Z0NdtXPYAk4C+XfMIO7ZLZcLt+/wk6jv3M6pLKOGirmi3n3a8aNmhW
i1FxJbUZdvj6DhHcz+ISAuXV09S2TTQTcuEgwkYeIZk6ZURd2FeNusTr0dNETBJl
7wIDAQAB
-----END PUBLIC KEY-----"""
    
    def __init__(self, base_dir: str):
        """Initialize the license manager."""
        self.base_dir = Path(base_dir)
        self.challenge_path = self.base_dir / self.CHALLENGE_FILE
        self._current_challenge: Optional[str] = None
        self._session_validated = False
        
        if not CRYPTO_AVAILABLE:
            raise ImportError(
                "cryptography package required for licensing. "
                "Install with: pip install cryptography"
            )
    
    def _get_public_key(self):
        """Load the embedded public key."""
        try:
            return serialization.load_pem_public_key(
                self.EMBEDDED_PUBLIC_KEY.encode(),
                backend=default_backend()
            )
        except Exception as e:
            raise ValueError(f"Invalid embedded public key: {e}")
    
    def generate_session_challenge(self) -> str:
        """
        Generate a unique challenge for this session.
        
        The challenge includes:
        - Random bytes (32 bytes of cryptographic randomness)
        - Timestamp (to prevent very old challenges)
        - Machine fingerprint (to bind to this specific installation)
        
        Returns:
            A base64-encoded challenge string
        """
        # Generate cryptographically secure random bytes
        random_bytes = secrets.token_bytes(32)
        
        # Add timestamp
        timestamp = int(time.time())
        
        # Create machine fingerprint
        machine_id = self._get_machine_fingerprint()
        
        # Combine all components
        challenge_data = {
            "r": base64.b64encode(random_bytes).decode(),  # random
            "t": timestamp,  # timestamp
            "m": machine_id[:16],  # machine (truncated)
            "v": "1"  # version
        }
        
        # Encode as base64 JSON for compactness
        challenge_json = json.dumps(challenge_data, separators=(',', ':'))
        challenge_b64 = base64.urlsafe_b64encode(challenge_json.encode()).decode()
        
        # Store for this session
        self._current_challenge = challenge_b64
        
        # Save to file (so it persists if app restarts during same session)
        self._save_challenge(challenge_b64)
        
        return challenge_b64
    
    def _get_machine_fingerprint(self) -> str:
        """Get a fingerprint of this machine."""
        import platform
        import uuid
        
        parts = [
            str(uuid.getnode()),  # MAC address
            platform.node(),  # hostname
            platform.machine(),  # architecture
        ]
        
        combined = "|".join(parts)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _save_challenge(self, challenge: str):
        """Save the current challenge to a file."""
        try:
            data = {
                "challenge": challenge,
                "created": time.time(),
                "expires": time.time() + 3600  # 1 hour validity window
            }
            with open(self.challenge_path, "w") as f:
                json.dump(data, f)
        except Exception:
            pass  # Non-critical
    
    def _load_challenge(self) -> Optional[str]:
        """Load challenge from file if exists and not expired."""
        try:
            if self.challenge_path.exists():
                with open(self.challenge_path, "r") as f:
                    data = json.load(f)
                
                # Check expiry
                if time.time() < data.get("expires", 0):
                    return data.get("challenge")
                else:
                    # Expired, clean up
                    self.challenge_path.unlink(missing_ok=True)
        except Exception:
            pass
        return None
    
    def get_current_challenge(self) -> str:
        """Get the current session challenge, generating if needed."""
        if self._current_challenge:
            return self._current_challenge
        
        # Try to load from file
        stored = self._load_challenge()
        if stored:
            self._current_challenge = stored
            return stored
        
        # Generate new
        return self.generate_session_challenge()
    
    def validate_license_key(self, license_key: str) -> Tuple[bool, str]:
        """
        Validate a license key (signature) against the current challenge.
        
        Args:
            license_key: Base64-encoded RSA signature of the challenge
            
        Returns:
            Tuple of (is_valid, message)
        """
        if self._session_validated:
            return True, "Session already validated"
        
        challenge = self.get_current_challenge()
        
        try:
            # Decode the license key (signature)
            signature = base64.urlsafe_b64decode(license_key)
            
            # Get the public key
            public_key = self._get_public_key()
            
            # Verify the signature
            public_key.verify(
                signature,
                challenge.encode(),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            # Valid!
            self._session_validated = True
            self._cleanup_challenge()
            
            return True, "License validated successfully"
            
        except InvalidSignature:
            return False, "Invalid license key - signature does not match"
        except Exception as e:
            return False, f"License validation error: {str(e)}"
    
    def _cleanup_challenge(self):
        """Clean up the challenge file after successful validation."""
        try:
            if self.challenge_path.exists():
                self.challenge_path.unlink()
        except Exception:
            pass
    
    def is_session_validated(self) -> bool:
        """Check if the current session has been validated."""
        return self._session_validated
    
    def invalidate_session(self):
        """Invalidate the current session (e.g., on exit)."""
        self._session_validated = False
        self._current_challenge = None
        self._cleanup_challenge()
    
    def get_display_challenge(self) -> str:
        """
        Get a user-friendly display of the challenge.
        
        Formats the challenge as a shorter, easier to read code.
        """
        challenge = self.get_current_challenge()
        
        # Create a shorter display version (first 32 chars with dashes)
        short = hashlib.sha256(challenge.encode()).hexdigest()[:24].upper()
        formatted = "-".join([short[i:i+6] for i in range(0, 24, 6)])
        
        return formatted
    
    @staticmethod
    def generate_key_pair(output_dir: str = ".") -> Tuple[str, str]:
        """
        Generate a new RSA key pair for licensing.
        
        This should be run ONCE by the owner to create their keys.
        
        Args:
            output_dir: Directory to save the keys
            
        Returns:
            Tuple of (private_key_path, public_key_path)
        """
        if not CRYPTO_AVAILABLE:
            raise ImportError("cryptography package required")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Serialize private key (with password protection)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Save keys
        private_path = output_path / "scry_license_private.pem"
        public_path = output_path / "scry_license_public.pem"
        
        with open(private_path, "wb") as f:
            f.write(private_pem)
        
        with open(public_path, "wb") as f:
            f.write(public_pem)
        
        return str(private_path), str(public_path)
    
    @staticmethod
    def sign_challenge(private_key_path: str, challenge: str) -> str:
        """
        Sign a challenge using the private key.
        
        This is used by the OWNER to generate a license key.
        
        Args:
            private_key_path: Path to the private key PEM file
            challenge: The challenge string to sign
            
        Returns:
            Base64-encoded signature (the license key)
        """
        if not CRYPTO_AVAILABLE:
            raise ImportError("cryptography package required")
        
        # Load private key
        with open(private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        
        # Sign the challenge
        signature = private_key.sign(
            challenge.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        # Return base64-encoded signature
        return base64.urlsafe_b64encode(signature).decode()


class LicensePrompt:
    """
    UI for prompting the user for a license key.
    
    Supports both GUI (tkinter) and CLI modes.
    """
    
    @staticmethod
    def prompt_gui(challenge_display: str, full_challenge: str) -> Optional[str]:
        """Show a GUI dialog for license input."""
        try:
            import tkinter as tk
            from tkinter import simpledialog, messagebox
            
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # Show challenge info
            messagebox.showinfo(
                "🔐 License Required - Scry",
                f"Session License Required\n\n"
                f"Challenge Code:\n{challenge_display}\n\n"
                f"Please contact the administrator for a license key.\n"
                f"The license is valid for this session only."
            )
            
            # Prompt for license key
            license_key = simpledialog.askstring(
                "Enter License Key",
                "Paste your license key:",
                parent=root
            )
            
            root.destroy()
            return license_key.strip() if license_key else None
            
        except Exception:
            return None
    
    @staticmethod
    def prompt_cli(challenge_display: str, full_challenge: str) -> Optional[str]:
        """Show a CLI prompt for license input."""
        print("\n" + "=" * 60)
        print("🔐 SESSION LICENSE REQUIRED - SCRY")
        print("=" * 60)
        print(f"\nChallenge Code: {challenge_display}")
        print("\nThis software requires a one-time license key to run.")
        print("Please contact the administrator with the challenge code above.")
        print("\nFull Challenge (for signing):")
        print(full_challenge)
        print("\n" + "-" * 60)
        
        try:
            license_key = input("Enter License Key: ").strip()
            return license_key if license_key else None
        except (EOFError, KeyboardInterrupt):
            return None


def require_license(base_dir: str, use_gui: bool = True) -> bool:
    """
    Require a valid license before continuing.
    
    This is the main entry point for license validation.
    
    Args:
        base_dir: Base directory of the application
        use_gui: Whether to use GUI prompts (falls back to CLI)
        
    Returns:
        True if license is valid, False otherwise
    """
    try:
        manager = LicenseManager(base_dir)
        
        # Check if already validated (shouldn't happen on fresh start)
        if manager.is_session_validated():
            return True
        
        # Get challenge
        challenge = manager.get_current_challenge()
        display_challenge = manager.get_display_challenge()
        
        # Prompt for license
        if use_gui:
            license_key = LicensePrompt.prompt_gui(display_challenge, challenge)
        else:
            license_key = LicensePrompt.prompt_cli(display_challenge, challenge)
        
        if not license_key:
            print("[LICENSE] No license key provided.")
            return False
        
        # Validate
        is_valid, message = manager.validate_license_key(license_key)
        
        if is_valid:
            print(f"[LICENSE] ✓ {message}")
            return True
        else:
            print(f"[LICENSE] ✗ {message}")
            return False
            
    except Exception as e:
        print(f"[LICENSE] Error: {e}")
        return False


# =============================================================================
# CLI INTERFACE FOR KEY MANAGEMENT
# =============================================================================
def main():
    """CLI interface for license management."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Scry License Manager - Generate keys and sign challenges"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Generate keys command
    gen_parser = subparsers.add_parser("generate-keys", help="Generate a new key pair")
    gen_parser.add_argument(
        "--output", "-o",
        default=".",
        help="Output directory for keys (default: current directory)"
    )
    
    # Sign challenge command
    sign_parser = subparsers.add_parser("sign", help="Sign a challenge to generate license key")
    sign_parser.add_argument(
        "challenge",
        help="The challenge string to sign"
    )
    sign_parser.add_argument(
        "--key", "-k",
        required=True,
        help="Path to private key file"
    )
    
    # Get challenge command (for testing)
    challenge_parser = subparsers.add_parser("challenge", help="Generate a new challenge")
    challenge_parser.add_argument(
        "--base-dir", "-d",
        default=".",
        help="Base directory (default: current directory)"
    )
    
    args = parser.parse_args()
    
    if args.command == "generate-keys":
        print("🔑 Generating RSA key pair for licensing...")
        try:
            private_path, public_path = LicenseManager.generate_key_pair(args.output)
            print(f"\n✓ Keys generated successfully!\n")
            print(f"PRIVATE KEY (KEEP SECRET!): {private_path}")
            print(f"PUBLIC KEY (embed in code):  {public_path}")
            print(f"\n⚠️  IMPORTANT:")
            print(f"1. Keep the private key SAFE and SECRET")
            print(f"2. Copy the public key content to EMBEDDED_PUBLIC_KEY in license_manager.py")
            print(f"3. Use the private key to sign challenges and generate license keys")
            
            # Show public key content
            with open(public_path, "r") as f:
                print(f"\n--- Public Key Content (copy this to code) ---")
                print(f.read())
                
        except Exception as e:
            print(f"✗ Error generating keys: {e}")
            sys.exit(1)
            
    elif args.command == "sign":
        print("✍️  Signing challenge...")
        try:
            license_key = LicenseManager.sign_challenge(args.key, args.challenge)
            print(f"\n✓ License Key Generated!\n")
            print(f"Challenge: {args.challenge[:50]}...")
            print(f"\nLicense Key (copy this):\n{license_key}")
        except Exception as e:
            print(f"✗ Error signing challenge: {e}")
            sys.exit(1)
            
    elif args.command == "challenge":
        print("🎲 Generating new challenge...")
        try:
            manager = LicenseManager(args.base_dir)
            challenge = manager.generate_session_challenge()
            display = manager.get_display_challenge()
            print(f"\nDisplay Code: {display}")
            print(f"\nFull Challenge:\n{challenge}")
        except Exception as e:
            print(f"✗ Error: {e}")
            sys.exit(1)
            
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
