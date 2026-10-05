"""Строка со скруглённой цветной подложкой (непрочитанное уведомление)."""

import tkinter as tk

from pharmacy.ui.drawing import rounded_box
from pharmacy.ui.widgets.common import parent_bg, photo

RADIUS = 6
MARGIN_X = 4  # отступ подложки от краёв строки
MARGIN_Y = 2
INSET = 2  # отступ содержимого от края подложки: оно не закрывает её скругления


class Highlight(tk.Frame):
    """Рамка с подложкой цвета ``color`` и скруглёнными углами.

    Содержимое кладётся в ``body``. Подложка отступает от краёв строки, а
    содержимое от подложки, поэтому прямоугольники виджетов не торчат из углов.

    Attributes:
        body: Рамка для содержимого строки.
        padding_x: Полный горизонтальный отступ содержимого от края рамки.
        padding_y: Полный вертикальный отступ содержимого от края рамки.
    """

    padding_x = MARGIN_X + INSET
    padding_y = MARGIN_Y + INSET

    def __init__(self, master: tk.Misc, color: str) -> None:
        """Создаёт строку.

        Args:
            master: Родительский виджет.
            color: Цвет подложки ``#RRGGBB``.
        """
        super().__init__(master, bg=parent_bg(master))
        self._color = color
        self._image = None
        self._canvas = tk.Canvas(self, bd=0, highlightthickness=0, bg=parent_bg(master))
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.body = tk.Frame(self, bg=color)
        self.body.pack(fill="x", padx=self.padding_x, pady=self.padding_y)
        self._canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, event: tk.Event) -> None:
        width = event.width - 2 * MARGIN_X
        height = event.height - 2 * MARGIN_Y
        if width <= 2 * RADIUS or height <= 2 * RADIUS:
            return
        self._image = photo(rounded_box(width, height, RADIUS, self._color), self)
        self._canvas.delete("all")
        self._canvas.create_image(MARGIN_X, MARGIN_Y, image=self._image, anchor="nw")
