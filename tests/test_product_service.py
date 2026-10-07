"""Тесты сервиса товаров."""

from datetime import date
from unittest import mock

from pharmacy.errors import NotFoundError, ValidationError
from pharmacy.models import HistoryAction
from pharmacy.repositories.history_repository import HistoryRepository
from pharmacy.services.product_service import (
    SORT_STATUS,
    SORT_STATUS_OK,
    ProductForm,
    ProductService,
    sort_by_status,
)
from pharmacy.services.status import ProductStatus
from pharmacy.utils.units import UNITS
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

    def test_missing_unit_defaults_to_pieces(self):
        for empty in ("", "   "):
            self.assertEqual(self.add(unit=empty).product.unit, "шт.")

    def test_unit_outside_the_list_is_rejected(self):
        for unit in ("кубометров", "штуковин", "xyz"):
            self.assert_invalid("unit", unit=unit)

    def test_different_spellings_become_one_unit(self):
        cases = {
            "таб": "табл.",
            "Таблетки": "табл.",
            "ТАБЛ.": "табл.",
            "шт": "шт.",
            "упаковка": "упак.",
            "гр": "г",
            "МЛ": "мл",
            "мг": "мг",
        }
        for written, saved in cases.items():
            self.assertEqual(self.add(unit=written).product.unit, saved, written)

    def test_every_listed_unit_is_accepted(self):
        for unit in UNITS:
            self.assertEqual(self.add(unit=unit).product.unit, unit)

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
            latest.description,
            "Парацетамол · количество изменено с 5 упак. до 10 упак.",
        )

    def test_minimum_change_is_described_with_the_unit(self):
        view = self.add(name="Бинт", unit="шт.", min_quantity="1")
        self.service.update_product(
            self.user_id,
            view.product.id,
            self.form(name="Бинт", unit="шт.", min_quantity="3"),
        )
        latest = self.history.list_for_user(self.user_id)[0]
        self.assertIn(
            "минимальный остаток изменён с 1 шт. до 3 шт.", latest.description
        )

    def test_unit_change_is_shown_next_to_the_numbers(self):
        view = self.add(name="Сироп", unit="мл", quantity="100")
        self.service.update_product(
            self.user_id,
            view.product.id,
            self.form(name="Сироп", unit="фл.", quantity="2"),
        )
        latest = self.history.list_for_user(self.user_id)[0]
        self.assertIn("количество изменено с 100 мл до 2 фл.", latest.description)

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


class StatusSortTest(ProductServiceTestCase):
    """Сортировка по состоянию: два направления, внутри группы по сроку годности."""

    def setUp(self) -> None:
        super().setUp()
        self.add(name="Просрочен давно", expiry_date="01.08.2026", quantity="5")
        self.add(name="Просрочен недавно", expiry_date="01.09.2026", quantity="5")
        self.add(name="Скоро", expiry_date="10.10.2026", quantity="5")
        self.add(name="Мало", expiry_date="", quantity="1", min_quantity="2")
        self.add(name="Норма 2028", expiry_date="01.01.2028", quantity="9")
        self.add(name="Норма 2027", expiry_date="01.06.2027", quantity="9")
        self.add(name="Норма без срока", expiry_date="", quantity="9")

    def names(self, sort, **kwargs):
        views = self.service.list_products(
            self.user_id, sort=sort, today=TODAY, **kwargs
        )
        return [view.product.name for view in views]

    def test_expired_first(self):
        self.assertEqual(
            self.names(SORT_STATUS),
            [
                "Просрочен давно",
                "Просрочен недавно",
                "Скоро",
                "Мало",
                "Норма 2027",
                "Норма 2028",
                "Норма без срока",
            ],
        )

    def test_normal_first(self):
        self.assertEqual(
            self.names(SORT_STATUS_OK),
            [
                "Норма 2027",
                "Норма 2028",
                "Норма без срока",
                "Мало",
                "Скоро",
                "Просрочен давно",
                "Просрочен недавно",
            ],
        )

    def test_inside_a_group_the_oldest_expiry_is_always_on_top(self):
        for sort in (SORT_STATUS, SORT_STATUS_OK):
            names = self.names(sort)
            self.assertLess(
                names.index("Просрочен давно"), names.index("Просрочен недавно")
            )
            self.assertLess(names.index("Норма 2027"), names.index("Норма 2028"))
            self.assertLess(names.index("Норма 2028"), names.index("Норма без срока"))

    def test_the_two_directions_swap_the_groups_only(self):
        first = self.names(SORT_STATUS)
        second = self.names(SORT_STATUS_OK)
        self.assertNotEqual(first, second)
        self.assertEqual(sorted(first), sorted(second))
        self.assertEqual(first[0], "Просрочен давно")
        self.assertEqual(second[-1], "Просрочен недавно")

    def test_works_together_with_filters_and_search(self):
        self.assertEqual(
            self.names(SORT_STATUS, search="норма"),
            ["Норма 2027", "Норма 2028", "Норма без срока"],
        )
        self.assertEqual(
            self.names(SORT_STATUS_OK, status=ProductStatus.EXPIRED),
            ["Просрочен давно", "Просрочен недавно"],
        )

    def test_statuses_are_recalculated_for_the_given_day(self):
        later = date(2027, 7, 1)
        views = self.service.list_products(self.user_id, sort=SORT_STATUS, today=later)
        names = [view.product.name for view in views]
        self.assertEqual(
            names[:4],
            [
                "Просрочен давно",
                "Просрочен недавно",
                "Скоро",
                "Норма 2027",
            ],
        )

    def test_user_warning_period_changes_the_groups(self):
        self.db.execute(
            "UPDATE users SET warning_days = 3 WHERE id = ?", (self.user_id,)
        )
        names = self.names(SORT_STATUS)
        self.assertLess(
            names.index("Мало"), names.index("Скоро")
        )  # «Скоро» теперь норма

    def test_helper_does_not_change_the_source_list(self):
        views = self.service.list_products(self.user_id, today=TODAY)
        before = [v.product.id for v in views]
        sort_by_status(views, problems_first=False)
        self.assertEqual([v.product.id for v in views], before)

    def test_empty_list(self):
        self.assertEqual(sort_by_status([]), [])

    def test_unknown_sort_is_still_rejected(self):
        with self.assertRaises(ValueError):
            self.names("status_up")


