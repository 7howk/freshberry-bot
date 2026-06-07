import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

# ----- ТВОИ ДАННЫЕ (ЗАМЕНИ ОБЯЗАТЕЛЬНО) -----
BOT_TOKEN = "8286121562:AAGAzHEavlD_C2nol3ZDLUPHnbLGKYs41MY"   # твой токен
ADMIN_ID = 1010873079   # твой ID (узнай у @userinfobot)

CONTACT_TEXT = "По вопросам заказов: @jhowk и @cuteru6 или +7 911 824-02-90"

PRICES = {
    "🍓 Клубника": 800,
    "🍒 Вишня": 1200,
    "🍒 Черешня": 1500,
    "🍑 Персик": 900,
    "🍊 Абрикос": 700,
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
temp_fruit = {}   # временный выбранный фрукт

# ------------------------------------------------------------------
# КЛАВИАТУРЫ
# ------------------------------------------------------------------
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍓 Клубника"), KeyboardButton(text="🍒 Вишня")],
        [KeyboardButton(text="🍒 Черешня"), KeyboardButton(text="🍑 Персик")],
        [KeyboardButton(text="🍊 Абрикос"), KeyboardButton(text="🛒 Корзина")],
        [KeyboardButton(text="✅ Оформить заказ"), KeyboardButton(text="📞 Контакты")],
        [KeyboardButton(text="💰 Цены"), KeyboardButton(text="🗑 Удалить товар")]
    ],
    resize_keyboard=True
)

weight_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="500 г"), KeyboardButton(text="1 кг")],
        [KeyboardButton(text="1.5 кг"), KeyboardButton(text="2 кг")],
        [KeyboardButton(text="🔙 Назад")]
    ],
    resize_keyboard=True
)

# Состояния для оформления заказа
class OrderForm(StatesGroup):
    name = State()
    surname = State()
    phone = State()
    address = State()

# ------------------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ------------------------------------------------------------------
def get_cart_text(user_id):
    if user_id not in cart or not cart[user_id]:
        return "🛒 Корзина пуста.", None
    items = cart[user_id]
    text = "🛒 Твоя корзина:\n\n"
    for i, item in enumerate(items, 1):
        text += f"{i}. {item['name']} — {item['weight_str']} — {item['price']}₽\n"
    total_w = sum(i["weight"] for i in items)
    total_p = sum(i["price"] for i in items)
    text += f"\n📦 Общий вес: {total_w}г ({total_w/1000:.1f}кг)\n💰 Итого: {total_p}₽"
    return text, items

