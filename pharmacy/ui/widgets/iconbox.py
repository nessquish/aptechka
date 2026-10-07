"""Цветной квадрат со значком (иконки в карточках, уведомлениях и истории)."""

from typing import Optional

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from pharmacy.ui.icons import icon_pixmap
from pharmacy.ui.paint import begin, fill_rounded
from pharmacy.ui.widgets.badge import tone_colors

# Название размера -> (сторона квадрата, радиус, размер значка).
SIZES = {"md": (34, 9, 16), "sm": (28, 8, 14)}


class IconBox(QWidget):
    """Скруглённый квадрат цветового тона с иконкой в центре."""

    def __init__(
        self,
        icon: str,
        tone: str = "primary",
        size: str = "md",
        parent: Optional[QWidget] = None,
    ) -> None:
        """Создаёт значок.

        Args:
            icon: Название иконки из ``icons.ICONS``.
            tone: Цветовой тон (см. ``badge.TONES``).
            size: ``md`` (34 px) или ``sm`` (28 px).
        """
        super().__init__(parent)
        self._side, self._radius, self._glyph = SIZES[size]
        self._icon = icon
        self._tone = tone
        self.setFixedSize(self._side, self._side)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        begin(painter)
        fill, ink = tone_colors(self._tone)
        fill_rounded(painter, QRectF(0, 0, self._side, self._side), self._radius, fill)
        offset = round((self._side - self._glyph) / 2)
        painter.drawPixmap(offset, offset, icon_pixmap(self._icon, self._glyph, ink))
