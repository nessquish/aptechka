"""Тесты репозиториев товаров, категорий и истории."""

import sqlite3
from datetime import date

from pharmacy.models import HistoryAction, ProductData
from pharmacy.repositories.category_repository import CategoryRepository
from pharmacy.repositories.history_repository import HistoryRepository
from pharmacy.repositories.product_repository import ProductRepository
from tests.helpers import DatabaseTestCase


class RepositoryTestCase(DatabaseTestCase):
    """База с репозиториями и готовым пользователем."""

    def setUp(self) -> None:
        super().setUp()
        self.products = ProductRepository(self.db)
        self.categories = CategoryRepository(self.db)
        self.history = HistoryRepository(self.db)
        self.user_id = self.add_user("anna")

    def data(self, name="Ибупрофен", **overrides) -> ProductData:
        """Готовые данные товара; отдельные поля можно заменить."""
        values = dict(
            name=name,
            category_id=self.category_id("Лекарства"),
            quantity=2.0,
            unit="упак.",
            expiry_date=date(2026, 10, 20),
            indications="Жаропонижающее",
            storage_place="Шкаф",
            min_quantity=3.0,
            note="",
        )
        values.update(overrides)
        return ProductData(**values)


class CategoryRepositoryTest(RepositoryTestCase):
    """Справочник категорий."""

    def test_list_all_in_order(self):
        names = [category.name for category in self.categories.list_all()]
        self.assertEqual(
            names,
            ["Лекарства", "Медицинские товары", "Бытовая химия", "Средства гигиены"],
        )

    def test_get_existing_and_missing(self):
        category = self.categories.get(self.category_id("Бытовая химия"))
        self.assertEqual(category.name, "Бытовая химия")
        self.assertIsNone(self.categories.get(999))