def get_delete_keyboard(user_id):
    """Создаёт инлайн-кнопки для удаления каждого товара"""
    if user_id not in cart or not cart[user_id]:
        return None
    items = cart[user_id]
    buttons = []
    for idx, item in enumerate(items, 1):
        buttons.append([InlineKeyboardButton(
            text=f"❌ {idx}. {item['name']} {item['weight_str']} — {item['price']}₽",
            callback_data=f"del_{idx}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Отмена", callback_data="del_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ------------------------------------------------------------------
# ОБРАБОТЧИКИ КОМАНД И КНОПОК
# ------------------------------------------------------------------
@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🍓 FreshBerry — свежие фрукты с доставкой!\n\n"
        "Выбери фрукт из меню, затем вес.\n"
        "После добавления нажми «✅ Оформить заказ» — я попрошу имя, фамилию, телефон и адрес.\n\n"
        "💰 Цены за 1 кг:\n"
        "🍓 Клубника — 800₽\n🍒 Вишня — 1200₽\n🍒 Черешня — 1500₽\n"
        "🍑 Персик — 900₽\n🍊 Абрикос — 700₽",
        reply_markup=main_kb
    )

@dp.message(lambda m: m.text == "💰 Цены")
async def prices_cmd(message: Message):
    await message.answer(
        "🍓 FreshBerry — свежие фрукты с доставкой!\n\n"
        "Выбери фрукт из меню, затем вес.\n"
        "После добавления нажми «✅ Оформить заказ» — я попрошу имя, фамилию, телефон и адрес.\n\n"
        "💰 Цены за 1 кг:\n"
        "🍓 Клубника — 800₽\n🍒 Вишня — 1200₽\n🍒 Черешня — 1500₽\n"
        "🍑 Персик — 900₽\n🍊 Абрикос — 700₽",
        reply_markup=main_kb
    )

@dp.message(lambda m: m.text in PRICES)
async def choose_fruit(message: Message, state: FSMContext):
    await state.clear()
    fruit = message.text
    temp_fruit[message.from_user.id] = fruit
    await message.answer(f"Выбрано: {fruit}\nТеперь выбери вес:", reply_markup=weight_kb)

@dp.message(lambda m: m.text in WEIGHTS)
async def add_to_cart(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in temp_fruit:
        await message.answer("Сначала выбери фрукт из главного меню.", reply_markup=main_kb)
        return
    fruit = temp_fruit[user_id]
    weight_str = message.text
    weight_grams = WEIGHTS[weight_str]
    price_per_kg = PRICES[fruit]
    price = int((weight_grams / 1000) * price_per_kg)
    weight_display = f"{weight_grams}г" if weight_grams < 1000 else f"{weight_grams//1000}кг"

    if user_id not in cart:
        cart[user_id] = []
    cart[user_id].append({
        "name": fruit,
        "weight": weight_grams,
        "weight_str": weight_display,
        "price": price
    })
    total_w = sum(i["weight"] for i in cart[user_id])
    total_p = sum(i["price"] for i in cart[user_id])
    await message.answer(
        f"✅ Добавлено: {fruit} {weight_display} — {price}₽\n\n"
        f"В корзине: {total_w}г ({total_w/1000:.1f}кг) на сумму {total_p}₽",
        reply_markup=main_kb
    )
    del temp_fruit[user_id]

@dp.message(lambda m: m.text == "🔙 Назад")
async def back_to_main(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in temp_fruit:
        del temp_fruit[user_id]
    await state.clear()
    await message.answer("Возврат в главное меню", reply_markup=main_kb)

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
    if keyboard:
        await message.answer("Нажми на товар, который хочешь удалить:", reply_markup=keyboard)
    else:
        await message.answer("Корзина пуста.")

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
            # Обновляем или удаляем клавиатуру
            new_kb = get_delete_keyboard(user_id)
            if new_kb:
                await callback.message.edit_reply_markup(reply_markup=new_kb)
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
    await message.answer("Для оформления заказа напиши своё Имя:", reply_markup=types.ReplyKeyboardRemove())

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
    items_text = "\n".join(f"{i['name']} — {i['weight_str']} — {i['price']}₽" for i in items)
    total_w = sum(i["weight"] for i in items)
    total_p = sum(i["price"] for i in items)

    order_msg = (
        f"🆕 НОВЫЙ ЗАКАЗ!\n\n"
        f"👤 Имя: {full_name}\n"
        f"📞 Телефон: {phone}\n"
        f"🏠 Адрес: {address}\n"
        f"🆔 Telegram ID: {user_id}\n"
        f"👥 Username: @{message.from_user.username or 'нет'}\n\n"
        f"📦 Состав:\n{items_text}\n\n"
        f"⚖️ Вес: {total_w}г ({total_w/1000:.1f}кг)\n"
        f"💰 Сумма: {total_p}₽\n"
        f"💸 Оплата наличными при получении."
    )
    try:
        await bot.send_message(ADMIN_ID, order_msg)
        await message.answer(
            "✅ Заказ отправлен! Продавец свяжется с тобой для подтверждения.\nСпасибо за покупку!",
            reply_markup=main_kb
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
    logging.info("🍓 FreshBerry запущен (инлайн-удаление, FSM)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())