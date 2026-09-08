from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel, TypeAdapter

from database.redis.base import BaseRedisRepository

# Constants
EXPECTED_LRANGE_COUNT = 2
EXPECTED_SECOND_VALUE = 2

any_adapter = TypeAdapter(Any)


class SampleModel(BaseModel):
    name: str
    value: int


class SampleRedisRepo(BaseRedisRepository):
    model = SampleModel


class SecretModel(BaseModel):
    name: str
    secret: str


class SecretRepo(BaseRedisRepository):
    model = SecretModel
    _secret_fields = {"secret"}


@pytest.fixture
def repo(mock_redis, cryptographer):
    return SampleRedisRepo(redis=mock_redis, crypto=cryptographer)


class TestBaseRedisRepository:
    async def test_get_deletes_corrupted_data(self, repo, mock_redis):
        mock_redis.get.return_value = "invalid json"
        mock_redis.delete = AsyncMock()

        result = await repo.get("bad_key")

        assert result is None
        mock_redis.delete.assert_called_once_with("bad_key")

    async def test_set_cache_serializes_and_caches(self, repo, mock_redis):
        data = SampleModel(name="test", value=123)

        await repo.set_cache("key1", data)

        mock_redis.set.assert_called_once()
        call_kwargs = mock_redis.set.call_args.kwargs
        assert call_kwargs["name"] == "key1"
        assert call_kwargs["ex"] == repo.expiry

    async def test_delete(self, repo, mock_redis):
        await repo.delete("key1")

        mock_redis.delete.assert_called_once_with("key1")

    async def test_exist_returns_true(self, repo, mock_redis):
        mock_redis.exists.return_value = 1

        result = await repo.exist("key1")

        assert result is True

    async def test_exist_returns_false(self, repo, mock_redis):
        mock_redis.exists.return_value = 0

        result = await repo.exist("key1")

        assert result is False

    async def test_rpush_adds_items(self, repo, mock_redis):
        data1 = SampleModel(name="a", value=1)
        data2 = SampleModel(name="b", value=2)

        await repo.rpush("list_key", data1, data2)

        mock_redis.rpush.assert_called_once()
        mock_redis.expire.assert_called_once_with("list_key", repo.expiry)

    async def test_lrange_returns_list(self, repo, mock_redis):
        mock_redis.lrange.return_value = ['{"name": "a", "value": 1}', '{"name": "b", "value": 2}']

        result = await repo.lrange("list_key")

        assert len(result) == EXPECTED_LRANGE_COUNT
        assert result[0].name == "a"
        assert result[1].value == EXPECTED_SECOND_VALUE

    async def test_lrange_returns_empty_on_error(self, repo, mock_redis):
        mock_redis.lrange.return_value = ["invalid"]
        repo.delete = AsyncMock()

        result = await repo.lrange("bad_list")

        assert result == []


class TestBaseRedisRepositorySecretFields:
    def test_is_secret_field_true_for_marked_field(self, cryptographer):
        class ModelWithSecret(BaseModel):
            name: str
            api_key: str

        class RepoWithSecret(BaseRedisRepository):
            model = ModelWithSecret
            _secret_fields = {"api_key"}

        repo_instance = RepoWithSecret(redis=AsyncMock(), crypto=cryptographer)
        assert repo_instance._is_secret_field("api_key") is True

    def test_is_secret_field_false_for_regular_field(self, cryptographer):
        class SimpleModel(BaseModel):
            name: str
            value: int

        class SimpleRepo(BaseRedisRepository):
            model = SimpleModel

        repo_instance = SimpleRepo(redis=AsyncMock(), crypto=cryptographer)
        assert repo_instance._is_secret_field("name") is False


class TestBaseRedisRepositoryEncryption:
    async def test_set_cache_encrypts_value(self, mock_redis, mock_cryptographer):
        repo = SecretRepo(redis=mock_redis, crypto=mock_cryptographer)
        data = SecretModel(name="test", secret="mysecret")
        mock_cryptographer.encrypt.return_value = "encrypted-secret"

        await repo.set_cache("key1", data)

        stored = mock_redis.set.call_args.kwargs["value"]
        assert b"encrypted-secret" in stored
        mock_cryptographer.encrypt.assert_called_once_with("mysecret")

    async def test_get_round_trip_decrypts(self, mock_redis, cryptographer):
        repo = SecretRepo(redis=mock_redis, crypto=cryptographer)
        data = SecretModel(name="test", secret="mysecret")

        await repo.set_cache("key1", data)
        encrypted_value = mock_redis.set.call_args.kwargs["value"]
        mock_redis.get.return_value = encrypted_value

        result = await repo.get("key1")

        assert result.secret == "mysecret"
