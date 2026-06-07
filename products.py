from config import PRODUCTS

def format_weight(weight_grams: int) -> str:
    """Преобразует граммы в читаемый вид: 500г, 1кг, 1.5кг"""
    if weight_grams < 1000:
        return f"{weight_grams} г"
    elif weight_grams % 1000 == 0:
        return f"{weight_grams // 1000} кг"
    else:
        return f"{weight_grams / 1000:.1f} кг"

def calculate_price(product_key: str, weight_grams: int) -> int:
    """Считает стоимость товара по весу"""
    _, price_per_kg = PRODUCTS[product_key]
    return int((weight_grams / 1000) * price_per_kg)