class SortDirectionsTest(ProductServiceTestCase):
    """Подвиды сортировки: каждое направление по смыслу."""

    def setUp(self) -> None:
        super().setUp()
        meds = self.category_id("Лекарства")
        chemistry = self.category_id("Бытовая химия")
        self.add(
            name="Борная кислота",
            quantity="5",
            expiry_date="01.03.2027",
            storage_place="",
        )
        self.add(
            name="аспирин",
            quantity="20",
            expiry_date="01.01.2027",
            storage_place="Шкаф",
        )
        self.add(
            name="Вата",
            quantity="1",
            expiry_date="",
            storage_place="Ящик",
            category_id=chemistry,
        )
        self.add(
            name="Гель",
            quantity="10",
            expiry_date="01.06.2028",
            storage_place="",
            category_id=meds,
        )

    def names(self, sort):
        views = self.service.list_products(self.user_id, sort=sort, today=TODAY)
        return [view.product.name for view in views]

    def test_name_both_ways_ignores_case(self):
        self.assertEqual(
            self.names("name"), ["аспирин", "Борная кислота", "Вата", "Гель"]
        )
        self.assertEqual(
            self.names("name_desc"), ["Гель", "Вата", "Борная кислота", "аспирин"]
        )

    def test_quantity_both_ways(self):
        self.assertEqual(
            self.names("quantity_desc"), ["аспирин", "Гель", "Борная кислота", "Вата"]
        )
        self.assertEqual(
            self.names("quantity"), ["Вата", "Борная кислота", "Гель", "аспирин"]
        )

    def test_expiry_both_ways_keeps_empty_dates_last(self):
        self.assertEqual(
            self.names("expiry"), ["аспирин", "Борная кислота", "Гель", "Вата"]
        )
        self.assertEqual(
            self.names("expiry_desc"), ["Гель", "Борная кислота", "аспирин", "Вата"]
        )

    def test_added_both_ways(self):
        self.db.execute("UPDATE products SET created_at = '2026-01-01 10:00:00'")
        self.db.execute(
            "UPDATE products SET created_at = '2026-09-09 10:00:00' WHERE name = 'Вата'"
        )
        self.assertEqual(self.names("added")[0], "Вата")
        self.assertEqual(self.names("added_asc")[-1], "Вата")

    def test_category_both_ways(self):
        asc = self.names("category")
        self.assertEqual(asc[0], "Вата")  # «Бытовая химия» раньше «Лекарства»
        self.assertEqual(self.names("category_desc")[-1], "Вата")

    def test_place_both_ways_keeps_empty_places_last(self):
        self.assertEqual(
            self.names("place"), ["аспирин", "Вата", "Борная кислота", "Гель"]
        )
        self.assertEqual(
            self.names("place_desc"), ["Вата", "аспирин", "Борная кислота", "Гель"]
        )

    def test_unknown_direction_is_rejected(self):
        with self.assertRaises(ValueError):
            self.names("name_up")


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
