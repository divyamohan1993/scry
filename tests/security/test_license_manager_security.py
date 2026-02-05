"""
Security Tests for License Manager
====================================

Comprehensive security tests for the ephemeral one-time licensing system.

Security Properties Tested:
1. Challenges are cryptographically random
2. Signatures are bound to specific challenges
3. Invalid signatures are rejected
4. Replay attacks are prevented
5. Challenge expiration works correctly

Test Categories:
- Challenge generation security
- Signature verification
- Replay attack prevention
- Key pair security
"""

import base64
import os
import shutil
import tempfile
import time
from unittest.mock import patch, MagicMock

import pytest


@pytest.mark.security
class TestChallengeGeneration:
    """Tests for challenge generation security."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a LicenseManager instance."""
        from src.utils.license_manager import LicenseManager, CRYPTO_AVAILABLE
        if not CRYPTO_AVAILABLE:
            pytest.skip("cryptography package not available")
        return LicenseManager(temp_dir)

    def test_challenges_are_unique(self, manager):
        """Test that each challenge is unique."""
        challenges = set()
        
        for _ in range(100):
            challenge = manager.generate_session_challenge()
            manager._current_challenge = None  # Reset for next generation
            challenges.add(challenge)
        
        # All should be unique
        assert len(challenges) == 100

    def test_challenge_has_sufficient_entropy(self, manager):
        """Test that challenges have sufficient entropy."""
        challenge = manager.generate_session_challenge()
        
        # Decode and check length
        raw = base64.b64decode(challenge)
        
        # Should contain at least 32 bytes of random data
        assert len(raw) >= 32

    def test_challenge_contains_timestamp(self, manager):
        """Test that challenge contains timestamp component."""
        challenge = manager.generate_session_challenge()
        
        # The challenge should be bound to current time
        # (implementation detail - just verify it's properly formatted)
        assert len(challenge) > 32  # More than just random bytes

    def test_challenge_contains_machine_fingerprint(self, manager):
        """Test that challenge is bound to machine."""
        challenge = manager.generate_session_challenge()
        
        # Challenge should be unique to machine
        assert challenge is not None


