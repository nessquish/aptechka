"""Запросы к таблице категорий."""

from typing import List, Optional

from pharmacy.models import Category
from pharmacy.repositories.base import BaseRepository


class CategoryRepository(BaseRepository):
    """Чтение справочника категорий."""

    def list_all(self) -> List[Category]:
        """Возвращает все категории в порядке добавления."""
        rows = self.db.fetch_all("SELECT id, name FROM categories ORDER BY id")
        return [Category(id=row["id"], name=row["name"]) for row in rows]

    def get(self, category_id: int) -> Optional[Category]:
        """Находит категорию по идентификатору (None, если нет)."""
        row = self.db.fetch_one(
            "SELECT id, name FROM categories WHERE id = ?", (category_id,)
        )
        return Category(id=row["id"], name=row["name"]) if row else None
