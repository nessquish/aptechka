"""Таблица из макета: шапка с сортировкой и строки с разделителями."""

import tkinter as tk
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Union

from pharmacy.ui import theme
from pharmacy.ui.drawing import rounded_box
from pharmacy.ui.fonts import font_spec, line_height
from pharmacy.ui.icons import render_icon
from pharmacy.ui.theme import palette
from pharmacy.ui.widgets.common import parent_bg, photo

HEADER_PADDING_Y = 10
CELL_PADDING_X = 12
CELL_PADDING_Y = 9
SORT_ICON = 12


@dataclass(frozen=True)
class Column:
    """Столбец таблицы.

    Attributes:
        title: Заголовок.
        weight: Относительная ширина столбца.
        fixed: Ширина в пикселях вместо относительной (например, у флажков).
    """

    title: str
    weight: int = 1
    fixed: Optional[int] = None


@dataclass(frozen=True)
class TextCell:
    """Текстовая ячейка.

    Attributes:
        text: Текст.
        color: Роль цвета: ``ink``, ``ink_2``, ``ink_3`` или ``primary``.
        bold: Полужирный шрифт.
        strike: Зачёркнутый текст (купленные позиции).
        on_click: Если задано, ячейка работает как ссылка.
    """

    text: str
    color: str = "ink"
    bold: bool = False
    strike: bool = False
    on_click: Optional[Callable[[], None]] = None


Cell = Union[str, TextCell, Callable[[tk.Misc], tk.Widget]]


class DataTable(tk.Frame):
    """Шапка и строки таблицы. Столбцы делят ширину пропорционально весам."""

    def __init__(self, master: tk.Misc, columns: Sequence[Column]) -> None:
        """Создаёт таблицу без строк.

        Args:
            master: Родитель (обычно ``body`` карточки с ``flush=True``).
            columns: Столбцы слева направо.
        """
        super().__init__(master, bg=parent_bg(master))
        self._columns = list(columns)
        self._sorted: Optional[int] = None
        self._images: list = []
        self._width = 0
        self._header_height = line_height(self, "small_medium") + 2 * HEADER_PADDING_Y
        self._header = tk.Canvas(
            self,
            bd=0,
            highlightthickness=0,
            bg=self.cget("bg"),
            height=self._header_height,
        )
        self._header.pack(fill="x")
        self._header.bind("<Configure>", self._on_resize)
        self._body = tk.Frame(self, bg=self.cget("bg"))
        self._body.pack(fill="x")

    def set_sorted(self, index: Optional[int]) -> None:
        """Показывает стрелку сортировки у столбца (None убирает стрелку)."""
        self._sorted = index
        if self._width:
            self._draw_header()

    def clear(self) -> None:
        """Удаляет все строки."""
        for child in self._body.winfo_children():
            child.destroy()

    def add_row(self, cells: Sequence[Cell], selected: bool = False) -> tk.Frame:
        """Добавляет строку.

        Args:
            cells: Содержимое ячеек по столбцам: текст, ``TextCell`` или
                функция, создающая виджет по родителю.
            selected: Подсветить строку (выбранная или непрочитанная).

        Returns:
            Рамка строки.
        """
        pal = palette()
        tk.Frame(self._body, bg=pal.line, height=1).pack(fill="x")
        row = tk.Frame(self._body, bg=pal.unread_bg if selected else pal.card)
        row.pack(fill="x")
        self._configure_columns(row)
        for index, cell in enumerate(cells):
            widget = self._make_cell(row, cell)
            widget.grid(
                row=0,
                column=index,
                sticky="w",
                padx=CELL_PADDING_X,
                pady=CELL_PADDING_Y,
            )
        return row

    def add_message(self, text: str) -> None:
        """Добавляет строку с сообщением на всю ширину («Ничего не найдено»)."""
        pal = palette()
        tk.Frame(self._body, bg=pal.line, height=1).pack(fill="x")
        tk.Label(
            self._body,
            text=text,
            bg=pal.card,
            fg=pal.ink_3,
            font=font_spec("body", self),
        ).pack(fill="x", pady=36)

    def _configure_columns(self, row: tk.Frame) -> None:
        for index, column in enumerate(self._columns):
            if column.fixed is not None:
                row.columnconfigure(index, minsize=column.fixed, weight=0)
            else:
                row.columnconfigure(
                    index, weight=column.weight, uniform="cells", minsize=0
                )

    def _make_cell(self, row: tk.Frame, cell: Cell) -> tk.Widget:
        pal = palette()
        background = row.cget("bg")
        if callable(cell):
            return cell(row)
        spec = TextCell(cell) if isinstance(cell, str) else cell
        colors = {
            "ink": pal.ink,
            "ink_2": pal.ink_2,
            "ink_3": pal.ink_3,
            "primary": pal.primary,
        }
        font = font_spec("strong" if spec.bold else "small", self)
        if spec.strike:
            font = (font[0], font[1], f"{font[2]} overstrike")
        label = tk.Label(
            row,
            text=spec.text,
            bg=background,
            fg=colors[spec.color],
            font=font,
            padx=0,
            pady=0,
            anchor="w",
        )
        if spec.on_click is not None:
            label.configure(cursor="hand2")
            label.bind("<Button-1>", lambda _event: spec.on_click())
        return label

    # --- шапка ---

    def _fractions(self) -> List[float]:
        """Левые края столбцов шапки в долях ширины."""
        fixed = sum(c.fixed or 0 for c in self._columns)
        flexible = sum(c.weight for c in self._columns if c.fixed is None) or 1
        free = max(self._width - fixed, 0)
        lefts, position = [], 0.0
        for column in self._columns:
            lefts.append(position)
            position += (
                column.fixed
                if column.fixed is not None
                else (free * column.weight / flexible)
            )
        return lefts

    def _on_resize(self, event: tk.Event) -> None:
        if event.width != self._width:
            self._width = event.width
            self._draw_header()

    def _draw_header(self) -> None:
        pal = palette()
        canvas = self._header
        canvas.delete("all")
        self._images = []
        radius = theme.CARD_RADIUS - 1
        shape = rounded_box(
            self._width, self._header_height + radius, radius, pal.table_head
        )
        self._images.append(
            photo(shape.crop((0, 0, self._width, self._header_height)), canvas)
        )
        canvas.create_image(0, 0, image=self._images[0], anchor="nw")
        middle = self._header_height / 2
        for index, (column, left) in enumerate(zip(self._columns, self._fractions())):
            item = canvas.create_text(
                left + CELL_PADDING_X,
                middle,
                text=column.title,
                anchor="w",
                fill=pal.ink_2,
                font=font_spec("small_medium", self),
            )
            if index == self._sorted:
                right = canvas.bbox(item)[2] + 4
                self._images.append(
                    photo(render_icon("arrow-down", SORT_ICON, pal.primary), canvas)
                )
                canvas.create_image(right, middle, image=self._images[-1], anchor="w")
