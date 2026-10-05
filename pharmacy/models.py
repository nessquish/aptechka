"""Модели данных приложения (слой Models из ТЗ).

Это простые неизменяемые структуры без логики: репозитории создают их из строк
базы, сервисы и интерфейс только читают.
"""

from dataclasses import dataclass


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
