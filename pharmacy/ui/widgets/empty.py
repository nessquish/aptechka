"""Пустое состояние: круглая иконка, заголовок, пояснение и кнопка."""

from typing import Callable, Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget

from pharmacy.ui.icons import icon_pixmap
from pharmacy.ui.paint import begin, fill_rounded
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.common import label
from pharmacy.ui.theme import palette

CIRCLE = 64
GLYPH = 28


class _Circle(QWidget):
    """Круг цвета акцента с иконкой в центре."""

    def __init__(self, icon: str) -> None:
        super().__init__()
        self._icon = icon
        self.setFixedSize(CIRCLE, CIRCLE)

    def paintEvent(self, _event) -> None:
        pal = palette()
        painter = QPainter(self)
        begin(painter)
        fill_rounded(
            painter, QRectF(0, 0, CIRCLE, CIRCLE), CIRCLE / 2, pal.primary_soft
        )
        offset = (CIRCLE - GLYPH) // 2
        painter.drawPixmap(offset, offset, icon_pixmap(self._icon, GLYPH, pal.primary))


class EmptyState(QWidget):
    """Содержимое пустой карточки по центру."""

    def __init__(
        self,
        title: str,
        message: str,
        button_text: Optional[str] = None,
        command: Optional[Callable[[], None]] = None,
        icon: str = "cross",
        parent: Optional[QWidget] = None,
    ) -> None:
        """Создаёт пустое состояние.

        Args:
            title: Заголовок.
            message: Пояснение (можно в несколько строк через перенос).
            button_text: Подпись кнопки (без неё кнопки нет).
            command: Что вызвать по кнопке.
            icon: Иконка в круге.
            parent: Родитель.
        """
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 60, 0, 60)
        layout.setSpacing(0)
        center = Qt.AlignmentFlag.AlignHCenter
        layout.addWidget(_Circle(icon), 0, center)
        layout.addSpacing(16)
        layout.addWidget(label(title, "section"), 0, center)
        layout.addSpacing(6)
        text = label(message, "body", "ink_2")
        text.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(text, 0, center)
        self.button: Optional[Button] = None
        if button_text:
            layout.addSpacing(18)
            self.button = Button(button_text, command, variant="primary", icon="plus")
            layout.addWidget(self.button, 0, center)
