import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery
import asyncio

# ========== НАСТРОЙКИ (ЗАМЕНИ НА СВОИ) ==========
BOT_TOKEN = os.getenv('BOT_TOKEN')   # на Bothost уже есть
ADMIN_ID = int(os.getenv('ADMIN_ID', 1010873079))  # ТВОЙ ID (узнай у @userinfobot)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Товары: ключ -> (название, цена за кг)
PRODUCTS = {
    "strawberry": ("🍓 Клубника", 800),
    "cherry": ("🍒 Вишня", 1200),
    "sweet_cherry": ("🍒 Черешня", 1500),
    "peach": ("🍑 Персик", 900),
    "apricot": ("🍊 Абрикос", 700),
}

# Доступные веса в граммах
WEIGHTS = [500, 1000, 1500, 2000]

# Корзина: {user_id: [{"name":..., "weight":..., "price":...}]}
carts = {}

# Главная клавиатура (reply-кнопки)
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍓 Клубника"), KeyboardButton(text="🍒 Вишня"), KeyboardButton(text="🍒 Черешня")],
        [KeyboardButton(text="🍑 Персик"), KeyboardButton(text="🍊 Абрикос")],
        [KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="✅ Оформить заказ")],
        [KeyboardButton(text="📞 Связаться с продавцом"), KeyboardButton(text="💰 Цены")]
    ],
    resize_keyboard=True
)

