import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery
import asyncio

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.getenv('BOT_TOKEN')   # на Bothost уже есть
ADMIN_ID = int(os.getenv('ADMIN_ID', 1010873079))  # замени на свой ID (узнай у @userinfobot)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Товары и цены за 1 кг
PRODUCTS = {
    "strawberry": {"name": "🍓 Клубника", "price": 800},
    "cherry": {"name": "🍒 Вишня", "price": 1200},
    "sweet_cherry": {"name": "🍒 Черешня", "price": 1500},
    "peach": {"name": "🍑 Персик", "price": 900},
    "apricot": {"name": "🍊 Абрикос", "price": 700},
}

# Доступные веса (в граммах) - только нужные
WEIGHTS = [500, 1000, 1500, 2000]   # 500г, 1кг, 1.5кг, 2кг

# Корзина: {user_id: [{"name": "🍓 Клубника", "weight": 500, "price": 400}]}
carts = {}

# Временные данные для ручного ввода веса
temp_user_product = {}

# ========== КЛАВИАТУРЫ (reply-кнопки внизу) ==========
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍓 Клубника"), KeyboardButton(text="🍒 Вишня"), KeyboardButton(text="🍒 Черешня")],
        [KeyboardButton(text="🍑 Персик"), KeyboardButton(text="🍊 Абрикос")],
        [KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="✅ Оформить заказ")],
        [KeyboardButton(text="📞 Связаться с продавцом"), KeyboardButton(text="💰 Цены")]
    ],
    resize_keyboard=True
)

def get_weight_keyboard(product_key):
    """Инлайн-кнопки для выбора веса"""
    buttons = []
    for w in WEIGHTS:
        price = int((w / 1000) * PRODUCTS[product_key]["price"])
        if w == 1000:
            text = f"1 кг — {price}₽"
        elif w == 1500:
            text = f"1.5 кг — {price}₽"
        elif w == 2000:
            text = f"2 кг — {price}₽"
        else:
            text = f"{w} г — {price}₽"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"{product_key}_{w}")])
    # Кнопка "Свой вес"
    buttons.append([InlineKeyboardButton(text="✏️ Свой вес", callback_data=f"custom_{product_key}")])
    # Кнопка "Назад"
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== ОБРАБОТЧИКИ ==========
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "🍓 Добро пожаловать в <b>FreshBerry</b>!\n\n"
        "Выбери фрукт из меню 👇\n\n"
        "💰 <b>Цены за 1 кг:</b>\n"
        "🍓 Клубника — 800₽\n"
        "🍒 Вишня — 1200₽\n"
        "🍒 Черешня — 1500₽\n"
        "🍑 Персик — 900₽\n"
        "🍊 Абрикос — 700₽\n\n"
        "📦 <b>Доступные веса:</b> 500г, 1кг, 1.5кг, 2кг (можно ввести свой).\n"
        "Оплата наличными при получении.",
        reply_markup=main_menu,
        parse_mode="HTML"
    )

# Выбор фрукта из главного меню
@dp.message(lambda message: message.text in ["🍓 Клубника", "🍒 Вишня", "🍒 Черешня", "🍑 Персик", "🍊 Абрикос"])
async def fruit_selected(message: Message):
    fruit_map = {
        "🍓 Клубника": "strawberry",
        "🍒 Вишня": "cherry",
        "🍒 Черешня": "sweet_cherry",
        "🍑 Персик": "peach",
        "🍊 Абрикос": "apricot",
    }
    key = fruit_map[message.text]
    await message.answer(
        f"{PRODUCTS[key]['name']} — {PRODUCTS[key]['price']}₽/кг\n\nВыбери вес:",
        reply_markup=get_weight_keyboard(key)
    )

