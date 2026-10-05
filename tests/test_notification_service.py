"""Тесты уведомлений о состоянии товаров."""

from datetime import date, timedelta

from pharmacy.errors import NotFoundError
from pharmacy.models import NotificationKind
from pharmacy.services.notification_service import NotificationService
from pharmacy.services.product_service import ProductForm, ProductService
from tests.helpers import DatabaseTestCase

TODAY = date(2026, 10, 1)


class NotificationTestCase(DatabaseTestCase):
    """База, сервис уведомлений и пользователь anna."""

    def setUp(self) -> None:
        super().setUp()
        self.service = NotificationService(self.db)
        self.user_id = self.add_user("anna")

    def make_product(
        self,
        name,
        quantity=5,
        min_quantity=1,
        expiry=None,
        unit="шт.",
        place="",
        user_id=None,
    ) -> int:
        """Добавляет товар напрямую в базу (сроки и количества заданы точно)."""
        return self.db.execute(
            "INSERT INTO products (user_id, category_id, name, quantity, unit,"
            " expiry_date, storage_place, min_quantity)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id or self.user_id,
                self.category_id(),
                name,
                quantity,
                unit,
                expiry.isoformat() if expiry else None,
                place,
                min_quantity,
            ),
        )

    def refresh(self, **kwargs) -> int:
        """Пересчитывает уведомления пользователя на дату TODAY."""
        return self.service.refresh(self.user_id, today=TODAY, **kwargs)

    def messages(self, **kwargs):
        """Тексты уведомлений пользователя (в порядке, не зависящем от времени)."""
        items = self.service.list_notifications(self.user_id, **kwargs)
        return sorted(item.message for item in items)


class CreationTest(NotificationTestCase):
    """Создание уведомлений из состояния товаров."""

    def test_expired_message_matches_design(self):
        self.make_product(
            "Активированный уголь", expiry=date(2026, 8, 15), place="Шкаф"
        )
        self.refresh()
        items = self.service.list_notifications(self.user_id)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].kind, NotificationKind.EXPIRED)
        self.assertEqual(
            items[0].message, "Активированный уголь · истёк 15.08.2026 · Шкаф"
        )
        self.assertFalse(items[0].is_read)

    def test_expired_message_without_storage_place(self):
        self.make_product("Бинт", expiry=date(2026, 9, 1))
        self.refresh()
        self.assertEqual(self.messages(), ["Бинт · истёк 01.09.2026"])

    def test_expiring_message_uses_correct_plural(self):
        self.make_product("Ибупрофен", expiry=date(2026, 10, 20))
        self.make_product("Витамин D", expiry=date(2026, 10, 25))
        self.make_product("Аспирин", expiry=date(2026, 10, 2))
        self.refresh()
        self.assertEqual(
            self.messages(),
            [
                "Аспирин · до 02.10.2026 · осталось 1 день",
                "Витамин D · до 25.10.2026 · осталось 24 дня",
                "Ибупрофен · до 20.10.2026 · осталось 19 дней",
            ],
        )

    def test_low_stock_message(self):
        self.make_product("Бинт", quantity=1, min_quantity=2, unit="шт.")
        self.refresh()
        self.assertEqual(self.messages(), ["Бинт · осталось 1 шт. (минимум 2 шт.)"])

    def test_healthy_product_gets_no_notification(self):
        self.make_product("Парацетамол", quantity=10, expiry=date(2027, 5, 12))
        self.assertEqual(self.refresh(), 0)
        self.assertEqual(self.messages(), [])

    def test_product_with_two_problems_gets_two_notifications(self):
        self.make_product(
            "Ибупрофен", quantity=1, min_quantity=3, expiry=date(2026, 10, 10)
        )
        self.refresh()
        kinds = {item.kind for item in self.service.list_notifications(self.user_id)}
        self.assertEqual(kinds, {NotificationKind.EXPIRING, NotificationKind.LOW_STOCK})

    def test_refresh_returns_number_of_new_notifications(self):
        self.make_product("Бинт", quantity=0, min_quantity=1)
        self.make_product("Уголь", expiry=date(2026, 9, 1))
        self.assertEqual(self.refresh(), 2)

    def test_second_refresh_creates_no_duplicates(self):
        self.make_product("Бинт", quantity=0, min_quantity=1)
        self.refresh()
        self.assertEqual(self.refresh(), 0)
        self.assertEqual(self.count_rows("notifications"), 1)

    def test_unknown_user(self):
        with self.assertRaises(NotFoundError):
            self.service.refresh(999)


