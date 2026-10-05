"""Модели данных приложения (слой Models из ТЗ).

Это простые неизменяемые структуры без логики: репозитории создают их из строк
базы, сервисы и интерфейс только читают.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class User:
    """Пользователь приложения.

    Attributes:
        id: Идентификатор.
        login: Логин для входа.
        username: Имя, которое показывается в интерфейсе.
        email: Электронная почта.
        password_hash: Хэш пароля (сам пароль нигде не хранится).
        warning_days: За сколько дней предупреждать об окончании срока годности.
        theme: Тема оформления: ``light`` или ``dark``.
        notify_expired: Показывать ли уведомления об истёкшем сроке.
        notify_low_stock: Показывать ли уведомления о низком остатке.
        created_at: Дата и время регистрации.
    """

    id: int
    login: str
    username: str
    email: str
    password_hash: str
    warning_days: int
    theme: str
    notify_expired: bool
    notify_low_stock: bool
    created_at: str


@dataclass(frozen=True)
class Category:
    """Категория товара (лекарства, бытовая химия и т. д.).

    Attributes:
        id: Идентификатор.
        name: Название категории.
    """

    id: int
    name: str


@dataclass(frozen=True)
class ProductData:
    """Проверенные данные товара, готовые к записи в базу.

    Attributes:
        name: Название.
        category_id: Идентификатор категории.
        quantity: Количество.
        unit: Единица измерения.
        expiry_date: Срок годности или None, если он не указан.
        indications: Показания или назначение (вносит сам пользователь).
        storage_place: Место хранения.
        min_quantity: Минимальный остаток, ниже которого нужно пополнять запас.
        note: Примечание.
    """

    name: str
    category_id: int
    quantity: float
    unit: str
    expiry_date: Optional[date]
    indications: str
    storage_place: str
    min_quantity: float
    note: str


@dataclass(frozen=True)
class Product:
    """Товар в аптечке пользователя.

    Attributes:
        id: Идентификатор.
        user_id: Владелец товара.
        category_id: Идентификатор категории.
        category_name: Название категории.
        name: Название.
        quantity: Количество.
        unit: Единица измерения.
        expiry_date: Срок годности или None.
        indications: Показания или назначение.
        storage_place: Место хранения.
        min_quantity: Минимальный остаток.
        note: Примечание.
        created_at: Дата и время добавления.
    """

    id: int
    user_id: int
    category_id: int
    category_name: str
    name: str
    quantity: float
    unit: str
    expiry_date: Optional[date]
    indications: str
    storage_place: str
    min_quantity: float
    note: str
    created_at: str


class HistoryAction:
    """Коды действий, которые записываются в историю."""

    PRODUCT_ADDED = "product_added"
    PRODUCT_UPDATED = "product_updated"
    PRODUCT_DELETED = "product_deleted"


@dataclass(frozen=True)
class HistoryRecord:
    """Запись в истории действий.

    Attributes:
        id: Идентификатор.
        user_id: Пользователь, выполнивший действие.
        product_id: Товар или None, если товар уже удалён.
        action: Код действия (см. HistoryAction).
        description: Описание для показа пользователю.
        created_at: Дата и время действия.
    """

    id: int
    user_id: int
    product_id: Optional[int]
    action: str
    description: str
    created_at: str
