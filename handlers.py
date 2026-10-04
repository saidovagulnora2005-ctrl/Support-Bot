from service import *
from keyboards import *
from aiogram import Router, F
from dotenv import load_dotenv
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandObject
from aiogram.utils.chat_action import ChatActionSender
from states import NewTicket,AddMessage,AdminReply,AIChat


load_dotenv()

router = Router()


def get_menu(telegram_id):
    if is_admin(telegram_id):
        return admin_menu
    return user_menu


async def send_long_message(message: Message,text: str):
    while len(text) > 4000:
        await message.answer(text[:4000])
        text = text[4000:]
    if text:
        await message.answer(text)


async def start_new_ticket(message: Message,state: FSMContext):
    await state.clear()
    clear_ai_history(message.from_user.id)
    await state.set_state(NewTicket.subject)
    await message.answer("📝 Создание заявки\n\n""Введите тему заявки:")


async def start_ai(message: Message,state: FSMContext):
    await state.clear()
    clear_ai_history(message.from_user.id)
    await state.set_state(AIChat.chat)
    await message.answer("🤖 AI-консультация началась.\n\n""Напишите свой вопрос: ",reply_markup = ai_btn)


@router.message(Command("start"))
async def start_handler(message: Message,state: FSMContext):
    await state.clear()
    clear_ai_history(message.from_user.id)
    print("USER ID:", message.from_user.id)
    print("ADMIN ID:", ADMIN_ID)
    print("IS ADMIN:", is_admin(message.from_user.id))
    if is_admin(message.from_user.id):
        text = (
            "👋 Добро пожаловать, администратор!\n\n"
            "🛠 Панель управления Alif Support Bot\n\n"
            "Здесь вы можете:\n"
            "🎫 просматривать заявки пользователей\n"
            "💬 отвечать на заявки\n"
            "🔴 закрывать заявки\n\n"
            "Команда:\n"
            "/admin_tickets — все заявки пользователей"
        )
    else:
        text = (
            "👋 Добро пожаловать в Alif Support Bot!\n\n"
            "Здесь вы можете:\n"
            "📝 отправить заявку в поддержку\n"
            "🤖 получить AI-консультацию\n\n"
            "Команды:\n"
            "/new_ticket — новая заявка\n"
            "/my_tickets — мои заявки\n"
            "/ticket <id> — открыть заявку\n"
            "/ai — AI-консультация\n"
            "/cancel — отменить действие"
        )
    await message.answer(text,reply_markup = get_menu(message.from_user.id))


