"""Форма товара: добавление и редактирование (макет Figma, экраны 05 и 07)."""

from typing import TYPE_CHECKING, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from pharmacy.errors import NotFoundError, ValidationError
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.common import Line, label
from pharmacy.ui.widgets.field import TextField
from pharmacy.ui.widgets.link import Link
from pharmacy.ui.widgets.page import PageHeader
from pharmacy.ui.widgets.select import Select
from pharmacy.services.product_service import UNITS, ProductForm, ProductView
from pharmacy.ui import sections
from pharmacy.ui.theme import CARD_SHADOW_PAD, SHADOW_PAD
from pharmacy.utils.dates import format_user_date
from pharmacy.utils.formatting import format_quantity

if TYPE_CHECKING:
    from pharmacy.ui.screens.shell import MainShell

CARD_WIDTH = 760 + 2 * CARD_SHADOW_PAD
PADDING_X = 24
PADDING_Y = 22
COLUMN_GAP = 18
ROW_GAP = 14


class ProductFormScreen(QWidget):
    """Форма добавления товара или редактирования уже существующего."""

    def __init__(self, shell: "MainShell", product_id: Optional[int] = None) -> None:
        """Создаёт форму.

        Args:
            shell: Оболочка главного окна.
            product_id: Редактируемый товар или None для нового.
        """
        super().__init__()
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())
        layout.addSpacing(18 - CARD_SHADOW_PAD)
        layout.addWidget(self._build_card(), 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        if self._existing is not None:
            self._fill(self._existing)

    @property
    def editing(self) -> bool:
        """Редактируется существующий товар."""
        return self._existing is not None

    @property
    def fields(self) -> Dict[str, object]:
        """Поля формы по именам из ``ProductForm``."""
        return self._fields

    # --- построение ---

    def _build_header(self) -> PageHeader:
        title = "Редактирование товара" if self.editing else "Добавить товар"
        back_text = "Назад к карточке" if self.editing else "Назад к списку"
        header = PageHeader(title)
        header.actions.addWidget(
            Link(
                back_text,
                self._go_back,
                style="lead_medium",
                icon="arrow-left",
                icon_side="left",
            )
        )
        header.actions.addSpacing(4)
        return header

    def _build_card(self) -> Card:
        card = Card()
        card.setFixedWidth(CARD_WIDTH)
        inset = card.inner_inset
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(
            PADDING_X - inset - SHADOW_PAD,
            PADDING_Y - inset - SHADOW_PAD,
            PADDING_X - inset - SHADOW_PAD,
            ROW_GAP - SHADOW_PAD - 2,
        )
        grid.setHorizontalSpacing(COLUMN_GAP - 2 * SHADOW_PAD)
        grid.setVerticalSpacing(ROW_GAP - SHADOW_PAD - 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self._add_fields(grid)
        card.body.addWidget(body)
        self._build_footer(card, inset)
        return card

    def _add_fields(self, grid: QGridLayout) -> None:
        categories = [(c.id, c.name) for c in self._services.products.list_categories()]
        change = self._refresh_save

        def text(title: str, **options) -> TextField:
            return TextField(title, on_change=change, **options)

        specs = (
            ("name", text("Название", placeholder="Введите название", required=True)),
            (
                "category_id",
                Select(
                    categories,
                    categories[0][0] if categories else None,
                    label_text="Категория",
                    required=True,
                    on_change=lambda _value: change(),
                ),
            ),
            ("quantity", text("Количество", placeholder="0", required=True)),
            (
                "unit",
                Select(
                    UNITS,
                    UNITS[0],
                    label_text="Единица измерения",
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
            span = 1
            if key == "note":
                row, col, span = 4, 0, 2
            grid.addWidget(widget, row, col, 1, span, Qt.AlignmentFlag.AlignTop)
            self._fields[key] = widget

    def _build_footer(self, card: Card, inset: int) -> None:
        rule = QHBoxLayout()
        rule.setContentsMargins(
            PADDING_X - inset, 20 - SHADOW_PAD, PADDING_X - inset, 0
        )
        rule.addWidget(Line("line"))
        card.body.addLayout(rule)
        row = QHBoxLayout()
        side = PADDING_X - inset - SHADOW_PAD
        row.setContentsMargins(side, 12, side, 12)
        row.setSpacing(0)
        row.addSpacing(SHADOW_PAD)
        row.addWidget(label("*", "label", "red"))
        row.addWidget(label(" — обязательные поля", "label", "ink_3"))
        row.addStretch(1)
        self.cancel_button = Button("Отмена", self._go_back)
        self._save = Button(
            "Сохранить изменения" if self.editing else "Сохранить",
            command=self._submit,
            variant="primary",
        )
        row.addWidget(self.cancel_button)
        row.addWidget(self._save)
        card.body.addLayout(row)

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

    @property
    def save_button(self) -> Button:
        """Кнопка «Сохранить»."""
        return self._save

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
