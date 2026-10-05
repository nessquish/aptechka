"""Экран «Список покупок» (макет Figma, экраны 09 и 10)."""

import tkinter as tk
from datetime import datetime
from typing import TYPE_CHECKING, List, Set

from pharmacy.errors import ValidationError
from pharmacy.models import ShoppingItem, ShoppingSource
from pharmacy.services.product_service import UNITS
from pharmacy.ui.theme import CARD_SHADOW_PAD, SHADOW_PAD, palette
from pharmacy.ui.widgets.actionbar import ActionBar
from pharmacy.ui.widgets.badge import Badge
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.combo import ComboField
from pharmacy.ui.widgets.controls import Checkbox, Segmented
from pharmacy.ui.widgets.dialog import Modal
from pharmacy.ui.widgets.field import TextField
from pharmacy.ui.widgets.page import PageHeader
from pharmacy.ui.widgets.select import Select
from pharmacy.ui.widgets.table import Column, DataTable, TextCell
from pharmacy.utils.dates import format_user_date
from pharmacy.utils.formatting import format_quantity

if TYPE_CHECKING:
    from pharmacy.ui.screens.shell import MainShell

FILTERS = (None, False, True)  # все, не куплено, куплено
SOURCE_LABELS = {
    ShoppingSource.NOTIFICATION: "Уведомление",
    ShoppingSource.MANUAL: "Вручную",
}
COLUMNS = (
    Column("", fixed=44),
    Column("Товар", 28),
    Column("Количество", 16),
    Column("Источник", 16),
    Column("Статус", 16),
    Column("Дата добавления", 20),
)
EMPTY_TEXT = "Список покупок пуст. Добавьте товар вручную или из уведомления."
DIALOG_WIDTH = 440
DEFAULT_UNIT = "шт."


def _created(item: ShoppingItem) -> str:
    """Дата добавления позиции в формате ДД.ММ.ГГГГ."""
    return format_user_date(datetime.strptime(item.created_at[:10], "%Y-%m-%d").date())


class ShoppingScreen(tk.Frame):
    """Таблица позиций с фильтрами-вкладками, выбором строк и действиями над ними."""

    def __init__(self, master: tk.Misc, shell: "MainShell", tab: int = 0) -> None:
        """Создаёт экран.

        Args:
            master: Родительский виджет.
            shell: Оболочка главного окна.
            tab: Выбранная вкладка: 0 все, 1 не куплено, 2 куплено.
        """
        pal = palette()
        super().__init__(master, bg=pal.bg)
        self._shell = shell
        self._services = shell.services
        self._user = shell.user
        self._filter = tab
        self._selected: Set[int] = set()
        self._visible: List[ShoppingItem] = []
        header = PageHeader(self, "Список покупок")
        header.pack(fill="x")
        self._tabs = Segmented(
            header.actions,
            self._tab_labels(),
            self._filter,
            self._on_tab,
        )
        self._tabs.pack(side="left", padx=(0, 10))
        Button(
            header.actions,
            "Добавить вручную",
            command=self._open_add_dialog,
            variant="primary",
            icon="plus",
        ).pack(side="left")
        self._build_table()
        self._reload()

    # --- построение ---

    def _build_table(self) -> None:
        pal = palette()
        card = Card(self, flush=True)
        card.pack(fill="x", pady=(18 - CARD_SHADOW_PAD - SHADOW_PAD, 0))
        self._bar = ActionBar(card.body, card)
        Button(
            self._bar.buttons,
            "Отметить как купленные",
            command=self._mark_bought,
            variant="primary",
            size="sm",
            icon="check",
        ).pack(side="left", padx=(0, 4))
        Button(
            self._bar.buttons,
            "Удалить из списка",
            command=self._remove_selected,
            variant="danger",
            size="sm",
        ).pack(side="left")
        self._table = DataTable(card.body, COLUMNS, card)
        self._table.pack(fill="x")
        self._select_all = self._table.set_header_widget(
            0,
            lambda parent: Checkbox(
                parent, False, self._toggle_all, background=pal.table_head
            ),
        )

    def _tab_labels(self) -> List[str]:
        items = self._services.shopping.list_items(self._user.id)
        bought = sum(1 for item in items if item.is_bought)
        return [
            f"Все · {len(items)}",
            f"Не куплено · {len(items) - bought}",
            f"Куплено · {bought}",
        ]

    # --- данные ---

    def _reload(self) -> None:
        """Заново читает список и перерисовывает вкладки, панель и таблицу."""
        self._visible = self._services.shopping.list_items(
            self._user.id, FILTERS[self._filter]
        )
        known = {item.id for item in self._visible}
        self._selected &= known
        self._tabs.set_items(self._tab_labels())
        self._table.clear()
        if not self._visible:
            self._table.add_message(EMPTY_TEXT)
        for item in self._visible:
            self._table.add_row(self._cells(item), item.id in self._selected)
        self._update_bar()

    def _cells(self, item: ShoppingItem) -> List:
        bought = item.is_bought
        muted = "ink_3" if bought else "ink_2"
        linked = item.product_id is not None and not bought
        name = TextCell(
            item.name,
            "ink_3" if bought else ("primary" if linked else "ink"),
            bold=True,
            strike=bought,
            on_click=(
                (lambda p=item.product_id: self._shell.open_product(p))
                if linked
                else None
            ),
        )
        return [
            lambda parent: Checkbox(
                parent,
                item.id in self._selected,
                lambda value, i=item.id: self._toggle(i, value),
            ),
            name,
            TextCell(f"{format_quantity(item.quantity)} {item.unit}", muted),
            TextCell(SOURCE_LABELS[item.source], muted),
            lambda parent: Badge(
                parent,
                "Куплено" if bought else "Не куплено",
                "green" if bought else "red",
            ),
            TextCell(_created(item), muted),
        ]

    def _update_bar(self) -> None:
        """Показывает панель действий, пока выбрана хотя бы одна строка."""
        count = len(self._selected)
        # Сначала шапка таблицы отдаёт верхнюю полосу карточки, потом панель
        # занимает её (или шапка забирает обратно, когда панель скрыта).
        self._table.set_rounded_top(not count)
        if count:
            self._bar.show(f"Выбрано: {count}", before=self._table)
        else:
            self._bar.hide()
        everything = bool(self._visible) and count == len(self._visible)
        self._select_all.set(everything)

    # --- события ---

    def _on_tab(self, index: int) -> None:
        self._filter = index
        self._selected.clear()
        self._reload()

    def _toggle(self, item_id: int, value: bool) -> None:
        if value:
            self._selected.add(item_id)
        else:
            self._selected.discard(item_id)
        self._reload()

    def _toggle_all(self, value: bool) -> None:
        self._selected = {item.id for item in self._visible} if value else set()
        self._reload()

    def _mark_bought(self) -> None:
        for item_id in sorted(self._selected):
            self._services.shopping.set_bought(self._user.id, item_id, True)
        self._selected.clear()
        self._reload()

    def _remove_selected(self) -> None:
        for item_id in sorted(self._selected):
            self._services.shopping.remove(self._user.id, item_id)
        self._selected.clear()
        self._reload()

    def _open_add_dialog(self) -> None:
        AddItemDialog(self._shell.app, self._services, self._user.id, self._reload)