# Обработка инлайн-кнопок (вес, свой вес, назад)
@dp.callback_query()
async def handle_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    # Назад в главное меню
    if data == "back_to_menu":
        await callback.message.answer("🔙 Возврат в главное меню", reply_markup=main_menu)
        await callback.answer()
        return

    # Свой вес
    if data.startswith("custom_"):
        product_key = data.split("_")[1]
        temp_user_product[user_id] = product_key
        await callback.message.answer(
            "✏️ <b>Введи свой вес</b>\n\n"
            "Напиши число в <b>граммах</b> или <b>килограммах</b>:\n"
            "• 750   → 750 грамм\n"
            "• 1.2   → 1.2 кг (1200 грамм)\n"
            "• 1.5   → 1.5 кг\n\n"
            "Минимум 100 г, максимум 5 кг.",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    # Обычный вес (например "strawberry_500")
    if "_" in data and not data.startswith("custom"):
        parts = data.split("_")
        if len(parts) == 2:
            product_key = parts[0]
            weight = int(parts[1])
            product = PRODUCTS[product_key]
            price = int((weight / 1000) * product["price"])
            weight_text = f"{weight}г" if weight < 1000 else f"{weight//1000}кг"

            # Добавляем в корзину
            if user_id not in carts:
                carts[user_id] = []
            carts[user_id].append({
                "name": product["name"],
                "weight": weight,
                "weight_text": weight_text,
                "price": price
            })

            total_weight = sum(item["weight"] for item in carts[user_id])
            total_price = sum(item["price"] for item in carts[user_id])

            await callback.message.answer(
                f"✅ <b>Добавлено!</b>\n\n"
                f"{product['name']} — {weight_text} — {price}₽\n\n"
                f"📦 <b>В корзине сейчас:</b>\n"
                f"Вес: {total_weight}г ({total_weight/1000:.1f}кг)\n"
                f"Сумма: {total_price}₽\n\n"
                f"Можешь добавить ещё или нажать «🛒 Корзина».",
                reply_markup=main_menu,
                parse_mode="HTML"
            )
            await callback.answer()
            return

# Обработка ручного ввода веса (после нажатия "Свой вес")
@dp.message()
async def custom_weight_input(message: Message):
    user_id = message.from_user.id
    if user_id not in temp_user_product:
        return  # не ожидаем ввод веса

    product_key = temp_user_product.pop(user_id)
    text = message.text.strip().lower().replace(" ", "").replace("кг", "").replace("г", "").replace(",", ".")
    try:
        if "." in text:
            weight_kg = float(text)
            weight = int(weight_kg * 1000)
        else:
            weight = int(text)

        if weight < 100:
            await message.answer("❌ Минимальный вес — 100 грамм. Попробуй ещё раз.")
            return
        if weight > 5000:
            await message.answer("❌ Максимальный вес — 5 кг. Попробуй ещё раз.")
            return

        product = PRODUCTS[product_key]
        price = int((weight / 1000) * product["price"])
        weight_text = f"{weight}г" if weight < 1000 else f"{weight//1000}кг" if weight % 1000 == 0 else f"{weight/1000:.1f}кг"

        if user_id not in carts:
            carts[user_id] = []
        carts[user_id].append({
            "name": product["name"],
            "weight": weight,
            "weight_text": weight_text,
            "price": price
        })

        total_weight = sum(item["weight"] for item in carts[user_id])
        total_price = sum(item["price"] for item in carts[user_id])

        await message.answer(
            f"✅ <b>Добавлено!</b>\n\n"
            f"{product['name']} — {weight_text} — {price}₽\n\n"
            f"📦 <b>В корзине:</b> {total_weight}г ({total_weight/1000:.1f}кг) на сумму {total_price}₽",
            reply_markup=main_menu,
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ Не удалось распознать вес. Напиши число, например: 750 или 1.2")

# Показать корзину
@dp.message(lambda message: message.text == "🛒 Корзина")
async def show_cart(message: Message):
    user_id = message.from_user.id
    if user_id not in carts or not carts[user_id]:
        await message.answer("🛒 Корзина пуста. Выбери фрукты из меню 👆")
        return

    text = "🛒 <b>Твоя корзина</b>\n\n"
    for i, item in enumerate(carts[user_id], 1):
        text += f"{i}. {item['name']} — {item['weight_text']} — {item['price']}₽\n"
    total_weight = sum(item["weight"] for item in carts[user_id])
    total_price = sum(item["price"] for item in carts[user_id])
    text += f"\n📦 Общий вес: {total_weight}г ({total_weight/1000:.1f}кг)\n💰 <b>Итого: {total_price}₽</b>"
    await message.answer(text, parse_mode="HTML")

# Оформить заказ
@dp.message(lambda message: message.text == "✅ Оформить заказ")
async def checkout(message: Message):
    user_id = message.from_user.id
    if user_id not in carts or not carts[user_id]:
        await message.answer("❌ Корзина пуста. Сначала добавь фрукты.")
        return

    username = message.from_user.username or "нет"
    name = message.from_user.full_name

    items_text = ""
    for item in carts[user_id]:
        items_text += f"{item['name']} — {item['weight_text']} — {item['price']}₽\n"
    total_weight = sum(item["weight"] for item in carts[user_id])
    total_price = sum(item["price"] for item in carts[user_id])

    order_msg = (
        f"🆕 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
        f"👤 {name} (@{username})\n"
        f"🆔 ID: {user_id}\n\n"
        f"📦 <b>Состав заказа:</b>\n{items_text}\n"
        f"⚖️ Общий вес: {total_weight}г ({total_weight/1000:.1f}кг)\n"
        f"💰 <b>Сумма: {total_price}₽</b>\n\n"
        f"💸 Оплата наличными при получении."
    )
    try:
        await bot.send_message(ADMIN_ID, order_msg, parse_mode="HTML")
        await message.answer(
            "✅ <b>Заказ отправлен!</b>\n\n"
            "Спасибо! Продавец свяжется с вами в ближайшее время для подтверждения.\n\n"
            "Если у вас есть вопросы, нажмите «📞 Связаться с продавцом».",
            parse_mode="HTML"
        )
        carts[user_id] = []  # очистка корзины
    except Exception as e:
        await message.answer("❌ Ошибка при отправке заказа. Попробуйте позже.")
        print(e)

# Связаться с продавцом
@dp.message(lambda message: message.text == "📞 Связаться с продавцом")
async def contact_seller(message: Message):
    await message.answer(
        "📞 <b>Как с нами связаться?</b>\n\n"
        "• <b>Telegram:</b> @твой_никнейм\n"
        "• <b>Телефон / WhatsApp:</b> +7 999 123-45-67\n"
        "• <b>Email:</b> freshberry@example.com\n\n"
        "Мы на связи с 9:00 до 21:00. Всегда рады помочь! 🍓",
        parse_mode="HTML"
    )

# Цены
@dp.message(lambda message: message.text == "💰 Цены")
async def prices(message: Message):
    text = "💰 <b>Прайс-лист (за 1 кг)</b>\n\n"
    for p in PRODUCTS.values():
        text += f"{p['name']} — {p['price']}₽\n"
    text += "\n📦 Минимальный заказ — 100 г.\n"
    text += "Доступные веса: 500г, 1кг, 1.5кг, 2кг + свой вес.\n"
    text += "💸 Оплата наличными при получении."
    await message.answer(text, parse_mode="HTML")

async def main():
    print("🍓 Бот FreshBerry успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())