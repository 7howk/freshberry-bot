import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import asyncio

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8286121562:AAGoiSnMvDFms15mmxyFz6uCBZlyumeAoOo"
ADMIN_ID = 1010873079  # ТВОЙ ID (узнай у @userinfobot)

# Контакты продавца
SELLER_TELEGRAM = "@твой_никнейм"
SELLER_PHONE = "+7 999 123-45-67"

# Товары и цены за кг
PRODUCTS = {
    "🍓 Клубника": 800,
    "🍒 Вишня": 1200,
    "🍒 Черешня": 1500,
    "🍑 Персик": 900,
    "🍊 Абрикос": 700,
}

# Доступные веса (граммы)
WEIGHTS = {
    "500 г": 500,
    "1 кг": 1000,
    "1.5 кг": 1500,
    "2 кг": 2000,
    "✏️ Свой вес": 0,  # специальное значение
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Корзина: {user_id: [{"name":..., "weight":..., "price":...}]}
carts = {}

# Временное состояние для ручного ввода веса
temp_weight = {}

# ========== КЛАВИАТУРЫ ==========
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍓 Клубника"), KeyboardButton(text="🍒 Вишня"), KeyboardButton(text="🍒 Черешня")],
        [KeyboardButton(text="🍑 Персик"), KeyboardButton(text="🍊 Абрикос")],
        [KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="✅ Оформить заказ")],
        [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="💰 Цены")]
    ],
    resize_keyboard=True
)

def weight_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="500 г"), KeyboardButton(text="1 кг"), KeyboardButton(text="1.5 кг")],
            [KeyboardButton(text="2 кг"), KeyboardButton(text="✏️ Свой вес"), KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

# ========== ОБРАБОТЧИКИ ==========
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "🍓 Добро пожаловать в FreshBerry!\n\n"
        "Выберите фрукт из меню 👇\n"
        "После выбора укажите вес.",
        reply_markup=main_menu
    )

# Выбор фрукта
@dp.message(lambda m: m.text in PRODUCTS)
async def choose_fruit(message: Message):
    fruit = message.text
    # Запоминаем, какой фрукт выбрал пользователь
    temp_weight[message.from_user.id] = {"fruit": fruit}
    await message.answer(
        f"Вы выбрали {fruit}. Теперь выберите вес:",
        reply_markup=weight_menu()
    )

# Обработка веса
@dp.message(lambda m: m.text in WEIGHTS or m.text == "✏️ Свой вес" or m.text == "🔙 Назад")
async def handle_weight(message: Message):
    user_id = message.from_user.id
    if user_id not in temp_weight or "fruit" not in temp_weight[user_id]:
        await message.answer("Сначала выберите фрукт из главного меню.", reply_markup=main_menu)
        return

    fruit = temp_weight[user_id]["fruit"]
    price_per_kg = PRODUCTS[fruit]

    # Назад
    if message.text == "🔙 Назад":
        del temp_weight[user_id]
        await message.answer("Возврат в главное меню.", reply_markup=main_menu)
        return

    # Свой вес
    if message.text == "✏️ Свой вес":
        await message.answer("Напишите вес в граммах (только цифры, например 300):")
        temp_weight[user_id]["waiting"] = True
        return

    # Готовый вес
    weight_text = message.text
    weight = WEIGHTS[weight_text]
    cost = int((weight / 1000) * price_per_kg)
    weight_str = f"{weight}г" if weight < 1000 else f"{weight//1000}кг"

    # Добавляем в корзину
    if user_id not in carts:
        carts[user_id] = []
    carts[user_id].append({
        "name": fruit,
        "weight": weight,
        "weight_str": weight_str,
        "price": cost
    })

    total_weight = sum(i["weight"] for i in carts[user_id])
    total_price = sum(i["price"] for i in carts[user_id])

    await message.answer(
        f"✅ Добавлено: {fruit} {weight_str} — {cost}₽\n\n"
        f"В вашей корзине: {total_weight}г ({total_weight/1000:.1f}кг) на сумму {total_price}₽",
        reply_markup=main_menu
    )
    del temp_weight[user_id]

