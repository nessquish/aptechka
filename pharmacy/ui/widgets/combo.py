"""Поле с подсказками: можно ввести своё значение или выбрать из списка."""

import tkinter as tk
from typing import Callable, Optional, Sequence

from pharmacy.ui.widgets.field import TextField
from pharmacy.ui.widgets.popup import PopupList


class ComboField(TextField):
    """Текстовое поле со стрелкой, которая открывает список готовых вариантов."""

    def __init__(
        self,
        master: tk.Misc,
        choices: Sequence[str],
        label: Optional[str] = None,
        placeholder: str = "",
        required: bool = False,
        on_change: Optional[Callable[[], None]] = None,
    ) -> None:
        """Создаёт поле.

        Args:
            master: Родительский виджет.
            choices: Варианты для выбора из списка.
            label: Подпись над полем.
            placeholder: Серая подсказка в пустом поле.
            required: Добавить красную звёздочку к подписи.
            on_change: Вызывается после изменения текста.
        """
        super().__init__(
            master,
            label,
            placeholder,
            required,
            trailing_icon="chevron-down",
            on_change=on_change,
        )
        self._choices = list(choices)
        self._popup: Optional[PopupList] = None

    def _on_canvas_click(self, event: tk.Event) -> None:
        if self._icon_hit(event.x):
            self._toggle_list()
        else:
            self._entry.focus_set()

    def _toggle_list(self) -> None:
        if self._popup is not None:
            self._popup.close()
            return
        if not self._choices:
            return
        options = [(name, name) for name in self._choices]
        self._popup = PopupList(
            self._canvas, options, self.get(), self._pick, self._closed
        )

    def _pick(self, value: object) -> None:
        self.set(str(value))
        self.clear_error()
        self._notify()

    def _closed(self) -> None:
        self._popup = None
