"""Панель действий над выбранными строками таблицы («Выбрано: 2» и кнопки)."""

import tkinter as tk
from typing import Optional

from pharmacy.ui import theme
from pharmacy.ui.drawing import rounded_box
from pharmacy.ui.fonts import font_spec
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.theme import palette
from pharmacy.ui.widgets.common import parent_bg, photo

HEIGHT = 46
PADDING_X = 14


class ActionBar(tk.Canvas):
    """Полоса цвета выделения с текстом слева и кнопками справа.

    Верхние углы скруглены, как у карточки, в которую панель вставлена.

    Attributes:
        buttons: Рамка справа, в которую кладутся кнопки.
    """

    def __init__(self, master: tk.Misc, card: Optional[Card] = None) -> None:
        """Создаёт панель.

        Args:
            master: Родительский виджет.
            card: Карточка, в которую вставлена панель (для гладких углов).
        """
        self._card = card
        super().__init__(
            master, bd=0, highlightthickness=0, bg=parent_bg(master), height=HEIGHT
        )
        pal = palette()
        self._text = ""
        self._image = None
        self._width = 0
        self.buttons = tk.Frame(self, bg=pal.bulk_bg)
        self._window = self.create_window(
            0, HEIGHT / 2, window=self.buttons, anchor="e"
        )
        self.bind("<Configure>", self._on_resize)
        if card is not None:
            card.on_redraw(lambda: self.winfo_exists() and self.after_idle(self._draw))

    def set_text(self, text: str) -> None:
        """Меняет текст слева."""
        self._text = text
        self._draw()

    def _on_resize(self, event: tk.Event) -> None:
        if event.width != self._width:
            self._width = event.width
            self._draw()

    def _draw(self) -> None:
        if self._width <= 0:
            return
        pal = palette()
        radius = theme.CARD_RADIUS - 1
        shape = rounded_box(self._width, HEIGHT + radius, radius, pal.bulk_bg).crop(
            (0, 0, self._width, HEIGHT)
        )
        under = self._card.capture(self) if self._card is not None else None
        if under is not None:
            under.alpha_composite(shape)
            shape = under
        self._image = photo(shape, self)
        self.delete("shape", "label")
        self.create_image(0, 0, image=self._image, anchor="nw", tags="shape")
        self.tag_lower("shape")
        self.create_text(
            PADDING_X,
            HEIGHT / 2,
            text=self._text,
            anchor="w",
            fill=pal.primary_ink,
            font=font_spec("small", self),
            tags="label",
        )
        self.coords(self._window, self._width - PADDING_X, HEIGHT / 2)
