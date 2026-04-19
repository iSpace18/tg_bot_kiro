import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import settings

logger = logging.getLogger(__name__)
router = Router()


class SupportStates(StatesGroup):
    waiting_message = State()


def support_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Написать в поддержку", callback_data="support_write")],
        [InlineKeyboardButton(text="❓ FAQ", callback_data="faq_list")],
    ])


@router.message(F.text == "🆘 Поддержка")
async def support_menu(message: Message):
    await message.answer(
        "🆘 <b>Поддержка</b>\n\n"
        "Если у вас возникли проблемы, вы можете:\n"
        "• Написать нам напрямую\n"
        "• Посмотреть раздел FAQ\n\n"
        "Время ответа: до 24 часов",
        reply_markup=support_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "support_write")
async def support_write(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✉️ Напишите ваш вопрос или опишите проблему.\n\n"
        "Мы ответим вам как можно скорее.",
    )
    await state.set_state(SupportStates.waiting_message)
    await callback.answer()


@router.message(SupportStates.waiting_message)
async def support_message_received(message: Message, state: FSMContext):
    await state.clear()

    # Forward to admins
    for admin_id in settings.ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"📩 <b>Обращение в поддержку</b>\n\n"
                f"От: {message.from_user.full_name} (@{message.from_user.username or 'нет'})\n"
                f"ID: <code>{message.from_user.id}</code>\n\n"
                f"Сообщение:\n{message.text}",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to forward support message to admin {admin_id}: {e}")

    await message.answer(
        "✅ Ваше сообщение отправлено в поддержку!\n\n"
        "Мы ответим вам в ближайшее время.",
    )
