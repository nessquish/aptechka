"""Поле с подсказками: можно ввести своё значение или выбрать из списка."""

from typing import Callable, Optional, Sequence

from PySide6.QtWidgets import QWidget

from pharmacy.ui.widgets.common import clickable
from pharmacy.ui.widgets.field import TextField
from pharmacy.ui.widgets.popup import PopupList


class ComboField(TextField):
    """Текстовое поле со стрелкой, которая открывает список готовых вариантов."""

    def __init__(
        self,
        choices: Sequence[str],
        label_text: Optional[str] = None,
        placeholder: str = "",
        required: bool = False,
        on_change: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Создаёт поле.

        Args:
            choices: Варианты для выбора из списка.
            label_text: Подпись над полем.
            placeholder: Серая подсказка в пустом поле.
            required: Добавить красную звёздочку к подписи.
            on_change: Вызывается после изменения текста.
            parent: Родитель.
        """
        super().__init__(
            label_text,
            placeholder,
            required,
            trailing_icon="chevron-down",
            on_change=on_change,
            parent=parent,
        )
        self._choices = list(choices)
        self._popup: Optional[PopupList] = None
        clickable(self._trailing, self.toggle_list)

    @property
    def popup(self) -> Optional[PopupList]:
        """Открытый сейчас список или None."""
        return self._popup

    def toggle_list(self) -> None:
        """Открывает список вариантов или закрывает, если он уже открыт."""
        if self._popup is not None:
            self._popup.close_list()
            return
        if not self._choices:
            return
        options = [(name, name) for name in self._choices]
        self._popup = PopupList(
            self.frame,
            options,
            self.get(),
            self._pick,
            self._closed,
            self.frame.box_rect(),
        )

    def _pick(self, value: object) -> None:
        self.set(str(value))
        self.clear_error()
        if self._on_change is not None:
            self._on_change()

    def _closed(self) -> None:
        self._popup = None
