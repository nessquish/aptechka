"""Проверка данных, которые вводит пользователь при регистрации и входе."""

import re
from typing import Optional

from pharmacy.errors import ValidationError

LOGIN_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,30}$")
# Адрес: имя до @ (латинские буквы, цифры и _ % + -, части через одиночную точку),
# затем домен из частей через точку (часть без дефиса по краям, до 63 знаков)
# и верхний домен из букв (от 2 знаков): gmail.com, mail.ru, yandex.ru и любые другие.
_LOCAL = r"[A-Za-z0-9_%+\-]+(?:\.[A-Za-z0-9_%+\-]+)*"
_DOMAIN_PART = r"[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?"
_TOP_DOMAIN = r"[A-Za-z]{2,24}"
EMAIL_PATTERN = re.compile(rf"^{_LOCAL}@(?:{_DOMAIN_PART}\.)+{_TOP_DOMAIN}$")
MAX_EMAIL_LOCAL_LENGTH = 64
EMAIL_ERROR = "Введите корректный email, например user@gmail.com"
MIN_PASSWORD_LENGTH = 8
MAX_USERNAME_LENGTH = 50
MAX_EMAIL_LENGTH = 100


def is_valid_email(email: str) -> bool:
    """Проверяет формат адреса электронной почты (без обращения к базе).

    Подходит для проверки прямо во время ввода: пробелы по краям не мешают.

    Args:
        email: Адрес, введённый пользователем.

    Returns:
        True, если адрес записан верно: есть имя, @, домен с точкой и верхний
        домен из букв, нет пробелов и лишних символов.
    """
    email = email.strip()
    if len(email) > MAX_EMAIL_LENGTH or not EMAIL_PATTERN.match(email):
        return False
    return len(email.split("@", 1)[0]) <= MAX_EMAIL_LOCAL_LENGTH


def validate_login(login: str) -> str:
    """Проверяет логин.

    Args:
        login: Логин, введённый пользователем.

    Returns:
        Логин без пробелов по краям.

    Raises:
        ValidationError: Если логин пустой или содержит недопустимые символы.
    """
    login = login.strip()
    if not login:
        raise ValidationError("Введите логин", "login")
    if not LOGIN_PATTERN.match(login):
        raise ValidationError(
            "Логин: от 3 до 30 символов, латинские буквы, цифры, точка, "
            "дефис и подчёркивание",
            "login",
        )
    return login


def validate_username(username: str) -> str:
    """Проверяет имя пользователя.

    Args:
        username: Имя, введённое пользователем.

    Returns:
        Имя без пробелов по краям.

    Raises:
        ValidationError: Если имя пустое или слишком длинное.
    """
    username = username.strip()
    if not username:
        raise ValidationError("Введите имя пользователя", "username")
    if len(username) > MAX_USERNAME_LENGTH:
        raise ValidationError(
            f"Имя не длиннее {MAX_USERNAME_LENGTH} символов", "username"
        )
    return username


def validate_email(email: str) -> str:
    """Проверяет адрес электронной почты.

    Args:
        email: Адрес, введённый пользователем.

    Returns:
        Адрес без пробелов по краям, в нижнем регистре.

    Raises:
        ValidationError: Если адрес пустой или записан неверно.
    """
    email = email.strip().lower()
    if not email:
        raise ValidationError("Введите адрес электронной почты", "email")
    if not is_valid_email(email):
        raise ValidationError(EMAIL_ERROR, "email")
    return email


def validate_password(
    password: str,
    repeat: Optional[str] = None,
    field: str = "password",
) -> None:
    """Проверяет новый пароль.

    Args:
        password: Пароль, введённый пользователем.
        repeat: Повтор пароля. Если передан, пароли должны совпадать.
        field: Имя поля пароля для сообщения об ошибке.

    Raises:
        ValidationError: Если пароль пустой, короткий или не совпал с повтором.
    """
    if not password:
        raise ValidationError("Введите пароль", field)
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Пароль не короче {MIN_PASSWORD_LENGTH} символов", field)
    if repeat is not None and password != repeat:
        raise ValidationError("Пароли не совпадают", f"{field}_repeat")
