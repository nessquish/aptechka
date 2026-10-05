"""Экран «Моя аптечка» (макет Figma, экраны 04 и 15): таблица товаров."""

import math
import tkinter as tk
from typing import TYPE_CHECKING, List, Optional

from pharmacy.services.product_service import ProductView
from pharmacy.services.status import ProductStatus
from pharmacy.ui import labels
from pharmacy.ui.fonts import font_spec
from pharmacy.ui.icons import render_icon
from pharmacy.ui.drawing import rounded_box
from pharmacy.ui.theme import CARD_SHADOW_PAD, SHADOW_PAD, palette
from pharmacy.ui.widgets.badge import Badge
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.common import photo
from pharmacy.ui.widgets.controls import Pagination
from pharmacy.ui.widgets.field import TextField
from pharmacy.ui.widgets.page import ACTION_INSET, PageHeader
from pharmacy.ui.widgets.select import Select
from pharmacy.ui.widgets.table import Column, DataTable, TextCell
from pharmacy.utils.dates import format_user_date
from pharmacy.utils.formatting import format_quantity

if TYPE_CHECKING:
    from pharmacy.ui.screens.shell import MainShell

PAGE_SIZE = 8
SEARCH_WIDTH = 260
SEARCH_DELAY_MS = 250
SORTS = (
    ("expiry", "срок годности"),
    ("name", "название"),
    ("quantity", "количество"),
    ("added", "дата добавления"),
)
# Какой столбец помечается стрелкой при каждой сортировке.
SORT_COLUMN = {"name": 0, "quantity": 2, "expiry": 4}
COLUMNS = (
    Column("Название", 30),
    Column("Категория", 20),
    Column("Количество", 14),
    Column("Ед. изм.", 11),
    Column("Срок годности", 17),
    Column("Место хранения", 17),
    Column("Состояние", 18),
)
EMPTY_ICON = 64


