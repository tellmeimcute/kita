from database.dao.base import BaseDao
from database.models import Suggestion


class SuggestionDAO(BaseDao[Suggestion]):
    model = Suggestion
