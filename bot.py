import asyncio
import logging
import re

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ----- ТВОИ ДАННЫЕ -----
# ВАЖНО: старый токен лучше перевыпустить через @BotFather, потому что он был отправлен в чат.
BOT_TOKEN = "8286121562:AAHk8avHA_w5OTTuH6XQX-ccj9mEhwIQSeI"
ADMIN_ID = 1010873079  # твой ID

CONTACT_TEXT = "По вопросам заказов: @jhowk и @cuteru6 или +7 911 824-02-90"

DELIVERY_PRICE = 350

# Цены считаются за 1 кг.
# Голубика: 230₽ за 100 г = 2300₽ за 1 кг.
PRICES = {
    "🍓 Клубника": 450,
    "🍒 Вишня": 630,
    "🍒 Черешня": 780,
    "🍑 Персик": 470,
    "🍊 Абрикос": 390,
    "🫐 Голубика": 2300,
}

WEIGHTS = {
    "500 г": 500,
    "1 кг": 1000,
    "1.5 кг": 1500,
    "2 кг": 2000,
}

logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Корзина: {user_id: [{"name":..., "weight":..., "weight_str":..., "price":...}]}
cart = {}
temp_fruit = {}  # временный выбранный фрукт

# ------------------------------------------------------------------
# КЛАВИАТУРЫ
# ------------------------------------------------------------------
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍓 Клубника"), KeyboardButton(text="🍒 Вишня")],
        [KeyboardButton(text="🍒 Черешня"), KeyboardButton(text="🍑 Персик")],
        [KeyboardButton(text="🍊 Абрикос"), KeyboardButton(text="🫐 Голубика")],
        [KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="✅ Оформить заказ")],
        [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="💰 Цены")],
        [KeyboardButton(text="🗑 Удалить товар")],
    ],
    resize_keyboard=True,
)

weight_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="500 г"), KeyboardButton(text="1 кг")],
        [KeyboardButton(text="1.5 кг"), KeyboardButton(text="2 кг")],
        [KeyboardButton(text="✏️ Свой вес")],
        [KeyboardButton(text="🔙 Назад")],
    ],
    resize_keyboard=True,
)

# ------------------------------------------------------------------
# СОСТОЯНИЯ
# ------------------------------------------------------------------
class WeightForm(StatesGroup):
    custom_weight = State()


class OrderForm(StatesGroup):
    name = State()
    surname = State()
    phone = State()
    address = State()

# ------------------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ------------------------------------------------------------------
def format_weight(weight_grams: int) -> str:
    """Красиво показывает вес: 700 г, 1 кг, 1.5 кг, 2.4 кг."""
    if weight_grams < 1000:
        return f"{weight_grams} г"

    kg = weight_grams / 1000
    if kg.is_integer():
        return f"{int(kg)} кг"
    return f"{kg:.2f}".rstrip("0").rstrip(".") + " кг"


def parse_custom_weight(text: str) -> int | None:
    """
    Принимает варианты:
    700, 700 г, 700 грамм, 0.7 кг, 2.4 кг, 2,4 кг.
    Если единица не указана и число больше 20 — считаем граммами.
    Если единица не указана и число до 20 — считаем килограммами.
    """
    text = text.lower().replace(",", ".").strip()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(кг|килограмм|килограмма|килограммов|г|гр|грамм|грамма|граммов)?", text)
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)

    if value <= 0:
        return None

    if unit in {"кг", "килограмм", "килограмма", "килограммов"}:
        grams = int(round(value * 1000))
    elif unit in {"г", "гр", "грамм", "грамма", "граммов"}:
        grams = int(round(value))
    else:
        # 700 -> 700 г, 2.4 -> 2.4 кг
        grams = int(round(value if value > 20 else value * 1000))

    if grams <= 0:
        return None
    return grams


def calc_item_price(fruit: str, weight_grams: int) -> int:
    return int(round((weight_grams / 1000) * PRICES[fruit]))


def add_item_to_user_cart(user_id: int, fruit: str, weight_grams: int) -> tuple[str, int]:
    price = calc_item_price(fruit, weight_grams)
    weight_display = format_weight(weight_grams)

    cart.setdefault(user_id, []).append(
        {
            "name": fruit,
            "weight": weight_grams,
            "weight_str": weight_display,
            "price": price,
        }
    )
    return weight_display, price


def get_cart_totals(user_id: int) -> tuple[int, int, int]:
    items = cart.get(user_id, [])
    total_w = sum(i["weight"] for i in items)
    products_total = sum(i["price"] for i in items)
    final_total = products_total + DELIVERY_PRICE if items else 0
    return total_w, products_total, final_total


def get_prices_text() -> str:
    return (
        "🍓 FreshBerry — быстрый доставщик свежих фруктов и ягод!\n\n"
        "Мы привозим спелые, сочные и отборные фрукты прямо к твоей двери.\n"
        "Собери корзину за пару кликов, выбери удобный вес и оформи заказ — всё быстро, просто и по приятным ценам.\n\n"
        "💰 Цены:\n"
        "🍓 Клубника — 450₽/кг\n"
        "🍊 Абрикос — 390₽/кг\n"
        "🍒 Черешня — 780₽/кг\n"
        "🍒 Вишня — 630₽/кг\n"
        "🍑 Персик — 470₽/кг\n"
        "🫐 Голубика — 230₽/100 г\n\n"
        f"🚚 Доставка — {DELIVERY_PRICE}₽ к сумме заказа"
    )


