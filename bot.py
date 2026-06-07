import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN, ADMIN_ID, SELLER_TELEGRAM, SELLER_PHONE, SELLER_EMAIL, PRODUCTS
from keyboards import main_kb, get_weight_keyboard
from database import carts
from states import temp_user_product
from products import format_weight, calculate_price

# Настройка логов
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# -------------------- СТАРТ --------------------
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "🍓 <b>FreshBerry — свежие фрукты с доставкой!</b>\n\n"
        "Выберите фрукт из меню ниже, затем укажите вес.\n\n"
        "<b>💰 Цены за 1 кг:</b>\n"
        "🍓 Клубника — 800₽\n"
        "🍒 Вишня — 1200₽\n"
        "🍒 Черешня — 1500₽\n"
        "🍑 Персик — 900₽\n"
        "🍊 Абрикос — 700₽\n\n"
        "📦 Вес: 500г, 1кг, 1.5кг, 2кг или свой (100г–5кг).\n"
        "💸 Оплата наличными при получении.",
        reply_markup=main_kb,
        parse_mode="HTML"
    )

# -------------------- ВЫБОР ФРУКТА --------------------
@dp.message(lambda m: m.text in ["🍓 Клубника", "🍒 Вишня", "🍒 Черешня", "🍑 Персик", "🍊 Абрикос"])
async def select_fruit(message: Message):
    mapping = {
        "🍓 Клубника": "strawberry",
        "🍒 Вишня": "cherry",
        "🍒 Черешня": "sweet_cherry",
        "🍑 Персик": "peach",
        "🍊 Абрикос": "apricot",
    }
    key = mapping[message.text]
    name, price = PRODUCTS[key]
    await message.answer(f"{name} — {price}₽/кг\n\nВыберите вес:", reply_markup=get_weight_keyboard(key))

# -------------------- ИНЛАЙН-КНОПКИ (вес, свой вес, назад) --------------------
@dp.callback_query()
async def handle_callback(call: CallbackQuery):
    user_id = call.from_user.id
    data = call.data

    # Назад в главное меню
    if data == "back":
        await call.message.answer("Главное меню:", reply_markup=main_kb)
        await call.answer()
        return

    # Свой вес
    if data.startswith("custom:"):
        product_key = data.split(":")[1]
        temp_user_product[user_id] = product_key
        await call.message.answer(
            "✏️ <b>Введите свой вес:</b>\n\n"
            "Напишите число в граммах или килограммах:\n"
            "• 750 — 750 г\n• 1.2 — 1.2 кг\n• 2.5 — 2.5 кг\n\n"
            "От 100 г до 5 кг.",
            parse_mode="HTML"
        )
        await call.answer()
        return

    # Обычный вес (формат "strawberry:500")
    if ":" in data:
        product_key, weight_str = data.split(":")
        weight = int(weight_str)
        name, price_per_kg = PRODUCTS[product_key]
        cost = calculate_price(product_key, weight)
        weight_text = format_weight(weight)

        if user_id not in carts:
            carts[user_id] = []
        carts[user_id].append({
            "name": name,
            "weight": weight,
            "weight_text": weight_text,
            "price": cost
        })

        total_weight = sum(i["weight"] for i in carts[user_id])
        total_price = sum(i["price"] for i in carts[user_id])

        await call.message.answer(
            f"✅ <b>Добавлено!</b>\n\n{name} — {weight_text} — {cost}₽\n\n"
            f"📦 <b>Ваша корзина:</b>\n• Вес: {total_weight} г ({total_weight/1000:.1f} кг)\n• Сумма: {total_price}₽",
            reply_markup=main_kb,
            parse_mode="HTML"
        )
        await call.answer()
        return

    await call.answer("Неизвестная команда")

