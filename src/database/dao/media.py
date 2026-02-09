from database.dao.base import BaseDao
from database.models import Media


class MediaDAO(BaseDao[Media]):
    model = Media