def get_cart_text(user_id):
    if user_id not in cart or not cart[user_id]:
        return "🛒 Корзина пуста.", None

    items = cart[user_id]
    text = "🛒 Твоя корзина:\n\n"
    for i, item in enumerate(items, 1):
        text += f"{i}. {item['name']} — {item['weight_str']} — {item['price']}₽\n"

    total_w, products_total, final_total = get_cart_totals(user_id)
    text += (
        f"\n📦 Общий вес: {total_w} г ({total_w / 1000:.2f} кг)\n"
        f"💰 Товары: {products_total}₽\n"
        f"🚚 Доставка: {DELIVERY_PRICE}₽\n"
        f"✅ Итого к оплате: {final_total}₽"
    )
    return text, items


def get_delete_keyboard(user_id):
    """Создаёт инлайн-кнопки для удаления каждого товара."""
    if user_id not in cart or not cart[user_id]:
        return None

    buttons = []
    for idx, item in enumerate(cart[user_id], 1):
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"❌ {idx}. {item['name']} {item['weight_str']} — {item['price']}₽",
                    callback_data=f"del_{idx}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="🔙 Отмена", callback_data="del_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ------------------------------------------------------------------
# ОБРАБОТЧИКИ КОМАНД И КНОПОК
# ------------------------------------------------------------------
@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    temp_fruit.pop(message.from_user.id, None)
    await message.answer(get_prices_text(), reply_markup=main_kb)


@dp.message(lambda m: m.text == "💰 Цены")
async def prices_cmd(message: Message):
    await message.answer(get_prices_text(), reply_markup=main_kb)


@dp.message(lambda m: m.text in PRICES)
async def choose_fruit(message: Message, state: FSMContext):
    await state.clear()
    fruit = message.text
    temp_fruit[message.from_user.id] = fruit
    await message.answer(
        f"Выбрано: {fruit}\nТеперь выбери вес или нажми «✏️ Свой вес»:",
        reply_markup=weight_kb,
    )


