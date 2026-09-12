import pytest
from cryptography.fernet import InvalidToken

# Constants
TEST_BOT_ID = 12345
SECOND_BOT_ID = 67890
HEX_CHARS = "0123456789abcdef"
SHA256_HEX_LENGTH = 64
INVALID_TOKEN = "a" * SHA256_HEX_LENGTH


class TestCryptographer:
    def test_encrypt_returns_string(self, cryptographer):
        plaintext = "hello world"
        encrypted = cryptographer.encrypt(plaintext)

        assert isinstance(encrypted, str)
        assert encrypted != plaintext

    def test_decrypt_returns_original(self, cryptographer):
        plaintext = "hello world"
        encrypted = cryptographer.encrypt(plaintext)
        decrypted = cryptographer.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_different_each_time(self, cryptographer):
        plaintext = "same text"
        enc1 = cryptographer.encrypt(plaintext)
        enc2 = cryptographer.encrypt(plaintext)
        assert enc1 != enc2

    def test_decrypt_wrong_value_raises(self, cryptographer):
        encrypted = cryptographer.encrypt("correct text")
        wrong_token = encrypted[:-1] + ("x" if encrypted[-1] != "x" else "y")

        with pytest.raises(InvalidToken):
            cryptographer.decrypt(wrong_token)

    def test_generate_bot_secret_returns_hex_string(self, cryptographer):
        secret = cryptographer.generate_bot_secret(TEST_BOT_ID)

        assert isinstance(secret, str)
        assert len(secret) == SHA256_HEX_LENGTH  # SHA256 digest = 32 bytes = 64 hex chars
        assert all(c in HEX_CHARS for c in secret)

    def test_generate_bot_secret_deterministic(self, cryptographer):
        secret1 = cryptographer.generate_bot_secret(TEST_BOT_ID)
        secret2 = cryptographer.generate_bot_secret(TEST_BOT_ID)

        assert secret1 == secret2

    def test_generate_bot_secret_different_per_bot_id(self, cryptographer):
        secret1 = cryptographer.generate_bot_secret(TEST_BOT_ID)
        secret2 = cryptographer.generate_bot_secret(SECOND_BOT_ID)

        assert secret1 != secret2

    def test_verify_bot_secret_valid(self, cryptographer):
        valid_token = cryptographer.generate_bot_secret(TEST_BOT_ID)

        assert cryptographer.verify_bot_secret(valid_token, TEST_BOT_ID) is True

    def test_verify_bot_secret_invalid(self, cryptographer):
        assert cryptographer.verify_bot_secret(INVALID_TOKEN, TEST_BOT_ID) is False

    def test_verify_bot_secret_wrong_bot_id(self, cryptographer):
        secret = cryptographer.generate_bot_secret(TEST_BOT_ID)

        assert cryptographer.verify_bot_secret(secret, SECOND_BOT_ID) is False
