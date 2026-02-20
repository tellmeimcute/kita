from aiogram.fsm.state import State, StatesGroup


class SuggestionViewerState(StatesGroup):
    in_viewer = State()

    in_solo_view = State()
