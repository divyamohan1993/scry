"""
Tests for the SecureKeyManager - Machine-Bound API Key Encryption

These tests verify that:
1. Keys are encrypted and decrypted correctly
2. Different installation paths produce different encryption keys
3. The encrypted format is properly detected
4. Invalid/copied installations fail decryption
"""

import os
import sys
import tempfile
import shutil
import pytest

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.secure_key_manager import SecureKeyManager, is_key_encrypted


class TestSecureKeyManager:
    """Test suite for SecureKeyManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a SecureKeyManager instance for testing."""
        return SecureKeyManager(temp_dir)

    def test_encrypt_decrypt_roundtrip(self, manager):
        """Test that encryption and decryption work correctly."""
        original_key = "AIzaSyTestKey123456789"
        
        encrypted = manager.encrypt_key(original_key)
        decrypted = manager.decrypt_key(encrypted)
        
        assert decrypted == original_key
        assert encrypted != original_key
        assert is_key_encrypted(encrypted)

    def test_encrypted_format_prefix(self, manager):
        """Test that encrypted keys have the correct prefix."""
        encrypted = manager.encrypt_key("test_key")
        
        assert encrypted.startswith("SCRY_ENC_V1:")
        assert is_key_encrypted(encrypted)

    def test_plain_text_not_detected_as_encrypted(self):
        """Test that plain text keys are not detected as encrypted."""
        plain_key = "AIzaSyTestKey123456789"
        
        assert not is_key_encrypted(plain_key)
        assert not is_key_encrypted("")
        assert not is_key_encrypted("SCRY_")  # Partial prefix

    def test_different_paths_different_keys(self, temp_dir):
        """Test that different installation paths produce different encryption."""
        path1 = os.path.join(temp_dir, "install1")
        path2 = os.path.join(temp_dir, "install2")
        
        os.makedirs(path1, exist_ok=True)
        os.makedirs(path2, exist_ok=True)
        
        manager1 = SecureKeyManager(path1)
        manager2 = SecureKeyManager(path2)
        
        original_key = "AIzaSyTestKey123456789"
        
        encrypted1 = manager1.encrypt_key(original_key)
        encrypted2 = manager2.encrypt_key(original_key)
        
        # Different paths should produce different encrypted values
        assert encrypted1 != encrypted2
        
        # Each manager can only decrypt its own encrypted key
        assert manager1.decrypt_key(encrypted1) == original_key
        assert manager2.decrypt_key(encrypted2) == original_key
        
        # Cross-decryption should fail
        assert manager1.decrypt_key(encrypted2) is None
        assert manager2.decrypt_key(encrypted1) is None

    def test_copy_invalidates_key(self, temp_dir):
        """Test that copying the installation invalidates existing keys."""
        original_path = os.path.join(temp_dir, "original")
        os.makedirs(original_path, exist_ok=True)
        
        # Create manager and encrypt a key
        manager_original = SecureKeyManager(original_path)
        original_key = "AIzaSyTestKey123456789"
        encrypted = manager_original.encrypt_key(original_key)
        
        # Verify decryption works
        assert manager_original.decrypt_key(encrypted) == original_key
        
        # Simulate copying - new installation path
        copied_path = os.path.join(temp_dir, "copied")
        shutil.copytree(original_path, copied_path)
        
        # Create manager from copied path
        manager_copied = SecureKeyManager(copied_path)
        
        # The copied installation should NOT be able to decrypt the key
        # (different path in key derivation)
        assert manager_copied.decrypt_key(encrypted) is None

    def test_empty_key_handling(self, manager):
        """Test handling of empty keys."""
        assert manager.encrypt_key("") == ""
        assert manager.decrypt_key("") is None
        assert manager.decrypt_key(None) is None

    def test_installation_id_created(self, manager, temp_dir):
        """Test that installation ID file is created."""
        # Trigger key derivation by encrypting
        manager.encrypt_key("test")
        
        installation_file = os.path.join(temp_dir, ".scry_installation")
        assert os.path.exists(installation_file)

    def test_validate_installation(self, manager, temp_dir):
        """Test installation validation."""
        # Before any operation
        is_valid, message = manager.validate_installation()
        
        # After encryption (which creates installation ID)
        manager.encrypt_key("test")
        is_valid, message = manager.validate_installation()
        assert is_valid
        assert "valid" in message.lower()

    def test_reset_installation(self, manager, temp_dir):
        """Test resetting the installation."""
        # Create installation
        encrypted = manager.encrypt_key("test_key")
        assert manager.decrypt_key(encrypted) == "test_key"
        
        # Reset
        manager.reset_installation()
        
        # After reset, a new installation ID is generated
        # So the old encrypted key should no longer work
        # (because the salt changed)
        # Note: This depends on implementation - in practice,
        # after reset, decrypt will fail because salt changed
        
        # Create new encrypted key with new salt
        new_encrypted = manager.encrypt_key("test_key")
        assert manager.decrypt_key(new_encrypted) == "test_key"
        
        # Old encrypted value should now fail
        assert manager.decrypt_key(encrypted) is None

    def test_migrate_plain_key_to_encrypted(self, manager, temp_dir):
        """Test migration of plain-text key to encrypted format."""
        # Create a mock .env file
        env_path = os.path.join(temp_dir, ".env")
        with open(env_path, "w") as f:
            f.write("GEMINI_API_KEY=plain_text_key\n")
            f.write("OTHER_VAR=value\n")
        
        # Migrate
        result = manager.migrate_plain_key_to_encrypted(env_path)
        assert result is True
        
        # Read back and verify
        with open(env_path, "r") as f:
            content = f.read()
        
        assert "SCRY_ENC_V1:" in content
        assert "plain_text_key" not in content
        assert "OTHER_VAR=value" in content

    def test_special_characters_in_key(self, manager):
        """Test handling of keys with special characters."""
        special_key = "AIzaSy+Test/Key=With+Special==Chars/"
        
        encrypted = manager.encrypt_key(special_key)
        decrypted = manager.decrypt_key(encrypted)
        
        assert decrypted == special_key

    def test_unicode_in_key(self, manager):
        """Test handling of unicode characters in keys."""
        unicode_key = "AIzaSy🔑Test🔒Key"
        
        encrypted = manager.encrypt_key(unicode_key)
        decrypted = manager.decrypt_key(encrypted)
        
        assert decrypted == unicode_key

    def test_long_key(self, manager):
        """Test handling of very long keys."""
        long_key = "A" * 1000
        
        encrypted = manager.encrypt_key(long_key)
        decrypted = manager.decrypt_key(encrypted)
        
        assert decrypted == long_key


class TestIsKeyEncrypted:
    """Test the is_key_encrypted utility function."""

    def test_encrypted_format(self):
        """Test detection of encrypted format."""
        assert is_key_encrypted("SCRY_ENC_V1:abc123")
        assert is_key_encrypted("SCRY_ENC_V1:")

    def test_plain_format(self):
        """Test detection of plain format."""
        assert not is_key_encrypted("AIzaSy123456789")
        assert not is_key_encrypted("some_plain_key")
        assert not is_key_encrypted("")
        assert not is_key_encrypted(None)

    def test_partial_prefix(self):
        """Test that partial prefixes are not detected."""
        assert not is_key_encrypted("SCRY_")
        assert not is_key_encrypted("SCRY_ENC_")
        assert not is_key_encrypted("SCRY_ENC_V1")
