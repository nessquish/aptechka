"""Карточка товара (макет Figma, экраны 06 и 08): просмотр и действия над товаром."""

import tkinter as tk
from datetime import datetime
from typing import TYPE_CHECKING, List, Tuple

from pharmacy.errors import NotFoundError, ValidationError
from pharmacy.services.product_service import ProductView
from pharmacy.services.status import ProductStatus
from pharmacy.ui import labels, sections
from pharmacy.ui.fonts import font_spec
from pharmacy.ui.theme import CARD_SHADOW_PAD, SHADOW_PAD, palette
from pharmacy.ui.widgets.badge import Badge
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.dialog import Dialog
from pharmacy.ui.widgets.iconbox import IconBox
from pharmacy.ui.widgets.link import Link
from pharmacy.ui.widgets.page import PageHeader
from pharmacy.utils.dates import format_user_date
from pharmacy.utils.formatting import format_quantity, plural

if TYPE_CHECKING:
    from pharmacy.ui.screens.shell import MainShell

CARD_WIDTH = 760 + 2 * CARD_SHADOW_PAD
PADDING_X = 22
COLUMN_GAP = 30
NO_DATA = "Нет данных"
DISCLAIMER = "Показания вносятся пользователем и не являются медицинской рекомендацией."
DELETE_TEXT = (
    "Товар будет удалён из аптечки вместе со связанными уведомлениями. "
    "Записи в истории останутся. Действие нельзя отменить."
)


def _days_phrase(days: int) -> str:
    """Подпись рядом со сроком: «через 19 дней» или «просрочено на 3 дня»."""
    if days < 0:
        count = -days
        return f"просрочено на {count} {plural(count, 'день', 'дня', 'дней')}"
    if days == 0:
        return "истекает сегодня"
    return f"через {days} {plural(days, 'день', 'дня', 'дней')}"


