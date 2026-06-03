from abc import ABC, abstractmethod
from typing import Generic, TypeVar

M_ = TypeVar("M_")
D_ = TypeVar("D_")


class IModelMapper(ABC, Generic[M_, D_]):
    """Interface for model mapping."""

    @abstractmethod
    def to_dto(self, model: M_) -> D_: ...

    @abstractmethod
    def from_dto(self, dto: D_) -> M_: ...
