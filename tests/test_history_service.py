"""Тесты истории действий."""

from datetime import date, timedelta

from pharmacy.models import HistoryAction
from pharmacy.services.history_service import ACTION_LABELS, HistoryService
from pharmacy.services.product_service import ProductForm, ProductService
from pharmacy.services.shopping_service import ShoppingService
from tests.helpers import DatabaseTestCase


class HistoryServiceTest(DatabaseTestCase):
    """Просмотр, фильтры и очистка истории."""

    def setUp(self) -> None:
        super().setUp()
        self.service = HistoryService(self.db)
        self.user_id = self.add_user("anna")
        products = ProductService(self.db)
        form = ProductForm(
            name="Бинт", category_id=self.category_id(), quantity="2", unit="шт."
        )
        view = products.add_product(self.user_id, form)
        self.product_id = view.product.id
        ShoppingService(self.db).add_manual(self.user_id, "Вата")

    def test_lists_newest_first(self):
        actions = [r.action for r in self.service.list_history(self.user_id)]
        self.assertEqual(
            actions, [HistoryAction.SHOPPING_ADDED, HistoryAction.PRODUCT_ADDED]
        )

    def test_filter_by_action(self):
        records = self.service.list_history(
            self.user_id, action=HistoryAction.PRODUCT_ADDED
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].product_id, self.product_id)

    def test_limit(self):
        self.assertEqual(len(self.service.list_history(self.user_id, limit=1)), 1)

    def test_filter_by_period(self):
        self.db.execute(
            "UPDATE history SET created_at = '2020-01-01 10:00:00' WHERE action = ?",
            (HistoryAction.PRODUCT_ADDED,),
        )
        recent = self.service.list_history(
            self.user_id, since=date.today() - timedelta(days=7)
        )
        self.assertEqual([r.action for r in recent], [HistoryAction.SHOPPING_ADDED])
        self.assertEqual(len(self.service.list_history(self.user_id)), 2)

    def test_history_survives_product_deletion(self):
        ProductService(self.db).delete_product(self.user_id, self.product_id)
        records = self.service.list_history(
            self.user_id, action=HistoryAction.PRODUCT_ADDED
        )
        self.assertEqual(len(records), 1)
        self.assertIsNone(records[0].product_id)

    def test_other_users_do_not_see_my_history(self):
        other_id = self.add_user("boris")
        self.assertEqual(self.service.list_history(other_id), [])

    def test_clear_removes_only_my_records(self):
        other_id = self.add_user("boris")
        ShoppingService(self.db).add_manual(other_id, "Бинт")
        self.assertEqual(self.service.clear(self.user_id), 2)
        self.assertEqual(self.service.list_history(self.user_id), [])
        self.assertEqual(len(self.service.list_history(other_id)), 1)

    def test_every_action_has_a_label(self):
        for action in (
            HistoryAction.PRODUCT_ADDED,
            HistoryAction.PRODUCT_UPDATED,
            HistoryAction.PRODUCT_DELETED,
            HistoryAction.SHOPPING_ADDED,
            HistoryAction.SHOPPING_BOUGHT,
            HistoryAction.SHOPPING_REMOVED,
        ):
            self.assertIn(action, ACTION_LABELS)