# -------------------- РУЧНОЙ ВВОД ВЕСА --------------------
@dp.message()
async def custom_weight_input(message: Message):
    user_id = message.from_user.id
    if user_id not in temp_user_product:
        return
    product_key = temp_user_product.pop(user_id)

    text = message.text.strip().replace(",", ".")
    try:
        if "кг" in text.lower():
            weight = int(float(text.lower().split("кг")[0]) * 1000)
        elif "г" in text.lower():
            weight = int(text.lower().split("г")[0])
        else:
            weight = int(float(text) * 1000 if "." in text else int(text))

        if weight < 100:
            await message.answer("❌ Минимум 100 грамм.")
            return
        if weight > 5000:
            await message.answer("❌ Максимум 5000 грамм (5 кг).")
            return

        name, _ = PRODUCTS[product_key]
        cost = calculate_price(product_key, weight)
        weight_text = format_weight(weight)

        if user_id not in carts:
            carts[user_id] = []
        carts[user_id].append({
            "name": name,
            "weight": weight,
            "weight_text": weight_text,
            "price": cost
        })

        total_weight = sum(i["weight"] for i in carts[user_id])
        total_price = sum(i["price"] for i in carts[user_id])

        await message.answer(
            f"✅ <b>Добавлено!</b>\n\n{name} — {weight_text} — {cost}₽\n\n"
            f"📦 <b>В корзине:</b> {total_weight} г ({total_weight/1000:.1f} кг) на сумму {total_price}₽",
            reply_markup=main_kb,
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ Не распознано. Напишите число, например: 750 или 1.2")

# -------------------- КОРЗИНА --------------------
@dp.message(lambda m: m.text == "🛒 Корзина")
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
    text += f"\n📦 <b>Общий вес:</b> {total_weight} г ({total_weight/1000:.1f} кг)\n💰 <b>Итого:</b> {total_price}₽"
    await message.answer(text, parse_mode="HTML")

# -------------------- ОФОРМЛЕНИЕ ЗАКАЗА --------------------
@dp.message(lambda m: m.text == "✅ Оформить заказ")
async def checkout(message: Message):
    user_id = message.from_user.id
    if user_id not in carts or not carts[user_id]:
        await message.answer("❌ Корзина пуста. Добавьте товары.")
        return

    username = message.from_user.username or "нет"
    name = message.from_user.full_name
    items = carts[user_id]

    items_text = "\n".join(f"{i['name']} — {i['weight_text']} — {i['price']}₽" for i in items)
    total_weight = sum(i["weight"] for i in items)
    total_price = sum(i["price"] for i in items)

    order = (
        f"🆕 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
        f"👤 {name} (@{username})\n🆔 {user_id}\n\n"
        f"📦 <b>Состав:</b>\n{items_text}\n\n"
        f"⚖️ Вес: {total_weight} г ({total_weight/1000:.1f} кг)\n💰 Сумма: {total_price}₽\n"
        f"💸 Оплата наличными при получении."
    )
    try:
        await bot.send_message(ADMIN_ID, order, parse_mode="HTML")
        await message.answer(
            "✅ <b>Заказ отправлен!</b>\n\nПродавец свяжется с вами.\n"
            "Если есть вопросы — нажмите «📞 Связаться с продавцом».",
            parse_mode="HTML"
        )
        carts[user_id] = []
    except Exception as e:
        await message.answer("❌ Ошибка при отправке заказа.")
        logging.error(e)

# -------------------- СВЯЗАТЬСЯ С ПРОДАВЦОМ --------------------
@dp.message(lambda m: m.text == "📞 Связаться с продавцом")
async def contact(message: Message):
    await message.answer(
        f"📞 <b>Связаться с нами</b>\n\n"
        f"• Telegram: {SELLER_TELEGRAM}\n"
        f"• Телефон: {SELLER_PHONE}\n"
        f"• Email: {SELLER_EMAIL}\n\n"
        f"Работаем с 9:00 до 21:00.",
        parse_mode="HTML"
    )

# -------------------- ПОКАЗАТЬ ЦЕНЫ --------------------
@dp.message(lambda m: m.text == "💰 Цены")
async def prices(message: Message):
    text = "💰 <b>Цены за 1 кг:</b>\n\n"
    for name, price in PRODUCTS.values():
        text += f"{name} — {price}₽\n"
    text += "\n📦 Веса: 500г, 1кг, 1.5кг, 2кг или свой (100г–5кг).\n💸 Оплата наличными."
    await message.answer(text, parse_mode="HTML")

# -------------------- ЗАПУСК --------------------
async def main():
    logging.info("🍓 FreshBerry запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())