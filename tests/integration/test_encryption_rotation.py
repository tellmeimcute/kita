from itertools import count
from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet
from dishka import AsyncContainer
from pydantic import SecretStr
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from core.cryptographer import Cryptographer
from scripts.rotate_encryption import rotate


def _key() -> str:
    return Fernet.generate_key().decode()


@pytest.fixture
async def encrypted_bots(request_container: AsyncContainer, id_generator: count):
    session: AsyncSession = await request_container.get(AsyncSession)
    engine: AsyncEngine = await request_container.get(AsyncEngine)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    old_key, new_key = _key(), _key()
    owner_id = next(id_generator)
    bot_ids = [next(id_generator) for _ in range(3)]

    await session.execute(
        text("INSERT INTO users (user_id, username, name) VALUES (:user_id, :username, :name)"),
        {"user_id": owner_id, "username": "rotation_owner", "name": "Rotation Owner"},
    )
    for index, bot_id in enumerate(bot_ids):
        token = Fernet(old_key).encrypt(f"token-{index}".encode()).decode()
        stored = token if index == 0 else f"v1:{token}"
        await session.execute(
            text(
                "INSERT INTO userbot (token, bot_id, username, owner_id) "
                "VALUES (:token, :bot_id, :username, :owner_id)"
            ),
            {
                "token": stored,
                "bot_id": bot_id,
                "username": f"rotation_bot_{index}",
                "owner_id": owner_id,
            },
        )
    await session.commit()

    config = MagicMock()
    config.webhook_secret.get_secret_value.return_value = "test-master-secret"
    config.encryption_keys = [SecretStr(f"v2:{new_key}"), SecretStr(f"v1:{old_key}")]

    yield session, session_maker, bot_ids, new_key, Cryptographer(config)

    delete_bots = text("DELETE FROM userbot WHERE bot_id IN :bot_ids").bindparams(
        bindparam("bot_ids", expanding=True)
    )
    await session.execute(delete_bots, {"bot_ids": bot_ids})
    await session.execute(
        text("DELETE FROM users WHERE user_id = :user_id"), {"user_id": owner_id}
    )
    await session.commit()


async def test_rotation_reencrypts_tokens_with_current_key(encrypted_bots):
    session, session_maker, bot_ids, new_key, crypto = encrypted_bots

    updated = await rotate(session_maker, crypto, batch_size=2)

    assert updated == 3
    stmt = text("SELECT token FROM userbot WHERE bot_id IN :bot_ids ORDER BY bot_id").bindparams(
        bindparam("bot_ids", expanding=True)
    )
    stored = (await session.execute(stmt, {"bot_ids": bot_ids})).scalars().all()
    assert all(token.startswith("v2:") for token in stored)
    assert Fernet(new_key).decrypt(stored[0][3:].encode()) == b"token-0"
    assert all(crypto.decrypt(token) == f"token-{index}" for index, token in enumerate(stored))


async def test_rotation_skips_tokens_with_current_version(encrypted_bots):
    session, session_maker, bot_ids, _, crypto = encrypted_bots
    select_one = text("SELECT token FROM userbot WHERE bot_id = :bot_id")

    token = (await session.execute(select_one, {"bot_id": bot_ids[0]})).scalar_one()
    fresh = crypto.rotate(token)
    await session.execute(
        text("UPDATE userbot SET token = :token WHERE bot_id = :bot_id"),
        {"token": fresh, "bot_id": bot_ids[0]},
    )
    await session.commit()

    updated = await rotate(session_maker, crypto, batch_size=2)

    assert updated == 2
    stored = (await session.execute(select_one, {"bot_id": bot_ids[0]})).scalar_one()
    assert stored == fresh
