"""Шрифт Inter из макета: подключение файлов и выбор начертания.

Файлы шрифта лежат в ``assets/fonts``. На Windows они подключаются только
на время работы программы и не устанавливаются в систему. Если подключить
шрифт не удалось (другая система или нет файлов), используется запасной.
"""

import ctypes
import sys
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from typing import Dict, Tuple

from pharmacy.ui.theme import TYPOGRAPHY, scaled

FONTS_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
_FR_PRIVATE = 0x10  # шрифт виден только этому процессу

FONT_FILES = (
    "Inter-Regular.ttf",
    "Inter-Medium.ttf",
    "Inter-SemiBold.ttf",
    "Inter-Bold.ttf",
    "Inter-ExtraBold.ttf",
)

# Насыщенность -> (имя семейства, толщина в терминах Tk). У промежуточных
# начертаний Inter в Windows своё имя семейства.
_INTER_FAMILIES: Dict[int, Tuple[str, str]] = {
    400: ("Inter", "normal"),
    500: ("Inter Medium", "normal"),
    600: ("Inter SemiBold", "normal"),
    700: ("Inter", "bold"),
    800: ("Inter ExtraBold", "normal"),
}
_FALLBACK_FAMILY = "Segoe UI"


def register_fonts() -> bool:
    """Подключает файлы шрифта Inter к процессу.

    Returns:
        True, если шрифты подключены. На системах кроме Windows и при
        отсутствии файлов возвращает False (будет использован запасной шрифт).
    """
    if sys.platform != "win32":
        return False
    files = [FONTS_DIR / name for name in FONT_FILES]
    if not all(path.is_file() for path in files):
        return False
    add_font = ctypes.windll.gdi32.AddFontResourceExW
    return all(add_font(str(path), _FR_PRIVATE, 0) for path in files)


def font_spec(style: str, root: tk.Misc = None) -> Tuple[str, int, str]:
    """Возвращает описание шрифта для виджета Tk.

    Args:
        style: Название стиля из ``theme.TYPOGRAPHY``.
        root: Любой виджет (нужен, чтобы проверить, есть ли шрифт Inter).

    Returns:
        Тройка (семейство, размер, толщина). Размер отрицательный: так Tk
        понимает пиксели, а не пункты, и текст совпадает с макетом.
    """
    size, weight = TYPOGRAPHY[style]
    size = scaled(size)
    family, tk_weight = _INTER_FAMILIES[weight]
    if root is not None and family not in tkfont.families(root):
        family = _FALLBACK_FAMILY
        tk_weight = "bold" if weight >= 600 else "normal"
    return family, -size, tk_weight


def text_width(widget: tk.Misc, text: str, style: str) -> int:
    """Возвращает ширину текста в пикселях в заданном стиле."""
    return tkfont.Font(widget, font=font_spec(style, widget)).measure(text)


def line_height(widget: tk.Misc, style: str) -> int:
    """Возвращает высоту строки текста в пикселях в заданном стиле."""
    return tkfont.Font(widget, font=font_spec(style, widget)).metrics("linespace")
