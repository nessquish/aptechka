"""Тесты работы с датами и форматирования значений."""

import unittest
from datetime import date

from pharmacy.utils.dates import days_until, format_user_date, parse_user_date
from pharmacy.utils.formatting import format_quantity, plural


class DatesTest(unittest.TestCase):
    """Даты: ввод ДД.ММ.ГГГГ и расчёт дней."""

    def test_parse_user_date(self):
        self.assertEqual(parse_user_date("20.10.2026"), date(2026, 10, 20))

    def test_parse_ignores_spaces(self):
        self.assertEqual(parse_user_date("  01.02.2027 "), date(2027, 2, 1))

    def test_parse_rejects_wrong_formats(self):
        for text in ("", "2026-10-20", "20/10/2026", "32.01.2026", "29.02.2027", "abc"):
            with self.assertRaises(ValueError, msg=text):
                parse_user_date(text)

    def test_format_user_date(self):
        self.assertEqual(format_user_date(date(2026, 3, 5)), "05.03.2026")

    def test_format_empty_date(self):
        self.assertEqual(format_user_date(None), "")

    def test_days_until(self):
        today = date(2026, 10, 1)
        self.assertEqual(days_until(date(2026, 10, 20), today), 19)
        self.assertEqual(days_until(today, today), 0)
        self.assertEqual(days_until(date(2026, 9, 30), today), -1)


class FormattingTest(unittest.TestCase):
    """Красивая запись количества."""

    def test_integer_without_fraction(self):
        self.assertEqual(format_quantity(2.0), "2")
        self.assertEqual(format_quantity(10), "10")
        self.assertEqual(format_quantity(0), "0")

    def test_fraction_without_trailing_zeros(self):
        self.assertEqual(format_quantity(1.5), "1.5")
        self.assertEqual(format_quantity(0.25), "0.25")

    def test_large_number(self):
        self.assertEqual(format_quantity(1234567.5), "1234567.5")


class PluralTest(unittest.TestCase):
    """Склонение слов после чисел."""

    def forms(self, number):
        return plural(number, "день", "дня", "дней")

    def test_one(self):
        for number in (1, 21, 101):
            self.assertEqual(self.forms(number), "день", number)

    def test_few(self):
        for number in (2, 3, 4, 22, 24, 102):
            self.assertEqual(self.forms(number), "дня", number)

    def test_many(self):
        for number in (0, 5, 9, 10, 20, 25, 30, 100):
            self.assertEqual(self.forms(number), "дней", number)

    def test_teens_are_always_many(self):
        for number in (11, 12, 13, 14, 111, 112):
            self.assertEqual(self.forms(number), "дней", number)

    def test_negative_number_uses_absolute_value(self):
        self.assertEqual(self.forms(-1), "день")


if __name__ == "__main__":
    unittest.main()
