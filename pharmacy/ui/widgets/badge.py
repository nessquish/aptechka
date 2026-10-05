"""Плашка состояния («Просрочен», «Норма», «Куплено» и другие)."""

import tkinter as tk
from typing import Optional, Tuple

from pharmacy.ui import theme
from pharmacy.ui.drawing import rounded_box
from pharmacy.ui.fonts import font_spec, line_height, text_width
from pharmacy.ui.icons import render_icon
from pharmacy.ui.theme import palette
from pharmacy.ui.widgets.common import parent_bg, photo

TONES = ("red", "amber", "green", "gray", "primary")
PADDING_X = 9
PADDING_Y = 3
ICON_SIZE = 11
ICON_GAP = 4


def tone_colors(tone: str) -> Tuple[str, str]:
    """Возвращает (фон, текст) для цветового тона плашки и значка."""
    pal = palette()
    return {
        "red": (pal.red_bg, pal.red),
        "amber": (pal.amber_bg, pal.amber),
        "green": (pal.green_bg, pal.green),
        "gray": (pal.gray_bg, pal.ink_2),
        "primary": (pal.primary_soft, pal.primary),
    }[tone]


class Badge(tk.Canvas):
    """Небольшая цветная плашка с текстом и необязательной иконкой."""

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        tone: str = "gray",
        icon: Optional[str] = None,
    ) -> None:
        """Создаёт плашку.

        Args:
            master: Родительский виджет.
            text: Текст.
            tone: ``red``, ``amber``, ``green``, ``gray`` или ``primary``.
            icon: Название иконки слева от текста.
        """
        super().__init__(master, bd=0, highlightthickness=0, bg=parent_bg(master))
        if tone not in TONES:
            raise ValueError(f"Неизвестный тон плашки: {tone}")
        fill, ink = tone_colors(tone)
        content = text_width(self, text, "badge")
        if icon:
            content += ICON_SIZE + ICON_GAP
        width = content + 2 * PADDING_X
        height = line_height(self, "badge") + 2 * PADDING_Y
        self.configure(width=width, height=height)
        self._images = [
            photo(rounded_box(width, height, theme.BADGE_RADIUS, fill), self)
        ]
        self.create_image(0, 0, image=self._images[0], anchor="nw")
        left = PADDING_X
        if icon:
            self._images.append(photo(render_icon(icon, ICON_SIZE, ink, 2.5), self))
            self.create_image(left, height / 2, image=self._images[1], anchor="w")
            left += ICON_SIZE + ICON_GAP
        self.create_text(
            left,
            height / 2,
            text=text,
            anchor="w",
            fill=ink,
            font=font_spec("badge", self),
        )
