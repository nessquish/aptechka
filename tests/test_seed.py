"""Тесты тестовых данных и работы с большим объёмом записей."""

import time

from pharmacy.db.seed import (
    DEMO_LOGIN,
    DEMO_PASSWORD,
    DEMO_PRODUCTS,
    seed_bulk,
    seed_demo,
)
from pharmacy.utils.security import verify_password
from tests.helpers import DatabaseTestCase


class SeedDemoTest(DatabaseTestCase):
    """Демо-данные соответствуют макету."""

    def test_demo_data_created(self):
        user_id = seed_demo(self.db)
        self.assertIsNotNone(user_id)
        self.assertEqual(self.count_rows("users"), 1)
        self.assertEqual(self.count_rows("products"), len(DEMO_PRODUCTS))
        self.assertEqual(self.count_rows("shopping_list"), 4)
        self.assertGreaterEqual(self.count_rows("history"), 3)

    def test_demo_password_is_stored_as_hash(self):
        seed_demo(self.db)
        row = self.db.fetch_one(
            "SELECT password_hash FROM users WHERE login = ?", (DEMO_LOGIN,)
        )
        self.assertNotEqual(row["password_hash"], DEMO_PASSWORD)
        self.assertTrue(verify_password(DEMO_PASSWORD, row["password_hash"]))

    def test_second_run_does_not_duplicate(self):
        seed_demo(self.db)
        self.assertIsNone(seed_demo(self.db))
        self.assertEqual(self.count_rows("users"), 1)
        self.assertEqual(self.count_rows("products"), len(DEMO_PRODUCTS))

    def test_demo_has_expired_and_expiring_products(self):
        seed_demo(self.db)
        expired = self.db.fetch_one(
            "SELECT COUNT(*) AS n FROM products WHERE expiry_date < date('now')"
        )
        soon = self.db.fetch_one(
            "SELECT COUNT(*) AS n FROM products"
            " WHERE expiry_date BETWEEN date('now') AND date('now', '+30 days')"
        )
        self.assertGreaterEqual(expired["n"], 1)
        self.assertGreaterEqual(soon["n"], 2)


class BulkDataTest(DatabaseTestCase):
    """Требование ТЗ: корректная работа минимум с 1000 записями."""

    def test_thousand_products_listed_in_under_one_second(self):
        user_id = self.add_user()
        seed_bulk(self.db, user_id, count=1000)
        started = time.perf_counter()
        rows = self.db.fetch_all(
            "SELECT p.*, c.name AS category FROM products p"
            " JOIN categories c ON c.id = p.category_id"
            " WHERE p.user_id = ? ORDER BY p.expiry_date",
            (user_id,),
        )
        elapsed = time.perf_counter() - started
        self.assertEqual(len(rows), 1000)
        self.assertLess(elapsed, 1.0)

    def test_bulk_data_is_reproducible(self):
        user_id = self.add_user()
        seed_bulk(self.db, user_id, count=50, seed=7)
        first = [
            row["expiry_date"] for row in self.db.fetch_all("SELECT * FROM products")
        ]
        self.db.execute("DELETE FROM products")
        seed_bulk(self.db, user_id, count=50, seed=7)
        second = [
            row["expiry_date"] for row in self.db.fetch_all("SELECT * FROM products")
        ]
        self.assertEqual(first, second)