@router.message(Command("cancel"))
async def cancel_handler(message: Message,state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Сейчас нечего отменять",reply_markup = get_menu(message.from_user.id))
        return
    await state.clear()
    clear_ai_history(message.from_user.id)
    await message.answer("✅ Действие отменено!",reply_markup = get_menu(message.from_user.id))


@router.message(Command("new_ticket"))
async def new_ticket_command(message: Message,state: FSMContext):
    await start_new_ticket(message,state)


@router.message(F.text == "📝 Отправить заявку")
async def new_ticket_button(message: Message,state: FSMContext):
    await start_new_ticket(message,state)


@router.message(Command("my_tickets"))
async def my_tickets_command(message: Message,state: FSMContext):
    await state.clear()
    clear_ai_history(message.from_user.id)
    await show_my_tickets(message)


@router.message(F.text == "📋 Мои заявки")
async def my_tickets_button(message: Message,state: FSMContext):
    await state.clear()
    clear_ai_history(message.from_user.id)
    await show_my_tickets(message)


async def show_my_tickets(message: Message):
    tickets = await get_user_tickets(message.from_user.id)
    if not tickets:
        await message.answer("📋 У вас пока нет заявок!")
        return
    for ticket in tickets:
        if ticket["status"] == "open":
            status = "🟢 Открыта"
        else:
            status = "🔴 Закрыта"
        text = (
            f"🎫 Заявка №{ticket['id']}\n"
            f"Тема: {ticket['subject']}\n"
            f"Статус: {status}\n"
            f"Создана: "
            f"{ticket['created_at'].strftime('%d.%m.%Y %H:%M')}"
        )
        await message.answer(text,reply_markup = user_ticket_btns(
                ticket["id"],
                ticket["status"]))


@router.message(Command("ticket"))
async def ticket_command(message: Message,command: CommandObject,state: FSMContext):
    await state.clear()
    clear_ai_history(message.from_user.id)
    if not command.args:
        await message.answer(
            "Используйте:\n"
            "/ticket <id>"
        )
        return
    try:
        ticket_id = int(command.args.strip())
    except ValueError:
        await message.answer("ID заявки должен быть числом!")
        return
    await show_ticket(message,ticket_id)


async def show_ticket(message: Message,ticket_id: int):
    ticket = await get_ticket(ticket_id,message.from_user.id)
    if ticket is None:
        await message.answer("❌ Заявка не найдена " "или у вас нет доступа!")
        return
    if ticket["status"] == "open":
        status = "🟢 Открыта"
    else:
        status = "🔴 Закрыта"
    text = (
        f"🎫 Заявка #{ticket['id']}\n"
        f"Тема: {ticket['subject']}\n"
        f"Статус: {status}\n\n"
        f"Описание:\n"
        f"{ticket['description']}")
    if ticket["closed_at"]:
        text += (
            "\n\nЗакрыта: "
            f"{ticket['closed_at'].strftime('%d.%m.%Y %H:%M')}")
    if is_admin(message.from_user.id):
        if ticket["status"] == "open":
            buttons = admin_ticket_buttons(ticket_id)
        else:
            buttons = None
    else:
        if ticket["status"] == "open":
            buttons = user_ticket_btns(ticket_id,"open")
        else:
            buttons = user_ticket_btns(ticket_id,"closed")
    await message.answer(text,reply_markup = buttons)
    if ticket["photo_file_id"]:
        await message.answer_photo(ticket["photo_file_id"],caption="📷 Фото заявки")
    messages = await get_ticket_messages(ticket_id)
    print("TICKET ID:", ticket_id)
    print("MESSAGES:", messages)
    if not messages:
        await message.answer("💬 Переписка пока пустая.")
        return
    history = "💬 Переписка:\n\n"
    for item in messages:
        if item["sender_role"] == "user":
            role = "Пользователь"
        else:
            role = "Администратор"

        time = item["created_at"].strftime("%d.%m.%Y %H:%M")
        history += (
            f"{role} ({time}):\n"
            f"{item['text']}\n\n")
    await send_long_message(message,history)


@router.message(NewTicket.subject, F.text)
async def ticket_subject(message: Message,state: FSMContext):
    subject = message.text.strip()
    if not subject:
        await message.answer("Тема не может быть пустой!\n""Введите тему:")
        return
    if len(subject) > 200:
        await message.answer("Тема слишком длинная.\n" "Максимум 200 символов!")
        return
    await state.update_data(subject=subject)
    await state.set_state(NewTicket.description)
    await message.answer("Теперь подробно опишите проблему:")


@router.message(NewTicket.subject)
async def ticket_subject_wrong(message: Message):
    await message.answer("Тема должна быть текстом")


@router.message(NewTicket.description, F.text)
async def ticket_description(message: Message,state: FSMContext):
    description = message.text.strip()
    if not description:
        await message.answer("Описание не может быть пустым!\n" "Опишите проблему:")
        return
    await state.update_data(description=description,photo_file_id=None)
    await state.set_state(NewTicket.photo)
    await message.answer("📷 Отправьте одно фото " "или нажмите «Пропустить»",reply_markup = skip_photo_keyboard())


@router.message(NewTicket.description)
async def ticket_description_wrong(message: Message):
    await message.answer("Описание должно быть текстом!")


@router.message(NewTicket.photo, F.photo)
async def ticket_photo(message: Message,state: FSMContext):
    photo_file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=photo_file_id)
    await state.set_state(NewTicket.confirm)
    data = await state.get_data()
    text = (
        "Проверьте заявку:\n\n"
        f"Тема: {data['subject']}\n\n"
        f"Описание:\n"
        f"{data['description']}"
    )
    await message.answer(text)
    await message.answer_photo(photo_file_id,caption = "📷 Фото заявки")
    await message.answer("Отправить заявку?",reply_markup=confirm_ticket_keyboard())


@router.message(NewTicket.photo)
async def ticket_photo_wrong(message: Message):
    await message.answer(
        "На этом шаге можно отправить "
        "только фото или нажать «Пропустить».")


