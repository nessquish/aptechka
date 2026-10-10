"""Тесты единиц измерения: общий список, значение по умолчанию, разные написания."""

import unittest

from pharmacy.errors import ValidationError
from pharmacy.services.shopping_service import ShoppingService
from pharmacy.utils.units import DEFAULT_UNIT, UNITS, normalize_unit
from tests.helpers import DatabaseTestCase


class UnitListTest(unittest.TestCase):
    def test_default_unit_is_pieces_and_comes_first(self):
        self.assertEqual(DEFAULT_UNIT, "шт.")
        self.assertEqual(UNITS[0], DEFAULT_UNIT)

    def test_list_has_the_units_from_the_spec(self):
        for unit in ("шт.", "упак.", "табл.", "мг", "г", "мл"):
            self.assertIn(unit, UNITS)

    def test_units_are_unique(self):
        self.assertEqual(len(UNITS), len(set(UNITS)))


class NormalizeTest(unittest.TestCase):
    def test_listed_units_stay_as_they_are(self):
        for unit in UNITS:
            self.assertEqual(normalize_unit(unit), unit)

    def test_empty_unit_becomes_pieces(self):
        for empty in ("", " ", "\t"):
            self.assertEqual(normalize_unit(empty), "шт.")

    def test_case_and_spaces_do_not_matter(self):
        self.assertEqual(normalize_unit("  МЛ "), "мл")
        self.assertEqual(normalize_unit("Шт."), "шт.")

    def test_spelling_variants_are_united(self):
        for written in ("таб", "таб.", "табл", "Таблетки", "таблетка", "ТАБЛЕТОК"):
            self.assertEqual(normalize_unit(written), "табл.", written)
        for written in ("уп", "уп.", "упак", "упаковка"):
            self.assertEqual(normalize_unit(written), "упак.", written)
        for written in ("гр", "гр.", "грамм", "г."):
            self.assertEqual(normalize_unit(written), "г", written)

    def test_unknown_unit_is_rejected_with_the_field_name(self):
        with self.assertRaises(ValidationError) as ctx:
            normalize_unit("кубометр")
        self.assertEqual(ctx.exception.field, "unit")
        self.assertEqual(ctx.exception.message, "Выберите единицу измерения из списка")

    def test_custom_field_name(self):
        with self.assertRaises(ValidationError) as ctx:
            normalize_unit("???", field="u")
        self.assertEqual(ctx.exception.field, "u")


class ShoppingUnitTest(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.shopping = ShoppingService(self.db)
        self.user_id = self.add_user("anna")

    def test_manual_item_without_unit_gets_pieces(self):
        item = self.shopping.add_manual(self.user_id, "Вата", "2", "")
        self.assertEqual(item.unit, "шт.")

    def test_manual_item_spelling_is_united(self):
        item = self.shopping.add_manual(self.user_id, "Анальгин", "10", "таб")
        self.assertEqual(item.unit, "табл.")

    def test_manual_item_with_unknown_unit_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            self.shopping.add_manual(self.user_id, "Вата", "2", "тонн")
        self.assertEqual(ctx.exception.field, "unit")

    def test_history_of_shopping_shows_the_unit(self):
        from pharmacy.repositories.history_repository import HistoryRepository

        self.shopping.add_manual(self.user_id, "Парацетамол", "10", "мг")
        latest = HistoryRepository(self.db).list_for_user(self.user_id)[0]
        self.assertIn("10 мг", latest.description)


if __name__ == "__main__":
    unittest.main()
