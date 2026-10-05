"""Цветной квадрат со значком (иконки в карточках, уведомлениях и истории)."""

import tkinter as tk

from pharmacy.ui.drawing import rounded_box
from pharmacy.ui.icons import render_icon
from pharmacy.ui.widgets.badge import tone_colors
from pharmacy.ui.widgets.common import parent_bg, photo

# Название размера -> (сторона квадрата, радиус, размер значка).
SIZES = {"md": (34, 9, 16), "sm": (28, 8, 14)}


class IconBox(tk.Canvas):
    """Скруглённый квадрат цветового тона с иконкой в центре."""

    def __init__(
        self, master: tk.Misc, icon: str, tone: str = "primary", size: str = "md"
    ) -> None:
        """Создаёт значок.

        Args:
            master: Родительский виджет.
            icon: Название иконки из ``icons.ICONS``.
            tone: Цветовой тон (см. ``badge.TONES``).
            size: ``md`` (34 px) или ``sm`` (28 px).
        """
        side, radius, glyph = SIZES[size]
        super().__init__(
            master,
            bd=0,
            highlightthickness=0,
            bg=parent_bg(master),
            width=side,
            height=side,
        )
        fill, ink = tone_colors(tone)
        self._images = [
            photo(rounded_box(side, side, radius, fill), self),
            photo(render_icon(icon, glyph, ink), self),
        ]
        self.create_image(0, 0, image=self._images[0], anchor="nw")
        self.create_image(side / 2, side / 2, image=self._images[1], anchor="center")
