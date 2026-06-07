import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery
import asyncio

# ===== ВСТАВЬ СВОЙ ТОКЕН СЮДА (для локального запуска) =====
# Получи его у @BotFather командой /token
BOT_TOKEN = "8286121562:AAGoiSnMvDFms15mmxyFz6uCBZlyumeAoOo"
# ============================================================

# Если токен не вставлен, показываем ошибку
if BOT_TOKEN == "ВСТАВЬ_СЮДА_ТВОЙ_ТОКЕН":
    print("❌ ОШИБКА: Вставь свой токен в переменную BOT_TOKEN!")
    exit(1)

# ID администратора (узнай у @userinfobot)
ADMIN_ID = 1010873079  # 👈 ЗАМЕНИ НА СВОЙ ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== ТОВАРЫ И ЦЕНЫ (за 1 кг) ==========
PRODUCTS = {
    # Ягоды
    "strawberry": {"name": "🍓 Клубника", "price": 800, "category": "berries"},
    "cherry": {"name": "🍒 Вишня", "price": 1200, "category": "berries"},
    "sweet_cherry": {"name": "🍒 Черешня", "price": 1500, "category": "berries"},
    # Косточковые
    "peach": {"name": "🍑 Персик", "price": 900, "category": "stone"},
    "apricot": {"name": "🍊 Абрикос", "price": 700, "category": "stone"},
    "nectarine": {"name": "🍑 Нектарин", "price": 950, "category": "stone"},
    "plum": {"name": "🟣 Слива", "price": 600, "category": "stone"},
}

# Доступные веса (в граммах)
AVAILABLE_WEIGHTS = [500, 1000, 1500, 2000]

# Корзина пользователей
carts = {}

# ========== КЛАВИАТУРЫ ==========
# Главное меню
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍓 Ягоды"), KeyboardButton(text="🍑 Персики и абрикосы")],
        [KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="✅ Оформить заказ")],
        [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="💰 Цены")]
    ],
    resize_keyboard=True
)

# Меню ягод
berries_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍓 Клубника"), KeyboardButton(text="🍒 Вишня")],
        [KeyboardButton(text="🍒 Черешня"), KeyboardButton(text="🔙 Назад")],
    ],
    resize_keyboard=True
)

# Меню косточковых
stone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍑 Персик"), KeyboardButton(text="🍊 Абрикос")],
        [KeyboardButton(text="🍑 Нектарин"), KeyboardButton(text="🟣 Слива")],
        [KeyboardButton(text="🔙 Назад")],
    ],
    resize_keyboard=True
)

