

from typing import TypeVar, Iterable, Any

from pydantic import BaseModel, ConfigDict, PrivateAttr

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
    
class TrackableDto(BaseDTO):
    __changed_data: dict[str, Any] = PrivateAttr(default_factory=dict)

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        self.__changed_data[name] = value

    @property
    def changed_data(self) -> dict[str, Any]:
        return self.__changed_data
    
    def prepare_changed_data(self) -> dict[str, Any]:
        return {
            k: v
            for k, v in self.changed_data.items()
            if not k.startswith("_")
        }