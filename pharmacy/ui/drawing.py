"""Рисование фигур для виджетов: скруглённые рамки, тени, градиент.

Фигуры рисуются в увеличенном размере и затем уменьшаются, поэтому края
гладкие, а не «лесенкой», как у стандартных фигур Tkinter. Результат это
обычное изображение Pillow, которое виджеты кладут на Canvas.
"""

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter

from pharmacy.ui.theme import hex_to_rgb

SCALE = 4  # во сколько раз рисуем крупнее, чем нужно
_GRADIENT_STEP = 8  # во сколько раз градиент считается мельче, чем показывается


@dataclass(frozen=True)
class Shadow:
    """Тень под фигурой (аналог ``box-shadow`` из макета).

    Attributes:
        dx: Смещение по горизонтали.
        dy: Смещение по вертикали.
        blur: Размытие.
        color: Цвет ``#RRGGBB``.
        opacity: Непрозрачность от 0 до 1.
    """

    dy: int
    blur: int
    color: str
    opacity: float
    dx: int = 0


def rgba(color: str, opacity: float = 1.0) -> Tuple[int, int, int, int]:
    """Переводит ``#RRGGBB`` и непрозрачность в цвет RGBA для Pillow."""
    red, green, blue = hex_to_rgb(color)
    return red, green, blue, round(255 * opacity)


def _shadow_layer(
    size: Tuple[int, int],
    box: Tuple[int, int, int, int],
    radius: int,
    shadow: Shadow,
) -> Image.Image:
    """Рисует одну размытую тень."""
    mask = Image.new("L", size, 0)
    left, top, right, bottom = box
    ImageDraw.Draw(mask).rounded_rectangle(
        (
            left + shadow.dx * SCALE,
            top + shadow.dy * SCALE,
            right + shadow.dx * SCALE,
            bottom + shadow.dy * SCALE,
        ),
        radius,
        fill=255,
    )
    # В CSS размытие 8px даёт сглаживание примерно на половину этой величины.
    mask = mask.filter(ImageFilter.GaussianBlur(shadow.blur * SCALE / 2))
    layer = Image.new("RGBA", size, rgba(shadow.color, shadow.opacity))
    layer.putalpha(mask.point(lambda value: round(value * shadow.opacity)))
    return layer


@lru_cache(maxsize=512)
def rounded_box(
    width: int,
    height: int,
    radius: int,
    fill: Optional[str],
    border: Optional[str] = None,
    border_width: int = 1,
    shadows: Tuple[Shadow, ...] = (),
    pad: int = 0,
    ring: Optional[str] = None,
    ring_width: int = 3,
) -> Image.Image:
    """Рисует скруглённый прямоугольник с границей, кольцом и тенями.

    Размер изображения больше размера фигуры на ``pad`` с каждой стороны:
    в этих полях помещаются тени и кольцо.

    Args:
        width: Ширина фигуры.
        height: Высота фигуры.
        radius: Радиус скругления углов.
        fill: Цвет заливки или None (без заливки).
        border: Цвет границы или None.
        border_width: Толщина границы.
        shadows: Тени под фигурой.
        pad: Поле вокруг фигуры.
        ring: Цвет кольца вокруг фигуры (как у поля с ошибкой) или None.
        ring_width: Толщина кольца.

    Returns:
        Изображение RGBA размером (width + 2 * pad, height + 2 * pad).
    """
    size = ((width + 2 * pad) * SCALE, (height + 2 * pad) * SCALE)
    box = (
        pad * SCALE,
        pad * SCALE,
        (pad + width) * SCALE - 1,
        (pad + height) * SCALE - 1,
    )
    scaled_radius = radius * SCALE
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    for shadow in shadows:
        image.alpha_composite(_shadow_layer(size, box, scaled_radius, shadow))
    draw = ImageDraw.Draw(image)
    if ring is not None:
        spread = ring_width * SCALE
        draw.rounded_rectangle(
            (box[0] - spread, box[1] - spread, box[2] + spread, box[3] + spread),
            scaled_radius + spread,
            fill=rgba(ring),
        )
    if border is not None:
        draw.rounded_rectangle(box, scaled_radius, fill=rgba(border))
        inset = border_width * SCALE
        inner = (box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset)
        # Без заливки внутренняя часть очищается: остаётся только граница.
        inner_fill = rgba(fill) if fill is not None else (0, 0, 0, 0)
        draw.rounded_rectangle(inner, max(scaled_radius - inset, 0), fill=inner_fill)
    elif fill is not None:
        draw.rounded_rectangle(box, scaled_radius, fill=rgba(fill))
    return image.resize((width + 2 * pad, height + 2 * pad), Image.Resampling.LANCZOS)


@lru_cache(maxsize=64)
def gradient_box(
    width: int, height: int, start: str, end: str, angle: float = 160.0
) -> Image.Image:
    """Рисует прямоугольник с линейным градиентом (как у левой части входа).

    Args:
        width: Ширина.
        height: Высота.
        start: Цвет в начале градиента.
        end: Цвет в конце.
        angle: Направление в градусах по правилам CSS (180 это сверху вниз).
    """
    radians = math.radians(angle)
    dx, dy = math.sin(radians), -math.cos(radians)
    length = abs(width * dx) + abs(height * dy)
    first, last = hex_to_rgb(start), hex_to_rgb(end)
    # Градиент плавный, поэтому считаем его в уменьшенном виде и растягиваем.
    small_w = max(width // _GRADIENT_STEP, 2)
    small_h = max(height // _GRADIENT_STEP, 2)
    image = Image.new("RGB", (small_w, small_h))
    pixels = image.load()
    for y in range(small_h):
        for x in range(small_w):
            px = (x + 0.5) * width / small_w
            py = (y + 0.5) * height / small_h
            along = ((px - width / 2) * dx + (py - height / 2) * dy) / length + 0.5
            along = min(max(along, 0.0), 1.0)
            pixels[x, y] = tuple(
                round(a + (b - a) * along) for a, b in zip(first, last)
            )
    return image.resize((width, height), Image.Resampling.BILINEAR)
