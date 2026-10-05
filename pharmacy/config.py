"""Настройки приложения: пути к файлам и значения по умолчанию."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "aptechka.db"

# Переменная окружения позволяет указать другой файл базы (например, для тестов).
DB_PATH_ENV = "APTECHKA_DB"

# За сколько дней до конца срока годности предупреждать (настройка пользователя).
DEFAULT_WARNING_DAYS = 30


def get_db_path() -> Path:
    """Возвращает путь к файлу базы данных.

    Returns:
        Путь из переменной окружения APTECHKA_DB, а если она не задана,
        файл ``data/aptechka.db`` в папке проекта.
    """
    override = os.environ.get(DB_PATH_ENV)
    return Path(override) if override else DEFAULT_DB_PATH
