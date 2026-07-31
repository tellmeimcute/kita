
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class RedisKey:
    bot_id: int | None = None
    user_id: int | None = None


@dataclass(frozen=True)
class MediaGroupKey(RedisKey):
    media_group_id: int


class KeyBuilder(ABC):
    @abstractmethod
    def build(
        self,
        key: RedisKey,
    ): ...


class KitaKeyBuilder(KeyBuilder):
    
    def __init__(
        self,
        *,
        prefix: str = "kita",
        separator: str = ":",
        with_bot_id: bool = True,
        with_user_id: bool = True,
    ):
        self.prefix = prefix
        self.separator = separator
        self.with_user_id = with_user_id
        self.with_bot_id = with_bot_id

    def build(
        self,
        key: RedisKey,
        part: Literal["user", "user_stats", "bot_config"] = None,
    ):
        parts = [self.prefix]
        if self.with_bot_id:
            parts.append(str(key.bot_id))
        if self.with_user_id:
            parts.append(str(key.user_id))

        if part:
            parts.append(part)
        return self.separator.join(parts)


class MediaGroupKeyBulder(KitaKeyBuilder):
    def build(
        self,
        key: MediaGroupKey,
        part: Literal["lock"] = None,
    ):
        parts = [self.prefix]

        if self.with_bot_id:
            parts.append(str(key.bot_id))
        if self.with_user_id:
            parts.append(str(key.user_id))

        parts.append(str(key.media_group_id))
        if part:
            parts.append(part)

        return self.separator.join(parts)
    