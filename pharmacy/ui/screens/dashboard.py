"""Экран «Главная» (макет Figma, экран 03): сводка по аптечке."""

import tkinter as tk
from datetime import date, datetime
from typing import TYPE_CHECKING, Callable, List

from pharmacy.services.dashboard_service import DashboardSummary
from pharmacy.services.product_service import ProductView
from pharmacy.services.status import ProductStatus
from pharmacy.ui import labels, sections
from pharmacy.ui.fonts import font_spec
from pharmacy.ui.theme import CARD_SHADOW_PAD, SHADOW_PAD, palette
from pharmacy.ui.widgets.badge import Badge
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.iconbox import IconBox
from pharmacy.ui.widgets.link import Link
from pharmacy.ui.widgets.page import PageHeader
from pharmacy.utils.dates import format_user_date
from pharmacy.utils.formatting import format_quantity

if TYPE_CHECKING:
    from pharmacy.ui.screens.shell import MainShell

STAT_GAP = 14 - 2 * CARD_SHADOW_PAD  # расстояние между карточками минус поля теней
COLUMN_GAP = 16 - 2 * CARD_SHADOW_PAD
LEFT_WEIGHT, RIGHT_WEIGHT = 16, 10  # колонки 1.6fr и 1fr из макета
OPEN_TAB = 1  # вкладка «Не куплено» в списке покупок
ROW_PADDING_X = 18
ROW_PADDING_Y = 8


def _make_clickable(widget: tk.Misc, command: Callable[[], None]) -> None:
    """Делает виджет и всё, что в нём лежит, нажимаемым (рука вместо стрелки)."""
    widget.configure(cursor="hand2")
    widget.bind("<Button-1>", lambda _event: command(), add="+")
    for child in widget.winfo_children():
        _make_clickable(child, command)


def _detail(view: ProductView) -> str:
    """Вторая строка в списке «Требуют внимания»."""
    product = view.product
    status = view.primary_status
    if status is ProductStatus.EXPIRED:
        return f"Срок годности истёк {format_user_date(product.expiry_date)}"
    if status is ProductStatus.EXPIRING:
        return f"Годен до {format_user_date(product.expiry_date)}"
    unit = product.unit
    return (
        f"Осталось {format_quantity(product.quantity)} {unit}"
        f" · минимум {format_quantity(product.min_quantity)} {unit}"
    )


