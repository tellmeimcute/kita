from pydantic import BaseModel, ConfigDict


class MediaDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filetype: str
    telegram_file_id: str
