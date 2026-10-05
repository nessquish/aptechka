"""Красная строка с сообщением об ошибке над формой («Неверный логин или пароль»)."""

import tkinter as tk

from pharmacy.ui import theme
from pharmacy.ui.drawing import rounded_box
from pharmacy.ui.fonts import font_spec, line_height
from pharmacy.ui.theme import palette
from pharmacy.ui.widgets.common import parent_bg, photo

PADDING_X = 10
PADDING_Y = 8


class ErrorBanner(tk.Canvas):
    """Сообщение об ошибке на розовой подложке. Пока текста нет, не занимает места."""

    def __init__(self, master: tk.Misc) -> None:
        """Создаёт скрытую плашку.

        Args:
            master: Родительский виджет.
        """
        super().__init__(
            master, bd=0, highlightthickness=0, bg=parent_bg(master), height=1
        )
        self._text = ""
        self._image = None
        self._width = 0
        self.bind("<Configure>", self._on_resize)

    @property
    def text(self) -> str:
        """Показанный сейчас текст (пустой, если плашки не видно)."""
        return self._text

    def show(self, text: str) -> None:
        """Показывает сообщение."""
        self._text = text
        self._draw()

    def hide(self) -> None:
        """Скрывает сообщение."""
        self._text = ""
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        if not self._text or self._width <= 0:
            self.configure(height=1)
            return
        pal = palette()
        font = font_spec("small", self)
        item = self.create_text(
            PADDING_X,
            PADDING_Y,
            text=self._text,
            anchor="nw",
            fill=pal.red,
            font=font,
            width=self._width - 2 * PADDING_X,
        )
        _, top, _, bottom = self.bbox(item)
        height = max(bottom - top, line_height(self, "small")) + 2 * PADDING_Y
        self._image = photo(
            rounded_box(self._width, height, theme.CONTROL_RADIUS, pal.red_bg), self
        )
        image = self.create_image(0, 0, image=self._image, anchor="nw")
        self.tag_lower(image)
        self.configure(height=height)

    def _on_resize(self, event: tk.Event) -> None:
        if event.width != self._width:
            self._width = event.width
            self._draw()
