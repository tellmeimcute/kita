from aiogram.fsm.state import State, StatesGroup


class CommandBanState(StatesGroup):
    wait_for_id = State()


class MassMessageState(StatesGroup):
    wait_for_message = State()
    wait_confirm = State()


class SuggestionViewerState(StatesGroup):
    in_viewer = State()
    in_solo_view = State()

class SendSuggestionState(StatesGroup):
    waiting_for_post = State()
