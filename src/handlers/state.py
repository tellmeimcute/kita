from aiogram.fsm.state import State, StatesGroup

class CommandBanState(StatesGroup):
    wait_for_id = State()

class MassMessageState(StatesGroup):
    wait_for_message = State()
    wait_confirm = State()