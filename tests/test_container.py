"""Тесты контейнера сервисов."""

from datetime import date, timedelta

from pharmacy.services.container import build_services
from pharmacy.services.product_service import ProductForm
from tests.helpers import DatabaseTestCase


class ContainerTest(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.services = build_services(self.db)

    def test_every_service_is_created(self):
        for name in (
            "auth",
            "products",
            "notifications",
            "shopping",
            "history",
            "settings",
            "dashboard",
        ):
            self.assertIsNotNone(getattr(self.services, name), name)

    def test_adding_a_product_creates_notification(self):
        user = self.services.auth.register(
            "anna", "Анна", "anna@mail.ru", "password1", "password1"
        )
        form = ProductForm(
            name="Бинт",
            category_id=self.category_id(),
            quantity="0",
            unit="шт.",
            min_quantity="1",
        )
        self.services.products.add_product(user.id, form)
        self.assertEqual(self.services.notifications.count_unread(user.id), 1)

    def test_changing_settings_refreshes_notifications(self):
        user = self.services.auth.register(
            "anna", "Анна", "anna@mail.ru", "password1", "password1"
        )
        expiry = (date.today() + timedelta(days=20)).isoformat()
        self.add_product(user.id, quantity=5, expiry_date=expiry)
        self.services.notifications.refresh(user.id)
        self.assertEqual(self.services.notifications.count_unread(user.id), 1)
        # Срок предупреждения короче 20 дней: уведомление больше не нужно.
        self.services.settings.update_settings(user.id, "10", "light", True, True)
        self.assertEqual(self.services.notifications.count_unread(user.id), 0)

    def test_services_are_immutable(self):
        with self.assertRaises(AttributeError):
            self.services.auth = None
