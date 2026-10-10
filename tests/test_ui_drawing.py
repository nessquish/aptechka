"""Тесты рисования: тени, скруглённые фигуры, иконки и значок программы."""

import unittest

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter

from pharmacy.ui import paint, runtime
from pharmacy.ui.icons import ICONS, icon_pixmap, icon_svg
from pharmacy.ui.paint import Shadow, draw_shadows, fill_rounded, qcolor
from tests.qt_helpers import WidgetTestCase


def canvas(width: int = 100, height: int = 60) -> tuple:
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.white)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    return image, painter


class RoundedFillTest(unittest.TestCase):
    def test_center_has_the_fill_color(self):
        image, painter = canvas()
        fill_rounded(painter, QRectF(10, 10, 60, 30), 8, "#5F57E8")
        painter.end()
        self.assertEqual(image.pixelColor(40, 25).name().upper(), "#5F57E8")

    def test_corner_stays_outside_the_shape(self):
        image, painter = canvas()
        fill_rounded(painter, QRectF(10, 10, 60, 30), 12, "#5F57E8")
        painter.end()
        self.assertEqual(image.pixelColor(10, 10).name().upper(), "#FFFFFF")

    def test_border_color_on_the_edge(self):
        image, painter = canvas()
        fill_rounded(painter, QRectF(10, 10, 60, 30), 8, "#FFFFFF", "#FF0000")
        painter.end()
        color = image.pixelColor(40, 10)
        self.assertGreater(color.red(), 200)
        self.assertLess(color.green(), 120)

    def test_without_fill_only_the_border_is_drawn(self):
        image, painter = canvas()
        fill_rounded(painter, QRectF(10, 10, 60, 30), 8, None, "#FF0000")
        painter.end()
        self.assertEqual(image.pixelColor(40, 25).name().upper(), "#FFFFFF")


class ShadowTest(unittest.TestCase):
    def test_shadow_is_drawn_below_the_shape(self):
        image, painter = canvas(100, 80)
        box = QRectF(20, 10, 60, 30)
        draw_shadows(painter, box, 8, (Shadow(4, 12, "#000000", 0.5),))
        painter.end()
        below = image.pixelColor(50, 45)
        above = image.pixelColor(50, 2)
        self.assertLess(below.red(), 255)
        self.assertLess(below.red(), above.red())

    def test_shadow_fades_away_from_the_shape(self):
        image, painter = canvas(100, 100)
        draw_shadows(
            painter, QRectF(20, 10, 60, 30), 8, (Shadow(4, 12, "#000000", 0.5),)
        )
        painter.end()
        near = image.pixelColor(50, 44).red()
        far = image.pixelColor(50, 70).red()
        self.assertLess(near, far)
        self.assertEqual(image.pixelColor(50, 95).red(), 255)

    def test_stronger_opacity_gives_a_darker_shadow(self):
        light_image, painter = canvas()
        draw_shadows(
            painter, QRectF(20, 10, 60, 30), 8, (Shadow(3, 8, "#000000", 0.1),)
        )
        painter.end()
        dark_image, painter = canvas()
        draw_shadows(
            painter, QRectF(20, 10, 60, 30), 8, (Shadow(3, 8, "#000000", 0.6),)
        )
        painter.end()
        self.assertLess(
            dark_image.pixelColor(50, 20).red(), light_image.pixelColor(50, 20).red()
        )


class ColorTest(unittest.TestCase):
    def test_qcolor_has_opacity(self):
        self.assertAlmostEqual(qcolor("#FF0000", 0.5).alphaF(), 0.5, places=2)

    def test_quantiles_are_sorted_outwards_in(self):
        values = list(paint._QUANTILES)
        self.assertEqual(values, sorted(values, reverse=True))


class IconTest(WidgetTestCase):
    def test_every_icon_draws_something(self):
        for name in ICONS:
            pixmap = icon_pixmap(name, 24, "#5F57E8")
            self.assertFalse(pixmap.isNull(), name)
            image = pixmap.toImage()
            painted = any(
                image.pixelColor(x, y).alpha() > 0
                for x in range(image.width())
                for y in range(image.height())
            )
            self.assertTrue(painted, name)

    def test_icon_size_follows_the_request(self):
        pixmap = icon_pixmap("check", 18, "#000000")
        self.assertEqual(round(pixmap.width() / pixmap.devicePixelRatio()), 18)

    def test_icon_uses_requested_color(self):
        image = icon_pixmap("minus", 24, "#FF0000").toImage()
        ratio = icon_pixmap("minus", 24, "#FF0000").devicePixelRatio()
        pixel = image.pixelColor(round(12 * ratio), round(12 * ratio))
        self.assertEqual((pixel.red(), pixel.green(), pixel.blue()), (255, 0, 0))
        self.assertEqual(pixel.alpha(), 255)

    def test_filled_cross_covers_its_center(self):
        pixmap = icon_pixmap("cross", 24, "#000000")
        center = round(12 * pixmap.devicePixelRatio())
        self.assertEqual(pixmap.toImage().pixelColor(center, center).alpha(), 255)

    def test_icons_are_cached(self):
        self.assertIs(
            icon_pixmap("check", 14, "#000000"), icon_pixmap("check", 14, "#000000")
        )

    def test_svg_contains_color_and_width(self):
        svg = icon_svg("plus", "#123456", 3.0)
        self.assertIn("#123456", svg)
        self.assertIn('stroke-width="3.0"', svg)
        self.assertIn('viewBox="0 0 24 24"', svg)

    def test_unknown_icon(self):
        with self.assertRaises(KeyError):
            icon_pixmap("nope", 24, "#000000")


class AppIconTest(WidgetTestCase):
    def test_icon_has_requested_size_and_rounded_corners(self):
        pixmap = runtime.render_app_icon(128)
        image = pixmap.toImage()
        self.assertEqual(image.width(), 128)
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)  # угол прозрачный
        self.assertEqual(image.pixelColor(64, 10).alpha(), 255)  # середина закрашена

    def test_cross_is_white_in_the_middle(self):
        image = runtime.render_app_icon(128).toImage()
        color = image.pixelColor(64, 64)
        self.assertEqual((color.red(), color.green(), color.blue()), (255, 255, 255))

    def test_ico_sizes_include_the_windows_standard_ones(self):
        for size in (16, 32, 48, 256):
            self.assertIn(size, runtime.ICON_SIZES)

    def test_every_size_renders(self):
        for size in runtime.ICON_SIZES:
            self.assertEqual(runtime.render_app_icon(size).width(), size)

    def test_window_icon_has_every_size(self):
        icon = runtime.app_icon()
        self.assertFalse(icon.isNull())
        self.assertGreaterEqual(len(icon.availableSizes()), len(runtime.ICON_SIZES) - 1)


class RuntimeTest(unittest.TestCase):
    def test_application_is_created_once(self):
        self.assertIs(runtime.application(), runtime.application())

    def test_screen_size_is_positive(self):
        width, height = runtime.screen_size()
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)


if __name__ == "__main__":
    unittest.main()
