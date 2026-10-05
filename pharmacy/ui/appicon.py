"""Значок приложения: белый крест на скруглённом фиолетовом квадрате, рисуется кодом."""

from PIL import Image

from pharmacy.ui.drawing import rounded_box
from pharmacy.ui.icons import render_icon
from pharmacy.ui.theme import LIGHT

# Размеры, из которых собирается файл .ico и значок окна.
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
_RADIUS_SHARE = 0.22  # радиус скругления относительно стороны
_CROSS_SHARE = 0.56  # размер креста относительно стороны


def render_app_icon(size: int = 256) -> Image.Image:
    """Рисует значок приложения.

    Args:
        size: Сторона квадрата в пикселях.

    Returns:
        Изображение RGBA с прозрачными углами.
    """
    base = rounded_box(size, size, round(size * _RADIUS_SHARE), LIGHT.primary)
    cross = render_icon("cross", round(size * _CROSS_SHARE), "#FFFFFF")
    offset = (size - cross.width) // 2
    image = base.copy()
    image.alpha_composite(cross, (offset, offset))
    return image