def get_weight_keyboard(product_id):
    """Создает инлайн-кнопки для выбора веса"""
    buttons = []
    for weight in AVAILABLE_WEIGHTS:
        weight_kg = weight / 1000
        price = int((weight / 1000) * PRODUCTS[product_id]["price"])
        text = f"{weight_kg} кг — {price}₽" if weight >= 1000 else f"{weight}г — {price}₽"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"add_{product_id}_{weight}")])
    
    buttons.append([InlineKeyboardButton(text="✏️ Свой вес", callback_data=f"custom_{product_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_category")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== ОБРАБОТЧИКИ ==========
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "🍓 Добро пожаловать в <b>FreshBerry</b>!\n\n"
        "У нас только свежие фрукты и ягоды 🍑🍒🍓\n\n"
        "<b>💰 Цены за 1 кг:</b>\n"
        "• Клубника — 800₽\n"
        "• Вишня — 1200₽\n"
        "• Черешня — 1500₽\n"
        "• Персик — 900₽\n"
        "• Абрикос — 700₽\n"
        "• Нектарин — 950₽\n"
        "• Слива — 600₽\n\n"
        "Выбери категорию 👇",
        reply_markup=main_keyboard,
        parse_mode="HTML"
    )

@dp.message(lambda message: message.text == "🍓 Ягоды")
async def show_berries(message: Message):
    await message.answer(
        "🍓 <b>Наши ягоды</b> 🍒\n\n"
        "Выбери что хочешь заказать:",
        reply_markup=berries_keyboard,
        parse_mode="HTML"
    )

@dp.message(lambda message: message.text == "🍑 Персики и абрикосы")
async def show_stone_fruits(message: Message):
    await message.answer(
        "🍑 <b>Косточковые фрукты</b> 🍊\n\n"
        "Выбери что хочешь заказать:",
        reply_markup=stone_keyboard,
        parse_mode="HTML"
    )

@dp.message(lambda message: message.text in ["🍓 Клубника", "🍒 Вишня", "🍒 Черешня", "🍑 Персик", "🍊 Абрикос", "🍑 Нектарин", "🟣 Слива"])
async def select_product(message: Message):
    product_map = {
        "🍓 Клубника": "strawberry",
        "🍒 Вишня": "cherry",
        "🍒 Черешня": "sweet_cherry",
        "🍑 Персик": "peach",
        "🍊 Абрикос": "apricot",
        "🍑 Нектарин": "nectarine",
        "🟣 Слива": "plum",
    }
    
    product_id = product_map.get(message.text)
    if not product_id:
        return
    
    await message.answer(
        f"{PRODUCTS[product_id]['name']}\n\n"
        f"💰 Цена: {PRODUCTS[product_id]['price']}₽ за 1 кг\n\n"
        f"Выбери вес:",
        reply_markup=get_weight_keyboard(product_id)
    )

@dp.callback_query()
async def handle_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    
    if data == "back_to_category":
        await callback.message.answer("Выбери категорию:", reply_markup=main_keyboard)
        await callback.answer()
        return
    
    if data.startswith("add_"):
        parts = data.split("_")
        product_id = parts[1]
        weight = int(parts[2])
        
        product = PRODUCTS[product_id]
        price_per_kg = product["price"]
        total_price = int((weight / 1000) * price_per_kg)
        
        weight_text = f"{weight/1000:.1f} кг" if weight >= 1000 else f"{weight} г"
        
        if user_id not in carts:
            carts[user_id] = []
        
        carts[user_id].append({
            "product_id": product_id,
            "name": product["name"],
            "weight": weight,
            "weight_text": weight_text,
            "price": total_price
        })
        
        total_weight = sum(item["weight"] for item in carts[user_id])
        total_price_sum = sum(item["price"] for item in carts[user_id])
        
        await callback.message.answer(
            f"✅ <b>Добавлено!</b>\n\n"
            f"📦 {product['name']} — {weight_text}\n"
            f"💰 {total_price}₽\n\n"
            f"📊 <b>В корзине:</b>\n"
            f"⚖️ Вес: {total_weight} г ({total_weight/1000:.1f} кг)\n"
            f"💵 Сумма: {total_price_sum}₽\n\n"
            f"Что дальше?\n"
            f"• Выбери еще фрукты\n"
            f"• Нажми 🛒 Корзина для просмотра\n"
            f"• Нажми ✅ Оформить заказ",
            reply_markup=main_keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data.startswith("custom_"):
        product_id = data.split("_")[1]
        product_name = PRODUCTS[product_id]["name"]
        
        await callback.message.answer(
            f"✏️ <b>Свой вес для {product_name}</b>\n\n"
            f"Напиши вес в граммах или килограммах:\n\n"
            f"Примеры:\n"
            f"• <code>750</code> — 750 грамм\n"
            f"• <code>1.5</code> — 1.5 кг (1500 грамм)\n"
            f"• <code>2</code> — 2 кг (2000 грамм)\n\n"
            f"Можно от 500 г до 5 кг",
            parse_mode="HTML"
        )
        await callback.answer()

@dp.message()
async def handle_custom_weight(message: Message):
    user_id = message.from_user.id
    text = message.text.lower().replace(' ', '').replace('кг', '').replace('г', '')
    text = text.replace(',', '.')
    
    # Проверяем, является ли сообщение числом (весом)
    try:
        float(text)
    except ValueError:
        return  # Не число - игнорируем
    
    # Спрашиваем какой продукт пользователь хочет добавить
    await message.answer(
        "🍓 Сначала выбери продукт!\n\n"
        "Нажми на кнопку с нужным фруктом или ягодой, а потом укажи вес.",
        reply_markup=main_keyboard
    )

@dp.message(lambda message: message.text == "🛒 Корзина")
async def show_cart(message: Message):
    user_id = message.from_user.id
    
    if user_id not in carts or not carts[user_id]:
        await message.answer(
            "🛒 Корзина пуста!\n\n"
            "Выбери фрукты в категориях 🍓🍑",
            reply_markup=main_keyboard
        )
        return
    
    items_text = ""
    for i, item in enumerate(carts[user_id], 1):
        items_text += f"{i}. {item['name']} — {item['weight_text']} — {item['price']}₽\n"
    
    total_weight = sum(item["weight"] for item in carts[user_id])
    total_price = sum(item["price"] for item in carts[user_id])
    
    await message.answer(
        f"🛒 <b>ТВОЯ КОРЗИНА</b>\n\n"
        f"{items_text}\n"
        f"📦 Всего: {total_weight} г ({total_weight/1000:.1f} кг)\n"
        f"💰 <b>ИТОГО: {total_price}₽</b>\n\n"
        f"Нажми «✅ Оформить заказ» для отправки!",
        reply_markup=main_keyboard,
        parse_mode="HTML"
    )

@dp.message(lambda message: message.text == "💰 Цены")
async def show_prices(message: Message):
    text = "💰 <b>ПРАЙС-ЛИСТ (за 1 кг)</b>\n\n"
    for product_id, product in PRODUCTS.items():
        text += f"{product['name']} — {product['price']}₽\n"
    text += "\n📦 Минимальный заказ — 500 г"
    await message.answer(text, parse_mode="HTML")

@dp.message(lambda message: message.text == "📞 Контакты")
async def show_contacts(message: Message):
    await message.answer(
        "📞 <b>Контакты для связи</b>\n\n"
        "По всем вопросам и заказам:\n"
        "• Telegram: @твой_никнейм\n"
        "• Телефон: +7 XXX XXX-XX-XX\n\n"
        "💸 <b>Оплата наличными</b> при получении!",
        parse_mode="HTML"
    )

@dp.message(lambda message: message.text == "✅ Оформить заказ")
async def checkout(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    name = message.from_user.full_name
    
    if user_id not in carts or not carts[user_id]:
        await message.answer("❌ Корзина пуста! Сначала добавь фрукты.")
        return
    
    items_text = ""
    for i, item in enumerate(carts[user_id], 1):
        items_text += f"{i}. {item['name']} — {item['weight_text']} — {item['price']}₽\n"
    
    total_weight = sum(item["weight"] for item in carts[user_id])
    total_price = sum(item["price"] for item in carts[user_id])
    
    order_text = (
        f"🆕 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
        f"👤 Покупатель: {name}\n"
        f"🆔 ID: {user_id}\n"
        f"📱 Username: @{username}\n\n"
        f"📦 <b>СОСТАВ ЗАКАЗА:</b>\n{items_text}\n"
        f"⚖️ Общий вес: {total_weight} г ({total_weight/1000:.1f} кг)\n"
        f"💰 <b>ИТОГО К ОПЛАТЕ: {total_price}₽</b>\n\n"
        f"💸 <b>ОПЛАТА НАЛИЧНЫМИ ПРИ ПОЛУЧЕНИИ</b>\n\n"
        f"📞 Свяжитесь с покупателем для подтверждения!"
    )
    
    try:
        await bot.send_message(ADMIN_ID, order_text, parse_mode="HTML")
        
        await message.answer(
            f"✅ <b>ЗАКАЗ ОТПРАВЛЕН!</b>\n\n"
            f"Ваш заказ:\n{items_text}\n"
            f"⚖️ Вес: {total_weight} г ({total_weight/1000:.1f} кг)\n"
            f"💰 Сумма: {total_price}₽\n\n"
            f"💸 <b>Оплата наличными при получении</b>\n\n"
            f"Спасибо за заказ! Я свяжусь с тобой в ближайшее время для подтверждения.\n\n"
            f"🍓 Хорошего дня!",
            reply_markup=main_keyboard,
            parse_mode="HTML"
        )
        
        carts[user_id] = []
        
    except Exception as e:
        await message.answer("❌ Ошибка при отправке заказа. Попробуй позже.")
        print(f"Ошибка: {e}")

@dp.message(lambda message: message.text == "🔙 Назад")
async def go_back(message: Message):
    await message.answer("Главное меню:", reply_markup=main_keyboard)

async def main():
    print("🍓 Бот FreshBerry запущен!")
    print(f"📊 Доступные товары: {len(PRODUCTS)}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())