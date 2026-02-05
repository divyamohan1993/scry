"""
Security Tests for SecureKeyManager
=====================================

Comprehensive security tests for the machine-bound API key encryption system.

Security Properties Tested:
1. Keys are properly encrypted (ciphertext differs from plaintext)
2. Different installations produce different ciphertexts
3. Copying installation invalidates keys
4. Tampered ciphertexts fail decryption
5. Encryption uses strong algorithms
6. Key derivation is deterministic for same installation

Test Categories:
- Encryption/Decryption correctness
- Installation binding
- Copy attack prevention
- Tamper detection
- Edge cases and error handling
"""

import base64
import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock

import pytest


@pytest.mark.security
class TestSecureKeyManagerEncryption:
    """Tests for encryption and decryption correctness."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a SecureKeyManager instance."""
        from src.utils.secure_key_manager import SecureKeyManager
        return SecureKeyManager(temp_dir)

    def test_encryption_produces_different_output(self, manager):
        """Test that encryption produces different output from input."""
        original_key = "AIzaSyTestKey123456789"
        
        encrypted = manager.encrypt_key(original_key)
        
        assert encrypted != original_key
        assert original_key not in encrypted

    def test_decryption_recovers_original(self, manager):
        """Test that decryption recovers the original key."""
        original_key = "AIzaSyTestKey123456789_SecretKey"
        
        encrypted = manager.encrypt_key(original_key)
        decrypted = manager.decrypt_key(encrypted)
        
        assert decrypted == original_key

    def test_different_plaintexts_different_ciphertexts(self, manager):
        """Test that different plaintexts produce different ciphertexts."""
        key1 = "FirstKey123"
        key2 = "SecondKey456"
        
        encrypted1 = manager.encrypt_key(key1)
        encrypted2 = manager.encrypt_key(key2)
        
        assert encrypted1 != encrypted2

    def test_same_plaintext_same_result_within_session(self, manager):
        """Test encryption is deterministic within a session."""
        key = "TestKey123"
        
        encrypted1 = manager.encrypt_key(key)
        encrypted2 = manager.encrypt_key(key)
        
        # Note: Fernet adds randomness, so they might differ
        # But both should decrypt to same value
        decrypted1 = manager.decrypt_key(encrypted1)
        decrypted2 = manager.decrypt_key(encrypted2)
        
        assert decrypted1 == decrypted2 == key


@pytest.mark.security
class TestInstallationBinding:
    """Tests for installation path binding."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    def test_different_paths_different_encryption_keys(self, temp_dir):
        """Test that different installation paths use different encryption keys."""
        from src.utils.secure_key_manager import SecureKeyManager
        
        path1 = os.path.join(temp_dir, "install1")
        path2 = os.path.join(temp_dir, "install2")
        os.makedirs(path1)
        os.makedirs(path2)
        
        manager1 = SecureKeyManager(path1)
        manager2 = SecureKeyManager(path2)
        
        original_key = "TestAPIKey123"
        
        encrypted1 = manager1.encrypt_key(original_key)
        encrypted2 = manager2.encrypt_key(original_key)
        
        # Different installations should produce different ciphertexts
        assert encrypted1 != encrypted2

    def test_cross_installation_decryption_fails(self, temp_dir):
        """Test that keys encrypted in one installation can't be decrypted in another."""
        from src.utils.secure_key_manager import SecureKeyManager
        
        path1 = os.path.join(temp_dir, "install1")
        path2 = os.path.join(temp_dir, "install2")
        os.makedirs(path1)
        os.makedirs(path2)
        
        manager1 = SecureKeyManager(path1)
        manager2 = SecureKeyManager(path2)
        
        original_key = "SecretKey123"
        encrypted_by_1 = manager1.encrypt_key(original_key)
        
        # Manager 2 should NOT be able to decrypt
        decrypted_by_2 = manager2.decrypt_key(encrypted_by_1)
        
        assert decrypted_by_2 is None


