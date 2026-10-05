"""Иконки макета (линейный набор Lucide), нарисованные кодом.

Каждая иконка описана набором простых фигур в квадрате 24 на 24. Из них
Pillow рисует изображение нужного размера и цвета, файлов с картинками нет.
"""

from functools import lru_cache
from typing import Dict, Iterator, List, Tuple, Union

from PIL import Image, ImageDraw
from svg.path import Move, parse_path

from pharmacy.ui.drawing import SCALE, rgba

GRID = 24  # размер квадрата, в котором описаны иконки
_CURVE_STEP = 0.25  # длина отрезка, на которые разбиваются кривые

Path = Tuple[str, str]
Circle = Tuple[str, float, float, float]
Rect = Tuple[str, float, float, float, float, float]
Primitive = Union[Path, Circle, Rect]


def _path(data: str) -> Path:
    return ("path", data)


def _filled(data: str) -> Path:
    return ("fill", data)


def _circle(cx: float, cy: float, r: float) -> Circle:
    return ("circle", cx, cy, r)


def _rect(x: float, y: float, w: float, h: float, rx: float = 0) -> Rect:
    return ("rect", x, y, w, h, rx)


ICONS: Dict[str, Tuple[Primitive, ...]] = {
    "search": (_circle(11, 11, 8), _path("m21 21-4.3-4.3")),
    "calendar": (
        _rect(3, 4, 18, 18, 2),
        _path("M16 2v4M8 2v4M3 10h18"),
    ),
    "cart": (
        _circle(8, 21, 1),
        _circle(19, 21, 1),
        _path(
            "M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57"
            "l1.65-7.43H5.12"
        ),
    ),
    "clock": (_circle(12, 12, 10), _path("M12 6v6l4 2")),
    "alert": (_circle(12, 12, 10), _path("M12 8v4M12 16h.01")),
    "x": (_path("M18 6 6 18M6 6l12 12"),),
    "trending-down": (
        _path("m22 17-8.5-8.5-5 5L2 7"),
        _path("M16 17h6v-6"),
    ),
    "pencil": (
        _path(
            "M21.17 6.81a1 1 0 0 0-3.98-3.98L3.84 16.17a2 2 0 0 0-.5.83l-1.32"
            " 4.35a.5.5 0 0 0 .62.62l4.35-1.32a2 2 0 0 0 .83-.5z"
        ),
    ),
    "plus": (_path("M5 12h14M12 5v14"),),
    "check": (_path("M20 6 9 17l-5-5"),),
    "logout": (
        _path("M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"),
        _path("m16 17 5-5-5-5M21 12H9"),
    ),
    "arrow-left": (_path("m12 19-7-7 7-7M19 12H5"),),
    "arrow-right": (_path("M5 12h14m-7-7 7 7-7 7"),),
    "arrow-down": (_path("M12 5v14m7-7-7 7-7-7"),),
    "chevron-left": (_path("m15 18-6-6 6-6"),),
    "chevron-right": (_path("m9 18 6-6-6-6"),),
    "chevron-down": (_path("m6 9 6 6 6-6"),),
    "moon": (_path("M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z"),),
    "sun": (
        _circle(12, 12, 4),
        _path(
            "M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41"
            "M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"
        ),
    ),
    "square": (_rect(5, 5, 14, 14, 1.5),),
    "minus": (_path("M5 12h14"),),
    "cross": (_filled("M9 2h6v7h7v6h-7v7H9v-7H2V9h7z"),),
    "eye": (
        _path(
            "M2.06 12.35a1 1 0 0 1 0-.7 10.75 10.75 0 0 1 19.88 0 1 1 0 0 1 0 .7"
            " 10.75 10.75 0 0 1-19.88 0"
        ),
        _circle(12, 12, 3),
    ),
    "eye-off": (
        _path(
            "M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696"
            " 10.747 10.747 0 0 1-1.444 2.49"
        ),
        _path("M14.084 14.158a3 3 0 0 1-4.242-4.242"),
        _path(
            "M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696"
            " 10.75 10.75 0 0 1 4.446-5.143"
        ),
        _path("m2 2 20 20"),
    ),
}

Point = Tuple[float, float]


def _subpaths(data: str) -> Iterator[List[Point]]:
    """Разбивает контур SVG на ломаные линии (кривые режутся на отрезки)."""
    current: List[Point] = []
    for segment in parse_path(data):
        if isinstance(segment, Move):
            if len(current) > 1:
                yield current
            current = [(segment.end.real, segment.end.imag)]
            continue
        if not current:
            current = [(segment.start.real, segment.start.imag)]
        steps = max(2, round(segment.length() / _CURVE_STEP))
        for index in range(1, steps + 1):
            point = segment.point(index / steps)
            current.append((point.real, point.imag))
    if len(current) > 1:
        yield current


def _stroke(
    draw: ImageDraw.ImageDraw,
    points: List[Point],
    color: Tuple[int, int, int, int],
    width: float,
) -> None:
    """Рисует линию с круглыми концами и углами."""
    flat = [(x, y) for x, y in points]
    draw.line(flat, fill=color, width=round(width), joint="curve")
    radius = width / 2
    for x, y in (flat[0], flat[-1]):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


@lru_cache(maxsize=256)
def render_icon(
    name: str, size: int, color: str, stroke_width: float = 2.0
) -> Image.Image:
    """Рисует иконку.

    Args:
        name: Название иконки из ``ICONS``.
        size: Сторона квадрата в пикселях.
        color: Цвет ``#RRGGBB``.
        stroke_width: Толщина линии в единицах сетки 24 на 24.

    Returns:
        Изображение RGBA размером size на size.

    Raises:
        KeyError: Если такой иконки нет.
    """
    primitives = ICONS[name]
    unit = size * SCALE / GRID
    paint = rgba(color)
    line = stroke_width * unit
    image = Image.new("RGBA", (size * SCALE, size * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for primitive in primitives:
        kind = primitive[0]
        if kind in ("path", "fill"):
            for points in _subpaths(primitive[1]):
                scaled = [(x * unit, y * unit) for x, y in points]
                if kind == "fill":
                    draw.polygon(scaled, fill=paint)
                else:
                    _stroke(draw, scaled, paint, line)
        elif kind == "circle":
            _, cx, cy, radius = primitive
            reach = (radius + stroke_width / 2) * unit
            draw.ellipse(
                (
                    cx * unit - reach,
                    cy * unit - reach,
                    cx * unit + reach,
                    cy * unit + reach,
                ),
                outline=paint,
                width=round(line),
            )
        else:
            _, x, y, width, height, corner = primitive
            half = stroke_width / 2
            draw.rounded_rectangle(
                (
                    (x - half) * unit,
                    (y - half) * unit,
                    (x + width + half) * unit,
                    (y + height + half) * unit,
                ),
                (corner + half) * unit,
                outline=paint,
                width=round(line),
            )
    return image.resize((size, size), Image.Resampling.LANCZOS)