# Ручной ввод веса
@dp.message()
async def custom_weight(message: Message):
    user_id = message.from_user.id
    if user_id not in temp_weight or not temp_weight[user_id].get("waiting"):
        return

    fruit = temp_weight[user_id]["fruit"]
    price_per_kg = PRODUCTS[fruit]
    del temp_weight[user_id]

    try:
        weight = int(message.text.strip())
        if weight < 100:
            await message.answer("Минимальный вес 100 грамм. Попробуйте снова.", reply_markup=main_menu)
            return
        if weight > 5000:
            await message.answer("Максимальный вес 5 кг. Попробуйте снова.", reply_markup=main_menu)
            return

        cost = int((weight / 1000) * price_per_kg)
        weight_str = f"{weight}г" if weight < 1000 else f"{weight//1000}кг"

        if user_id not in carts:
            carts[user_id] = []
        carts[user_id].append({
            "name": fruit,
            "weight": weight,
            "weight_str": weight_str,
            "price": cost
        })

        total_weight = sum(i["weight"] for i in carts[user_id])
        total_price = sum(i["price"] for i in carts[user_id])

        await message.answer(
            f"✅ Добавлено: {fruit} {weight_str} — {cost}₽\n\n"
            f"В корзине: {total_weight}г ({total_weight/1000:.1f}кг) на сумму {total_price}₽",
            reply_markup=main_menu
        )
    except ValueError:
        await message.answer("Не удалось распознать вес. Напишите только число (например 750).", reply_markup=main_menu)

# Корзина
@dp.message(lambda m: m.text == "🛒 Корзина")
async def show_cart(message: Message):
    user_id = message.from_user.id
    if user_id not in carts or not carts[user_id]:
        await message.answer("Корзина пуста. Добавьте фрукты через главное меню.")
        return

    items = carts[user_id]
    text = "🛒 Ваша корзина:\n\n"
    for i, item in enumerate(items, 1):
        text += f"{i}. {item['name']} — {item['weight_str']} — {item['price']}₽\n"
    total_weight = sum(i["weight"] for i in items)
    total_price = sum(i["price"] for i in items)
    text += f"\nОбщий вес: {total_weight}г ({total_weight/1000:.1f}кг)\nИтого: {total_price}₽"
    await message.answer(text)

# Оформить заказ
@dp.message(lambda m: m.text == "✅ Оформить заказ")
async def checkout(message: Message):
    user_id = message.from_user.id
    if user_id not in carts or not carts[user_id]:
        await message.answer("Корзина пуста. Добавьте фрукты.")
        return

    username = message.from_user.username or "нет"
    name = message.from_user.full_name
    items = carts[user_id]

    items_text = "\n".join(f"{i['name']} — {i['weight_str']} — {i['price']}₽" for i in items)
    total_weight = sum(i["weight"] for i in items)
    total_price = sum(i["price"] for i in items)

    order = (
        f"🆕 НОВЫЙ ЗАКАЗ!\n\n"
        f"Покупатель: {name} (@{username})\n"
        f"ID: {user_id}\n\n"
        f"Состав:\n{items_text}\n\n"
        f"Вес: {total_weight}г ({total_weight/1000:.1f}кг)\n"
        f"Сумма: {total_price}₽\n"
        f"Оплата: наличные при получении."
    )
    try:
        await bot.send_message(ADMIN_ID, order)
        await message.answer("✅ Заказ отправлен продавцу! Он свяжется с вами.")
        carts[user_id] = []
    except Exception as e:
        await message.answer("Ошибка при отправке заказа. Попробуйте позже.")
        logging.error(e)

# Контакты
@dp.message(lambda m: m.text == "📞 Контакты")
async def contacts(message: Message):
    await message.answer(
        f"Связаться с нами:\n\n"
        f"Telegram: {SELLER_TELEGRAM}\n"
        f"Телефон: {SELLER_PHONE}\n\n"
        f"Работаем с 9 до 21."
    )

# Цены
@dp.message(lambda m: m.text == "💰 Цены")
async def prices(message: Message):
    text = "💰 Цены за 1 кг:\n\n"
    for name, price in PRODUCTS.items():
        text += f"{name} — {price}₽\n"
    text += "\nМинимальный заказ: 100г. Вес: 500г, 1кг, 1.5кг, 2кг или свой."
    await message.answer(text)

async def main():
    logging.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())