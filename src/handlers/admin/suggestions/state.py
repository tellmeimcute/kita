from aiogram.fsm.state import State, StatesGroup


class SuggestionViewer(StatesGroup):
    in_viewer = State()