class DashboardScreen(tk.Frame):
    """Приветствие, четыре счётчика, товары, требующие внимания, и новые товары."""

    def __init__(self, master: tk.Misc, shell: "MainShell") -> None:
        pal = palette()
        super().__init__(master, bg=pal.bg)
        self._shell = shell
        self._services = shell.services
        self._user = shell.user
        summary = self._services.dashboard.summary(self._user.id)
        self._build_header()
        self._build_subtitle()
        self._build_stats(summary)
        self._build_columns(summary)

    # --- верхняя часть ---

    def _build_header(self) -> None:
        text = f"{labels.greeting(datetime.now().hour)}, {self._user.username}!"
        header = PageHeader(self, text)
        header.pack(fill="x")
        Button(
            header.actions,
            "Добавить товар",
            command=lambda: self._shell.navigate(sections.MY_KIT),
            variant="primary",
            icon="plus",
        ).pack()

    def _build_subtitle(self) -> None:
        pal = palette()
        today = format_user_date(date.today())
        tk.Label(
            self,
            text=f"Вот краткая информация о ваших запасах на {today}",
            bg=pal.bg,
            fg=pal.ink_2,
            font=font_spec("lead", self),
            padx=0,
        ).pack(anchor="w", padx=CARD_SHADOW_PAD, pady=(8, 16))

    def _build_stats(self, summary: DashboardSummary) -> None:
        pal = palette()
        row = tk.Frame(self, bg=pal.bg)
        row.pack(fill="x")
        shell = self._shell
        stats = (
            ("cross", "primary", summary.total, "Товаров в аптечке", shell.open_kit),
            (
                "alert",
                "amber",
                summary.attention_total,
                "Требуют внимания",
                lambda: shell.navigate(sections.NOTIFICATIONS),
            ),
            (
                "x",
                "red",
                summary.expired,
                "Просрочено",
                lambda: shell.open_kit(ProductStatus.EXPIRED),
            ),
            (
                "cart",
                "green",
                summary.shopping_open,
                "В списке покупок",
                lambda: shell.open_shopping(OPEN_TAB),
            ),
        )
        for column, (icon, tone, value, caption, command) in enumerate(stats):
            row.columnconfigure(column, weight=1, uniform="stat")
            card = Card(row)
            card.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else STAT_GAP, 0),
            )
            self._fill_stat(card, icon, tone, value, caption)
            _make_clickable(card, command)

    def _fill_stat(
        self, card: Card, icon: str, tone: str, value: int, caption: str
    ) -> None:
        pal = palette()
        inset = card.inner_inset
        inner = tk.Frame(card.body, bg=pal.card)
        inner.pack(fill="x", padx=16 - inset, pady=14 - inset)
        IconBox(inner, icon, tone).pack(side="left", padx=(0, 12))
        texts = tk.Frame(inner, bg=pal.card)
        texts.pack(side="left")
        tk.Label(
            texts,
            text=str(value),
            bg=pal.card,
            fg=pal.ink,
            font=font_spec("number", self),
            padx=0,
            pady=0,
        ).pack(anchor="w")
        tk.Label(
            texts,
            text=caption,
            bg=pal.card,
            fg=pal.ink_2,
            font=font_spec("small", self),
            padx=0,
            pady=0,
        ).pack(anchor="w")

    # --- два списка ---

    def _build_columns(self, summary: DashboardSummary) -> None:
        pal = palette()
        columns = tk.Frame(self, bg=pal.bg)
        columns.pack(fill="x", pady=(16 - 2 * CARD_SHADOW_PAD, 0))
        columns.columnconfigure(0, weight=LEFT_WEIGHT, uniform="column")
        columns.columnconfigure(1, weight=RIGHT_WEIGHT, uniform="column")
        left = self._list_card(
            columns,
            "Требуют внимания",
            "Все уведомления",
            lambda: self._shell.navigate(sections.NOTIFICATIONS),
        )
        left.grid(row=0, column=0, sticky="new")
        right = self._list_card(
            columns,
            "Последние добавленные",
            "Вся аптечка",
            lambda: self._shell.navigate(sections.MY_KIT),
        )
        right.grid(row=0, column=1, sticky="new", padx=(COLUMN_GAP, 0))
        self._fill_attention(left, summary.attention)
        self._fill_recent(right, summary.recent_products)

    def _list_card(
        self, master: tk.Misc, title: str, link: str, command: Callable[[], None]
    ) -> Card:
        """Карточка со строкой заголовка и ссылкой справа."""
        pal = palette()
        card = Card(master)
        head = tk.Frame(card.body, bg=pal.card)
        head.pack(fill="x", padx=ROW_PADDING_X - card.inner_inset, pady=(10, 10))
        tk.Label(
            head,
            text=title,
            bg=pal.card,
            fg=pal.ink,
            font=font_spec("section", self),
            padx=0,
        ).pack(side="left")
        Link(head, link, command, icon="arrow-right").pack(side="right")
        self._divider(card.body)
        return card

    def _divider(self, master: tk.Misc) -> None:
        tk.Frame(master, bg=palette().line_soft, height=1).pack(fill="x")

    def _row(self, card: Card) -> tk.Frame:
        """Строка списка внутри карточки с отступами макета."""
        row = tk.Frame(card.body, bg=palette().card)
        row.pack(
            fill="x",
            padx=ROW_PADDING_X - card.inner_inset - SHADOW_PAD,
            pady=ROW_PADDING_Y,
        )
        return row

    def _fill_attention(self, card: Card, views: List[ProductView]) -> None:
        pal = palette()
        if not views:
            tk.Label(
                card.body,
                text="Всё в порядке: срочных дел нет",
                bg=pal.card,
                fg=pal.ink_3,
                font=font_spec("body", self),
            ).pack(pady=40)
            return
        for index, view in enumerate(views):
            if index:
                self._divider(card.body)
            self._attention_row(card, view)

    def _attention_row(self, card: Card, view: ProductView) -> None:
        pal = palette()
        status = view.primary_status
        row = self._row(card)
        IconBox(
            row, labels.STATUS_ICONS[status], labels.STATUS_TONES[status], "sm"
        ).pack(side="left", padx=(SHADOW_PAD, 12))
        texts = tk.Frame(row, bg=pal.card)
        texts.pack(side="left", fill="x", expand=True)
        self._product_link(texts, view).pack(anchor="w")
        tk.Label(
            texts,
            text=_detail(view),
            bg=pal.card,
            fg=pal.ink_2,
            font=font_spec("small", self),
            padx=0,
            pady=0,
        ).pack(anchor="w")
        product_id = view.product.id
        if self._services.shopping.is_in_list(self._user.id, product_id):
            action = Button(row, "В списке", size="sm", icon="check")
            action.set_enabled(False)
        else:
            action = Button(
                row,
                "В список",
                size="sm",
                command=lambda: self._add_to_list(product_id),
            )
        action.pack(side="right")
        Badge(row, status.label, labels.STATUS_TONES[status]).pack(
            side="right", padx=(0, 12)
        )

    def _fill_recent(self, card: Card, views: List[ProductView]) -> None:
        pal = palette()
        if not views:
            tk.Label(
                card.body,
                text="Товаров пока нет",
                bg=pal.card,
                fg=pal.ink_3,
                font=font_spec("body", self),
            ).pack(pady=40)
            return
        for index, view in enumerate(views):
            if index:
                self._divider(card.body)
            row = self._row(card)
            product = view.product
            added = format_user_date(
                datetime.strptime(product.created_at[:10], "%Y-%m-%d").date()
            )
            self._product_link(row, view).pack(anchor="w", padx=SHADOW_PAD)
            tk.Label(
                row,
                text=f"{labels.short_category(product.category_name)} · {added}",
                bg=pal.card,
                fg=pal.ink_2,
                font=font_spec("small", self),
                padx=0,
                pady=0,
            ).pack(anchor="w", padx=SHADOW_PAD)

    def _product_link(self, master: tk.Misc, view: ProductView) -> Link:
        """Название товара, по нажатию на которое открывается его карточка."""
        product_id = view.product.id
        return Link(
            master,
            view.product.name,
            lambda: self._shell.open_product(product_id),
            style="strong",
        )

    def _add_to_list(self, product_id: int) -> None:
        """Добавляет товар в список покупок и обновляет экран."""
        self._services.shopping.add_from_product(self._user.id, product_id)
        self._shell.navigate(sections.HOME)