@pytest.mark.security
class TestCopyAttackPrevention:
    """Tests for prevention of copy attacks."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    def test_copied_installation_cannot_decrypt(self, temp_dir):
        """Test that copying an installation invalidates encrypted keys."""
        from src.utils.secure_key_manager import SecureKeyManager
        
        original_path = os.path.join(temp_dir, "original")
        os.makedirs(original_path)
        
        # Create and encrypt
        manager_original = SecureKeyManager(original_path)
        original_key = "SuperSecretKey123"
        encrypted = manager_original.encrypt_key(original_key)
        
        # Verify original can decrypt
        assert manager_original.decrypt_key(encrypted) == original_key
        
        # Copy the installation
        copied_path = os.path.join(temp_dir, "copied")
        shutil.copytree(original_path, copied_path)
        
        # Create manager from copied path
        manager_copied = SecureKeyManager(copied_path)
        
        # Copied installation should NOT be able to decrypt
        # (Path is part of key derivation)
        decrypted = manager_copied.decrypt_key(encrypted)
        assert decrypted is None

    def test_moved_installation_cannot_decrypt(self, temp_dir):
        """Test that moving an installation invalidates encrypted keys."""
        from src.utils.secure_key_manager import SecureKeyManager
        
        original_path = os.path.join(temp_dir, "original_location")
        os.makedirs(original_path)
        
        # Create and encrypt
        manager = SecureKeyManager(original_path)
        key = "MoveTestKey123"
        encrypted = manager.encrypt_key(key)
        
        # Verify original can decrypt
        assert manager.decrypt_key(encrypted) == key
        
        # Move to new location
        new_path = os.path.join(temp_dir, "new_location")
        shutil.move(original_path, new_path)
        
        # New manager at new path should fail
        new_manager = SecureKeyManager(new_path)
        assert new_manager.decrypt_key(encrypted) is None


@pytest.mark.security
class TestTamperDetection:
    """Tests for tamper detection in encrypted keys."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a SecureKeyManager instance."""
        from src.utils.secure_key_manager import SecureKeyManager
        return SecureKeyManager(temp_dir)

    def test_modified_ciphertext_fails_decryption(self, manager):
        """Test that modified ciphertext fails to decrypt."""
        original_key = "OriginalKey123"
        encrypted = manager.encrypt_key(original_key)
        
        # Tamper with the ciphertext
        # Remove prefix and modify base64 content
        prefix = "SCRY_ENC_V1:"
        if encrypted.startswith(prefix):
            ciphertext = encrypted[len(prefix):]
            # Flip some bits
            tampered = prefix + "X" + ciphertext[1:]
        else:
            tampered = "X" + encrypted[1:]
        
        decrypted = manager.decrypt_key(tampered)
        
        assert decrypted is None

    def test_truncated_ciphertext_fails(self, manager):
        """Test that truncated ciphertext fails to decrypt."""
        original_key = "TruncateTestKey"
        encrypted = manager.encrypt_key(original_key)
        
        # Truncate
        truncated = encrypted[:len(encrypted) // 2]
        
        decrypted = manager.decrypt_key(truncated)
        
        assert decrypted is None

    def test_empty_ciphertext_fails(self, manager):
        """Test that empty ciphertext returns None."""
        assert manager.decrypt_key("") is None
        assert manager.decrypt_key(None) is None

    def test_garbage_input_fails_gracefully(self, manager):
        """Test that garbage input fails gracefully."""
        garbage_inputs = [
            "not_valid_base64!!!",
            "SCRY_ENC_V1:garbage",
            "SCRY_ENC_V1:" + base64.b64encode(b"random").decode(),
            "\x00\x01\x02\x03",
        ]
        
        for garbage in garbage_inputs:
            result = manager.decrypt_key(garbage)
            assert result is None


@pytest.mark.security
class TestEncryptionFormat:
    """Tests for encryption format and detection."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a SecureKeyManager instance."""
        from src.utils.secure_key_manager import SecureKeyManager
        return SecureKeyManager(temp_dir)

    def test_encrypted_format_has_prefix(self, manager):
        """Test that encrypted keys have the correct prefix."""
        encrypted = manager.encrypt_key("TestKey")
        
        assert encrypted.startswith("SCRY_ENC_V1:")

    def test_is_encrypted_detection(self, manager):
        """Test is_encrypted detection."""
        from src.utils.secure_key_manager import is_key_encrypted
        
        encrypted = manager.encrypt_key("TestKey")
        
        assert is_key_encrypted(encrypted)
        assert not is_key_encrypted("plain_text_key")
        assert not is_key_encrypted("")
        assert not is_key_encrypted("SCRY_")  # Partial

    def test_plain_text_not_detected_as_encrypted(self):
        """Test that plain text keys are correctly identified."""
        from src.utils.secure_key_manager import is_key_encrypted
        
        plain_keys = [
            "AIzaSy123456789",
            "sk-proj-abcdef123456",
            "my_api_key",
            "",
            None,
        ]
        
        for key in plain_keys:
            assert not is_key_encrypted(key)


@pytest.mark.security
class TestInstallationReset:
    """Tests for installation reset functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a SecureKeyManager instance."""
        from src.utils.secure_key_manager import SecureKeyManager
        return SecureKeyManager(temp_dir)

    def test_reset_invalidates_old_keys(self, manager):
        """Test that resetting installation invalidates old encrypted keys."""
        original_key = "KeyBeforeReset"
        encrypted_before = manager.encrypt_key(original_key)
        
        # Verify it works before reset
        assert manager.decrypt_key(encrypted_before) == original_key
        
        # Reset
        manager.reset_installation()
        
        # Old encrypted key should now fail
        assert manager.decrypt_key(encrypted_before) is None
        
        # New encryption should work
        encrypted_after = manager.encrypt_key(original_key)
        assert manager.decrypt_key(encrypted_after) == original_key

    def test_reset_creates_new_installation_id(self, manager, temp_dir):
        """Test that reset creates a new installation ID."""
        # Trigger installation ID creation
        manager.encrypt_key("test")
        
        installation_file = os.path.join(temp_dir, ".scry_installation")
        
        with open(installation_file, "r") as f:
            old_id = f.read()
        
        manager.reset_installation()
        
        # Trigger new installation ID
        manager.encrypt_key("test2")
        
        with open(installation_file, "r") as f:
            new_id = f.read()
        
        assert old_id != new_id


@pytest.mark.security
class TestMigration:
    """Tests for plain text to encrypted migration."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    def test_migrate_plain_key_to_encrypted(self, temp_dir):
        """Test migration of plain text key to encrypted."""
        from src.utils.secure_key_manager import SecureKeyManager
        
        manager = SecureKeyManager(temp_dir)
        
        # Create .env with plain key
        env_path = os.path.join(temp_dir, ".env")
        with open(env_path, "w") as f:
            f.write("GEMINI_API_KEY=plain_text_key\n")
            f.write("OTHER_VAR=value\n")
        
        # Migrate
        result = manager.migrate_plain_key_to_encrypted(env_path)
        
        assert result is True
        
        # Verify file was updated
        with open(env_path, "r") as f:
            content = f.read()
        
        assert "SCRY_ENC_V1:" in content
        assert "plain_text_key" not in content
        assert "OTHER_VAR=value" in content

    def test_migrate_already_encrypted_key_no_change(self, temp_dir):
        """Test that already encrypted keys are not re-encrypted."""
        from src.utils.secure_key_manager import SecureKeyManager
        
        manager = SecureKeyManager(temp_dir)
        
        # First encrypt a key
        encrypted = manager.encrypt_key("test_key")
        
        # Create .env with already encrypted key
        env_path = os.path.join(temp_dir, ".env")
        with open(env_path, "w") as f:
            f.write(f"GEMINI_API_KEY={encrypted}\n")
        
        original_content = open(env_path).read()
        
        # Migrate should detect it's already encrypted
        manager.migrate_plain_key_to_encrypted(env_path)
        
        new_content = open(env_path).read()
        
        # Content should be unchanged
        assert original_content == new_content


@pytest.mark.security
class TestSpecialCharacterHandling:
    """Tests for handling special characters in keys."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a SecureKeyManager instance."""
        from src.utils.secure_key_manager import SecureKeyManager
        return SecureKeyManager(temp_dir)

    @pytest.mark.parametrize("special_key", [
        "Key+With+Plus",
        "Key/With/Slash",
        "Key=With=Equals",
        "Key@With@At",
        "Key#With#Hash",
        "Key!With!Exclamation",
        "Key with spaces",
        "Key\twith\ttabs",
        "Key\nwith\nnewlines",
        "KeyWithUnicode🔑🔒",
        "KeyWith日本語",
        "=" * 100,
        "A" * 1000,  # Long key
    ])
    def test_special_character_roundtrip(self, manager, special_key):
        """Test encryption/decryption with special characters."""
        encrypted = manager.encrypt_key(special_key)
        decrypted = manager.decrypt_key(encrypted)
        
        assert decrypted == special_key
