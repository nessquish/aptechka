"""Тесты подписей: приветствие, категории, тона состояний."""

import unittest

from pharmacy.services.status import ProductStatus
from pharmacy.ui import labels
from pharmacy.ui.widgets.badge import TONES


class GreetingTest(unittest.TestCase):
    def test_parts_of_the_day(self):
        cases = {
            0: "Доброй ночи",
            4: "Доброй ночи",
            5: "Доброе утро",
            11: "Доброе утро",
            12: "Добрый день",
            17: "Добрый день",
            18: "Добрый вечер",
            22: "Добрый вечер",
            23: "Доброй ночи",
        }
        for hour, phrase in cases.items():
            self.assertEqual(labels.greeting(hour), phrase, hour)

    def test_every_hour_has_a_greeting(self):
        for hour in range(24):
            self.assertTrue(labels.greeting(hour))


class CategoryTest(unittest.TestCase):
    def test_long_names_are_shortened_like_in_the_design(self):
        self.assertEqual(labels.short_category("Медицинские товары"), "Мед. товары")
        self.assertEqual(labels.short_category("Средства гигиены"), "Гигиена")

    def test_other_names_stay(self):
        self.assertEqual(labels.short_category("Лекарства"), "Лекарства")
        self.assertEqual(labels.short_category("Бытовая химия"), "Бытовая химия")


class StatusLabelsTest(unittest.TestCase):
    def test_every_status_has_tone_and_icon(self):
        for status in ProductStatus:
            self.assertIn(labels.STATUS_TONES[status], TONES)
            self.assertTrue(labels.STATUS_ICONS[status])


if __name__ == "__main__":
    unittest.main()
