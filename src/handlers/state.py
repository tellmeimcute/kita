from aiogram.fsm.state import State, StatesGroup

class CommandBanState(StatesGroup):
    wait_for_id = State()