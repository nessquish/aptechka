"""Маленькая кнопка с одной иконкой (свернуть или развернуть боковую панель)."""

from typing import Callable, Optional

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QAbstractButton, QSizePolicy, QWidget

from pharmacy.ui.icons import icon_pixmap
from pharmacy.ui.paint import begin, fill_rounded
from pharmacy.ui.theme import mix, palette

SIZE = 28
ICON_SIZE = 16
RADIUS = 7


class IconButton(QAbstractButton):
    """Квадратная кнопка с иконкой, при наведении подсвечивается."""

    def __init__(
        self,
        icon: str,
        command: Callable[[], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        """Создаёт кнопку.

        Args:
            icon: Название иконки из ``icons.ICONS``.
            command: Что вызвать при нажатии.
        """
        super().__init__(parent)
        self._icon = icon
        self.setFixedSize(SIZE, SIZE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda _checked=False: command())

    def sizeHint(self) -> QSize:
        return QSize(SIZE, SIZE)

    def paintEvent(self, _event) -> None:
        pal = palette()
        painter = QPainter(self)
        begin(painter)
        hover = self.underMouse()
        if hover:
            chip = mix(pal.side, pal.primary_soft, 0.7)
            fill_rounded(painter, QRectF(0, 0, SIZE, SIZE), RADIUS, chip)
        color = pal.primary_ink if hover else pal.ink_2
        offset = round((SIZE - ICON_SIZE) / 2)
        painter.drawPixmap(offset, offset, icon_pixmap(self._icon, ICON_SIZE, color))

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)
