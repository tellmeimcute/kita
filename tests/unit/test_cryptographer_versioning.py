from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr

from core.cryptographer import Cryptographer


def _key() -> str:
    return Fernet.generate_key().decode()


@pytest.fixture
def rotating_cryptographer():
    old_key = _key()
    new_key = _key()
    config = MagicMock()
    config.webhook_secret.get_secret_value.return_value = "test-master-secret"
    config.encryption_keys = [SecretStr(f"v2:{new_key}"), SecretStr(f"v1:{old_key}")]
    return Cryptographer(config), old_key, new_key


def test_encrypt_uses_current_key_version(rotating_cryptographer):
    crypto, _, new_key = rotating_cryptographer

    token = crypto.encrypt("secret")

    assert token.startswith("v2:")
    assert Fernet(new_key).decrypt(token[3:].encode()) == b"secret"
    assert list(crypto.fernets) == ["v2", "v1"]


def test_decrypts_with_old_key(rotating_cryptographer):
    crypto, old_key, _ = rotating_cryptographer
    token = Fernet(old_key).encrypt(b"secret").decode()

    assert crypto.decrypt(f"v1:{token}") == "secret"
    assert crypto.decrypt(token) == "secret"


def test_rotate_uses_token_version_and_current_key(rotating_cryptographer):
    crypto, old_key, new_key = rotating_cryptographer
    token = Fernet(old_key).encrypt(b"secret").decode()

    rotated = crypto.rotate(f"v1:{token}")

    assert rotated.startswith("v2:")
    assert Fernet(new_key).decrypt(rotated[3:].encode()) == b"secret"
    assert crypto.decrypt(rotated) == "secret"


def test_decrypt_unknown_version_raises(rotating_cryptographer):
    crypto, _, _ = rotating_cryptographer

    with pytest.raises(InvalidToken):
        crypto.decrypt("v9:not-a-token")


def test_need_rotation(rotating_cryptographer):
    crypto, old_key, _ = rotating_cryptographer
    token = Fernet(old_key).encrypt(b"secret").decode()

    assert crypto.need_rotation(f"v1:{token}") is True
    assert crypto.need_rotation(token) is True
    assert crypto.need_rotation(crypto.encrypt("secret")) is False


def test_rotate_legacy_v1(rotating_cryptographer):
    crypto, old_key, _ = rotating_cryptographer
    token = Fernet(old_key).encrypt(b"secret").decode()

    assert crypto.rotate(token).startswith("v2:")
