from aiogram.types import ReplyKeyboardMarkup,KeyboardButton,InlineKeyboardMarkup,InlineKeyboardButton


user_menu = ReplyKeyboardMarkup(
    keyboard = [
        [
            KeyboardButton(text = "📝 Отправить заявку"),
            KeyboardButton(text = "📋 Мои заявки"),
        ],
        [
            KeyboardButton(text = "🤖 AI-консультация")
        ]
    ],
    resize_keyboard = True
    )


admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📥 Заявки пользователей")
        ]
    ],
    resize_keyboard=True
)


ai_btn = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🚪 Завершить консультацию")
        ],
    ],
    resize_keyboard=True
)


def user_ticket_btns(ticket_id, status):
    buttons = [
        [
            InlineKeyboardButton(text="👀 Открыть",callback_data=f"ticket_open_{ticket_id}")
        ]
    ]
    if status == "open":
        buttons[0].append(
            InlineKeyboardButton(text="✍️ Дополнить",callback_data=f"ticket_add_{ticket_id}")
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_ticket_buttons(ticket_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👀 Открыть",callback_data=f"ticket_open_{ticket_id}")
            ],
            [
                InlineKeyboardButton(text="💬 Ответить",callback_data=f"ticket_reply_{ticket_id}"),
                InlineKeyboardButton(text="✅ Закрыть",callback_data=f"ticket_close_{ticket_id}")
            ]
        ]
    )


def confirm_ticket_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить",callback_data="ticket_confirm_send"),
                InlineKeyboardButton(text="❌ Отменить",callback_data="ticket_confirm_cancel")
            ]
        ]
    )


def skip_photo_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Пропустить",callback_data="ticket_skip_photo")
            ]
        ]
    )