@router.message(AddMessage.text, F.text)
async def add_message_handler(message: Message,state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("Сообщение не может быть пустым")
        return
    data = await state.get_data()
    ticket_id = data["ticket_id"]
    result = await add_user_message(ticket_id,message.from_user.id,text)
    await state.clear()
    if not result:
        await message.answer("❌ Заявка уже закрыта "
            "или у вас нет доступа.")
        return
    await message.answer(
        f"✅ Сообщение добавлено "
        f"в заявку #{ticket_id}",reply_markup=get_menu(message.from_user.id))


@router.message(AddMessage.text)
async def add_message_wrong(message: Message):
    await message.answer("Дополнение принимается только текстом")


@router.message(Command("admin_tickets"))
async def admin_tickets_command(message: Message,state: FSMContext):
    await state.clear()
    clear_ai_history(message.from_user.id)
    await show_admin_tickets(message)


@router.message(F.text == "📥 Заявки пользователей")
async def admin_tickets_button(message: Message,state: FSMContext):
    await state.clear()
    clear_ai_history(message.from_user.id)
    await show_admin_tickets(message)


async def show_admin_tickets(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа.")
        return
    tickets = await get_open_tickets()
    if not tickets:
        await message.answer("📥 Открытых заявок нет")
        return
    for ticket in tickets:
        text = (
            f"🎫 Заявка #{ticket['id']}\n"
            f"Пользователь: {ticket['telegram_id']}\n"
            f"Тема: {ticket['subject']}\n"
            f"Статус: 🟢 Открыта" )
        await message.answer(text,reply_markup=admin_ticket_buttons(ticket["id"]))


@router.message(AdminReply.text, F.text)
async def admin_reply_handler(message: Message,state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer("❌ У вас нет доступа!")
        return
    text = message.text.strip()
    if not text:
        await message.answer("Ответ не может быть пустым!")
        return
    data = await state.get_data()
    ticket_id = data["ticket_id"]
    result = await add_admin_message(ticket_id,message.from_user.id,text)
    await state.clear()
    if result is None:
        await message.answer("❌ Заявка уже закрыта " "или не найдена!")
        return
    telegram_id = result["telegram_id"]
    try:
        await message.bot.send_message(telegram_id,f"📩 Ответ по заявке №{ticket_id}:\n\n" f"{text}")
        await message.answer(f"✅ Ответ по заявке №{ticket_id} " "отправлен пользователю.")
    except Exception:
        await message.answer(
            f"✅ Ответ по заявке №{ticket_id} "
            "сохранён в БД,\n"
            "но уведомление пользователю "
            "отправить не удалось.")


@router.message(AdminReply.text)
async def admin_reply_wrong(message: Message):
    await message.answer("Ответ принимается только тексто!.")


@router.message(Command("ai"))
async def ai_command(message: Message,state: FSMContext):
    await start_ai(message,state)


@router.message(F.text == "🤖 AI-консультация")
async def ai_button(message: Message,state: FSMContext):
    await start_ai(message,state)


@router.message(AIChat.chat,F.text == "🚪 Завершить консультацию")
async def finish_ai_button(message: Message,state: FSMContext):
    await state.clear()
    clear_ai_history(message.from_user.id)
    await message.answer("✅ AI-консультация завершена.",reply_markup = get_menu(message.from_user.id))


@router.message(AIChat.chat,F.text == "📝 Отправить заявку")
async def ticket_from_ai(message: Message,state: FSMContext):
    await start_new_ticket(message,state)


@router.message(AIChat.chat,F.text)
async def ai_text_handler(message: Message):
    try:
        async with ChatActionSender(bot=message.bot,chat_id=message.chat.id,action="typing"):
            answer = await ask_ai(message.from_user.id,message.text)
        await message.answer(answer,reply_markup=ai_btn)
    except Exception:
        await message.answer(
            "❌ Не удалось получить ответ AI.\n\n"
            "Попробуйте повторить вопрос "
            "или завершите консультацию.")


@router.message(AIChat.chat)
async def ai_non_text_handler(message: Message):
    await message.answer("Для консультации отправьте текст!")


@router.message(NewTicket.confirm)
async def confirm_wrong_message(message: Message):
    await message.answer("Выберите «✅ Отправить» " "или «❌ Отменить».")


@router.message()
async def unknown_message(message: Message):
    await message.answer("Выберите действие в меню",reply_markup=get_menu(message.from_user.id))

@router.message()
async def ai_handler(message: Message):
    async with ChatActionSender(bot = message.bot,chat_id = message.chat.id,action = "typing"):
        answer = await ask_ai(message.from_user.id,message.text)
    await message.answer(answer)