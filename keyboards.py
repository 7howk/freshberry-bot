from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import PRODUCTS, WEIGHTS

# Главная reply-клавиатура (под строкой ввода)
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍓 Клубника"), KeyboardButton(text="🍒 Вишня"), KeyboardButton(text="🍒 Черешня")],
        [KeyboardButton(text="🍑 Персик"), KeyboardButton(text="🍊 Абрикос")],
        [KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="✅ Оформить заказ")],
        [KeyboardButton(text="📞 Связаться с продавцом"), KeyboardButton(text="💰 Цены")]
    ],
    resize_keyboard=True
)

def get_weight_keyboard(product_key: str) -> InlineKeyboardMarkup:
    """Клавиатура для выбора веса конкретного товара"""
    name, price_per_kg = PRODUCTS[product_key]
    builder = InlineKeyboardBuilder()
    for w in WEIGHTS:
        cost = int((w / 1000) * price_per_kg)
        if w == 1000:
            label = f"1 кг — {cost}₽"
        elif w == 1500:
            label = f"1.5 кг — {cost}₽"
        elif w == 2000:
            label = f"2 кг — {cost}₽"
        else:
            label = f"{w} г — {cost}₽"
        builder.button(text=label, callback_data=f"{product_key}:{w}")
    builder.button(text="✏️ Свой вес", callback_data=f"custom:{product_key}")
    builder.button(text="🔙 Назад", callback_data="back")
    builder.adjust(1)
    return builder.as_markup()