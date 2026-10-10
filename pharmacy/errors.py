"""Ошибки приложения.

Тексты ошибок написаны для пользователя: интерфейс показывает их как есть.
"""

from typing import Optional


class AppError(Exception):
    """Базовая ошибка приложения."""


class ValidationError(AppError):
    """Введены неверные данные.

    Attributes:
        message: Понятное пользователю описание проблемы.
        field: Имя поля формы, к которому относится ошибка (если известно),
            чтобы интерфейс мог показать сообщение под нужным полем.
    """

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        """Создаёт ошибку проверки данных.

        Args:
            message: Текст для пользователя.
            field: Имя поля формы.
        """
        super().__init__(message)
        self.message = message
        self.field = field


class AuthenticationError(AppError):
    """Вход не удался: аккаунт не найден или пароль неверный.

    Attributes:
        field: Поле формы, в котором ошибка: ``login`` (такого аккаунта нет)
            или ``password`` (аккаунт найден, пароль не подошёл).
    """

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        """Создаёт ошибку входа.

        Args:
            message: Текст для пользователя.
            field: Имя поля формы, которое нужно подсветить.
        """
        super().__init__(message)
        self.field = field


class NotFoundError(AppError):
    """Запись не найдена или принадлежит другому пользователю."""