class SettingsTest(NotificationTestCase):
    """Настройки пользователя влияют на уведомления."""

    def setUp(self) -> None:
        super().setUp()
        self.make_product("Уголь", expiry=date(2026, 9, 1))
        self.make_product("Ибупрофен", expiry=date(2026, 10, 20))
        self.make_product("Бинт", quantity=0, min_quantity=1)

    def kinds(self):
        items = self.service.list_notifications(self.user_id)
        return sorted(item.kind for item in items)

    def test_all_kinds_by_default(self):
        self.refresh()
        self.assertEqual(self.kinds(), ["expired", "expiring", "low_stock"])

    def test_expired_notifications_can_be_turned_off(self):
        self.db.execute(
            "UPDATE users SET notify_expired = 0 WHERE id = ?", (self.user_id,)
        )
        self.refresh()
        self.assertEqual(self.kinds(), ["expiring", "low_stock"])

    def test_low_stock_notifications_can_be_turned_off(self):
        self.db.execute(
            "UPDATE users SET notify_low_stock = 0 WHERE id = ?", (self.user_id,)
        )
        self.refresh()
        self.assertEqual(self.kinds(), ["expired", "expiring"])

    def test_shorter_warning_period_removes_expiring_notification(self):
        self.refresh()
        self.db.execute(
            "UPDATE users SET warning_days = 5 WHERE id = ?", (self.user_id,)
        )
        self.refresh()
        self.assertEqual(self.kinds(), ["expired", "low_stock"])

    def test_turning_setting_off_removes_existing_notifications(self):
        self.refresh()
        self.db.execute(
            "UPDATE users SET notify_low_stock = 0 WHERE id = ?", (self.user_id,)
        )
        self.refresh()
        self.assertNotIn("low_stock", self.kinds())


class LifecycleTest(NotificationTestCase):
    """Что происходит с уведомлением, когда товар меняется."""

    def test_notification_removed_when_cause_disappears(self):
        product_id = self.make_product("Бинт", quantity=0, min_quantity=1)
        self.refresh()
        self.db.execute("UPDATE products SET quantity = 5 WHERE id = ?", (product_id,))
        self.refresh()
        self.assertEqual(self.count_rows("notifications"), 0)

    def test_message_updated_but_notification_kept(self):
        product_id = self.make_product("Бинт", quantity=1, min_quantity=2)
        self.refresh()
        before = self.service.list_notifications(self.user_id)[0]
        self.service.mark_read(self.user_id, before.id)
        self.db.execute("UPDATE products SET quantity = 0 WHERE id = ?", (product_id,))
        self.refresh()
        after = self.service.list_notifications(self.user_id)[0]
        self.assertEqual(after.id, before.id)
        self.assertEqual(after.message, "Бинт · осталось 0 шт. (минимум 2 шт.)")
        self.assertTrue(after.is_read)

    def test_read_notification_stays_read_after_refresh(self):
        self.make_product("Бинт", quantity=0, min_quantity=1)
        self.refresh()
        item = self.service.list_notifications(self.user_id)[0]
        self.service.mark_read(self.user_id, item.id)
        self.refresh()
        self.assertTrue(self.service.list_notifications(self.user_id)[0].is_read)

    def test_deleted_notification_returns_while_problem_remains(self):
        self.make_product("Бинт", quantity=0, min_quantity=1)
        self.refresh()
        item = self.service.list_notifications(self.user_id)[0]
        self.service.delete(self.user_id, item.id)
        self.assertEqual(self.count_rows("notifications"), 0)
        self.refresh()
        self.assertEqual(self.count_rows("notifications"), 1)

    def test_refresh_of_one_product_leaves_others_alone(self):
        first = self.make_product("Первый", quantity=0, min_quantity=1)
        second = self.make_product("Второй", quantity=0, min_quantity=1)
        self.refresh()
        self.db.execute(
            "UPDATE products SET quantity = 9 WHERE id IN (?, ?)", (first, second)
        )
        self.refresh(product_id=first)
        # Первый пересчитан и уведомление исчезло, второй не тронут.
        self.assertEqual(self.messages(), ["Второй · осталось 0 шт. (минимум 1 шт.)"])

    def test_refresh_of_deleted_product_does_nothing(self):
        self.assertEqual(self.refresh(product_id=999), 0)

    def test_other_users_products_do_not_create_notifications_for_me(self):
        other_id = self.add_user("boris")
        self.make_product("Чужой бинт", quantity=0, min_quantity=1, user_id=other_id)
        self.refresh()
        self.assertEqual(self.messages(), [])
        self.service.refresh(other_id, today=TODAY)
        self.assertEqual(len(self.service.list_notifications(other_id)), 1)

    def test_deleting_product_removes_its_notifications(self):
        product_id = self.make_product("Бинт", quantity=0, min_quantity=1)
        self.refresh()
        self.db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        self.assertEqual(self.count_rows("notifications"), 0)


