"""Тесты рисования: скруглённые рамки, тени, градиент и иконки."""

import unittest

from pharmacy.ui.drawing import Shadow, gradient_box, rounded_box
from pharmacy.ui.icons import ICONS, render_icon
from pharmacy.ui.theme import hex_to_rgb


def rgba_at(image, x, y):
    return image.getpixel((x, y))


class RoundedBoxTest(unittest.TestCase):
    def test_size_includes_padding(self):
        image = rounded_box(100, 40, 8, "#FFFFFF", pad=5)
        self.assertEqual(image.size, (110, 50))

    def test_center_has_fill_color(self):
        image = rounded_box(60, 30, 8, "#5F57E8")
        self.assertEqual(rgba_at(image, 30, 15), (95, 87, 232, 255))

    def test_corner_is_transparent(self):
        image = rounded_box(60, 30, 12, "#5F57E8")
        self.assertEqual(rgba_at(image, 0, 0)[3], 0)

    def test_border_color_on_the_edge(self):
        image = rounded_box(60, 30, 8, "#FFFFFF", border="#FF0000")
        red, green, blue, alpha = rgba_at(image, 30, 0)
        self.assertGreater(red, 200)
        self.assertLess(green, 80)
        self.assertEqual(alpha, 255)

    def test_without_fill_the_inside_is_transparent(self):
        image = rounded_box(60, 30, 8, None, border="#FF0000")
        self.assertEqual(rgba_at(image, 30, 15)[3], 0)

    def test_shadow_is_drawn_below_the_shape(self):
        shadow = Shadow(dy=3, blur=8, color="#000000", opacity=0.5)
        image = rounded_box(60, 30, 8, "#FFFFFF", shadows=(shadow,), pad=10)
        below = rgba_at(image, 40, 10 + 30 + 2)
        self.assertGreater(below[3], 0)
        self.assertEqual(rgba_at(image, 40, 0)[3] < below[3], True)

    def test_ring_surrounds_the_shape(self):
        image = rounded_box(
            60, 30, 8, "#FFFFFF", border="#FF0000", pad=3, ring="#FBE3E8", ring_width=3
        )
        for got, want in zip(rgba_at(image, 30, 1)[:3], hex_to_rgb("#FBE3E8")):
            self.assertAlmostEqual(got, want, delta=10)

    def test_results_are_cached(self):
        first = rounded_box(50, 20, 6, "#FFFFFF")
        second = rounded_box(50, 20, 6, "#FFFFFF")
        self.assertIs(first, second)


class GradientTest(unittest.TestCase):
    def test_ends_follow_the_given_colors(self):
        image = gradient_box(40, 40, "#000000", "#FFFFFF", angle=180)
        top = image.getpixel((20, 0))
        bottom = image.getpixel((20, 39))
        self.assertLess(top[0], 40)
        self.assertGreater(bottom[0], 215)
        self.assertLess(top[0], bottom[0])

    def test_size(self):
        self.assertEqual(gradient_box(30, 20, "#000000", "#FFFFFF").size, (30, 20))


class IconTest(unittest.TestCase):
    def test_every_icon_draws_something(self):
        for name in ICONS:
            image = render_icon(name, 24, "#5F57E8")
            self.assertEqual(image.size, (24, 24), name)
            self.assertIsNotNone(image.getbbox(), name)

    def test_icon_uses_requested_color(self):
        image = render_icon("minus", 24, "#FF0000")
        pixel = image.getpixel((12, 12))
        self.assertEqual(pixel[:3], (255, 0, 0))
        self.assertEqual(pixel[3], 255)

    def test_filled_cross_covers_its_center(self):
        self.assertEqual(render_icon("cross", 24, "#000000").getpixel((12, 12))[3], 255)

    def test_icons_stay_inside_their_square(self):
        for name in ICONS:
            bbox = render_icon(name, 32, "#000000").getbbox()
            self.assertGreaterEqual(bbox[0], 0, name)
            self.assertLessEqual(bbox[2], 32, name)

    def test_unknown_icon(self):
        with self.assertRaises(KeyError):
            render_icon("nope", 24, "#000000")


if __name__ == "__main__":
    unittest.main()