class ProductCardScreen(tk.Frame):
    """Подробные данные о товаре и действия над ним."""

    def __init__(self, master: tk.Misc, shell: "MainShell", product_id: int) -> None:
        pal = palette()
        super().__init__(master, bg=pal.bg)
        self._shell = shell
        self._services = shell.services
        self._user = shell.user
        self._product_id = product_id
        self._view: ProductView = self._services.products.get_product(
            self._user.id, product_id
        )
        header = PageHeader(self, "Карточка товара")
        header.pack(fill="x")
        Link(
            header.actions,
            "Назад к списку",
            lambda: shell.navigate(sections.MY_KIT),
            style="lead_medium",
            icon="arrow-left",
            icon_side="left",
        ).pack(padx=(0, 4))
        self._build_card()
        tk.Label(
            self,
            text=DISCLAIMER,
            bg=pal.bg,
            fg=pal.ink_3,
            font=font_spec("label", self),
            padx=0,
        ).pack(anchor="w", padx=CARD_SHADOW_PAD, pady=(10 - CARD_SHADOW_PAD, 0))

    # --- построение ---

    def _build_card(self) -> None:
        pal = palette()
        holder = tk.Frame(self, bg=pal.bg)
        holder.pack(fill="x", pady=(18 - CARD_SHADOW_PAD, 0))
        holder.columnconfigure(0, minsize=CARD_WIDTH)
        card = Card(holder)
        card.grid(row=0, column=0, sticky="new")
        inset = card.inner_inset
        self._build_head(card, inset)
        tk.Frame(card.body, bg=pal.line, height=1).pack(fill="x")
        self._build_details(card, inset)
        tk.Frame(card.body, bg=pal.line, height=1).pack(fill="x")
        self._build_actions(card, inset)

    def _build_head(self, card: Card, inset: int) -> None:
        pal = palette()
        product = self._view.product
        head = tk.Frame(card.body, bg=pal.card)
        head.pack(fill="x", padx=PADDING_X - inset, pady=(18 - inset, 18))
        IconBox(head, "cross", "primary").pack(side="left", padx=(0, 12))
        names = tk.Frame(head, bg=pal.card)
        names.pack(side="left")
        tk.Label(
            names,
            text=product.name,
            bg=pal.card,
            fg=pal.ink,
            font=font_spec("product_title", self),
            padx=0,
            pady=0,
        ).pack(anchor="w")
        added = datetime.strptime(product.created_at[:10], "%Y-%m-%d").date()
        tk.Label(
            names,
            text=f"{product.category_name} · добавлен {format_user_date(added)}",
            bg=pal.card,
            fg=pal.ink_3,
            font=font_spec("small", self),
            padx=0,
            pady=0,
        ).pack(anchor="w", pady=(2, 0))
        for status in reversed(self._view.statuses):
            Badge(head, status.label, labels.STATUS_TONES[status]).pack(
                side="right", padx=(6, 0)
            )

    def _details(self) -> List[Tuple[str, str, str]]:
        """Пары «название поля, значение, цвет значения» для таблицы данных."""
        product = self._view.product
        unit = product.unit
        expiry = NO_DATA
        if product.expiry_date is not None:
            expiry = format_user_date(product.expiry_date)
        return [
            ("Количество", f"{format_quantity(product.quantity)} {unit}", "ink"),
            (
                "Минимальный остаток",
                f"{format_quantity(product.min_quantity)} {unit}",
                "ink",
            ),
            ("Срок годности", expiry, "ink" if product.expiry_date else "ink_3"),
            ("Место хранения", product.storage_place or NO_DATA, "ink"),
            ("Показания / назначение", product.indications or NO_DATA, "ink"),
            ("Примечание", product.note or NO_DATA, "ink"),
        ]

    def _build_details(self, card: Card, inset: int) -> None:
        pal = palette()
        grid = tk.Frame(card.body, bg=pal.card)
        grid.pack(fill="x", padx=PADDING_X - inset, pady=(2, 2))
        grid.columnconfigure(0, weight=1, uniform="detail")
        grid.columnconfigure(1, weight=1, uniform="detail")
        wide = {"Показания / назначение", "Примечание"}
        row = column = 0
        for title, value, color in self._details():
            cell = tk.Frame(grid, bg=pal.card)
            if title in wide:
                if column:
                    row, column = row + 1, 0
                cell.grid(row=row, column=0, columnspan=2, sticky="ew")
                row += 1
            else:
                padx = (0, COLUMN_GAP) if column == 0 else (0, 0)
                cell.grid(row=row, column=column, sticky="ew", padx=padx)
                column += 1
                if column == 2:
                    row, column = row + 1, 0
            self._fill_cell(cell, title, value, color)

    def _fill_cell(self, cell: tk.Frame, title: str, value: str, color: str) -> None:
        pal = palette()
        colors = {"ink": pal.ink, "ink_3": pal.ink_3}
        inner = tk.Frame(cell, bg=pal.card)
        inner.pack(fill="x", pady=11)
        tk.Label(
            inner,
            text=title,
            bg=pal.card,
            fg=pal.ink_3,
            font=font_spec("label", self),
            padx=0,
            pady=0,
        ).pack(anchor="w", pady=(0, 4))
        line = tk.Frame(inner, bg=pal.card)
        line.pack(anchor="w")
        tk.Label(
            line,
            text=value,
            bg=pal.card,
            fg=colors[color],
            font=font_spec("value", self),
            padx=0,
            pady=0,
        ).pack(side="left")
        if title == "Срок годности" and self._view.days_left is not None:
            tone = pal.red if self._view.days_left < 0 else pal.amber
            if ProductStatus.EXPIRED not in self._view.statuses and (
                ProductStatus.EXPIRING not in self._view.statuses
            ):
                tone = pal.ink_3
            tk.Label(
                line,
                text=f" · {_days_phrase(self._view.days_left)}",
                bg=pal.card,
                fg=tone,
                font=font_spec("small", self),
                padx=0,
                pady=0,
            ).pack(side="left")
        tk.Frame(cell, bg=pal.line_soft, height=1).pack(fill="x")

    def _build_actions(self, card: Card, inset: int) -> None:
        pal = palette()
        row = tk.Frame(card.body, bg=pal.card)
        row.pack(fill="x", padx=PADDING_X - inset - SHADOW_PAD, pady=(10, 10))
        Button(row, "Удалить", command=self._confirm_delete, variant="danger").pack(
            side="left"
        )
        Button(
            row,
            "Редактировать",
            command=lambda: self._shell.open_product_form(self._product_id),
            variant="primary",
        ).pack(side="right")
        if self._services.shopping.is_in_list(self._user.id, self._product_id):
            listed = Button(row, "В списке покупок", icon="check")
            listed.set_enabled(False)
        else:
            listed = Button(row, "В список покупок", command=self._add_to_list)
        listed.pack(side="right")

    # --- действия ---

    def _add_to_list(self) -> None:
        try:
            self._services.shopping.add_from_product(self._user.id, self._product_id)
        except (NotFoundError, ValidationError):
            pass
        self._shell.open_product(self._product_id)

    def _confirm_delete(self) -> None:
        Dialog(
            self._shell.app,
            f"Удалить товар «{self._view.product.name}»?",
            DELETE_TEXT,
            "Удалить",
            self._delete,
            confirm_variant="danger_solid",
            warning=True,
        )

    def _delete(self) -> None:
        try:
            self._services.products.delete_product(self._user.id, self._product_id)
        except NotFoundError:
            pass
        self._shell.navigate(sections.MY_KIT)
