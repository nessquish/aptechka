"""Общие помощники для тестов."""

import tempfile
import unittest
from pathlib import Path
from typing import Optional

from pharmacy.db.connection import Database


class DatabaseTestCase(unittest.TestCase):
    """Базовый класс: каждому тесту выдаётся чистая база во временной папке."""

    def setUp(self) -> None:
        """Создаёт временную базу со схемой перед каждым тестом."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = Database(Path(tmp.name) / "test.db")
        self.db.init_schema()

    def add_user(self, login: str = "user1", email: Optional[str] = None) -> int:
        """Добавляет пользователя и возвращает его идентификатор."""
        return self.db.execute(
            "INSERT INTO users (login, username, email, password_hash)"
            " VALUES (?, ?, ?, ?)",
            (login, login.title(), email or f"{login}@example.com", "hash"),
        )

    def category_id(self, name: str = "Лекарства") -> int:
        """Возвращает идентификатор категории по названию."""
        row = self.db.fetch_one("SELECT id FROM categories WHERE name = ?", (name,))
        return row["id"]

    def add_product(
        self,
        user_id: int,
        name: str = "Ибупрофен",
        quantity: float = 2,
        expiry_date: Optional[str] = None,
    ) -> int:
        """Добавляет товар в категорию «Лекарства» и возвращает его идентификатор."""
        return self.db.execute(
            "INSERT INTO products (user_id, category_id, name, quantity, expiry_date)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, self.category_id(), name, quantity, expiry_date),
        )

    def count_rows(self, table: str) -> int:
        """Возвращает число строк в таблице (имя таблицы задаётся в тестах)."""
        return self.db.fetch_one(f"SELECT COUNT(*) AS n FROM {table}")["n"]
