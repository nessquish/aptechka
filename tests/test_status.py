"""Тесты расчёта состояния товара."""

import unittest
from datetime import date, timedelta

from pharmacy.services.status import (
    ProductStatus,
    get_statuses,
    primary_status,
)

TODAY = date(2026, 10, 1)


def statuses(expiry=None, quantity=5, minimum=1, warning_days=30):
    """Состояния товара на фиксированную дату TODAY."""
    return get_statuses(expiry, quantity, minimum, warning_days, TODAY)


class ExpiryStatusTest(unittest.TestCase):
    """Срок годности."""

    def test_past_date_is_expired(self):
        self.assertEqual(statuses(TODAY - timedelta(days=1)), [ProductStatus.EXPIRED])

    def test_today_is_expiring_not_expired(self):
        self.assertEqual(statuses(TODAY), [ProductStatus.EXPIRING])

    def test_exactly_warning_days_is_expiring(self):
        self.assertEqual(statuses(TODAY + timedelta(days=30)), [ProductStatus.EXPIRING])

    def test_one_day_beyond_warning_is_ok(self):
        self.assertEqual(statuses(TODAY + timedelta(days=31)), [ProductStatus.OK])

    def test_no_expiry_date_is_ok(self):
        self.assertEqual(statuses(None), [ProductStatus.OK])

    def test_warning_days_setting_is_respected(self):
        expiry = TODAY + timedelta(days=10)
        self.assertEqual(statuses(expiry, warning_days=7), [ProductStatus.OK])
        self.assertEqual(statuses(expiry, warning_days=14), [ProductStatus.EXPIRING])


class StockStatusTest(unittest.TestCase):
    """Остаток."""

    def test_below_minimum_is_low(self):
        self.assertEqual(statuses(quantity=1, minimum=2), [ProductStatus.LOW_STOCK])

    def test_equal_to_minimum_is_low(self):
        self.assertEqual(statuses(quantity=1, minimum=1), [ProductStatus.LOW_STOCK])

    def test_above_minimum_is_ok(self):
        self.assertEqual(statuses(quantity=3, minimum=2), [ProductStatus.OK])

    def test_zero_quantity_is_low_even_without_minimum(self):
        self.assertEqual(statuses(quantity=0, minimum=0), [ProductStatus.LOW_STOCK])

    def test_no_minimum_and_stock_present_is_ok(self):
        self.assertEqual(statuses(quantity=5, minimum=0), [ProductStatus.OK])


class CombinedStatusTest(unittest.TestCase):
    """Несколько проблем сразу."""

    def test_expiring_and_low_stock_both_reported(self):
        result = statuses(TODAY + timedelta(days=5), quantity=1, minimum=2)
        self.assertEqual(result, [ProductStatus.EXPIRING, ProductStatus.LOW_STOCK])

    def test_primary_status_prefers_expired(self):
        result = statuses(TODAY - timedelta(days=5), quantity=0, minimum=1)
        self.assertEqual(primary_status(result), ProductStatus.EXPIRED)

    def test_primary_status_expiring_before_low_stock(self):
        result = [ProductStatus.LOW_STOCK, ProductStatus.EXPIRING]
        self.assertEqual(primary_status(result), ProductStatus.EXPIRING)

    def test_primary_status_of_ok(self):
        self.assertEqual(primary_status([ProductStatus.OK]), ProductStatus.OK)


class LabelTest(unittest.TestCase):
    """Подписи состояний для интерфейса."""

    def test_labels_are_russian(self):
        self.assertEqual(ProductStatus.EXPIRED.label, "Просрочен")
        self.assertEqual(ProductStatus.EXPIRING.label, "Скоро истекает")
        self.assertEqual(ProductStatus.LOW_STOCK.label, "Низкий остаток")
        self.assertEqual(ProductStatus.OK.label, "Норма")


if __name__ == "__main__":
    unittest.main()
