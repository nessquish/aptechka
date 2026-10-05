"""Тесты сервиса товаров."""

from datetime import date
from unittest import mock

from pharmacy.errors import NotFoundError, ValidationError
from pharmacy.models import HistoryAction
from pharmacy.repositories.history_repository import HistoryRepository
from pharmacy.services.product_service import ProductForm, ProductService
from pharmacy.services.status import ProductStatus
from tests.helpers import DatabaseTestCase

TODAY = date(2026, 10, 1)


class ProductServiceTestCase(DatabaseTestCase):
    """База, сервис и пользователь anna."""

    def setUp(self) -> None:
        super().setUp()
        self.service = ProductService(self.db)
        self.history = HistoryRepository(self.db)
        self.user_id = self.add_user("anna")

    def form(self, **overrides) -> ProductForm:
        """Корректная форма товара; отдельные поля можно заменить."""
        values = dict(
            name="Ибупрофен",
            category_id=self.category_id("Лекарства"),
            quantity="2",
            unit="упак.",
            expiry_date="20.10.2026",
            indications="Жаропонижающее",
            storage_place="Шкаф",
            min_quantity="3",
            note="",
        )
        values.update(overrides)
        return ProductForm(**values)

    def add(self, **overrides):
        """Добавляет товар пользователю anna."""
        return self.service.add_product(self.user_id, self.form(**overrides))


class AddProductTest(ProductServiceTestCase):
    """Добавление товара."""

    def test_add_stores_parsed_values(self):
        view = self.add(quantity="1,5", expiry_date="05.03.2027", min_quantity="")
        product = view.product
        self.assertEqual(product.name, "Ибупрофен")
        self.assertEqual(product.quantity, 1.5)
        self.assertEqual(product.expiry_date, date(2027, 3, 5))
        self.assertEqual(product.min_quantity, 0.0)
        self.assertEqual(product.category_name, "Лекарства")

    def test_text_fields_are_trimmed(self):
        view = self.add(name="  Бинт  ", storage_place="  Аптечка ")
        self.assertEqual(view.product.name, "Бинт")
        self.assertEqual(view.product.storage_place, "Аптечка")

    def test_expiry_date_is_optional(self):
        self.assertIsNone(self.add(expiry_date="").product.expiry_date)

    def test_past_expiry_date_is_allowed(self):
        view = self.add(expiry_date="01.01.2020")
        self.assertEqual(view.product.expiry_date, date(2020, 1, 1))

    def test_add_writes_history(self):
        view = self.add()
        records = self.history.list_for_user(self.user_id)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].action, HistoryAction.PRODUCT_ADDED)
        self.assertEqual(records[0].product_id, view.product.id)
        self.assertEqual(records[0].description, "Ибупрофен · добавлен в аптечку")

    def test_failed_history_write_rolls_back_the_product(self):
        with mock.patch.object(
            self.service._history, "add", side_effect=RuntimeError("сбой")
        ):
            with self.assertRaises(RuntimeError):
                self.add()
        self.assertEqual(self.count_rows("products"), 0)


class ValidationTest(ProductServiceTestCase):
    """Проверка формы: сообщение и поле, к которому оно относится."""

    def assert_invalid(self, field, **overrides):
        with self.assertRaises(ValidationError) as ctx:
            self.add(**overrides)
        self.assertEqual(ctx.exception.field, field)
        self.assertEqual(self.count_rows("products"), 0)

    def test_name_required(self):
        self.assert_invalid("name", name="   ")

    def test_name_too_long(self):
        self.assert_invalid("name", name="а" * 101)

    def test_category_required(self):
        self.assert_invalid("category_id", category_id=None)

    def test_unknown_category_rejected(self):
        self.assert_invalid("category_id", category_id=999)

    def test_quantity_required(self):
        self.assert_invalid("quantity", quantity="")

    def test_quantity_must_be_number(self):
        self.assert_invalid("quantity", quantity="два")
        self.assert_invalid("quantity", quantity="nan")
        self.assert_invalid("quantity", quantity="inf")

    def test_negative_quantity_rejected(self):
        self.assert_invalid("quantity", quantity="-1")

    def test_huge_quantity_rejected(self):
        self.assert_invalid("quantity", quantity="1e9")

    def test_unit_required(self):
        self.assert_invalid("unit", unit="  ")

    def test_negative_minimum_rejected(self):
        self.assert_invalid("min_quantity", min_quantity="-2")

    def test_invalid_expiry_date_rejected(self):
        self.assert_invalid("expiry_date", expiry_date="2026-10-20")
        self.assert_invalid("expiry_date", expiry_date="31.02.2026")

    def test_long_note_rejected(self):
        self.assert_invalid("note", note="я" * 501)

    def test_zero_quantity_is_allowed(self):
        self.assertEqual(self.add(quantity="0").product.quantity, 0.0)


