"""Тесты сводки главного экрана."""

from datetime import date

from pharmacy.services.dashboard_service import (
    ATTENTION_LIMIT,
    RECENT_HISTORY_LIMIT,
    DashboardService,
)
from pharmacy.services.notification_service import NotificationService
from pharmacy.services.shopping_service import ShoppingService
from pharmacy.services.status import ProductStatus
from tests.helpers import DatabaseTestCase

TODAY = date(2026, 10, 1)


class DashboardTest(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.service = DashboardService(self.db)
        self.user_id = self.add_user("anna")

    def make_product(self, name, quantity=5, min_quantity=1, expiry=None, user_id=None):
        return self.db.execute(
            "INSERT INTO products (user_id, category_id, name, quantity,"
            " min_quantity, expiry_date) VALUES (?, ?, ?, ?, ?, ?)",
            (
                user_id or self.user_id,
                self.category_id(),
                name,
                quantity,
                min_quantity,
                expiry,
            ),
        )

    def summary(self, user_id=None):
        return self.service.summary(user_id or self.user_id, today=TODAY)

    def test_empty_account(self):
        result = self.summary()
        self.assertEqual(
            (result.total, result.expired, result.expiring, result.low_stock),
            (0, 0, 0, 0),
        )
        self.assertEqual(result.attention, [])
        self.assertEqual(result.recent_history, [])
        self.assertEqual(result.unread_notifications, 0)
        self.assertEqual(result.shopping_open, 0)

    def test_counters(self):
        self.make_product("Здоровый", expiry="2027-05-12")
        self.make_product("Просроченный", expiry="2026-08-15")
        self.make_product("Скоро", expiry="2026-10-20")
        self.make_product("Мало", quantity=0)
        result = self.summary()
        self.assertEqual(result.total, 4)
        self.assertEqual(result.expired, 1)
        self.assertEqual(result.expiring, 1)
        self.assertEqual(result.low_stock, 1)

    def test_product_with_two_problems_counts_in_both(self):
        self.make_product("Двойной", quantity=0, expiry="2026-10-10")
        result = self.summary()
        self.assertEqual((result.expiring, result.low_stock), (1, 1))
        self.assertEqual(result.total, 1)

    def test_attention_excludes_healthy_and_sorts_by_urgency(self):
        self.make_product("Здоровый", expiry="2027-05-12")
        self.make_product("Мало", quantity=0)
        self.make_product("Скоро позже", expiry="2026-10-25")
        self.make_product("Скоро раньше", expiry="2026-10-05")
        self.make_product("Просроченный", expiry="2026-08-15")
        names = [v.product.name for v in self.summary().attention]
        self.assertEqual(names, ["Просроченный", "Скоро раньше", "Скоро позже", "Мало"])

    def test_attention_total_counts_all_problem_products(self):
        for number in range(ATTENTION_LIMIT + 3):
            self.make_product(f"Товар {number}", quantity=0)
        self.make_product("Здоровый", expiry="2027-05-12")
        result = self.summary()
        self.assertEqual(result.attention_total, ATTENTION_LIMIT + 3)
        self.assertEqual(len(result.attention), ATTENTION_LIMIT)

    def test_recent_products_newest_first_and_limited(self):
        for number in range(7):
            product_id = self.make_product(f"Товар {number}")
            self.db.execute(
                "UPDATE products SET created_at = ? WHERE id = ?",
                (f"2026-09-{10 + number} 12:00:00", product_id),
            )
        names = [v.product.name for v in self.summary().recent_products]
        self.assertEqual(names, ["Товар 6", "Товар 5", "Товар 4", "Товар 3", "Товар 2"])

    def test_attention_is_limited(self):
        for number in range(ATTENTION_LIMIT + 3):
            self.make_product(f"Товар {number}", quantity=0)
        result = self.summary()
        self.assertEqual(len(result.attention), ATTENTION_LIMIT)
        self.assertEqual(result.low_stock, ATTENTION_LIMIT + 3)
        for view in result.attention:
            self.assertEqual(view.primary_status, ProductStatus.LOW_STOCK)

    def test_recent_history_is_limited_and_newest_first(self):
        shopping = ShoppingService(self.db)
        for number in range(RECENT_HISTORY_LIMIT + 2):
            shopping.add_manual(self.user_id, f"Позиция {number}")
        records = self.summary().recent_history
        self.assertEqual(len(records), RECENT_HISTORY_LIMIT)
        self.assertTrue(records[0].description.startswith("Позиция 6"))

    def test_unread_notifications_and_open_shopping(self):
        self.make_product("Мало", quantity=0)
        NotificationService(self.db).refresh(self.user_id, today=TODAY)
        shopping = ShoppingService(self.db)
        bought = shopping.add_manual(self.user_id, "Куплено")
        shopping.add_manual(self.user_id, "Нужно")
        shopping.set_bought(self.user_id, bought.id)
        result = self.summary()
        self.assertEqual(result.unread_notifications, 1)
        self.assertEqual(result.shopping_open, 1)

    def test_data_of_other_users_is_not_included(self):
        other_id = self.add_user("boris")
        self.make_product("Чужой", quantity=0, user_id=other_id)
        ShoppingService(self.db).add_manual(other_id, "Чужая позиция")
        result = self.summary()
        self.assertEqual(result.total, 0)
        self.assertEqual(result.recent_history, [])
        self.assertEqual(result.shopping_open, 0)
        self.assertEqual(self.summary(other_id).total, 1)