class AddItemDialog(Modal):
    """Окно «Добавить в список покупок»: название, количество и единица."""

    def __init__(self, host: tk.Misc, services, user_id: int, on_added) -> None:
        """Открывает окно.

        Args:
            host: Окно приложения.
            services: Сервисы приложения.
            user_id: Владелец списка.
            on_added: Вызывается после добавления позиции.
        """
        super().__init__(host, DIALOG_WIDTH, on_enter=self._submit)
        pal = palette()
        self._services = services
        self._user_id = user_id
        self._on_added = on_added
        self.add_title("Добавить в список покупок")
        self.add_text("Выберите товар из аптечки или введите новое название", bottom=16)
        names = [v.product.name for v in services.products.list_products(user_id)]
        self.name = ComboField(
            self.body, names, "Название товара", "Введите название", required=True
        )
        self.name.pack(fill="x", pady=(0, 8))
        row = tk.Frame(self.body, bg=pal.card)
        row.pack(fill="x")
        row.columnconfigure(0, weight=1, uniform="add")
        row.columnconfigure(1, weight=1, uniform="add")
        self.quantity = TextField(row, "Количество", required=True)
        self.quantity.set("1")
        self.quantity.grid(row=0, column=0, sticky="new")
        self.unit = Select(row, UNITS, DEFAULT_UNIT, label="Единица измерения")
        self.unit.grid(row=0, column=1, sticky="new")
        buttons = self.footer()
        Button(buttons, "Отмена", command=self.close).pack(side="left", padx=(0, 4))
        Button(buttons, "Добавить", command=self._submit, variant="primary").pack(
            side="left"
        )
        self.name.focus_field()

    def _submit(self) -> None:
        for field in (self.name, self.quantity, self.unit):
            field.clear_error()
        try:
            self._services.shopping.add_manual(
                self._user_id,
                self.name.get(),
                self.quantity.get(),
                self.unit.get() or DEFAULT_UNIT,
            )
        except ValidationError as error:
            target = {"name": self.name, "quantity": self.quantity}.get(
                error.field or ""
            )
            if target is not None:
                target.set_error(error.message)
            return
        self.close()
        self._on_added()
