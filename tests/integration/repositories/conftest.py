from dataclasses import dataclass

import pytest
from dishka import AsyncContainer

from database.dto import UserDTO
from database.repository import UserRepository
from interfaces import UnitOfWorkProtocol


@dataclass(frozen=True)
class RepositoryContext:
    uow: UnitOfWorkProtocol
    user_repo: UserRepository
    test_user_dto: UserDTO


@pytest.fixture
async def repository_context(
    request_container: AsyncContainer,
    test_user_dto: UserDTO,
) -> RepositoryContext:
    return RepositoryContext(
        uow=await request_container.get(UnitOfWorkProtocol),
        user_repo=await request_container.get(UserRepository),
        test_user_dto=test_user_dto,
    )
