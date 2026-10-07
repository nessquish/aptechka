"""Ссылка: цветной текст, на который можно нажать."""

from typing import Callable, Optional

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QAbstractButton, QSizePolicy, QWidget

from pharmacy.ui.fonts import font, line_height, text_width
from pharmacy.ui.icons import icon_pixmap
from pharmacy.ui.paint import begin, qcolor
from pharmacy.ui.theme import palette

ICON_SIZE = 14
ICON_GAP = 6


class Link(QAbstractButton):
    """Текст цвета акцента без подчёркивания, нажатие вызывает команду."""

    def __init__(
        self,
        text: str,
        command: Callable[[], None],
        style: str = "small_medium",
        icon: Optional[str] = None,
        icon_side: str = "right",
        parent: Optional[QWidget] = None,
    ) -> None:
        """Создаёт ссылку.

        Args:
            text: Текст ссылки.
            command: Что вызвать при нажатии.
            style: Стиль текста из ``theme.TYPOGRAPHY``.
            icon: Название иконки рядом с текстом (например, стрелка).
            icon_side: С какой стороны от текста иконка: ``right`` или ``left``.
        """
        super().__init__(parent)
        self.setText(text)
        self._style = style
        self._icon = icon
        self._icon_side = icon_side
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.clicked.connect(lambda _checked=False: command())

    def sizeHint(self) -> QSize:
        width = text_width(self.text(), self._style)
        if self._icon:
            width += ICON_SIZE + ICON_GAP
        return QSize(width, max(line_height(self._style), ICON_SIZE))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        begin(painter)
        color = palette().primary
        left = 0
        text_left = 0
        if self._icon:
            icon_top = round((self.height() - ICON_SIZE) / 2)
            glyph = icon_pixmap(self._icon, ICON_SIZE, color)
            if self._icon_side == "left":
                painter.drawPixmap(0, icon_top, glyph)
                text_left = ICON_SIZE + ICON_GAP
            else:
                left = text_width(self.text(), self._style) + ICON_GAP
                painter.drawPixmap(left, icon_top, glyph)
        painter.setPen(qcolor(color))
        painter.setFont(font(self._style))
        painter.drawText(
            QRectF(text_left, 0, self.width() - text_left, self.height()),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.text(),
        )