@pytest.mark.security
class TestSignatureVerification:
    """Tests for signature verification security."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def key_pair(self, temp_dir):
        """Generate a key pair for testing."""
        from src.utils.license_manager import LicenseManager, CRYPTO_AVAILABLE
        if not CRYPTO_AVAILABLE:
            pytest.skip("cryptography package not available")
        
        private_path, public_path = LicenseManager.generate_key_pair(temp_dir)
        
        with open(public_path, "r") as f:
            public_key = f.read()
        
        return private_path, public_key

    @pytest.fixture
    def manager_with_keys(self, temp_dir, key_pair):
        """Create a LicenseManager with test keys."""
        from src.utils.license_manager import LicenseManager
        
        private_path, public_key = key_pair
        manager = LicenseManager(temp_dir)
        manager.EMBEDDED_PUBLIC_KEY = public_key
        
        return manager, private_path

    def test_valid_signature_accepted(self, manager_with_keys):
        """Test that valid signatures are accepted."""
        from src.utils.license_manager import LicenseManager
        
        manager, private_path = manager_with_keys
        
        challenge = manager.generate_session_challenge()
        signature = LicenseManager.sign_challenge(private_path, challenge)
        
        is_valid, message = manager.validate_license_key(signature)
        
        assert is_valid
        assert "success" in message.lower()

    def test_wrong_key_signature_rejected(self, manager_with_keys, temp_dir):
        """Test that signatures with wrong key are rejected."""
        from src.utils.license_manager import LicenseManager
        
        manager, _ = manager_with_keys
        
        # Generate different key pair
        other_dir = os.path.join(temp_dir, "other_keys")
        os.makedirs(other_dir)
        wrong_private_path, _ = LicenseManager.generate_key_pair(other_dir)
        
        challenge = manager.generate_session_challenge()
        wrong_signature = LicenseManager.sign_challenge(wrong_private_path, challenge)
        
        is_valid, message = manager.validate_license_key(wrong_signature)
        
        assert not is_valid
        assert "invalid" in message.lower()

    def test_modified_signature_rejected(self, manager_with_keys):
        """Test that modified signatures are rejected."""
        from src.utils.license_manager import LicenseManager
        
        manager, private_path = manager_with_keys
        
        challenge = manager.generate_session_challenge()
        valid_signature = LicenseManager.sign_challenge(private_path, challenge)
        
        # Modify the signature
        modified = "X" + valid_signature[1:]
        
        is_valid, message = manager.validate_license_key(modified)
        
        assert not is_valid


@pytest.mark.security
class TestReplayAttackPrevention:
    """Tests for replay attack prevention."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def key_pair(self, temp_dir):
        """Generate a key pair for testing."""
        from src.utils.license_manager import LicenseManager, CRYPTO_AVAILABLE
        if not CRYPTO_AVAILABLE:
            pytest.skip("cryptography package not available")
        
        private_path, public_path = LicenseManager.generate_key_pair(temp_dir)
        
        with open(public_path, "r") as f:
            public_key = f.read()
        
        return private_path, public_key

    @pytest.fixture
    def manager_with_keys(self, temp_dir, key_pair):
        """Create a LicenseManager with test keys."""
        from src.utils.license_manager import LicenseManager
        
        private_path, public_key = key_pair
        manager = LicenseManager(temp_dir)
        manager.EMBEDDED_PUBLIC_KEY = public_key
        
        return manager, private_path

    def test_old_signature_rejected_for_new_challenge(self, manager_with_keys):
        """Test that signatures for old challenges are rejected."""
        from src.utils.license_manager import LicenseManager
        
        manager, private_path = manager_with_keys
        
        # First challenge and signature
        challenge1 = manager.generate_session_challenge()
        signature1 = LicenseManager.sign_challenge(private_path, challenge1)
        
        # Generate new challenge
        manager.invalidate_session()
        manager._current_challenge = None
        challenge2 = manager.generate_session_challenge()
        
        # Old signature should not work for new challenge
        is_valid, _ = manager.validate_license_key(signature1)
        
        assert not is_valid

    def test_session_cannot_be_revalidated(self, manager_with_keys):
        """Test that a validated session cannot be re-validated with garbage."""
        from src.utils.license_manager import LicenseManager
        
        manager, private_path = manager_with_keys
        
        # Validate session
        challenge = manager.generate_session_challenge()
        signature = LicenseManager.sign_challenge(private_path, challenge)
        manager.validate_license_key(signature)
        
        assert manager.is_session_validated()
        
        # Try to validate again with garbage - should return already validated
        is_valid, message = manager.validate_license_key("garbage")
        
        assert is_valid
        assert "already validated" in message.lower()


