"""Проверка адреса почты прямо в поле: при уходе с поля, при вводе и перед отправкой."""

from typing import Callable

from pharmacy.ui.widgets.field import TextField
from pharmacy.utils.validation import EMAIL_ERROR, is_valid_email


class EmailCheck:
    """Следит за полем почты и сообщает, можно ли продолжать.

    Пока пользователь первый раз печатает адрес, ошибку не показываем: она
    появляется, когда он ушёл с поля или нажал кнопку. После этого поле
    проверяется на каждой букве, так что подсветка пропадает, как только адрес
    исправлен.

    Attributes:
        valid: Записан ли в поле корректный адрес.
    """

    def __init__(
        self, field: TextField, on_state: Callable[[bool], None] = lambda valid: None
    ) -> None:
        """Подключает проверку к полю.

        Args:
            field: Поле, в которое вводят адрес.
            on_state: Вызывается с True или False при каждой правке и при
                первом показе (например, включает и выключает кнопку).
        """
        self._field = field
        self._on_state = on_state
        self._touched = False
        field.connect_edited(self._edited)
        field.connect_blur(self._left)
        self.valid = is_valid_email(field.get())
        on_state(self.valid)

    def _refresh(self) -> None:
        self.valid = is_valid_email(self._field.get())
        if self._touched:
            if self.valid:
                self._field.clear_error()
            else:
                self._field.set_error(EMAIL_ERROR)
        self._on_state(self.valid)

    def _edited(self, _text: str) -> None:
        self._refresh()

    def _left(self) -> None:
        """Пользователь ушёл с поля: с этого момента показываем ошибку."""
        self._touched = True
        self._refresh()

    def check(self) -> bool:
        """Проверяет адрес перед отправкой и показывает ошибку, если он неверный."""
        self._touched = True
        self._refresh()
        return self.valid
