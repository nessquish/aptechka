"""Подписи и тона для показа данных: состояния, категории, приветствие."""

from typing import Dict, Tuple

from pharmacy.services.status import ProductStatus

# Состояние товара -> цвет плашки, значок и тон значка.
STATUS_TONES: Dict[ProductStatus, str] = {
    ProductStatus.EXPIRED: "red",
    ProductStatus.EXPIRING: "amber",
    ProductStatus.LOW_STOCK: "amber",
    ProductStatus.OK: "green",
}
STATUS_ICONS: Dict[ProductStatus, str] = {
    ProductStatus.EXPIRED: "alert",
    ProductStatus.EXPIRING: "clock",
    ProductStatus.LOW_STOCK: "trending-down",
    ProductStatus.OK: "check",
}

# Короткие названия категорий для таблиц и подписей, как в макете.
_SHORT_CATEGORIES = {
    "Медицинские товары": "Мед. товары",
    "Средства гигиены": "Гигиена",
}

# (час начала, приветствие): выбирается последнее подходящее по времени суток.
_GREETINGS: Tuple[Tuple[int, str], ...] = (
    (0, "Доброй ночи"),
    (5, "Доброе утро"),
    (12, "Добрый день"),
    (18, "Добрый вечер"),
    (23, "Доброй ночи"),
)


def short_category(name: str) -> str:
    """Возвращает короткое название категории (или само название)."""
    return _SHORT_CATEGORIES.get(name, name)


def greeting(hour: int) -> str:
    """Возвращает приветствие по часу суток (0-23)."""
    text = _GREETINGS[0][1]
    for start, phrase in _GREETINGS:
        if hour >= start:
            text = phrase
    return text
