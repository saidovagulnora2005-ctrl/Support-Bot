from aiogram.fsm.state import State, StatesGroup


class NewTicket(StatesGroup):
    subject = State()
    description = State()
    photo = State()
    confirm = State()


class AddMessage(StatesGroup):
    text = State()


class AdminReply(StatesGroup):
    text = State()


class AIChat(StatesGroup):
    chat = State()