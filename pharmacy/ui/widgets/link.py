"""Ссылка: цветной текст, на который можно нажать."""

import tkinter as tk
from typing import Callable, Optional

from PIL import Image

from pharmacy.ui.fonts import font_spec
from pharmacy.ui.icons import render_icon
from pharmacy.ui.theme import palette
from pharmacy.ui.widgets.common import parent_bg, photo

ICON_SIZE = 14
ICON_GAP = 6


class Link(tk.Label):
    """Текст цвета акцента без подчёркивания, нажатие вызывает команду."""

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None],
        style: str = "small_medium",
        icon: Optional[str] = None,
        icon_side: str = "right",
    ) -> None:
        """Создаёт ссылку.

        Args:
            master: Родительский виджет.
            text: Текст ссылки.
            command: Что вызвать при нажатии.
            style: Стиль текста из ``theme.TYPOGRAPHY``.
            icon: Название иконки рядом с текстом (например, стрелка).
            icon_side: С какой стороны от текста иконка: ``right`` или ``left``.
        """
        pal = palette()
        super().__init__(
            master,
            text=text,
            bg=parent_bg(master),
            fg=pal.primary,
            font=font_spec(style, master),
            cursor="hand2",
            padx=0,
        )
        if icon:
            glyph = render_icon(icon, ICON_SIZE, pal.primary)
            padded = Image.new("RGBA", (ICON_SIZE + ICON_GAP, ICON_SIZE), (0, 0, 0, 0))
            on_left = icon_side == "left"
            padded.paste(glyph, (0 if on_left else ICON_GAP, 0))
            self._icon = photo(padded, self)
            self.configure(image=self._icon, compound=icon_side)
        self.bind("<Button-1>", lambda _event: command())
