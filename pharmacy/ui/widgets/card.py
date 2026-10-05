"""Карточка: белая скруглённая область с тенью, внутри которой лежит содержимое."""

import math
import tkinter as tk
from typing import Callable, List, Optional, Tuple

from PIL import Image

from pharmacy.ui import theme
from pharmacy.ui.drawing import Shadow, rgba, rounded_box
from pharmacy.ui.theme import CARD_SHADOW_PAD, MODAL_SHADOW_PAD, palette
from pharmacy.ui.widgets.common import parent_bg, photo

BORDER = 1
CORNER_CLEARANCE = 1 - math.sqrt(0.5)  # на сколько прямоугольник вписывается в дугу


def _shadows(elevated: bool) -> Tuple[Shadow, ...]:
    """Тени карточки: обычная лёгкая или большая у окна входа и диалогов."""
    pal = palette()
    if elevated:
        return (Shadow(10, 30, pal.shadow, 0.10), Shadow(1, 3, pal.shadow, 0.05))
    return (Shadow(3, 10, pal.shadow, 0.06), Shadow(1, 2, pal.shadow, 0.04))


class Card(tk.Frame):
    """Карточка с рамкой и тенью.

    Содержимое кладётся в ``body``. Размер карточки определяется
    содержимым, если высота не задана явно, а по ширине она занимает
    столько, сколько ей даст родитель.

    Attributes:
        body: Рамка для содержимого карточки.
        inner_inset: Отступ содержимого от видимого края карточки. Его вычитают
            из отступов макета, чтобы расстояния на экране совпали с макетом.
    """

    def __init__(
        self,
        master: tk.Misc,
        height: Optional[int] = None,
        radius: int = theme.CARD_RADIUS,
        elevated: bool = False,
        backdrop: Optional[Image.Image] = None,
        flush: bool = False,
    ) -> None:
        """Создаёт карточку.

        Args:
            master: Родительский виджет.
            height: Высота в пикселях. Если не задана, по содержимому.
            radius: Радиус скругления углов.
            elevated: Большая тень (окно входа, модальные окна).
            backdrop: Изображение всего родителя, на которое ложится тень.
                Нужно, когда карточка стоит над затемнением, а не над
                однотонным фоном.
            flush: Содержимое доходит до боковых и верхнего края (таблицы).
                Скруглённые верхние углы тогда рисует само содержимое.
        """
        super().__init__(master, bg=parent_bg(master))
        self._radius = radius
        self._elevated = elevated
        self._backdrop = backdrop
        self._shadow_pad = MODAL_SHADOW_PAD if elevated else CARD_SHADOW_PAD
        self._image = None
        self._flat: Optional[Image.Image] = (
            None  # карточка вместе с тенью, без прозрачности
        )
        self._listeners: List[Callable[[], None]] = []
        self._background = tk.Canvas(
            self, bd=0, highlightthickness=0, bg=parent_bg(master)
        )
        self._background.place(x=0, y=0, relwidth=1, relheight=1)
        self.body = tk.Frame(self, bg=palette().card)
        # Содержимое прямоугольное, поэтому отступаем от углов настолько,
        # чтобы оно не закрывало скруглённые края карточки.
        clearance = BORDER + math.ceil(radius * CORNER_CLEARANCE)
        self.inner_inset = BORDER if flush else clearance
        side = self._shadow_pad + self.inner_inset
        bottom = self._shadow_pad + clearance
        self.body.pack(fill="both", expand=True, padx=side, pady=(side, bottom))
        if height is not None:
            self.configure(height=height)
            self.pack_propagate(False)
        self._background.bind("<Configure>", self._on_resize)

    def _on_resize(self, event: tk.Event) -> None:
        """Рисует рамку и тень под содержимым по новому размеру."""
        pad = self._shadow_pad
        if event.width <= 2 * pad + 2 or event.height <= 2 * pad + 2:
            return
        pal = palette()
        shape = rounded_box(
            event.width - 2 * pad,
            event.height - 2 * pad,
            self._radius,
            pal.card,
            pal.line,
            shadows=_shadows(self._elevated),
            pad=pad,
        )
        if self._backdrop is not None:
            left, top = self.winfo_x(), self.winfo_y()
            base = self._backdrop.crop(
                (left, top, left + event.width, top + event.height)
            )
        else:
            base = Image.new("RGBA", shape.size, rgba(self._background.cget("bg"), 1.0))
        base.alpha_composite(shape)
        self._flat = base
        shape = base
        self._image = photo(shape, self)
        self._background.delete("all")
        self._background.create_image(0, 0, image=self._image, anchor="nw")
        for listener in list(self._listeners):
            listener()

    def on_redraw(self, listener: Callable[[], None]) -> None:
        """Вызывает функцию каждый раз, когда карточка перерисована."""
        self._listeners.append(listener)

    def capture(self, widget: tk.Misc) -> Optional[Image.Image]:
        """Возвращает кусок нарисованной карточки (рамка, тень) под виджетом.

        Содержимое с закруглёнными углами, которое лежит у самого края карточки
        (шапка таблицы), рисуется поверх этого куска, и углы остаются гладкими.
        Возвращает None, пока карточка не нарисована.
        """
        if self._flat is None:
            return None
        left = widget.winfo_rootx() - self._background.winfo_rootx()
        top = widget.winfo_rooty() - self._background.winfo_rooty()
        box = (left, top, left + widget.winfo_width(), top + widget.winfo_height())
        if (
            left < 0
            or top < 0
            or box[2] > self._flat.width
            or box[3] > self._flat.height
        ):
            return None
        return self._flat.crop(box)
