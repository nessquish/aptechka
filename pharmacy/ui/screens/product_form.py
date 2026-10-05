"""Форма товара: добавление и редактирование (макет Figma, экраны 05 и 07)."""

import tkinter as tk
from typing import TYPE_CHECKING, Dict, Optional

from pharmacy.errors import NotFoundError, ValidationError
from pharmacy.services.product_service import UNITS, ProductForm, ProductView
from pharmacy.ui import sections
from pharmacy.ui.fonts import font_spec
from pharmacy.ui.theme import CARD_SHADOW_PAD, SHADOW_PAD, palette
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.field import TextField
from pharmacy.ui.widgets.link import Link
from pharmacy.ui.widgets.page import PageHeader
from pharmacy.ui.widgets.select import Select
from pharmacy.utils.dates import format_user_date
from pharmacy.utils.formatting import format_quantity

if TYPE_CHECKING:
    from pharmacy.ui.screens.shell import MainShell

CARD_WIDTH = 760 + 2 * CARD_SHADOW_PAD
PADDING_X = 24
PADDING_Y = 22
COLUMN_GAP = 18
ROW_GAP = 14


class ProductFormScreen(tk.Frame):
    """Форма добавления товара или редактирования уже существующего."""

    def __init__(
        self,
        master: tk.Misc,
        shell: "MainShell",
        product_id: Optional[int] = None,
    ) -> None:
        """Создаёт форму.

        Args:
            master: Родительский виджет.
            shell: Оболочка главного окна.
            product_id: Редактируемый товар или None для нового.
        """
        pal = palette()
        super().__init__(master, bg=pal.bg)
        self._shell = shell
        self._services = shell.services
        self._user = shell.user
        self._product_id = product_id
        self._existing: Optional[ProductView] = None
        if product_id is not None:
            self._existing = self._services.products.get_product(
                self._user.id, product_id
            )
        self._fields: Dict[str, object] = {}
        self._build_header()
        self._build_card()
        if self._existing is not None:
            self._fill(self._existing)

    @property
    def editing(self) -> bool:
        """Редактируется существующий товар."""
        return self._existing is not None

    # --- построение ---

    def _build_header(self) -> None:
        title = "Редактирование товара" if self.editing else "Добавить товар"
        back_text = "Назад к карточке" if self.editing else "Назад к списку"
        header = PageHeader(self, title)
        header.pack(fill="x")
        Link(
            header.actions,
            back_text,
            self._go_back,
            style="lead_medium",
            icon="arrow-left",
            icon_side="left",
        ).pack(padx=(0, 4))

    def _build_card(self) -> None:
        pal = palette()
        holder = tk.Frame(self, bg=pal.bg)
        holder.pack(fill="x", pady=(18 - CARD_SHADOW_PAD, 0))
        holder.columnconfigure(0, minsize=CARD_WIDTH)
        card = Card(holder)
        card.grid(row=0, column=0, sticky="new")
        inset = card.inner_inset
        body = tk.Frame(card.body, bg=pal.card)
        body.pack(
            fill="x",
            padx=PADDING_X - inset - SHADOW_PAD,
            pady=(PADDING_Y - inset - SHADOW_PAD, 0),
        )
        grid = tk.Frame(body, bg=pal.card)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1, uniform="field")
        grid.columnconfigure(1, weight=1, uniform="field")
        self._add_fields(grid)
        self._build_footer(card, inset)

    def _put(
        self, grid: tk.Frame, key: str, widget: tk.Misc, row: int, col: int
    ) -> None:
        span = 2 if key == "note" else 1
        widget.grid(
            row=row,
            column=col,
            columnspan=span,
            sticky="new",
            padx=(0, COLUMN_GAP - 2 * SHADOW_PAD) if col == 0 and span == 1 else 0,
            pady=(0, ROW_GAP - SHADOW_PAD - 2),
        )
        self._fields[key] = widget

    def _add_fields(self, grid: tk.Frame) -> None:
        categories = [(c.id, c.name) for c in self._services.products.list_categories()]
        change = self._refresh_save

        def text(label: str, **options) -> TextField:
            return TextField(grid, label, on_change=change, **options)

        specs = (
            ("name", text("Название", placeholder="Введите название", required=True)),
            (
                "category_id",
                Select(
                    grid,
                    categories,
                    categories[0][0] if categories else None,
                    label="Категория",
                    required=True,
                    on_change=lambda _value: change(),
                ),
            ),
            ("quantity", text("Количество", placeholder="0", required=True)),
            (
                "unit",
                Select(
                    grid,
                    UNITS,
                    UNITS[0],
                    label="Единица измерения",
                    required=True,
                    on_change=lambda _value: change(),
                ),
            ),
            (
                "expiry_date",
                text(
                    "Срок годности", placeholder="ДД.ММ.ГГГГ", trailing_icon="calendar"
                ),
            ),
            (
                "storage_place",
                text("Место хранения", placeholder="Например: шкаф, кухня"),
            ),
            (
                "min_quantity",
                text(
                    "Минимальный остаток",
                    placeholder="При меньшем количестве придёт уведомление",
                ),
            ),
            (
                "indications",
                text("Показания / назначение", placeholder="Например: жаропонижающее"),
            ),
            (
                "note",
                text("Примечание", placeholder="Введите примечание", multiline=True),
            ),
        )
        for index, (key, widget) in enumerate(specs):
            row, col = divmod(index, 2)
            if key == "note":
                row, col = 4, 0
            self._put(grid, key, widget, row, col)

    def _build_footer(self, card: Card, inset: int) -> None:
        pal = palette()
        tk.Frame(card.body, bg=pal.line, height=1).pack(
            fill="x", padx=PADDING_X - inset, pady=(20 - SHADOW_PAD, 0)
        )
        row = tk.Frame(card.body, bg=pal.card)
        row.pack(fill="x", padx=PADDING_X - inset - SHADOW_PAD, pady=(12, 12))
        note = tk.Frame(row, bg=pal.card)
        note.pack(side="left", padx=SHADOW_PAD)
        tk.Label(
            note,
            text="*",
            bg=pal.card,
            fg=pal.red,
            font=font_spec("label", self),
            padx=0,
        ).pack(side="left")
        tk.Label(
            note,
            text=" — обязательные поля",
            bg=pal.card,
            fg=pal.ink_3,
            font=font_spec("label", self),
            padx=0,
        ).pack(side="left")
        self._save = Button(
            row,
            "Сохранить изменения" if self.editing else "Сохранить",
            command=self._submit,
            variant="primary",
        )
        self._save.pack(side="right")
        Button(row, "Отмена", command=self._go_back).pack(side="right", padx=(0, 0))

    # --- данные ---

    def _fill(self, view: ProductView) -> None:
        product = view.product
        self._fields["name"].set(product.name)
        self._fields["category_id"].set(product.category_id)
        self._fields["quantity"].set(format_quantity(product.quantity))
        self._fields["unit"].set(product.unit)
        self._fields["expiry_date"].set(
            format_user_date(product.expiry_date) if product.expiry_date else ""
        )
        self._fields["storage_place"].set(product.storage_place)
        self._fields["min_quantity"].set(format_quantity(product.min_quantity))
        self._fields["indications"].set(product.indications)
        self._fields["note"].set(product.note)

    def read_form(self) -> ProductForm:
        """Собирает введённые значения в форму для сервиса."""
        values = {key: widget.get() for key, widget in self._fields.items()}
        return ProductForm(**values)

    def _refresh_save(self) -> None:
        """Кнопка недоступна, пока у какого-нибудь поля показана ошибка."""
        has_error = any(w.error is not None for w in self._fields.values())
        self._save.set_enabled(not has_error)

    def _submit(self) -> None:
        for widget in self._fields.values():
            widget.clear_error()
        try:
            form = self.read_form()
            if self.editing:
                view = self._services.products.update_product(
                    self._user.id, self._product_id, form
                )
                self._shell.open_product(view.product.id)
            else:
                self._services.products.add_product(self._user.id, form)
                self._shell.navigate(sections.MY_KIT)
        except ValidationError as error:
            field = self._fields.get(error.field or "")
            if field is not None:
                field.set_error(error.message)
            self._refresh_save()
        except NotFoundError:
            self._shell.navigate(sections.MY_KIT)

    def _go_back(self) -> None:
        if self.editing:
            self._shell.open_product(self._product_id)
        else:
            self._shell.navigate(sections.MY_KIT)
