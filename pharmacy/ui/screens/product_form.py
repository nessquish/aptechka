"""Форма товара: окно добавления и экран редактирования (макет Figma, 05 и 07)."""

from datetime import date
from typing import TYPE_CHECKING, Callable, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from pharmacy.errors import NotFoundError, ValidationError
from pharmacy.services.container import Services
from pharmacy.services.product_service import ProductForm, ProductView
from pharmacy.ui import sections
from pharmacy.ui.theme import CARD_SHADOW_PAD, SHADOW_PAD
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.common import Line, label
from pharmacy.ui.widgets.dialog import Modal
from pharmacy.ui.widgets.field import TextField
from pharmacy.ui.widgets.link import Link
from pharmacy.ui.widgets.page import PageHeader
from pharmacy.ui.widgets.select import Select
from pharmacy.utils.dates import format_user_date
from pharmacy.utils.formatting import format_quantity
from pharmacy.utils.units import DEFAULT_UNIT, UNITS

if TYPE_CHECKING:
    from pharmacy.ui.screens.shell import MainShell

CARD_WIDTH = 760 + 2 * CARD_SHADOW_PAD
PADDING_X = 24
PADDING_Y = 22
COLUMN_GAP = 18
ROW_GAP = 14
DIALOG_WIDTH = 720
DIALOG_COLUMNS = 3
ADD_TITLE = "Добавить товар в аптечку"


def make_fields(services: Services, change: Callable[[], None]) -> Dict[str, QWidget]:
    """Создаёт поля формы товара в том порядке, в котором они стоят на экране.

    Args:
        services: Сервисы приложения (нужны категории).
        change: Вызывается после каждой правки пользователем.

    Returns:
        Поля по именам из ``ProductForm``.
    """
    categories = [(c.id, c.name) for c in services.products.list_categories()]

    def text(title: str, **options) -> TextField:
        return TextField(title, on_change=change, **options)

    fields: Dict[str, QWidget] = {}

    def unit_picked(_value: object) -> None:
        show_units(fields)
        change()

    fields.update(
        {
            "name": text("Название", placeholder="Введите название", required=True),
            "category_id": Select(
                categories,
                categories[0][0] if categories else None,
                label_text="Категория",
                required=True,
                on_change=lambda _value: change(),
            ),
            "quantity": text("Количество", placeholder="0", required=True),
            "unit": Select(
                UNITS,
                DEFAULT_UNIT,
                label_text="Единица измерения",
                required=True,
                on_change=unit_picked,
            ),
            "expiry_date": text(
                "Срок годности", placeholder="ДД.ММ.ГГГГ", trailing_icon="calendar"
            ),
            "storage_place": text(
                "Место хранения", placeholder="Например: шкаф, кухня"
            ),
            "min_quantity": text(
                "Минимальный остаток",
                placeholder="При меньшем количестве придёт уведомление",
            ),
            "indications": text(
                "Показания / назначение", placeholder="Например: жаропонижающее"
            ),
            "note": text(
                "Примечание", placeholder="Введите примечание", multiline=True
            ),
        }
    )
    show_units(fields)
    return fields


def show_units(fields: Dict[str, QWidget]) -> None:
    """Дописывает выбранную единицу к подписям «Количество» и «Минимальный остаток».

    Так рядом с числом всегда видно, в чём оно измеряется.
    """
    unit = fields["unit"].get() or DEFAULT_UNIT
    fields["quantity"].set_title(f"Количество ({unit})")
    fields["min_quantity"].set_title(f"Минимальный остаток ({unit})")


def read_form(fields: Dict[str, QWidget]) -> ProductForm:
    """Собирает введённые значения в форму для сервиса."""
    return ProductForm(**{key: widget.get() for key, widget in fields.items()})


def show_error(fields: Dict[str, QWidget], error: ValidationError) -> None:
    """Подсвечивает поле, к которому относится ошибка проверки."""
    field = fields.get(error.field or "")
    if field is not None:
        field.set_error(error.message)


def has_error(fields: Dict[str, QWidget]) -> bool:
    """Подсвечено ли ошибкой хотя бы одно поле."""
    return any(widget.error is not None for widget in fields.values())