class ProductCrudTest(RepositoryTestCase):
    """Создание, чтение, изменение, удаление."""

    def test_add_and_get(self):
        product_id = self.products.add(self.user_id, self.data())
        product = self.products.get(self.user_id, product_id)
        self.assertEqual(product.name, "Ибупрофен")
        self.assertEqual(product.category_name, "Лекарства")
        self.assertEqual(product.quantity, 2.0)
        self.assertEqual(product.expiry_date, date(2026, 10, 20))
        self.assertEqual(product.indications, "Жаропонижающее")
        self.assertTrue(product.created_at)

    def test_product_without_expiry_date(self):
        product_id = self.products.add(self.user_id, self.data(expiry_date=None))
        self.assertIsNone(self.products.get(self.user_id, product_id).expiry_date)

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.products.get(self.user_id, 999))

    def test_other_users_product_is_not_visible(self):
        product_id = self.products.add(self.user_id, self.data())
        other_id = self.add_user("boris")
        self.assertIsNone(self.products.get(other_id, product_id))

    def test_update(self):
        product_id = self.products.add(self.user_id, self.data())
        changed = self.products.update(
            self.user_id, product_id, self.data("Нурофен", quantity=7.5)
        )
        product = self.products.get(self.user_id, product_id)
        self.assertTrue(changed)
        self.assertEqual(product.name, "Нурофен")
        self.assertEqual(product.quantity, 7.5)

    def test_update_other_users_product_changes_nothing(self):
        product_id = self.products.add(self.user_id, self.data())
        other_id = self.add_user("boris")
        changed = self.products.update(other_id, product_id, self.data("Взлом"))
        self.assertFalse(changed)
        self.assertEqual(self.products.get(self.user_id, product_id).name, "Ибупрофен")

    def test_delete(self):
        product_id = self.products.add(self.user_id, self.data())
        self.assertTrue(self.products.delete(self.user_id, product_id))
        self.assertIsNone(self.products.get(self.user_id, product_id))

    def test_delete_other_users_product_changes_nothing(self):
        product_id = self.products.add(self.user_id, self.data())
        other_id = self.add_user("boris")
        self.assertFalse(self.products.delete(other_id, product_id))
        self.assertIsNotNone(self.products.get(self.user_id, product_id))

    def test_negative_quantity_rejected_by_database(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.products.add(self.user_id, self.data(quantity=-1.0))


class ProductListTest(RepositoryTestCase):
    """Поиск, фильтр и сортировка."""

    def setUp(self) -> None:
        super().setUp()
        chemistry = self.category_id("Бытовая химия")
        self.products.add(
            self.user_id, self.data("Ибупрофен", expiry_date=date(2026, 10, 20))
        )
        self.products.add(self.user_id, self.data("аспирин", expiry_date=None))
        self.products.add(
            self.user_id,
            self.data("Бинт", category_id=chemistry, expiry_date=date(2026, 9, 1)),
        )

    def names(self, **kwargs):
        return [p.name for p in self.products.list_for_user(self.user_id, **kwargs)]

    def test_only_own_products_listed(self):
        other_id = self.add_user("boris")
        self.products.add(other_id, self.data("Чужой товар"))
        self.assertNotIn("Чужой товар", self.names())
        self.assertEqual(len(self.names()), 3)

    def test_search_ignores_case_for_cyrillic(self):
        self.assertEqual(self.names(search="ИБУ"), ["Ибупрофен"])
        self.assertEqual(self.names(search="ибу"), ["Ибупрофен"])

    def test_search_finds_part_of_name(self):
        self.assertEqual(self.names(search="пирин"), ["аспирин"])

    def test_search_wildcards_are_literal(self):
        self.assertEqual(self.names(search="%"), [])
        self.assertEqual(self.names(search="_"), [])

    def test_blank_search_returns_everything(self):
        self.assertEqual(len(self.names(search="   ")), 3)

    def test_filter_by_category(self):
        chemistry = self.category_id("Бытовая химия")
        self.assertEqual(self.names(category_id=chemistry), ["Бинт"])

    def test_sort_by_name_ignores_case(self):
        self.assertEqual(self.names(sort="name"), ["аспирин", "Бинт", "Ибупрофен"])

    def test_sort_by_expiry_puts_missing_dates_last(self):
        self.assertEqual(self.names(sort="expiry"), ["Бинт", "Ибупрофен", "аспирин"])

    def test_unknown_sort_rejected(self):
        with self.assertRaises(ValueError):
            self.names(sort="name; DROP TABLE products")
        self.assertEqual(self.count_rows("products"), 3)

    def test_hostile_search_text_is_harmless(self):
        self.assertEqual(self.names(search="'; DROP TABLE products; --"), [])
        self.assertEqual(self.count_rows("products"), 3)


class HistoryRepositoryTest(RepositoryTestCase):
    """Журнал действий."""

    def test_add_and_list_newest_first(self):
        self.history.add(self.user_id, None, HistoryAction.PRODUCT_ADDED, "первое")
        self.history.add(self.user_id, None, HistoryAction.PRODUCT_DELETED, "второе")
        records = self.history.list_for_user(self.user_id)
        self.assertEqual([r.description for r in records], ["второе", "первое"])

    def test_filter_by_action_and_limit(self):
        self.history.add(self.user_id, None, HistoryAction.PRODUCT_ADDED, "а")
        self.history.add(self.user_id, None, HistoryAction.PRODUCT_DELETED, "б")
        self.history.add(self.user_id, None, HistoryAction.PRODUCT_DELETED, "в")
        deleted = self.history.list_for_user(
            self.user_id, action=HistoryAction.PRODUCT_DELETED
        )
        self.assertEqual(len(deleted), 2)
        self.assertEqual(len(self.history.list_for_user(self.user_id, limit=1)), 1)

    def test_other_users_history_not_visible(self):
        other_id = self.add_user("boris")
        self.history.add(other_id, None, HistoryAction.PRODUCT_ADDED, "чужое")
        self.assertEqual(self.history.list_for_user(self.user_id), [])
