"""Тесты оформления: палитры, смешивание цветов, стили текста."""

import dataclasses
import re
import unittest

from pharmacy.ui import theme
from pharmacy.ui.theme import DARK, LIGHT, TYPOGRAPHY, Palette, hex_to_rgb, mix

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class PaletteTest(unittest.TestCase):
    """Обе палитры полные и состоят из настоящих цветов."""

    def test_every_color_is_a_hex_value(self):
        for name, palette in (("light", LIGHT), ("dark", DARK)):
            for field in dataclasses.fields(Palette):
                value = getattr(palette, field.name)
                self.assertRegex(value, HEX, f"{name}.{field.name}")

    def test_light_palette_matches_design(self):
        self.assertEqual(LIGHT.primary, "#5F57E8")
        self.assertEqual(LIGHT.bg, "#F6F7FC")
        self.assertEqual(LIGHT.red, "#D3415E")

    def test_dark_theme_differs_from_light(self):
        self.assertNotEqual(DARK.bg, LIGHT.bg)
        self.assertNotEqual(DARK.ink, LIGHT.ink)


class ThemeSwitchTest(unittest.TestCase):
    def tearDown(self):
        theme.set_theme(theme.LIGHT_THEME)

    def test_default_is_light(self):
        self.assertEqual(theme.theme_name(), "light")
        self.assertIs(theme.palette(), LIGHT)

    def test_switch_to_dark_and_back(self):
        theme.set_theme("dark")
        self.assertIs(theme.palette(), DARK)
        theme.set_theme("light")
        self.assertIs(theme.palette(), LIGHT)

    def test_unknown_theme_is_rejected(self):
        with self.assertRaises(ValueError):
            theme.set_theme("pink")
        self.assertEqual(theme.theme_name(), "light")


class ColorMathTest(unittest.TestCase):
    def test_hex_to_rgb(self):
        self.assertEqual(hex_to_rgb("#5F57E8"), (95, 87, 232))
        self.assertEqual(hex_to_rgb("000000"), (0, 0, 0))

    def test_mix_ends_and_middle(self):
        self.assertEqual(mix("#000000", "#FFFFFF", 0), "#000000")
        self.assertEqual(mix("#000000", "#FFFFFF", 1), "#FFFFFF")
        self.assertEqual(mix("#000000", "#FFFFFF", 0.5), "#808080")


class TypographyTest(unittest.TestCase):
    def test_sizes_and_weights_are_available_in_inter(self):
        allowed = {400, 500, 600, 700, 800}
        for style, (size, weight) in TYPOGRAPHY.items():
            self.assertGreater(size, 0, style)
            self.assertIn(weight, allowed, style)


if __name__ == "__main__":
    unittest.main()
