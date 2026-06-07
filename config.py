import os

# Токен бота (получи у @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8286121562:AAGoiSnMvDFms15mmxyFz6uCBZlyumeAoOo")

# Твой Telegram ID (узнай у @userinfobot)
ADMIN_ID = int(os.getenv("ADMIN_ID", 1010873079))

# Контакты продавца
SELLER_TELEGRAM = "@jhowk"
SELLER_PHONE = "+7 911 824-02-90"

# Цены и товары
PRODUCTS = {
    "strawberry": ("🍓 Клубника", 800),
    "cherry": ("🍒 Вишня", 1200),
    "sweet_cherry": ("🍒 Черешня", 1500),
    "peach": ("🍑 Персик", 900),
    "apricot": ("🍊 Абрикос", 700),
}

# Доступные веса (граммы)
WEIGHTS = [500, 1000, 1500, 2000]   # 500г, 1кг, 1.5кг, 2кг