class MyKitScreen(tk.Frame):
    """Список товаров с поиском, фильтрами, сортировкой и страницами."""

    def __init__(self, master: tk.Misc, shell: "MainShell") -> None:
        pal = palette()
        super().__init__(master, bg=pal.bg)
        self._shell = shell
        self._services = shell.services
        self._user = shell.user
        self._search = ""
        self._category: Optional[int] = None
        self._status: Optional[ProductStatus] = None
        self._sort = SORTS[0][0]
        self._page = 1
        self._search_job: Optional[str] = None
        self.bind("<Destroy>", self._on_destroy)
        PageHeader(self, "Моя аптечка").pack(fill="x")
        if self._services.products.list_products(self._user.id):
            self._build_toolbar()
            self._build_table()
            self._reload()
        else:
            self._build_empty()

    def _on_destroy(self, event: tk.Event) -> None:
        """Отменяет отложенный поиск, если экран закрыли раньше срабатывания."""
        if event.widget is self and self._search_job is not None:
            self.after_cancel(self._search_job)
            self._search_job = None

    # --- пустая аптечка (экран 15) ---

    def _build_empty(self) -> None:
        pal = palette()
        card = Card(self)
        card.pack(fill="x", pady=(18 - CARD_SHADOW_PAD, 0))
        inner = tk.Frame(card.body, bg=pal.card)
        inner.pack(pady=60)
        circle = tk.Canvas(
            inner,
            width=EMPTY_ICON,
            height=EMPTY_ICON,
            bd=0,
            highlightthickness=0,
            bg=pal.card,
        )
        circle.pack(pady=(0, 16))
        self._images = [
            photo(
                rounded_box(EMPTY_ICON, EMPTY_ICON, EMPTY_ICON // 2, pal.primary_soft),
                circle,
            ),
            photo(render_icon("cross", 28, pal.primary), circle),
        ]
        circle.create_image(0, 0, image=self._images[0], anchor="nw")
        circle.create_image(
            EMPTY_ICON / 2, EMPTY_ICON / 2, image=self._images[1], anchor="center"
        )
        tk.Label(
            inner,
            text="В аптечке пока пусто",
            bg=pal.card,
            fg=pal.ink,
            font=font_spec("section", self),
        ).pack(pady=(0, 6))
        tk.Label(
            inner,
            text=(
                "Добавьте первое лекарство или бытовое средство,\n"
                "чтобы следить за сроками годности и остатками"
            ),
            bg=pal.card,
            fg=pal.ink_2,
            font=font_spec("body", self),
            justify="center",
        ).pack(pady=(0, 18))
        Button(
            inner,
            "Добавить товар",
            command=self._shell.open_product_form,
            variant="primary",
            icon="plus",
        ).pack()

    # --- панель ---

    def _build_toolbar(self) -> None:
        pal = palette()
        bar = tk.Frame(self, bg=pal.bg)
        bar.pack(fill="x", padx=ACTION_INSET, pady=(18 - SHADOW_PAD, 14 - SHADOW_PAD))
        Button(
            bar,
            "Добавить товар",
            command=self._shell.open_product_form,
            variant="primary",
            icon="plus",
        ).pack(side="left", padx=(0, 8 - 2 * SHADOW_PAD))
        self._search_field = TextField(
            bar,
            placeholder="Поиск по названию…",
            leading_icon="search",
            compact=True,
            width=SEARCH_WIDTH,
            on_change=self._on_search,
        )
        self._search_field.pack(side="left", padx=(0, 8 - 2 * SHADOW_PAD))
        categories = [(None, "Все категории")] + [
            (c.id, c.name) for c in self._services.products.list_categories()
        ]
        Select(bar, categories, None, compact=True, on_change=self._on_category).pack(
            side="left", padx=(0, 8 - 2 * SHADOW_PAD)
        )
        states = [(None, "Любое состояние")] + [(s, s.label) for s in ProductStatus]
        Select(bar, states, None, compact=True, on_change=self._on_status).pack(
            side="left"
        )
        Select(
            bar,
            SORTS,
            self._sort,
            compact=True,
            prefix="Сортировка: ",
            on_change=self._on_sort,
        ).pack(side="right")

    def _on_search(self) -> None:
        """Ищет с задержкой, чтобы не перерисовывать таблицу на каждую букву."""
        if self._search_job is not None:
            self.after_cancel(self._search_job)
        self._search_job = self.after(SEARCH_DELAY_MS, self._apply_search)

    def _apply_search(self) -> None:
        self._search_job = None
        self._search = self._search_field.get().strip()
        self._page = 1
        self._reload()

    def _on_category(self, value: object) -> None:
        self._category = value
        self._page = 1
        self._reload()

    def _on_status(self, value: object) -> None:
        self._status = value
        self._page = 1
        self._reload()

    def _on_sort(self, value: object) -> None:
        self._sort = value
        self._page = 1
        self._reload()

    # --- таблица ---

    def _build_table(self) -> None:
        card = Card(self, flush=True)
        card.pack(fill="x")
        self._table = DataTable(card.body, COLUMNS)
        self._table.pack(fill="x")
        self._footer = tk.Frame(card.body, bg=palette().card)
        self._footer.pack(fill="x")

    def _reload(self) -> None:
        """Заново читает товары по текущим условиям и перерисовывает таблицу."""
        views = self._services.products.list_products(
            self._user.id,
            search=self._search,
            category_id=self._category,
            status=self._status,
            sort=self._sort,
        )
        pages = max(math.ceil(len(views) / PAGE_SIZE), 1)
        self._page = min(self._page, pages)
        start = (self._page - 1) * PAGE_SIZE
        shown = views[start : start + PAGE_SIZE]
        self._table.set_sorted(SORT_COLUMN.get(self._sort))
        self._table.clear()
        if not shown:
            self._table.add_message("Ничего не найдено")
        for view in shown:
            self._table.add_row(self._cells(view))
        self._build_footer(len(views), start, len(shown), pages)

    def _cells(self, view: ProductView) -> List:
        product = view.product
        status = view.primary_status
        expiry = (
            TextCell(format_user_date(product.expiry_date), "ink_2")
            if product.expiry_date
            else TextCell("—", "ink_3")
        )
        return [
            TextCell(
                product.name,
                "primary",
                bold=True,
                on_click=lambda p=product.id: self._shell.open_product(p),
            ),
            TextCell(labels.short_category(product.category_name), "ink_2"),
            TextCell(format_quantity(product.quantity), "ink_2"),
            TextCell(product.unit, "ink_2"),
            expiry,
            TextCell(product.storage_place or "—", "ink_2"),
            lambda parent: Badge(parent, status.label, labels.STATUS_TONES[status]),
        ]

    def _build_footer(self, total: int, start: int, shown: int, pages: int) -> None:
        pal = palette()
        for child in self._footer.winfo_children():
            child.destroy()
        tk.Frame(self._footer, bg=pal.line, height=1).pack(fill="x")
        row = tk.Frame(self._footer, bg=pal.card)
        row.pack(fill="x", padx=14, pady=10)
        text = (
            f"Показано {start + 1}–{start + shown} из {total}"
            if shown
            else "Показано 0 из 0"
        )
        tk.Label(
            row,
            text=text,
            bg=pal.card,
            fg=pal.ink_2,
            font=font_spec("small", self),
            padx=0,
        ).pack(side="left")
        Pagination(row, self._page, pages, self._on_page).pack(side="right")

    def _on_page(self, page: int) -> None:
        self._page = page
        self._reload()
