from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Created[T]:
    dto: T
    created: bool