# Функция создаёт инлайн-кнопки для выбора веса конкретного товара
def weight_buttons(product_key):
    name, price_per_kg = PRODUCTS[product_key]
    buttons = []
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
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"{product_key}:{w}")])
    buttons.append([InlineKeyboardButton(text="✏️ Свой вес", callback_data=f"custom:{product_key}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# -------------------- ОБРАБОТЧИКИ --------------------
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "🍓 <b>FreshBerry — свежие фрукты с доставкой</b>\n\n"
        "Выбери фрукт из меню ниже. После выбора появится выбор веса.\n\n"
        "<b>💰 Цены за 1 кг:</b>\n"
        "🍓 Клубника — 800₽\n"
        "🍒 Вишня — 1200₽\n"
        "🍒 Черешня — 1500₽\n"
        "🍑 Персик — 900₽\n"
        "🍊 Абрикос — 700₽\n\n"
        "📦 Доступные веса: 500г, 1кг, 1.5кг, 2кг или свой.\n"
        "💸 Оплата наличными при получении.",
        reply_markup=main_kb,
        parse_mode="HTML"
    )

# Выбор фрукта из главного меню
@dp.message(lambda msg: msg.text in ["🍓 Клубника", "🍒 Вишня", "🍒 Черешня", "🍑 Персик", "🍊 Абрикос"])
async def select_fruit(message: Message):
    fruit_name = message.text
    mapping = {
        "🍓 Клубника": "strawberry",
        "🍒 Вишня": "cherry",
        "🍒 Черешня": "sweet_cherry",
        "🍑 Персик": "peach",
        "🍊 Абрикос": "apricot",
    }
    key = mapping[fruit_name]
    name, price = PRODUCTS[key]
    await message.answer(
        f"{name} — {price}₽/кг\n\nВыбери вес:",
        reply_markup=weight_buttons(key)
    )

# Обработка всех инлайн-кнопок
@dp.callback_query()
async def handle_callback(call: CallbackQuery):
    user_id = call.from_user.id
    data = call.data

    # Назад
    if data == "back":
        await call.message.answer("Главное меню:", reply_markup=main_kb)
        await call.answer()
        return

    # Свой вес
    if data.startswith("custom:"):
        product_key = data.split(":")[1]
        # Запоминаем, для какого товара ожидаем вес
        if "temp" not in carts:
            carts["temp"] = {}
        carts["temp"][user_id] = product_key
        await call.message.answer(
            "✏️ <b>Введи свой вес:</b>\n\n"
            "Напиши число в граммах (только цифры), например:\n"
            "• 750\n"
            "• 1200\n"
            "• 300\n\n"
            "Минимум 100 г, максимум 5000 г (5 кг).",
            parse_mode="HTML"
        )
        await call.answer()
        return

    # Обычный выбор веса (формат "strawberry:500")
    if ":" in data:
        product_key, weight_str = data.split(":")
        weight = int(weight_str)
        name, price_per_kg = PRODUCTS[product_key]
        cost = int((weight / 1000) * price_per_kg)
        weight_text = f"{weight}г" if weight < 1000 else f"{weight//1000}кг"

        # Добавляем в корзину
        if user_id not in carts:
            carts[user_id] = []
        carts[user_id].append({
            "name": name,
            "weight": weight,
            "weight_text": weight_text,
            "price": cost
        })

        # Подсчёт общего веса и суммы
        total_weight = sum(item["weight"] for item in carts[user_id])
        total_price = sum(item["price"] for item in carts[user_id])

        await call.message.answer(
            f"✅ <b>Добавлено!</b>\n\n"
            f"{name} — {weight_text} — {cost}₽\n\n"
            f"📦 <b>Ваша корзина:</b>\n"
            f"• Общий вес: {total_weight}г ({total_weight/1000:.1f}кг)\n"
            f"• Общая сумма: {total_price}₽\n\n"
            f"Можете добавить ещё или нажать «🛒 Корзина».",
            reply_markup=main_kb,
            parse_mode="HTML"
        )
        await call.answer()
        return

    await call.answer("Неизвестная команда")

# Обработка ручного ввода веса (после "Свой вес")
@dp.message()
async def custom_weight(message: Message):
    user_id = message.from_user.id
    # Проверяем, ожидаем ли мы ввод веса
    if "temp" not in carts or user_id not in carts["temp"]:
        return
    product_key = carts["temp"].pop(user_id)

    text = message.text.strip()
    try:
        weight = int(text)
        if weight < 100:
            await message.answer("❌ Минимальный вес — 100 грамм. Попробуйте ещё раз.")
            return
        if weight > 5000:
            await message.answer("❌ Максимальный вес — 5000 грамм (5 кг). Попробуйте ещё раз.")
            return

        name, price_per_kg = PRODUCTS[product_key]
        cost = int((weight / 1000) * price_per_kg)
        weight_text = f"{weight}г" if weight < 1000 else f"{weight//1000}кг" if weight % 1000 == 0 else f"{weight/1000:.1f}кг"

        if user_id not in carts:
            carts[user_id] = []
        carts[user_id].append({
            "name": name,
            "weight": weight,
            "weight_text": weight_text,
            "price": cost
        })

        total_weight = sum(item["weight"] for item in carts[user_id])
        total_price = sum(item["price"] for item in carts[user_id])

        await message.answer(
            f"✅ <b>Добавлено!</b>\n\n"
            f"{name} — {weight_text} — {cost}₽\n\n"
            f"📦 <b>В корзине:</b> {total_weight}г ({total_weight/1000:.1f}кг) на сумму {total_price}₽",
            reply_markup=main_kb,
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ Не распознано. Введите только число, например: 750")

# Показать корзину
@dp.message(lambda msg: msg.text == "🛒 Корзина")
async def show_cart(message: Message):
    user_id = message.from_user.id
    if user_id not in carts or not carts[user_id]:
        await message.answer("🛒 Корзина пуста. Выберите фрукты в главном меню.")
        return

    items = carts[user_id]
    text = "🛒 <b>Ваша корзина:</b>\n\n"
    for i, item in enumerate(items, 1):
        text += f"{i}. {item['name']} — {item['weight_text']} — {item['price']}₽\n"
    total_weight = sum(i["weight"] for i in items)
    total_price = sum(i["price"] for i in items)
    text += f"\n📦 <b>Общий вес:</b> {total_weight}г ({total_weight/1000:.1f}кг)\n💰 <b>Итого:</b> {total_price}₽"
    await message.answer(text, parse_mode="HTML")

# Оформить заказ
@dp.message(lambda msg: msg.text == "✅ Оформить заказ")
async def checkout(message: Message):
    user_id = message.from_user.id
    if user_id not in carts or not carts[user_id]:
        await message.answer("❌ Корзина пуста. Добавьте фрукты перед оформлением.")
        return

    username = message.from_user.username or "нет"
    name = message.from_user.full_name
    items = carts[user_id]

    items_text = "\n".join(f"{i['name']} — {i['weight_text']} — {i['price']}₽" for i in items)
    total_weight = sum(i["weight"] for i in items)
    total_price = sum(i["price"] for i in items)

    order_msg = (
        f"🆕 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
        f"👤 {name} (@{username})\n"
        f"🆔 ID: {user_id}\n\n"
        f"📦 <b>Состав:</b>\n{items_text}\n\n"
        f"⚖️ Вес: {total_weight}г ({total_weight/1000:.1f}кг)\n"
        f"💰 Сумма: {total_price}₽\n"
        f"💸 Оплата наличными при получении."
    )
    try:
        await bot.send_message(ADMIN_ID, order_msg, parse_mode="HTML")
        await message.answer(
            "✅ <b>Заказ успешно отправлен!</b>\n\n"
            "Спасибо! Продавец свяжется с вами для подтверждения.\n\n"
            "Если остались вопросы, нажмите «📞 Связаться с продавцом».",
            parse_mode="HTML"
        )
        carts[user_id] = []  # очищаем корзину
    except Exception as e:
        await message.answer("❌ Ошибка при отправке заказа. Попробуйте позже.")
        print(e)

# Связаться с продавцом
@dp.message(lambda msg: msg.text == "📞 Связаться с продавцом")
async def contact(message: Message):
    await message.answer(
        "📞 <b>Связаться с нами</b>\n\n"
        "• <b>Telegram:</b> @твой_никнейм\n"
        "• <b>Телефон / WhatsApp:</b> +7 999 123-45-67\n"
        "• <b>Email:</b> freshberry@example.com\n\n"
        "Мы работаем с 9:00 до 21:00. Напишите или позвоните — ответим быстро! 🍓",
        parse_mode="HTML"
    )

# Цены
@dp.message(lambda msg: msg.text == "💰 Цены")
async def prices(message: Message):
    text = "💰 <b>Прайс-лист (за 1 кг)</b>\n\n"
    for key, (name, price) in PRODUCTS.items():
        text += f"{name} — {price}₽\n"
    text += "\n📦 <b>Доступные веса:</b> 500г, 1кг, 1.5кг, 2кг или свой (100г – 5кг).\n"
    text += "💸 Оплата наличными при получении."
    await message.answer(text, parse_mode="HTML")

async def main():
    print("🍓 Бот FreshBerry запущен и работает корректно!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())