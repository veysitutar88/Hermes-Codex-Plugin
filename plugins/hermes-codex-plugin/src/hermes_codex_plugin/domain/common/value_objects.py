from abc import ABC
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

V = TypeVar("V", bound=Any)


@dataclass(frozen=True)
class BaseValueObject(ABC):
    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        """Check that a value is valid to create this value object."""


@dataclass(frozen=True, eq=False)
class ValueObject(BaseValueObject, ABC, Generic[V]):
    value: V

    def to_raw(self) -> V:
        return self.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ValueObject):
            return self.value == other.value
        return self.value == other

    def __hash__(self) -> int:
        return hash(self.value)

    def __str__(self) -> str:
        return str(self.value)
