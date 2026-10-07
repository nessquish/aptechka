"""Проверка поля по ходу работы: при уходе с поля, при вводе и перед отправкой."""

from typing import Callable, Optional

from pharmacy.errors import ValidationError
from pharmacy.ui.widgets.field import TextField
from pharmacy.utils.validation import EMAIL_ERROR, is_valid_email, validate_login

Rule = Callable[[str], Optional[str]]  # текст ошибки или None, если всё верно


def email_error(text: str) -> Optional[str]:
    """Ошибка в адресе почты или None, если адрес записан верно."""
    return None if is_valid_email(text) else EMAIL_ERROR


def login_error(text: str) -> Optional[str]:
    """Ошибка в логине или None, если логин подходит."""
    try:
        validate_login(text)
    except ValidationError as error:
        return error.message
    return None


LOGIN_OR_EMAIL_EMPTY = "Введите логин или эл. почту"


def login_or_email_error(text: str) -> Optional[str]:
    """Ошибка в поле «Логин / Эл. почта» или None, если записано верно.

    В логине не бывает «@», поэтому по ней понятно, что ввели: почту или логин.
    """
    text = text.strip()
    if not text:
        return LOGIN_OR_EMAIL_EMPTY
    return email_error(text) if "@" in text else login_error(text)


class LiveCheck:
    """Следит за полем и сообщает, можно ли продолжать.

    Пока пользователь первый раз вводит значение, ошибку не показываем: она
    появляется, когда он ушёл с поля или нажал кнопку. После этого поле
    проверяется на каждой букве, так что подсветка пропадает, как только
    значение исправлено.

    Attributes:
        valid: Верно ли значение в поле.
    """

    def __init__(
        self,
        field: TextField,
        rule: Rule,
        on_state: Callable[[bool], None] = lambda valid: None,
    ) -> None:
        """Подключает проверку к полю.

        Args:
            field: Поле ввода.
            rule: Правило: по тексту возвращает ошибку или None.
            on_state: Вызывается с True или False при каждой правке и при
                подключении (например, включает и выключает кнопку).
        """
        self._field = field
        self._rule = rule
        self._on_state = on_state
        self._touched = False
        field.connect_edited(self._edited)
        field.connect_blur(self._left)
        self.valid = rule(field.get()) is None
        on_state(self.valid)

    def _refresh(self) -> None:
        message = self._rule(self._field.get())
        self.valid = message is None
        if self._touched:
            if self.valid:
                self._field.clear_error()
            else:
                self._field.set_error(message)
        self._on_state(self.valid)

    def _edited(self, _text: str) -> None:
        self._refresh()

    def _left(self) -> None:
        """Пользователь ушёл с поля: с этого момента показываем ошибку."""
        self._touched = True
        self._refresh()

    def check(self) -> bool:
        """Проверяет значение перед отправкой и показывает ошибку, если оно неверно."""
        self._touched = True
        self._refresh()
        return self.valid