class ReadingTest(NotificationTestCase):
    """Чтение, отметка прочитанным, удаление, фильтры."""

    def setUp(self) -> None:
        super().setUp()
        self.make_product("Бинт", quantity=0, min_quantity=1)
        self.make_product("Уголь", expiry=date(2026, 9, 1))
        self.make_product("Ибупрофен", expiry=date(2026, 10, 20))
        self.refresh()

    def test_count_unread(self):
        self.assertEqual(self.service.count_unread(self.user_id), 3)

    def test_mark_read_reduces_counter(self):
        item = self.service.list_notifications(self.user_id)[0]
        self.service.mark_read(self.user_id, item.id)
        self.assertEqual(self.service.count_unread(self.user_id), 2)

    def test_mark_all_read(self):
        self.assertEqual(self.service.mark_all_read(self.user_id), 3)
        self.assertEqual(self.service.count_unread(self.user_id), 0)
        self.assertEqual(self.service.mark_all_read(self.user_id), 0)

    def test_filter_by_kind(self):
        items = self.service.list_notifications(
            self.user_id, kind=NotificationKind.LOW_STOCK
        )
        self.assertEqual(len(items), 1)

    def test_filter_unread_only(self):
        item = self.service.list_notifications(self.user_id)[0]
        self.service.mark_read(self.user_id, item.id)
        unread = self.service.list_notifications(self.user_id, unread_only=True)
        self.assertEqual(len(unread), 2)

    def test_filter_by_period(self):
        today = date.today()
        self.assertEqual(
            len(self.service.list_notifications(self.user_id, since=today)), 3
        )
        tomorrow = today + timedelta(days=1)
        self.assertEqual(
            self.service.list_notifications(self.user_id, since=tomorrow), []
        )

    def test_delete_and_delete_all(self):
        item = self.service.list_notifications(self.user_id)[0]
        self.service.delete(self.user_id, item.id)
        self.assertEqual(self.count_rows("notifications"), 2)
        self.assertEqual(self.service.delete_all(self.user_id), 2)
        self.assertEqual(self.count_rows("notifications"), 0)

    def test_other_user_cannot_touch_my_notification(self):
        other_id = self.add_user("boris")
        item = self.service.list_notifications(self.user_id)[0]
        with self.assertRaises(NotFoundError):
            self.service.mark_read(other_id, item.id)
        with self.assertRaises(NotFoundError):
            self.service.delete(other_id, item.id)
        self.assertEqual(self.count_rows("notifications"), 3)
        self.assertEqual(self.service.delete_all(other_id), 0)
        self.assertEqual(self.count_rows("notifications"), 3)


class ProductServiceHookTest(NotificationTestCase):
    """Сервис товаров сам пересчитывает уведомления."""

    def setUp(self) -> None:
        super().setUp()
        self.products = ProductService(self.db, notifications=self.service)

    def form(self, quantity) -> ProductForm:
        return ProductForm(
            name="Бинт",
            category_id=self.category_id(),
            quantity=quantity,
            unit="шт.",
            min_quantity="2",
        )

    def test_adding_low_stock_product_creates_notification(self):
        self.products.add_product(self.user_id, self.form("1"))
        self.assertEqual(self.count_rows("notifications"), 1)

    def test_restocking_product_removes_notification(self):
        view = self.products.add_product(self.user_id, self.form("1"))
        self.products.update_product(self.user_id, view.product.id, self.form("10"))
        self.assertEqual(self.count_rows("notifications"), 0)

    def test_service_works_without_notifications(self):
        plain = ProductService(self.db)
        plain.add_product(self.user_id, self.form("1"))
        self.assertEqual(self.count_rows("notifications"), 0)