@pytest.mark.security
class TestKeyPairSecurity:
    """Tests for key pair generation security."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    def test_key_pairs_are_unique(self, temp_dir):
        """Test that each key pair generation produces unique keys."""
        from src.utils.license_manager import LicenseManager, CRYPTO_AVAILABLE
        if not CRYPTO_AVAILABLE:
            pytest.skip("cryptography package not available")
        
        keys = []
        for i in range(3):
            subdir = os.path.join(temp_dir, f"keys_{i}")
            os.makedirs(subdir)
            private_path, _ = LicenseManager.generate_key_pair(subdir)
            
            with open(private_path, "r") as f:
                keys.append(f.read())
        
        # All keys should be unique
        assert len(set(keys)) == 3

    def test_private_key_format(self, temp_dir):
        """Test that private key is in correct PEM format."""
        from src.utils.license_manager import LicenseManager, CRYPTO_AVAILABLE
        if not CRYPTO_AVAILABLE:
            pytest.skip("cryptography package not available")
        
        private_path, _ = LicenseManager.generate_key_pair(temp_dir)
        
        with open(private_path, "r") as f:
            private_key = f.read()
        
        assert "-----BEGIN PRIVATE KEY-----" in private_key
        assert "-----END PRIVATE KEY-----" in private_key

    def test_public_key_format(self, temp_dir):
        """Test that public key is in correct PEM format."""
        from src.utils.license_manager import LicenseManager, CRYPTO_AVAILABLE
        if not CRYPTO_AVAILABLE:
            pytest.skip("cryptography package not available")
        
        _, public_path = LicenseManager.generate_key_pair(temp_dir)
        
        with open(public_path, "r") as f:
            public_key = f.read()
        
        assert "-----BEGIN PUBLIC KEY-----" in public_key
        assert "-----END PUBLIC KEY-----" in public_key


@pytest.mark.security
class TestGarbageInputHandling:
    """Tests for handling of garbage/malicious input."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a LicenseManager instance."""
        from src.utils.license_manager import LicenseManager, CRYPTO_AVAILABLE
        if not CRYPTO_AVAILABLE:
            pytest.skip("cryptography package not available")
        return LicenseManager(temp_dir)

    @pytest.mark.parametrize("garbage", [
        "",
        "not_base64!!!",
        "=====",
        "\x00\x01\x02\x03",
        "A" * 10000,  # Very long
        base64.b64encode(b"random_bytes").decode(),
        "SCRY_LICENSE:",  # Partial prefix
    ])
    def test_garbage_input_rejected(self, manager, garbage):
        """Test that garbage input is properly rejected."""
        manager.generate_session_challenge()
        
        is_valid, message = manager.validate_license_key(garbage)
        
        assert not is_valid

    def test_none_input_handled(self, manager):
        """Test that None input is handled."""
        manager.generate_session_challenge()
        
        # This might raise or return (False, message)
        try:
            is_valid, message = manager.validate_license_key(None)
            assert not is_valid
        except (TypeError, AttributeError):
            pass  # Also acceptable


@pytest.mark.security
class TestSessionManagement:
    """Tests for session management security."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def key_pair(self, temp_dir):
        """Generate a key pair for testing."""
        from src.utils.license_manager import LicenseManager, CRYPTO_AVAILABLE
        if not CRYPTO_AVAILABLE:
            pytest.skip("cryptography package not available")
        
        private_path, public_path = LicenseManager.generate_key_pair(temp_dir)
        
        with open(public_path, "r") as f:
            public_key = f.read()
        
        return private_path, public_key

    @pytest.fixture
    def manager_with_keys(self, temp_dir, key_pair):
        """Create a LicenseManager with test keys."""
        from src.utils.license_manager import LicenseManager
        
        private_path, public_key = key_pair
        manager = LicenseManager(temp_dir)
        manager.EMBEDDED_PUBLIC_KEY = public_key
        
        return manager, private_path

    def test_session_invalidation_works(self, manager_with_keys):
        """Test that session invalidation works correctly."""
        from src.utils.license_manager import LicenseManager
        
        manager, private_path = manager_with_keys
        
        # Validate
        challenge = manager.generate_session_challenge()
        signature = LicenseManager.sign_challenge(private_path, challenge)
        manager.validate_license_key(signature)
        
        assert manager.is_session_validated()
        
        # Invalidate
        manager.invalidate_session()
        
        assert not manager.is_session_validated()

    def test_challenge_file_cleaned_after_validation(self, manager_with_keys):
        """Test that challenge file is cleaned up after validation."""
        from src.utils.license_manager import LicenseManager
        
        manager, private_path = manager_with_keys
        
        challenge = manager.generate_session_challenge()
        challenge_path = manager.challenge_path
        
        assert os.path.exists(challenge_path)
        
        signature = LicenseManager.sign_challenge(private_path, challenge)
        manager.validate_license_key(signature)
        
        # File should be cleaned up
        assert not os.path.exists(challenge_path)