class ProductFormDialog(Modal):
    """Окно «Добавить товар в аптечку»: открывается поверх текущего экрана.

    Attributes:
        fields: Поля формы по именам из ``ProductForm``.
        added_field: Дата добавления (только показывается, ставится сама).
    """

    def __init__(
        self,
        host: QWidget,
        services: Services,
        user_id: int,
        on_saved: Callable[[], None],
    ) -> None:
        """Открывает окно.

        Args:
            host: Окно приложения.
            services: Сервисы приложения.
            user_id: Владелец аптечки.
            on_saved: Вызывается после сохранения (окно к этому моменту закрыто).
        """
        super().__init__(host, DIALOG_WIDTH, on_enter=self._submit)
        self._services = services
        self._user_id = user_id
        self._on_saved = on_saved
        self.add_title(ADD_TITLE)
        self.fields = make_fields(services, self._refresh_save)
        self.added_field = TextField(
            "Дата добавления",
            readonly=True,
            trailing_icon="calendar",
        )
        self.added_field.set(format_user_date(date.today()))
        self.body.addLayout(self._build_grid())
        self.body.addSpacing(8)
        self.body.addLayout(self._build_footer())
        self.fields["name"].focus_field()

    def _build_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setContentsMargins(-SHADOW_PAD, 0, -SHADOW_PAD, 0)
        grid.setHorizontalSpacing(COLUMN_GAP - 2 * SHADOW_PAD)
        grid.setVerticalSpacing(ROW_GAP - SHADOW_PAD - 2)
        for column in range(DIALOG_COLUMNS):
            grid.setColumnStretch(column, 1)
        order = [
            widget
            for key, widget in self.fields.items()
            if key not in ("note", "indications", "min_quantity", "storage_place")
        ]
        # Дата добавления стоит рядом со сроком годности.
        order.insert(list(self.fields).index("expiry_date") + 1, self.added_field)
        order += [
            self.fields["storage_place"],
            self.fields["min_quantity"],
            self.fields["indications"],
        ]
        for index, widget in enumerate(order):
            row, column = divmod(index, DIALOG_COLUMNS)
            grid.addWidget(widget, row, column, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(
            self.fields["note"],
            len(order) // DIALOG_COLUMNS,
            0,
            1,
            DIALOG_COLUMNS,
            Qt.AlignmentFlag.AlignTop,
        )
        return grid

    def _build_footer(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 8, 0, 0)
        row.setSpacing(4)
        row.addWidget(label("*", "label", "red"))
        row.addWidget(label(" — обязательные поля", "label", "ink_3"))
        row.addStretch(1)
        self.cancel_button = Button("Отмена", self.close_modal)
        self.save_button = Button("Сохранить", self._submit, variant="primary")
        row.addWidget(self.cancel_button)
        row.addWidget(self.save_button)
        return row

    def _refresh_save(self) -> None:
        """Кнопка недоступна, пока у какого-нибудь поля показана ошибка."""
        self.save_button.set_enabled(not has_error(self.fields))

    def _submit(self) -> None:
        for widget in self.fields.values():
            widget.clear_error()
        try:
            self._services.products.add_product(self._user_id, read_form(self.fields))
        except ValidationError as error:
            show_error(self.fields, error)
            self._refresh_save()
            return
        self.close_modal()
        self._on_saved()


class ProductFormScreen(QWidget):
    """Экран редактирования уже существующего товара."""

    def __init__(self, shell: "MainShell", product_id: int) -> None:
        """Создаёт форму.

        Args:
            shell: Оболочка главного окна.
            product_id: Редактируемый товар.
        """
        super().__init__()
        self._shell = shell
        self._services = shell.services
        self._user = shell.user
        self._product_id = product_id
        self._existing: ProductView = self._services.products.get_product(
            self._user.id, product_id
        )
        self._fields = make_fields(self._services, self._refresh_save)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())
        layout.addSpacing(18 - CARD_SHADOW_PAD)
        layout.addWidget(self._build_card(), 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        self._fill(self._existing)

    @property
    def editing(self) -> bool:
        """Экран всегда редактирует существующий товар."""
        return True

    @property
    def fields(self) -> Dict[str, QWidget]:
        """Поля формы по именам из ``ProductForm``."""
        return self._fields

    # --- построение ---

    def _build_header(self) -> PageHeader:
        header = PageHeader("Редактирование товара")
        header.actions.addWidget(
            Link(
                "Назад к карточке",
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
        for index, (key, widget) in enumerate(self._fields.items()):
            row, col = divmod(index, 2)
            span = 1
            if key == "note":
                row, col, span = 4, 0, 2
            grid.addWidget(widget, row, col, 1, span, Qt.AlignmentFlag.AlignTop)
        card.body.addWidget(body)
        self._build_footer(card, inset)
        return card

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
            "Сохранить изменения", command=self._submit, variant="primary"
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
        show_units(self._fields)
        self._fields["expiry_date"].set(
            format_user_date(product.expiry_date) if product.expiry_date else ""
        )
        self._fields["storage_place"].set(product.storage_place)
        self._fields["min_quantity"].set(format_quantity(product.min_quantity))
        self._fields["indications"].set(product.indications)
        self._fields["note"].set(product.note)

    def read_form(self) -> ProductForm:
        """Собирает введённые значения в форму для сервиса."""
        return read_form(self._fields)

    @property
    def save_button(self) -> Button:
        """Кнопка «Сохранить изменения»."""
        return self._save

    def _refresh_save(self) -> None:
        """Кнопка недоступна, пока у какого-нибудь поля показана ошибка."""
        self._save.set_enabled(not has_error(self._fields))

    def _submit(self) -> None:
        for widget in self._fields.values():
            widget.clear_error()
        try:
            view = self._services.products.update_product(
                self._user.id, self._product_id, self.read_form()
            )
            self._shell.open_product(view.product.id)
        except ValidationError as error:
            show_error(self._fields, error)
            self._refresh_save()
        except NotFoundError:
            self._shell.navigate(sections.MY_KIT)

    def _go_back(self) -> None:
        self._shell.open_product(self._product_id)
