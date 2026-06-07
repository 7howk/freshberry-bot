import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import asyncio

# ------------------------------------------------------------------
# НАСТРОЙКИ (замени своими данными)
# ------------------------------------------------------------------
BOT_TOKEN = "8286121562:AAGoiSnMvDFms15mmxyFz6uCBZ1yumeAo0o"   # Твой токен
ADMIN_ID = 1010873079   # Твой ID (узнай у @userinfobot)

# Контакты продавца
SELLER_TELEGRAM = "@jhowk"
SELLER_PHONE = "+7 911 824-02-90"

# Товары и цены (за 1 кг)
PRODUCTS = {
    "🍓 Клубника": 800,
    "🍒 Вишня": 1200,
    "🍒 Черешня": 1500,
    "🍑 Персик": 900,
    "🍊 Абрикос": 700,
}

# Веса
WEIGHTS = {
    "500 г": 500,
    "1 кг": 1000,
    "1.5 кг": 1500,
    "2 кг": 2000,
    "✏️ Свой вес": 0,
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Корзина
carts = {}
temp = {}   # временное хранилище {user_id: {"fruit":..., "waiting": True/False}}

# ------------------------------------------------------------------
# КЛАВИАТУРЫ
# ------------------------------------------------------------------
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍓 Клубника"), KeyboardButton(text="🍒 Вишня"), KeyboardButton(text="🍒 Черешня")],
        [KeyboardButton(text="🍑 Персик"), KeyboardButton(text="🍊 Абрикос")],
        [KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="✅ Оформить заказ")],
        [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="💰 Цены")]
    ],
    resize_keyboard=True
)

