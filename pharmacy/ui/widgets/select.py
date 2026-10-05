"""Выпадающий список: поле, по нажатию на которое открывается список вариантов."""

import tkinter as tk
from typing import Callable, Optional, Sequence, Union

from pharmacy.ui.fonts import font_spec, text_width
from pharmacy.ui.theme import palette
from pharmacy.ui.widgets.field import (
    ICON_INSET,
    ICON_SIZE,
    RING_PAD,
    TEXT_INSET,
    LabeledBox,
)
from pharmacy.ui.widgets.popup import Option, PopupList

OptionLike = Union[str, Option]
COMPACT_TEXT_INSET = 12
COMPACT_ARROW_GAP = 8  # расстояние между текстом и стрелкой в фильтре


def _normalize(options: Sequence[OptionLike]) -> list:
    """Приводит варианты к виду (значение, подпись)."""
    return [(item, item) if isinstance(item, str) else tuple(item) for item in options]


class Select(LabeledBox):
    """Поле выбора из списка.

    Хранит значение выбранного варианта, а не его подпись: например,
    для категории это идентификатор.
    """

    def __init__(
        self,
        master: tk.Misc,
        options: Sequence[OptionLike],
        value: object = None,
        label: Optional[str] = None,
        required: bool = False,
        placeholder: str = "",
        compact: bool = False,
        prefix: str = "",
        width: Optional[int] = None,
        on_change: Optional[Callable[[object], None]] = None,
    ) -> None:
        """Создаёт поле выбора.

        Args:
            master: Родительский виджет.
            options: Варианты: подписи или пары (значение, подпись).
            value: Выбранное значение (по умолчанию ничего не выбрано).
            label: Подпись над полем.
            required: Добавить красную звёздочку к подписи.
            placeholder: Серый текст, пока ничего не выбрано.
            compact: Вид фильтра на панели: граница цвета карточек, ширина по тексту.
            prefix: Слова перед значением («Сортировка: »).
            width: Ширина поля (в компактном виде по самому длинному варианту).
            on_change: Вызывается с новым значением после выбора пользователем.
        """
        super().__init__(master, label, required, compact=compact)
        self._choices = _normalize(options)
        self._value = value
        self._placeholder = placeholder
        self._prefix = prefix
        self._compact = compact
        self._on_change = on_change
        self._popup: Optional[PopupList] = None
        self._inset = COMPACT_TEXT_INSET if compact else TEXT_INSET
        self._fixed_width = width
        if width is not None:
            self.set_width(width)
        self._fit_width()
        self._canvas.configure(cursor="hand2")
        self._canvas.bind("<ButtonPress-1>", self._toggle)

    @property
    def value(self) -> object:
        """Значение выбранного варианта (None, если ничего не выбрано)."""
        return self._value

    def get(self) -> object:
        """Возвращает значение выбранного варианта."""
        return self._value

    def set(self, value: object) -> None:
        """Выбирает вариант по значению."""
        self._value = value
        self._fit_width()
        self._draw()

    def set_options(self, options: Sequence[OptionLike]) -> None:
        """Заменяет список вариантов."""
        self._choices = _normalize(options)
        self._fit_width()
        self._draw()

    def _label_of(self, value: object) -> str:
        for item, label in self._choices:
            if item == value:
                return label
        return ""

    def _natural_width(self) -> int:
        """Ширина по выбранному значению: текст, отступы и стрелка."""
        shown = self._label_of(self._value) or self._placeholder
        text = text_width(self, self._prefix + shown, "body")
        return text + COMPACT_TEXT_INSET + COMPACT_ARROW_GAP + ICON_SIZE + ICON_INSET

    def _fit_width(self) -> None:
        """Подгоняет ширину фильтра под выбранное значение (как в макете)."""
        if self._compact and self._fixed_width is None:
            self.set_width(self._natural_width())

    def _toggle(self, _event: tk.Event) -> None:
        if self._popup is not None:
            self._popup.close()
            return
        self._popup = PopupList(
            self._canvas, self._choices, self._value, self._pick, self._closed
        )
        self._draw()  # рамка становится голубой, пока список открыт

    def _pick(self, value: object) -> None:
        self._value = value
        self.clear_error()
        self._fit_width()
        self._draw()
        if self._on_change is not None:
            self._on_change(value)

    def _closed(self) -> None:
        self._popup = None
        if self.winfo_exists():
            self._draw()

    def _colors(self):
        """Голубая рамка только пока открыт список (а не пока поле «в фокусе»)."""
        if self._error is None and self._popup is not None:
            return palette().primary, None
        return super()._colors()

    def _place_content(self) -> None:
        pal = palette()
        middle = RING_PAD + self._box_height / 2
        text = self._label_of(self._value)
        if text:
            text, color = self._prefix + text, pal.ink_2 if self._compact else pal.ink
        else:
            text, color = self._placeholder, pal.ink_3
        self._canvas.delete("text")
        self._canvas.create_text(
            RING_PAD + self._inset,
            middle,
            text=text,
            anchor="w",
            fill=color,
            font=font_spec("body", self),
            tags="text",
        )
        self._draw_icon("chevron-down", self._width - RING_PAD - ICON_INSET, "e")