@dp.message(lambda m: m.text in WEIGHTS)
async def add_to_cart(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in temp_fruit:
        await message.answer("Сначала выбери фрукт из главного меню.", reply_markup=main_kb)
        return

    fruit = temp_fruit[user_id]
    weight_grams = WEIGHTS[message.text]
    weight_display, price = add_item_to_user_cart(user_id, fruit, weight_grams)
    total_w, products_total, final_total = get_cart_totals(user_id)

    await message.answer(
        f"✅ Добавлено: {fruit} {weight_display} — {price}₽\n\n"
        f"В корзине: {total_w} г ({total_w / 1000:.2f} кг)\n"
        f"Товары: {products_total}₽\n"
        f"Доставка: {DELIVERY_PRICE}₽\n"
        f"Итого: {final_total}₽",
        reply_markup=main_kb,
    )
    temp_fruit.pop(user_id, None)
    await state.clear()


@dp.message(lambda m: m.text == "✏️ Свой вес")
async def ask_custom_weight(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in temp_fruit:
        await message.answer("Сначала выбери фрукт из главного меню.", reply_markup=main_kb)
        return

    await state.set_state(WeightForm.custom_weight)
    await message.answer(
        "Напиши нужный вес. Например: 700 г, 0.7 кг или 2.4 кг.",
        reply_markup=weight_kb,
    )


@dp.message(lambda m: m.text == "🔙 Назад")
async def back_to_main(message: Message, state: FSMContext):
    user_id = message.from_user.id
    temp_fruit.pop(user_id, None)
    await state.clear()
    await message.answer("Возврат в главное меню", reply_markup=main_kb)


@dp.message(WeightForm.custom_weight)
async def add_custom_weight_to_cart(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in temp_fruit:
        await state.clear()
        await message.answer("Сначала выбери фрукт из главного меню.", reply_markup=main_kb)
        return

    weight_grams = parse_custom_weight(message.text)
    if weight_grams is None:
        await message.answer(
            "Не понял вес. Напиши, например: 700 г, 0.7 кг или 2.4 кг."
        )
        return

    fruit = temp_fruit[user_id]
    weight_display, price = add_item_to_user_cart(user_id, fruit, weight_grams)
    total_w, products_total, final_total = get_cart_totals(user_id)

    await message.answer(
        f"✅ Добавлено: {fruit} {weight_display} — {price}₽\n\n"
        f"В корзине: {total_w} г ({total_w / 1000:.2f} кг)\n"
        f"Товары: {products_total}₽\n"
        f"Доставка: {DELIVERY_PRICE}₽\n"
        f"Итого: {final_total}₽",
        reply_markup=main_kb,
    )
    temp_fruit.pop(user_id, None)
    await state.clear()


@dp.message(lambda m: m.text == "🛒 Корзина")
async def show_cart(message: Message):
    text, _ = get_cart_text(message.from_user.id)
    await message.answer(text)


@dp.message(lambda m: m.text == "🗑 Удалить товар")
async def delete_item(message: Message):
    user_id = message.from_user.id
    if user_id not in cart or not cart[user_id]:
        await message.answer("Корзина пуста, нечего удалять.")
        return

    keyboard = get_delete_keyboard(user_id)
    await message.answer("Нажми на товар, который хочешь удалить:", reply_markup=keyboard)

# ------------------------------------------------------------------
# УДАЛЕНИЕ ЧЕРЕЗ INLINE-КНОПКИ
# ------------------------------------------------------------------
@dp.callback_query(lambda c: c.data and c.data.startswith("del_"))
async def process_delete(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    if data == "del_cancel":
        await callback.message.delete()
        await callback.answer("Отмена")
        await callback.message.answer("Возврат в главное меню", reply_markup=main_kb)
        return

    try:
        idx = int(data.split("_")[1]) - 1
        if user_id in cart and 0 <= idx < len(cart[user_id]):
            removed = cart[user_id].pop(idx)
            await callback.answer(f"Удалено: {removed['name']} {removed['weight_str']}")

            new_kb = get_delete_keyboard(user_id)
            if new_kb:
                await callback.message.edit_reply_markup(reply_markup=new_kb)
                text, _ = get_cart_text(user_id)
                await callback.message.answer(text)
            else:
                await callback.message.delete()
                await callback.message.answer("Корзина теперь пуста.", reply_markup=main_kb)
        else:
            await callback.answer("Товар не найден")
    except Exception as e:
        await callback.answer("Ошибка")
        logging.error(e)

# ------------------------------------------------------------------
# ОФОРМЛЕНИЕ ЗАКАЗА (FSM)
# ------------------------------------------------------------------
@dp.message(lambda m: m.text == "✅ Оформить заказ")
async def start_order(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in cart or not cart[user_id]:
        await message.answer("Корзина пуста. Добавь фрукты.")
        return

    await state.set_state(OrderForm.name)
    await message.answer(
        "Для оформления заказа напиши своё Имя:",
        reply_markup=types.ReplyKeyboardRemove(),
    )


@dp.message(OrderForm.name)
async def order_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(OrderForm.surname)
    await message.answer("Теперь напиши свою Фамилию:")


@dp.message(OrderForm.surname)
async def order_surname(message: Message, state: FSMContext):
    await state.update_data(surname=message.text.strip())
    await state.set_state(OrderForm.phone)
    await message.answer("📞 Введи номер телефона (например, +7 999 123-45-67):")


@dp.message(OrderForm.phone)
async def order_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(OrderForm.address)
    await message.answer("🏠 Введи адрес доставки (улица, дом, квартира):")


@dp.message(OrderForm.address)
async def order_address(message: Message, state: FSMContext):
    user_id = message.from_user.id
    address = message.text.strip()
    data = await state.get_data()
    name = data.get("name", "")
    surname = data.get("surname", "")
    phone = data.get("phone", "")
    full_name = f"{name} {surname}".strip()

    if user_id not in cart or not cart[user_id]:
        await message.answer("Корзина пуста. Заказ не оформлен.", reply_markup=main_kb)
        await state.clear()
        return

    items = cart[user_id]
    items_text = "\n".join(
        f"{i['name']} — {i['weight_str']} — {i['price']}₽" for i in items
    )
    total_w, products_total, final_total = get_cart_totals(user_id)

    order_msg = (
        f"🆕 НОВЫЙ ЗАКАЗ!\n\n"
        f"👤 Имя: {full_name}\n"
        f"📞 Телефон: {phone}\n"
        f"🏠 Адрес: {address}\n"
        f"🆔 Telegram ID: {user_id}\n"
        f"👥 Username: @{message.from_user.username or 'нет'}\n\n"
        f"📦 Состав:\n{items_text}\n\n"
        f"⚖️ Вес: {total_w} г ({total_w / 1000:.2f} кг)\n"
        f"💰 Товары: {products_total}₽\n"
        f"🚚 Доставка: {DELIVERY_PRICE}₽\n"
        f"✅ Итого к оплате: {final_total}₽\n"
        f"💸 Оплата наличными при получении."
    )

    try:
        await bot.send_message(ADMIN_ID, order_msg)
        await message.answer(
            "✅ Заказ отправлен! Продавец свяжется с тобой для подтверждения.\nСпасибо за покупку!",
            reply_markup=main_kb,
        )
        cart[user_id] = []
        await state.clear()
    except Exception as e:
        await message.answer("❌ Ошибка при отправке заказа. Попробуй позже.", reply_markup=main_kb)
        logging.error(e)


@dp.message(lambda m: m.text == "📞 Контакты")
async def contacts(message: Message):
    await message.answer(CONTACT_TEXT)

# ------------------------------------------------------------------
# ЗАПУСК
# ------------------------------------------------------------------
async def main():
    logging.info("🍓 FreshBerry запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
