

from typing import TypeVar, Iterable

from pydantic import BaseModel, ConfigDict

from database.models.abstract_model import AbstractModel

ModelSQL = TypeVar("ModelSQL", bound="AbstractModel")
ModelDTO = TypeVar("ModelDTO", bound="BaseDTO")

class BaseDTO(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        populate_by_name=True,
    )

    @classmethod
    def from_model_list(
        cls: type[ModelDTO],
        model_instances: Iterable[ModelSQL],
    ):
        return [
            cls.model_validate(model)
            for model in model_instances
            if model is not None
        ]