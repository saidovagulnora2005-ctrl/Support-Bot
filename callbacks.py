from service import *
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from states import NewTicket,AddMessage,AdminReply
from keyboards import confirm_ticket_keyboard,user_ticket_btns,admin_ticket_buttons


router = Router()


async def send_history(callback,messages):
    if not messages:
        await callback.message.answer("💬 Переписка пока пустая")
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
            f"{item['text']}\n\n"
        )
    while len(history) > 4000:
        await callback.message.answer(history[:4000])
        history = history[4000:]
    await callback.message.answer(history)


@router.callback_query(F.data.startswith("ticket_open_"))
async def open_ticket_callback(callback: CallbackQuery,state: FSMContext):
    try:
        ticket_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("Неверный ID.",show_alert=True)
        return
    ticket = await get_ticket(ticket_id,callback.from_user.id)
    if ticket is None:
        await callback.answer("Заявка не найдена или доступа нет.",show_alert=True)
        return
    await state.clear()
    await callback.answer()
    text = (
        f"🎫 Заявка #{ticket['id']}\n"
        f"Тема: {ticket['subject']}\n"
        f"Статус: {ticket['status']}\n\n"
        f"Описание:\n{ticket['description']}")
    if ticket["closed_at"]:
        text += (
            "\n\nЗакрыта: "
            f"{ticket['closed_at'].strftime('%d.%m.%Y %H:%M')}")
    buttons = None
    if ticket["status"] == "open":
        if is_admin(callback.from_user.id):
            buttons = admin_ticket_buttons(ticket_id)
        else:
            buttons = user_ticket_btns(ticket_id,"open")
    await callback.message.answer(text,reply_markup=buttons)
    if ticket["photo_file_id"]:
        await callback.message.answer_photo(ticket["photo_file_id"],caption="Фото заявки")
    messages = await get_ticket_messages(ticket_id)
    await send_history(callback,messages)


@router.callback_query(F.data.startswith("ticket_add_"))
async def add_ticket_callback(callback: CallbackQuery,state: FSMContext):
    try:
        ticket_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("Неверный ID.",show_alert=True)
        return
    ticket = await get_ticket(ticket_id,callback.from_user.id)
    if ticket is None:
        await callback.answer("Нет доступа к заявке.",show_alert=True)
        return
    if ticket["status"] == "closed":
        await callback.answer("Заявка уже закрыта.",show_alert=True)
        return
    await state.clear()
    await state.update_data(ticket_id=ticket_id)
    await state.set_state(AddMessage.text)
    await callback.answer()
    await callback.message.answer(f"Заявка №{ticket_id}\n""Напишите дополнение:")


@router.callback_query(F.data.startswith("ticket_reply_"))
async def reply_ticket_callback(callback: CallbackQuery,state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!",show_alert=True)
        return
    try:
        ticket_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("Неверный ID!",show_alert = True)
        return
    ticket = await get_ticket(ticket_id,callback.from_user.id)
    if ticket is None:
        await callback.answer("Заявка не найдена!",show_alert = True)
        return
    if ticket["status"] == "closed":
        await callback.answer("Заявка уже закрыта",show_alert = True)
        return
    await state.clear()
    await state.update_data(ticket_id=ticket_id)
    await state.set_state(AdminReply.text)
    await callback.answer()
    await callback.message.answer(
        f"Заявка #{ticket_id}\n"
        f"Тема: {ticket['subject']}\n\n"
        "Напишите ответ:")


@router.callback_query(F.data.startswith("ticket_close_"))
async def close_ticket_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!",show_alert = True)
        return
    try:
        ticket_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("Неверный ID!",show_alert = True)
        return
    result = await close_ticket(ticket_id,callback.from_user.id)
    if result == "no_access":
        await callback.answer("Нет доступа!",show_alert = True)
        return
    if result == "not_found":
        await callback.answer("Заявка не найдена!",show_alert = True)
        return
    if result == "closed":
        await callback.answer("Заявка уже закрыта",show_alert=True)
        return
    await callback.answer("Заявка закрыта",show_alert=True)
    await callback.message.answer(f"✅ Заявка №{ticket_id} закрыта.")
    try:
        await callback.bot.send_message(result["telegram_id"],f"✅ Ваша заявка №{ticket_id} закрыта")
    except Exception as error:
        print("Close ticket error: ",error)


@router.callback_query(F.data == "ticket_skip_photo")
async def skip_photo_callback(callback: CallbackQuery,state: FSMContext):
    current_state = await state.get_state()
    if current_state != NewTicket.photo.state:
        await callback.answer("Сейчас пропустить нельзя",show_alert=True)
        return
    await state.update_data(photo_file_id=None)
    await state.set_state(NewTicket.confirm)
    await callback.answer()
    data = await state.get_data()
    text = (
        "Проверьте заявку:\n\n"
        f"Тема: {data['subject']}\n\n"
        f"Описание:\n{data['description']}")
    await callback.message.answer(text)
    await callback.message.answer("Отправить заявку?",reply_markup=confirm_ticket_keyboard())


@router.callback_query(F.data == "ticket_confirm_send")
async def confirm_send_callback(callback: CallbackQuery,state: FSMContext):
    current_state = await state.get_state()
    if current_state != NewTicket.confirm.state:
        await callback.answer("Заявка уже обработана.",show_alert=True)
        return
    data = await state.get_data()
    try:
        ticket_id = await create_ticket(
            callback.from_user.id,
            data["subject"],
            data["description"],
            data.get("photo_file_id"))
    except Exception:
        await callback.answer("Ошибка при создании заявки.",show_alert=True)
        return
    await state.clear()
    await callback.answer("Заявка отправлена!",show_alert=True)
    await callback.message.answer(f"✅ Заявка #{ticket_id} создана.")


@router.callback_query(F.data == "ticket_confirm_cancel")
async def confirm_cancel_callback(callback: CallbackQuery,state: FSMContext):
    current_state = await state.get_state()
    if current_state != NewTicket.confirm.state:
        await callback.answer("Заявка уже обработана.",show_alert=True)
        return
    await state.clear()
    await callback.answer("Заявка отменена.",show_alert=True)
    await callback.message.answer("❌ Заявка не создана")