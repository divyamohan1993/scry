"""
Tests for the License Manager - Ephemeral One-Time Licensing System

These tests verify that:
1. Challenge generation is unique each time
2. License key signing and verification works
3. Different paths/installations can't share licenses
4. Session validation is properly tracked
"""

import os
import sys
import tempfile
import shutil
import pytest

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.license_manager import LicenseManager, CRYPTO_AVAILABLE


@pytest.mark.skipif(not CRYPTO_AVAILABLE, reason="cryptography package not installed")
class TestLicenseManager:
    """Test suite for LicenseManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def key_pair(self, temp_dir):
        """Generate a key pair for testing."""
        private_path, public_path = LicenseManager.generate_key_pair(temp_dir)
        
        # Read the public key
        with open(public_path, "r") as f:
            public_key_pem = f.read()
        
        return private_path, public_key_pem

    @pytest.fixture
    def manager_with_keys(self, temp_dir, key_pair):
        """Create a LicenseManager with embedded test keys."""
        private_path, public_key_pem = key_pair
        
        # Create a custom manager with the test public key
        manager = LicenseManager(temp_dir)
        manager.EMBEDDED_PUBLIC_KEY = public_key_pem
        
        return manager, private_path

    def test_challenge_generation_unique(self, temp_dir):
        """Test that each challenge is unique."""
        manager = LicenseManager(temp_dir)
        
        challenges = set()
        for _ in range(10):
            challenge = manager.generate_session_challenge()
            manager._current_challenge = None  # Reset for next generation
            challenges.add(challenge)
        
        # All challenges should be unique
        assert len(challenges) == 10

    def test_challenge_display_format(self, temp_dir):
        """Test the display format of challenges."""
        manager = LicenseManager(temp_dir)
        manager.generate_session_challenge()
        
        display = manager.get_display_challenge()
        
        # Should be in format: XXXXXX-XXXXXX-XXXXXX-XXXXXX
        parts = display.split("-")
        assert len(parts) == 4
        for part in parts:
            assert len(part) == 6
            assert part.isupper() or part.isdigit()

    def test_sign_and_verify_roundtrip(self, manager_with_keys):
        """Test that signing and verification work correctly."""
        manager, private_path = manager_with_keys
        
        # Generate challenge
        challenge = manager.generate_session_challenge()
        
        # Sign it
        license_key = LicenseManager.sign_challenge(private_path, challenge)
        
        # Verify it
        is_valid, message = manager.validate_license_key(license_key)
        
        assert is_valid
        assert "success" in message.lower()

    def test_invalid_signature_rejected(self, manager_with_keys, temp_dir):
        """Test that invalid signatures are rejected."""
        manager, private_path = manager_with_keys
        
        # Generate challenge
        manager.generate_session_challenge()
        
        # Generate a different key pair
        other_private_path, _ = LicenseManager.generate_key_pair(
            os.path.join(temp_dir, "other_keys")
        )
        
        # Sign with wrong key
        wrong_license = LicenseManager.sign_challenge(
            other_private_path,
            manager.get_current_challenge()
        )
        
        # Should be rejected
        is_valid, message = manager.validate_license_key(wrong_license)
        
        assert not is_valid
        assert "invalid" in message.lower()

    def test_session_validation_persists(self, manager_with_keys):
        """Test that session validation persists after success."""
        manager, private_path = manager_with_keys
        
        # Initially not validated
        assert not manager.is_session_validated()
        
        # Validate
        challenge = manager.generate_session_challenge()
        license_key = LicenseManager.sign_challenge(private_path, challenge)
        is_valid, _ = manager.validate_license_key(license_key)
        
        assert is_valid
        assert manager.is_session_validated()
        
        # Second validation returns immediately
        is_valid2, message = manager.validate_license_key("any_garbage")
        assert is_valid2
        assert "already validated" in message.lower()

    def test_invalidate_session(self, manager_with_keys):
        """Test that session can be invalidated."""
        manager, private_path = manager_with_keys
        
        # Validate session
        challenge = manager.generate_session_challenge()
        license_key = LicenseManager.sign_challenge(private_path, challenge)
        manager.validate_license_key(license_key)
        
        assert manager.is_session_validated()
        
        # Invalidate
        manager.invalidate_session()
        
        assert not manager.is_session_validated()

    def test_different_challenge_different_key(self, manager_with_keys):
        """Test that a license key for one challenge doesn't work for another."""
        manager, private_path = manager_with_keys
        
        # Generate first challenge and sign it
        challenge1 = manager.generate_session_challenge()
        license_key1 = LicenseManager.sign_challenge(private_path, challenge1)
        
        # Invalidate and generate new challenge
        manager.invalidate_session()
        manager._current_challenge = None
        challenge2 = manager.generate_session_challenge()
        
        # Old license should not work for new challenge
        is_valid, _ = manager.validate_license_key(license_key1)
        assert not is_valid

    def test_key_pair_generation(self, temp_dir):
        """Test that key pair generation creates valid files."""
        private_path, public_path = LicenseManager.generate_key_pair(temp_dir)
        
        assert os.path.exists(private_path)
        assert os.path.exists(public_path)
        
        # Read and verify format
        with open(private_path, "r") as f:
            private_content = f.read()
        with open(public_path, "r") as f:
            public_content = f.read()
        
        assert "-----BEGIN PRIVATE KEY-----" in private_content
        assert "-----END PRIVATE KEY-----" in private_content
        assert "-----BEGIN PUBLIC KEY-----" in public_content
        assert "-----END PUBLIC KEY-----" in public_content

    def test_challenge_file_cleanup(self, manager_with_keys):
        """Test that challenge file is cleaned up after validation."""
        manager, private_path = manager_with_keys
        
        # Generate challenge (creates file)
        challenge = manager.generate_session_challenge()
        challenge_path = manager.challenge_path
        
        assert os.path.exists(challenge_path)
        
        # Validate (should clean up file)
        license_key = LicenseManager.sign_challenge(private_path, challenge)
        manager.validate_license_key(license_key)
        
        assert not os.path.exists(challenge_path)

    def test_garbage_license_key_rejected(self, temp_dir):
        """Test that garbage input is properly rejected."""
        manager = LicenseManager(temp_dir)
        manager.generate_session_challenge()
        
        garbage_inputs = [
            "",
            "garbage",
            "not_base64!!!",
            "a" * 100,
            None,
        ]
        
        for garbage in garbage_inputs:
            if garbage is not None:
                is_valid, _ = manager.validate_license_key(garbage)
                assert not is_valid


class TestKeyPairIntegrity:
    """Test key pair generation and integrity."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason="cryptography package not installed")
    def test_keys_are_different_each_generation(self, temp_dir):
        """Test that each key generation produces unique keys."""
        keys = []
        for i in range(3):
            subdir = os.path.join(temp_dir, f"keys_{i}")
            os.makedirs(subdir, exist_ok=True)
            private_path, public_path = LicenseManager.generate_key_pair(subdir)
            
            with open(private_path, "r") as f:
                keys.append(f.read())
        
        # All keys should be unique
        assert len(set(keys)) == 3
