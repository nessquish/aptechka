"""Карточка товара (макет Figma, экраны 06 и 08): просмотр и действия над товаром."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from pharmacy.errors import NotFoundError, ValidationError
from pharmacy.ui.widgets.badge import Badge
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.common import Line, label, pad
from pharmacy.ui.widgets.dialog import Dialog
from pharmacy.ui.widgets.iconbox import IconBox
from pharmacy.ui.widgets.link import Link
from pharmacy.ui.widgets.page import PageHeader
from pharmacy.services.product_service import ProductView
from pharmacy.services.status import ProductStatus
from pharmacy.ui import labels, sections
from pharmacy.ui.theme import CARD_SHADOW_PAD, SHADOW_PAD
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
WIDE_FIELDS = {"Показания / назначение", "Примечание"}


def _days_phrase(days: int) -> str:
    """Подпись рядом со сроком: «через 19 дней» или «просрочено на 3 дня»."""
    if days < 0:
        count = -days
        return f"просрочено на {count} {plural(count, 'день', 'дня', 'дней')}"
    if days == 0:
        return "истекает сегодня"
    return f"через {days} {plural(days, 'день', 'дня', 'дней')}"


def _box(parent: QWidget, margins: Tuple[int, int, int, int]) -> QVBoxLayout:
    layout = QVBoxLayout(parent)
    layout.setContentsMargins(*margins)
    layout.setSpacing(0)
    return layout


class ProductCardScreen(QWidget):
    """Подробные данные о товаре и действия над ним."""

    def __init__(self, shell: "MainShell", product_id: int) -> None:
        super().__init__()
        self._shell = shell
        self._services = shell.services
        self._user = shell.user
        self._product_id = product_id
        self._view: ProductView = self._services.products.get_product(
            self._user.id, product_id
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = PageHeader("Карточка товара")
        header.actions.addWidget(
            Link(
                "Назад к списку",
                lambda: shell.navigate(sections.MY_KIT),
                style="lead_medium",
                icon="arrow-left",
                icon_side="left",
            )
        )
        header.actions.addSpacing(4)
        layout.addWidget(header)
        layout.addSpacing(18 - CARD_SHADOW_PAD)
        self.card = self._build_card()
        layout.addWidget(self.card, 0, Qt.AlignmentFlag.AlignLeft)
        note = label(DISCLAIMER, "label", "ink_3")
        pad(note, CARD_SHADOW_PAD, 10 - CARD_SHADOW_PAD, 0, 0)
        layout.addWidget(note)
        layout.addStretch(1)

    # --- построение ---

    def _build_card(self) -> Card:
        card = Card()
        card.setFixedWidth(CARD_WIDTH)
        inset = card.inner_inset
        card.body.addWidget(self._build_head(inset))
        card.body.addWidget(Line("line"))
        card.body.addWidget(self._build_details(inset))
        card.body.addWidget(Line("line"))
        card.body.addWidget(self._build_actions(inset))
        return card

    def _build_head(self, inset: int) -> QWidget:
        product = self._view.product
        head = QWidget()
        row = QHBoxLayout(head)
        row.setContentsMargins(PADDING_X - inset, 18 - inset, PADDING_X - inset, 18)
        row.setSpacing(0)
        row.addWidget(IconBox("cross", "primary"))
        row.addSpacing(12)
        names = QVBoxLayout()
        names.setContentsMargins(0, 0, 0, 0)
        names.setSpacing(0)
        names.addWidget(label(product.name, "product_title", tight=True))
        added = datetime.strptime(product.created_at[:10], "%Y-%m-%d").date()
        names.addSpacing(2)
        names.addWidget(
            label(
                f"{product.category_name} · добавлен {format_user_date(added)}",
                "small",
                "ink_3",
                tight=True,
            )
        )
        row.addLayout(names)
        row.addStretch(1)
        for status in self._view.statuses:
            row.addSpacing(6)
            row.addWidget(Badge(status.label, labels.STATUS_TONES[status]))
        return head

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

    def _build_details(self, inset: int) -> QWidget:
        host = QWidget()
        grid = QGridLayout(host)
        grid.setContentsMargins(PADDING_X - inset, 2, PADDING_X - inset, 2)
        grid.setSpacing(0)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        row = column = 0
        for title, value, color in self._details():
            cell = self._detail_cell(title, value, color)
            if title in WIDE_FIELDS:
                if column:
                    row, column = row + 1, 0
                grid.addWidget(cell, row, 0, 1, 2)
                row += 1
            else:
                if column == 0:
                    cell.layout().setContentsMargins(0, 0, COLUMN_GAP, 0)
                grid.addWidget(cell, row, column)
                column += 1
                if column == 2:
                    row, column = row + 1, 0
        return host

    def _detail_cell(self, title: str, value: str, color: str) -> QWidget:
        cell = QWidget()
        outer = QVBoxLayout(cell)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        inner = QVBoxLayout()
        inner.setContentsMargins(0, 11, 0, 11)
        inner.setSpacing(0)
        inner.addWidget(label(title, "label", "ink_3", tight=True))
        inner.addSpacing(4)
        line = QHBoxLayout()
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(0)
        line.addWidget(
            label(value, "value", color, wrap=title in WIDE_FIELDS, tight=True)
        )
        if title == "Срок годности" and self._view.days_left is not None:
            tone = "red" if self._view.days_left < 0 else "amber"
            if ProductStatus.EXPIRED not in self._view.statuses and (
                ProductStatus.EXPIRING not in self._view.statuses
            ):
                tone = "ink_3"
            line.addWidget(
                label(
                    f" · {_days_phrase(self._view.days_left)}",
                    "small",
                    tone,
                    tight=True,
                )
            )
        line.addStretch(1)
        inner.addLayout(line)
        outer.addLayout(inner)
        outer.addWidget(Line("line_soft"))
        return cell

    def _build_actions(self, inset: int) -> QWidget:
        host = QWidget()
        row = QHBoxLayout(host)
        side = PADDING_X - inset - SHADOW_PAD
        row.setContentsMargins(side, 10, side, 10)
        row.setSpacing(0)
        self.delete_button = Button(
            "Удалить", command=self._confirm_delete, variant="danger"
        )
        row.addWidget(self.delete_button)
        row.addStretch(1)
        if self._services.shopping.is_in_list(self._user.id, self._product_id):
            self.list_button = Button("В списке покупок", icon="check")
            self.list_button.set_enabled(False)
        else:
            self.list_button = Button("В список покупок", command=self._add_to_list)
        row.addWidget(self.list_button)
        self.edit_button = Button(
            "Редактировать",
            command=lambda: self._shell.open_product_form(self._product_id),
            variant="primary",
        )
        row.addWidget(self.edit_button)
        return host

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
