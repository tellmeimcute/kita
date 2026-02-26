


from .base import BaseDTO


class MediaDTO(BaseDTO):
    id: int
    filetype: str
    telegram_file_id: str
