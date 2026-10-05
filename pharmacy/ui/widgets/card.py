"""Карточка: белая скруглённая область с тенью, внутри которой лежит содержимое."""

import tkinter as tk
from typing import Optional

from pharmacy.ui import theme
from pharmacy.ui.drawing import Shadow, rounded_box
from pharmacy.ui.theme import CARD_SHADOW_PAD, palette
from pharmacy.ui.widgets.common import parent_bg, photo

BORDER = 1
INSET = CARD_SHADOW_PAD + BORDER


class Card(tk.Frame):
    """Карточка с рамкой и тенью.

    Содержимое кладётся в ``body``. Размер карточки определяется
    содержимым, если высота не задана явно, а по ширине она занимает
    столько, сколько ей даст родитель.

    Attributes:
        body: Рамка для содержимого карточки.
    """

    def __init__(
        self,
        master: tk.Misc,
        height: Optional[int] = None,
        radius: int = theme.CARD_RADIUS,
    ) -> None:
        """Создаёт карточку.

        Args:
            master: Родительский виджет.
            height: Высота в пикселях. Если не задана, по содержимому.
            radius: Радиус скругления углов.
        """
        super().__init__(master, bg=parent_bg(master))
        self._radius = radius
        self._image = None
        self._background = tk.Canvas(
            self, bd=0, highlightthickness=0, bg=parent_bg(master)
        )
        self._background.place(x=0, y=0, relwidth=1, relheight=1)
        self.body = tk.Frame(self, bg=palette().card)
        self.body.pack(fill="both", expand=True, padx=INSET, pady=INSET)
        if height is not None:
            self.configure(height=height)
            self.pack_propagate(False)
        self._background.bind("<Configure>", self._on_resize)

    def _on_resize(self, event: tk.Event) -> None:
        """Рисует рамку и тень под содержимым по новому размеру."""
        if event.width <= 2 * INSET or event.height <= 2 * INSET:
            return
        pal = palette()
        shape = rounded_box(
            event.width - 2 * CARD_SHADOW_PAD,
            event.height - 2 * CARD_SHADOW_PAD,
            self._radius,
            pal.card,
            pal.line,
            shadows=(
                Shadow(3, 10, pal.shadow, 0.06),
                Shadow(1, 2, pal.shadow, 0.04),
            ),
            pad=CARD_SHADOW_PAD,
        )
        self._image = photo(shape, self)
        self._background.delete("all")
        self._background.create_image(0, 0, image=self._image, anchor="nw")
