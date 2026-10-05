"""Настройки приложения: пути к файлам и значения по умолчанию."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_FOLDER = "Моя аптечка"  # папка данных установленной программы


def _default_db_path() -> Path:
    """Возвращает путь к базе по умолчанию.

    При запуске из исходников база лежит в ``data`` рядом с проектом. Собранная
    программа (``.exe``) распаковывается во временную папку, а рядом с ней может
    не быть прав на запись, поэтому данные хранятся в папке пользователя Windows
    (``%LOCALAPPDATA%``). Так они сохраняются между запусками и обновлениями.
    """
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / APP_FOLDER / "data" / "aptechka.db"
    return PROJECT_ROOT / "data" / "aptechka.db"


DEFAULT_DB_PATH = _default_db_path()

# Переменная окружения позволяет указать другой файл базы (например, для тестов).
DB_PATH_ENV = "APTECHKA_DB"

# За сколько дней до конца срока годности предупреждать (настройка пользователя).
DEFAULT_WARNING_DAYS = 30


def get_db_path() -> Path:
    """Возвращает путь к файлу базы данных.

    Returns:
        Путь из переменной окружения APTECHKA_DB, а если она не задана,
        путь по умолчанию (см. ``_default_db_path``).
    """
    override = os.environ.get(DB_PATH_ENV)
    return Path(override) if override else DEFAULT_DB_PATH
