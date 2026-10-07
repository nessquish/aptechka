"""Шрифт Inter из макета: подключение файлов и выбор начертания.

Файлы шрифта лежат в ``assets/fonts``. Они подключаются только на время работы
программы и не устанавливаются в систему. Если подключить шрифт не удалось,
используется запасной.
"""

from functools import lru_cache
from pathlib import Path
from typing import Dict

from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics

from pharmacy.ui import theme
from pharmacy.ui.theme import TYPOGRAPHY

FONTS_DIR = Path(__file__).resolve().parent / "assets" / "fonts"

FONT_FILES = (
    "Inter-Regular.ttf",
    "Inter-Medium.ttf",
    "Inter-SemiBold.ttf",
    "Inter-Bold.ttf",
    "Inter-ExtraBold.ttf",
)

INTER = "Inter"
# Насыщенность из макета -> толщина Qt. Qt собирает все файлы Inter в одно
# семейство и выбирает нужный по толщине.
_WEIGHTS: Dict[int, QFont.Weight] = {
    400: QFont.Weight.Normal,
    500: QFont.Weight.Medium,
    600: QFont.Weight.DemiBold,
    700: QFont.Weight.Bold,
    800: QFont.Weight.ExtraBold,
}
_FALLBACK_FAMILY = "Segoe UI"


def register_fonts() -> bool:
    """Подключает файлы шрифта Inter к программе.

    Returns:
        True, если все шрифты подключены. Если файлов нет, возвращает False
        (будет использован запасной шрифт).
    """
    files = [FONTS_DIR / name for name in FONT_FILES]
    if not all(path.is_file() for path in files):
        return False
    results = [QFontDatabase.addApplicationFont(str(path)) for path in files]
    _font.cache_clear()
    return all(result >= 0 for result in results)


@lru_cache(maxsize=None)
def _installed(family: str) -> bool:
    return family in QFontDatabase.families()


@lru_cache(maxsize=256)
def _font(style: str, size_name: str) -> QFont:
    size, weight = TYPOGRAPHY[style]
    family, qt_weight = INTER, _WEIGHTS[weight]
    if not _installed(family):
        family = _FALLBACK_FAMILY
        qt_weight = QFont.Weight.Bold if weight >= 600 else QFont.Weight.Normal
    font = QFont(family)
    font.setPixelSize(theme.scaled(size))
    font.setWeight(qt_weight)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return font


def font(style: str) -> QFont:
    """Возвращает шрифт стиля из ``theme.TYPOGRAPHY`` с учётом размера текста."""
    return QFont(_font(style, theme.text_size_name()))


def text_width(text: str, style: str) -> int:
    """Возвращает ширину текста в пикселях в заданном стиле."""
    return QFontMetrics(font(style)).horizontalAdvance(text)


def line_height(style: str) -> int:
    """Возвращает высоту строки текста в пикселях в заданном стиле."""
    return QFontMetrics(font(style)).height()
