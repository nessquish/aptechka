"""Маленькая кнопка с одной иконкой (свернуть или развернуть боковую панель)."""

import tkinter as tk
from typing import Callable

from pharmacy.ui.drawing import rounded_box
from pharmacy.ui.icons import render_icon
from pharmacy.ui.theme import mix, palette
from pharmacy.ui.widgets.common import parent_bg, photo

SIZE = 28
ICON_SIZE = 16
RADIUS = 7


class IconButton(tk.Canvas):
    """Квадратная кнопка с иконкой, при наведении подсвечивается."""

    def __init__(self, master: tk.Misc, icon: str, command: Callable[[], None]) -> None:
        """Создаёт кнопку.

        Args:
            master: Родительский виджет.
            icon: Название иконки из ``icons.ICONS``.
            command: Что вызвать при нажатии.
        """
        super().__init__(
            master,
            bd=0,
            highlightthickness=0,
            bg=parent_bg(master),
            width=SIZE,
            height=SIZE,
            cursor="hand2",
        )
        self._icon = icon
        self._command = command
        self._hover = False
        self._images: list = []
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda _event: self._command())
        self._draw()

    def _on_enter(self, _event: tk.Event) -> None:
        self._hover = True
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hover = False
        self._draw()

    def _draw(self) -> None:
        pal = palette()
        self.delete("all")
        self._images = []
        if self._hover:
            chip = rounded_box(SIZE, SIZE, RADIUS, mix(pal.side, pal.primary_soft, 0.7))
            self._images.append(photo(chip, self))
            self.create_image(0, 0, image=self._images[-1], anchor="nw")
        color = pal.primary_ink if self._hover else pal.ink_2
        self._images.append(photo(render_icon(self._icon, ICON_SIZE, color), self))
        self.create_image(SIZE / 2, SIZE / 2, image=self._images[-1], anchor="center")
