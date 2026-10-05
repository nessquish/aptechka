"""Мелкие элементы управления: вкладки, переключатели, чекбокс, пагинация."""

import tkinter as tk
from typing import Callable, List, Optional, Sequence, Tuple

from pharmacy.ui import theme
from pharmacy.ui.drawing import Shadow, rounded_box
from pharmacy.ui.fonts import font_spec, line_height, text_width
from pharmacy.ui.icons import render_icon
from pharmacy.ui.theme import palette
from pharmacy.ui.widgets.common import parent_bg, photo

Callback = Callable[[int], None]


class Segmented(tk.Canvas):
    """Ряд вариантов, из которых выбран один.

    Два вида из макета: ``tabs`` (вкладки на серой подложке) и ``outline``
    (рамка с выделенным вариантом, как выбор темы).
    """

    PAD = 4  # поле под тень выбранного варианта

    def __init__(
        self,
        master: tk.Misc,
        items: Sequence[str],
        active: int = 0,
        on_change: Optional[Callback] = None,
        variant: str = "tabs",
    ) -> None:
        """Создаёт переключатель.

        Args:
            master: Родительский виджет.
            items: Подписи вариантов.
            active: Номер выбранного варианта.
            on_change: Вызывается с номером выбранного варианта.
            variant: ``tabs`` или ``outline``.
        """
        super().__init__(master, bd=0, highlightthickness=0, bg=parent_bg(master))
        if variant not in ("tabs", "outline"):
            raise ValueError(f"Неизвестный вид переключателя: {variant}")
        self._variant = variant
        self._items = list(items)
        self._active = active
        self._on_change = on_change
        self._images: list = []
        self._spans: List[Tuple[int, int]] = []
        self._padding_x = 12 if variant == "tabs" else 14
        self._gap = 4 if variant == "tabs" else 0
        self._edge = 3 if variant == "tabs" else 1
        self._height = line_height(self, "small") + 12 + 2 * self._edge
        self.bind("<Button-1>", self._on_click)
        self.configure(cursor="hand2")
        self._draw()

    @property
    def active(self) -> int:
        """Номер выбранного варианта."""
        return self._active

    def select(self, index: int) -> None:
        """Выбирает вариант без вызова обработчика."""
        self._active = index
        self._draw()

    def set_items(self, items: Sequence[str]) -> None:
        """Заменяет подписи (например, обновляет числа во вкладках)."""
        self._items = list(items)
        self._draw()

    def _draw(self) -> None:
        pal = palette()
        self.delete("all")
        self._images = []
        widths = [
            text_width(self, text, "small_medium") + 2 * self._padding_x
            for text in self._items
        ]
        total = sum(widths) + self._gap * (len(widths) - 1) + 2 * self._edge
        self.configure(width=total + 2 * self.PAD, height=self._height + 2 * self.PAD)
        radius = 8 if self._variant == "tabs" else theme.CONTROL_RADIUS
        base = rounded_box(
            total,
            self._height,
            radius,
            pal.tabs_bg if self._variant == "tabs" else pal.input_bg,
            None if self._variant == "tabs" else pal.line,
            pad=self.PAD,
        )
        self._images.append(photo(base, self))
        self.create_image(0, 0, image=self._images[0], anchor="nw")
        self._spans = []
        left = self.PAD + self._edge
        top = self.PAD + self._edge
        inner = self._height - 2 * self._edge
        for index, (text, width) in enumerate(zip(self._items, widths)):
            self._spans.append((left, left + width))
            chosen = index == self._active
            if chosen:
                self._draw_chosen(left, top, width, inner)
            self.create_text(
                left + width / 2,
                top + inner / 2,
                text=text,
                fill=pal.primary_ink if chosen else pal.ink_2,
                font=font_spec("small_medium" if chosen else "small", self),
            )
            left += width + self._gap

    def _draw_chosen(self, left: int, top: int, width: int, height: int) -> None:
        pal = palette()
        if self._variant == "tabs":
            fill, shadows, radius = pal.card, (Shadow(1, 3, pal.shadow, 0.08),), 6
        else:
            fill, shadows, radius = pal.primary_soft, (), 6
        chip = rounded_box(width, height, radius, fill, shadows=shadows, pad=3)
        self._images.append(photo(chip, self))
        self.create_image(left - 3, top - 3, image=self._images[-1], anchor="nw")

    def _on_click(self, event: tk.Event) -> None:
        for index, (left, right) in enumerate(self._spans):
            if left <= event.x < right and index != self._active:
                self._active = index
                self._draw()
                if self._on_change is not None:
                    self._on_change(index)
                return