class UpdateProductTest(ProductServiceTestCase):
    """Изменение товара."""

    def test_update_changes_values(self):
        view = self.add()
        updated = self.service.update_product(
            self.user_id, view.product.id, self.form(name="Нурофен", quantity="7")
        )
        self.assertEqual(updated.product.name, "Нурофен")
        self.assertEqual(updated.product.quantity, 7.0)

    def test_quantity_change_is_described_in_history(self):
        view = self.add(name="Парацетамол", quantity="5")
        self.service.update_product(
            self.user_id, view.product.id, self.form(name="Парацетамол", quantity="10")
        )
        latest = self.history.list_for_user(self.user_id)[0]
        self.assertEqual(latest.action, HistoryAction.PRODUCT_UPDATED)
        self.assertEqual(
            latest.description, "Парацетамол · количество изменено с 5 до 10"
        )

    def test_other_changes_listed_by_field_name(self):
        view = self.add()
        self.service.update_product(
            self.user_id,
            view.product.id,
            self.form(expiry_date="01.01.2028", storage_place="Кухня"),
        )
        latest = self.history.list_for_user(self.user_id)[0]
        self.assertIn("изменено: срок годности, место хранения", latest.description)

    def test_update_without_changes_writes_no_history(self):
        view = self.add()
        self.service.update_product(self.user_id, view.product.id, self.form())
        self.assertEqual(len(self.history.list_for_user(self.user_id)), 1)

    def test_invalid_update_changes_nothing(self):
        view = self.add()
        with self.assertRaises(ValidationError):
            self.service.update_product(
                self.user_id, view.product.id, self.form(quantity="-5")
            )
        self.assertEqual(
            self.service.get_product(self.user_id, view.product.id).product.quantity,
            2.0,
        )

    def test_update_unknown_product(self):
        with self.assertRaises(NotFoundError):
            self.service.update_product(self.user_id, 999, self.form())


class DeleteProductTest(ProductServiceTestCase):
    """Удаление товара."""

    def test_delete_removes_product(self):
        view = self.add()
        self.service.delete_product(self.user_id, view.product.id)
        self.assertEqual(self.count_rows("products"), 0)

    def test_history_survives_deletion_with_product_name(self):
        view = self.add(name="Ибупрофен")
        self.service.delete_product(self.user_id, view.product.id)
        records = self.history.list_for_user(self.user_id)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].action, HistoryAction.PRODUCT_DELETED)
        self.assertEqual(records[0].description, "Ибупрофен · удалён из аптечки")
        self.assertTrue(all(record.product_id is None for record in records))

    def test_delete_unknown_product(self):
        with self.assertRaises(NotFoundError):
            self.service.delete_product(self.user_id, 999)


class OwnershipTest(ProductServiceTestCase):
    """Данные пользователей разделены."""

    def setUp(self) -> None:
        super().setUp()
        self.other_id = self.add_user("boris")
        self.view = self.add()

    def test_other_user_cannot_read(self):
        with self.assertRaises(NotFoundError):
            self.service.get_product(self.other_id, self.view.product.id)

    def test_other_user_cannot_update(self):
        with self.assertRaises(NotFoundError):
            self.service.update_product(
                self.other_id, self.view.product.id, self.form(name="Взлом")
            )
        self.assertEqual(
            self.service.get_product(self.user_id, self.view.product.id).product.name,
            "Ибупрофен",
        )

    def test_other_user_cannot_delete(self):
        with self.assertRaises(NotFoundError):
            self.service.delete_product(self.other_id, self.view.product.id)
        self.assertEqual(self.count_rows("products"), 1)

    def test_other_user_sees_empty_list(self):
        self.assertEqual(self.service.list_products(self.other_id), [])


class ListProductsTest(ProductServiceTestCase):
    """Таблица «Моя аптечка»: состояния, поиск, фильтры, сортировка."""

    def setUp(self) -> None:
        super().setUp()
        chemistry = self.category_id("Бытовая химия")
        self.add(name="Просрочка", expiry_date="01.09.2026", quantity="5")
        self.add(name="Скоро", expiry_date="10.10.2026", quantity="5")
        self.add(name="Мало", expiry_date="", quantity="1", min_quantity="2")
        self.add(
            name="Всё хорошо",
            expiry_date="01.01.2028",
            quantity="9",
            category_id=chemistry,
        )

    def names(self, **kwargs):
        views = self.service.list_products(self.user_id, today=TODAY, **kwargs)
        return [view.product.name for view in views]

    def test_statuses_calculated(self):
        views = {
            view.product.name: view
            for view in self.service.list_products(self.user_id, today=TODAY)
        }
        self.assertEqual(views["Просрочка"].primary_status, ProductStatus.EXPIRED)
        self.assertEqual(views["Скоро"].primary_status, ProductStatus.EXPIRING)
        self.assertEqual(views["Мало"].primary_status, ProductStatus.LOW_STOCK)
        self.assertEqual(views["Всё хорошо"].primary_status, ProductStatus.OK)

    def test_days_left_calculated(self):
        views = {
            view.product.name: view
            for view in self.service.list_products(self.user_id, today=TODAY)
        }
        self.assertEqual(views["Скоро"].days_left, 9)
        self.assertEqual(views["Просрочка"].days_left, -30)
        self.assertIsNone(views["Мало"].days_left)

    def test_filter_by_status(self):
        self.assertEqual(self.names(status=ProductStatus.EXPIRED), ["Просрочка"])
        self.assertEqual(self.names(status=ProductStatus.EXPIRING), ["Скоро"])
        self.assertEqual(self.names(status=ProductStatus.LOW_STOCK), ["Мало"])
        self.assertEqual(self.names(status=ProductStatus.OK), ["Всё хорошо"])

    def test_filter_by_category(self):
        chemistry = self.category_id("Бытовая химия")
        self.assertEqual(self.names(category_id=chemistry), ["Всё хорошо"])

    def test_search_and_sort(self):
        self.assertEqual(self.names(search="ПРОС"), ["Просрочка"])
        self.assertEqual(
            self.names(sort="expiry"), ["Просрочка", "Скоро", "Всё хорошо", "Мало"]
        )

    def test_user_setting_changes_warning_period(self):
        self.db.execute(
            "UPDATE users SET warning_days = 3 WHERE id = ?", (self.user_id,)
        )
        self.assertEqual(self.names(status=ProductStatus.EXPIRING), [])
        self.assertEqual(self.names(status=ProductStatus.OK), ["Всё хорошо", "Скоро"])

    def test_categories_for_dropdown(self):
        names = [category.name for category in self.service.list_categories()]
        self.assertEqual(len(names), 4)
        self.assertIn("Лекарства", names)