def weight_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="500 г"), KeyboardButton(text="1 кг"), KeyboardButton(text="1.5 кг")],
            [KeyboardButton(text="2 кг"), KeyboardButton(text="✏️ Свой вес"), KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

# ------------------------------------------------------------------
# ОБРАБОТЧИКИ
# ------------------------------------------------------------------
@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(
        "🍓 FreshBerry — свежие фрукты с доставкой\n\n"
        "Выбери фрукт из меню, затем укажи вес.\n\n"
        "💰 Цены за 1 кг:\n"
        "🍓 Клубника — 800₽\n"
        "🍒 Вишня — 1200₽\n"
        "🍒 Черешня — 1500₽\n"
        "🍑 Персик — 900₽\n"
        "🍊 Абрикос — 700₽",
        reply_markup=main_menu
    )

# Выбор фрукта
@dp.message(lambda m: m.text in PRODUCTS)
async def fruit_selected(message: Message):
    fruit = message.text
    temp[message.from_user.id] = {"fruit": fruit}
    await message.answer(f"Выбрано: {fruit}\nТеперь выбери вес:", reply_markup=weight_keyboard())

# Обработка веса (кнопки)
@dp.message(lambda m: m.text in WEIGHTS or m.text in ["✏️ Свой вес", "🔙 Назад"])
async def weight_selected(message: Message):
    user_id = message.from_user.id

    if user_id not in temp or "fruit" not in temp[user_id]:
        await message.answer("Сначала выбери фрукт из главного меню.", reply_markup=main_menu)
        return

    fruit = temp[user_id]["fruit"]
    price_kg = PRODUCTS[fruit]

    # Назад
    if message.text == "🔙 Назад":
        del temp[user_id]
        await message.answer("Возврат в главное меню.", reply_markup=main_menu)
        return

    # Свой вес
    if message.text == "✏️ Свой вес":
        temp[user_id]["waiting"] = True
        await message.answer("Напиши вес в граммах (только цифры, например 300 или 1250):")
        return

    # Обычные веса
    weight = WEIGHTS[message.text]
    cost = int((weight / 1000) * price_kg)
    weight_str = f"{weight}г" if weight < 1000 else f"{weight//1000}кг"

    # Добавляем в корзину
    if user_id not in carts:
        carts[user_id] = []
    carts[user_id].append({"name": fruit, "weight": weight, "str": weight_str, "price": cost})

    total_w = sum(i["weight"] for i in carts[user_id])
    total_p = sum(i["price"] for i in carts[user_id])
    await message.answer(
        f"✅ Добавлено: {fruit} {weight_str} — {cost}₽\n\n"
        f"В корзине: {total_w}г ({total_w/1000:.1f}кг) на сумму {total_p}₽",
        reply_markup=main_menu
    )
    del temp[user_id]

# Ручной ввод веса (число)
@dp.message()
async def custom_weight_input(message: Message):
    user_id = message.from_user.id
    if user_id not in temp or not temp[user_id].get("waiting"):
        return

    fruit = temp[user_id]["fruit"]
    price_kg = PRODUCTS[fruit]
    del temp[user_id]

    try:
        weight = int(message.text.strip())
        if weight < 100:
            await message.answer("Минимум 100 грамм. Попробуй снова.", reply_markup=main_menu)
            return
        if weight > 5000:
            await message.answer("Максимум 5 кг. Попробуй снова.", reply_markup=main_menu)
            return

        cost = int((weight / 1000) * price_kg)
        weight_str = f"{weight}г" if weight < 1000 else f"{weight//1000}кг" if weight % 1000 == 0 else f"{weight/1000:.1f}кг"

        if user_id not in carts:
            carts[user_id] = []
        carts[user_id].append({"name": fruit, "weight": weight, "str": weight_str, "price": cost})

        total_w = sum(i["weight"] for i in carts[user_id])
        total_p = sum(i["price"] for i in carts[user_id])
        await message.answer(
            f"✅ Добавлено: {fruit} {weight_str} — {cost}₽\n\n"
            f"В корзине: {total_w}г ({total_w/1000:.1f}кг) на сумму {total_p}₽",
            reply_markup=main_menu
        )
    except ValueError:
        await message.answer("Не понял. Напиши число, например 300.", reply_markup=main_menu)

# Корзина
@dp.message(lambda m: m.text == "🛒 Корзина")
async def show_cart(message: Message):
    user_id = message.from_user.id
    if user_id not in carts or not carts[user_id]:
        await message.answer("Корзина пуста.")
        return
    items = carts[user_id]
    text = "🛒 Твоя корзина:\n\n"
    for i, it in enumerate(items, 1):
        text += f"{i}. {it['name']} — {it['str']} — {it['price']}₽\n"
    total_w = sum(i["weight"] for i in items)
    total_p = sum(i["price"] for i in items)
    text += f"\nОбщий вес: {total_w}г ({total_w/1000:.1f}кг)\nИтого: {total_p}₽"
    await message.answer(text)

# Оформление заказа
@dp.message(lambda m: m.text == "✅ Оформить заказ")
async def checkout(message: Message):
    user_id = message.from_user.id
    if user_id not in carts or not carts[user_id]:
        await message.answer("Корзина пуста. Добавь фрукты.")
        return
    username = message.from_user.username or "нет"
    name = message.from_user.full_name
    items = carts[user_id]

    items_text = "\n".join(f"{i['name']} — {i['str']} — {i['price']}₽" for i in items)
    total_w = sum(i["weight"] for i in items)
    total_p = sum(i["price"] for i in items)

    order = f"🆕 НОВЫЙ ЗАКАЗ!\n\nПокупатель: {name} (@{username})\nID: {user_id}\n\nСостав:\n{items_text}\n\nВес: {total_w}г ({total_w/1000:.1f}кг)\nСумма: {total_p}₽\nОплата: наличные при получении."
    try:
        await bot.send_message(ADMIN_ID, order)
        await message.answer("✅ Заказ отправлен продавцу! Он свяжется с тобой.")
        carts[user_id] = []
    except Exception as e:
        await message.answer("Ошибка при отправке.")
        logging.error(e)

# Контакты
@dp.message(lambda m: m.text == "📞 Контакты")
async def contacts(message: Message):
    await message.answer(f"📞 Связаться с нами:\nTelegram: {SELLER_TELEGRAM}\nТелефон: {SELLER_PHONE}")

# Цены
@dp.message(lambda m: m.text == "💰 Цены")
async def prices(message: Message):
    text = "💰 Цены за 1 кг:\n\n"
    for name, price in PRODUCTS.items():
        text += f"{name} — {price}₽\n"
    text += "\nДоступные веса: 500г, 1кг, 1.5кг, 2кг или свой (100г–5кг)."
    await message.answer(text)

async def main():
    logging.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())