class Toggle(tk.Canvas):
    """Переключатель включено/выключено (34 на 19 пикселей)."""

    WIDTH, HEIGHT, KNOB = 34, 19, 15

    def __init__(
        self,
        master: tk.Misc,
        value: bool = False,
        on_change: Optional[Callable[[bool], None]] = None,
    ) -> None:
        super().__init__(
            master,
            bd=0,
            highlightthickness=0,
            bg=parent_bg(master),
            width=self.WIDTH,
            height=self.HEIGHT,
            cursor="hand2",
        )
        self._value = value
        self._on_change = on_change
        self._images: list = []
        self.bind("<Button-1>", self._on_click)
        self._draw()

    @property
    def value(self) -> bool:
        """Включён ли переключатель."""
        return self._value

    def set(self, value: bool) -> None:
        """Включает или выключает без вызова обработчика."""
        self._value = value
        self._draw()

    def _draw(self) -> None:
        pal = palette()
        self.delete("all")
        track = pal.primary if self._value else pal.checkbox_line
        self._images = [
            photo(rounded_box(self.WIDTH, self.HEIGHT, self.HEIGHT // 2, track), self),
            photo(rounded_box(self.KNOB, self.KNOB, self.KNOB // 2, "#FFFFFF"), self),
        ]
        self.create_image(0, 0, image=self._images[0], anchor="nw")
        inset = (self.HEIGHT - self.KNOB) // 2
        left = self.WIDTH - inset - self.KNOB if self._value else inset
        self.create_image(left, inset, image=self._images[1], anchor="nw")

    def _on_click(self, _event: tk.Event) -> None:
        self._value = not self._value
        self._draw()
        if self._on_change is not None:
            self._on_change(self._value)


class Checkbox(tk.Canvas):
    """Флажок 14 на 14 пикселей с галочкой."""

    SIZE = 14

    def __init__(
        self,
        master: tk.Misc,
        value: bool = False,
        on_change: Optional[Callable[[bool], None]] = None,
    ) -> None:
        super().__init__(
            master,
            bd=0,
            highlightthickness=0,
            bg=parent_bg(master),
            width=self.SIZE,
            height=self.SIZE,
            cursor="hand2",
        )
        self._value = value
        self._on_change = on_change
        self._images: list = []
        self.bind("<Button-1>", self._on_click)
        self._draw()

    @property
    def value(self) -> bool:
        """Отмечен ли флажок."""
        return self._value

    def set(self, value: bool) -> None:
        """Ставит или снимает отметку без вызова обработчика."""
        self._value = value
        self._draw()

    def _draw(self) -> None:
        pal = palette()
        self.delete("all")
        if self._value:
            box = rounded_box(self.SIZE, self.SIZE, 4, pal.primary)
        else:
            box = rounded_box(
                self.SIZE, self.SIZE, 4, pal.input_bg, pal.checkbox_line, border_width=2
            )
        self._images = [photo(box, self)]
        self.create_image(0, 0, image=self._images[0], anchor="nw")
        if self._value:
            self._images.append(photo(render_icon("check", 10, "#FFFFFF", 3.5), self))
            self.create_image(
                self.SIZE / 2, self.SIZE / 2, image=self._images[1], anchor="center"
            )

    def _on_click(self, _event: tk.Event) -> None:
        self._value = not self._value
        self._draw()
        if self._on_change is not None:
            self._on_change(self._value)


class Pagination(tk.Canvas):
    """Кнопки страниц: стрелки и номера."""

    CELL, GAP = 24, 4

    def __init__(
        self,
        master: tk.Misc,
        page: int,
        pages: int,
        on_change: Callback,
    ) -> None:
        """Создаёт пагинацию.

        Args:
            master: Родительский виджет.
            page: Номер текущей страницы (с 1).
            pages: Сколько всего страниц.
            on_change: Вызывается с номером выбранной страницы.
        """
        super().__init__(master, bd=0, highlightthickness=0, bg=parent_bg(master))
        self._page = page
        self._pages = max(pages, 1)
        self._on_change = on_change
        self._images: list = []
        self._targets: List[Tuple[int, int]] = []
        self.configure(cursor="hand2")
        self.bind("<Button-1>", self._on_click)
        self._draw()

    def _cells(self) -> List[Tuple[str, int]]:
        numbers = [("page", n) for n in range(1, self._pages + 1)]
        return [("prev", self._page - 1)] + numbers + [("next", self._page + 1)]

    def _draw(self) -> None:
        pal = palette()
        self.delete("all")
        self._images = []
        self._targets = []
        cells = self._cells()
        size = self.CELL
        self.configure(
            width=len(cells) * size + (len(cells) - 1) * self.GAP, height=size
        )
        for index, (kind, target) in enumerate(cells):
            left = index * (size + self.GAP)
            current = kind == "page" and target == self._page
            enabled = 1 <= target <= self._pages
            if current:
                box = rounded_box(size, size, 6, pal.primary, pal.primary)
            else:
                box = rounded_box(size, size, 6, pal.input_bg, pal.line)
            self._images.append(photo(box, self))
            self.create_image(left, 0, image=self._images[-1], anchor="nw")
            center = (left + size / 2, size / 2)
            if kind == "page":
                self.create_text(
                    *center,
                    text=str(target),
                    fill=pal.on_primary if current else pal.ink_2,
                    font=font_spec("small", self),
                )
            else:
                name = "chevron-left" if kind == "prev" else "chevron-right"
                colour = pal.ink_2 if enabled else pal.checkbox_line
                self._images.append(photo(render_icon(name, 14, colour), self))
                self.create_image(*center, image=self._images[-1], anchor="center")
            self._targets.append((left, target if enabled else 0))

    def _on_click(self, event: tk.Event) -> None:
        for left, target in self._targets:
            if left <= event.x < left + self.CELL and target and target != self._page:
                self._page = target
                self._draw()
                self._on_change(target)
                return
