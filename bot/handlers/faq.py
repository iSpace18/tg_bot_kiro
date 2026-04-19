import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
router = Router()

FAQ_ITEMS = [
    {
        "q": "Что такое VPN и зачем он нужен?",
        "a": "VPN (Virtual Private Network) — это технология, которая шифрует ваш интернет-трафик и скрывает реальный IP-адрес. Используется для обхода блокировок, защиты данных в публичных сетях и анонимности в интернете.",
    },
    {
        "q": "Как подключиться к VPN?",
        "a": "1. Купите тариф или активируйте пробный период\n2. Скопируйте полученный ключ (vless://...)\n3. Установите приложение v2rayNG (Android) или Streisand (iOS)\n4. Добавьте ключ в приложение\n5. Нажмите подключиться",
    },
    {
        "q": "Какие приложения поддерживаются?",
        "a": "• Android: v2rayNG, NekoBox\n• iOS: Streisand, Shadowrocket\n• Windows: v2rayN, Nekoray\n• macOS: V2Box, Streisand",
    },
    {
        "q": "Что делать если VPN не работает?",
        "a": "1. Проверьте срок действия ключа в разделе «Профиль»\n2. Убедитесь, что ключ скопирован полностью\n3. Попробуйте переподключиться\n4. Обратитесь в поддержку",
    },
    {
        "q": "Как продлить подписку?",
        "a": "Перейдите в раздел «💳 Купить VPN» и выберите нужный тариф. После оплаты вы получите новый ключ.",
    },
    {
        "q": "Возможен ли возврат средств?",
        "a": "Возврат возможен в течение 24 часов с момента покупки, если VPN не работал. Обратитесь в поддержку с описанием проблемы.",
    },
]


def faq_list_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for i, item in enumerate(FAQ_ITEMS):
        buttons.append([InlineKeyboardButton(text=f"❓ {item['q'][:40]}...", callback_data=f"faq:{i}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def faq_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К списку вопросов", callback_data="faq_list")]
    ])


@router.message(F.text == "❓ FAQ")
async def faq_menu(message: Message):
    await message.answer(
        "❓ <b>Часто задаваемые вопросы</b>\n\nВыберите вопрос:",
        reply_markup=faq_list_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "faq_list")
async def faq_list(callback: CallbackQuery):
    await callback.message.edit_text(
        "❓ <b>Часто задаваемые вопросы</b>\n\nВыберите вопрос:",
        reply_markup=faq_list_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("faq:"))
async def faq_item(callback: CallbackQuery):
    idx = int(callback.data.split(":")[1])
    if idx >= len(FAQ_ITEMS):
        await callback.answer("Вопрос не найден", show_alert=True)
        return

    item = FAQ_ITEMS[idx]
    await callback.message.edit_text(
        f"❓ <b>{item['q']}</b>\n\n{item['a']}",
        reply_markup=faq_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
