"""Красная строка с сообщением об ошибке над формой («Неверный логин или пароль»)."""

from typing import Optional

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget

from pharmacy.ui.paint import begin, fill_rounded
from pharmacy.ui.widgets.common import label
from pharmacy.ui import theme
from pharmacy.ui.theme import SHADOW_PAD, palette

PADDING_X = 10
PADDING_Y = 8


class ErrorBanner(QWidget):
    """Сообщение об ошибке на розовой подложке. Пока текста нет, не занимает места."""

    def __init__(self, gap_below: int = 0, parent: Optional[QWidget] = None) -> None:
        """Создаёт скрытую плашку.

        Args:
            gap_below: Отступ под плашкой, пока она показана.
            parent: Родитель.
        """
        super().__init__(parent)
        self._gap = gap_below
        self._label = label("", "small", "red", wrap=True, bare=True)
        layout = QVBoxLayout(self)
        # Края плашки совпадают с краями полей: у тех по бокам поле под тень.
        layout.setContentsMargins(
            SHADOW_PAD + PADDING_X,
            PADDING_Y,
            SHADOW_PAD + PADDING_X,
            PADDING_Y + gap_below,
        )
        layout.addWidget(self._label)
        self.setVisible(False)

    @property
    def text(self) -> str:
        """Показанный сейчас текст (пустой, если плашки не видно)."""
        return self._label.text()

    def show_message(self, text: str) -> None:
        """Показывает сообщение."""
        self._label.setText(text)
        self.setVisible(bool(text))

    def hide_message(self) -> None:
        """Скрывает сообщение."""
        self.show_message("")

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        begin(painter)
        box = QRectF(
            SHADOW_PAD, 0, self.width() - 2 * SHADOW_PAD, self.height() - self._gap
        )
        fill_rounded(painter, box, theme.CONTROL_RADIUS, palette().red_bg)
