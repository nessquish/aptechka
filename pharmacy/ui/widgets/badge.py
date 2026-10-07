"""Плашка состояния («Просрочен», «Норма», «Куплено» и другие)."""

from typing import Optional, Tuple

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from pharmacy.ui.fonts import font, line_height, text_width
from pharmacy.ui.icons import icon_pixmap
from pharmacy.ui.paint import begin, fill_rounded, qcolor
from pharmacy.ui import theme
from pharmacy.ui.theme import palette

TONES = ("red", "amber", "green", "gray", "primary")
PADDING_X = 9
PADDING_Y = 3
ICON_SIZE = 11
ICON_GAP = 4


def tone_colors(tone: str) -> Tuple[str, str]:
    """Возвращает (фон, текст) для цветового тона плашки и значка."""
    pal = palette()
    return {
        "red": (pal.red_bg, pal.red),
        "amber": (pal.amber_bg, pal.amber),
        "green": (pal.green_bg, pal.green),
        "gray": (pal.gray_bg, pal.ink_2),
        "primary": (pal.primary_soft, pal.primary),
    }[tone]


def measure_badge(text: str, icon: Optional[str] = None) -> int:
    """Ширина плашки по тексту и иконке (для выравнивания столбцов)."""
    content = text_width(text, "badge")
    if icon:
        content += ICON_SIZE + ICON_GAP
    return content + 2 * PADDING_X


def badge_height() -> int:
    """Высота плашки."""
    return line_height("badge") + 2 * PADDING_Y


class Badge(QWidget):
    """Небольшая цветная плашка с текстом и необязательной иконкой."""

    def __init__(
        self,
        text: str,
        tone: str = "gray",
        icon: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Создаёт плашку.

        Args:
            text: Текст.
            tone: ``red``, ``amber``, ``green``, ``gray`` или ``primary``.
            icon: Название иконки слева от текста.

        Raises:
            ValueError: Если такого тона нет.
        """
        super().__init__(parent)
        if tone not in TONES:
            raise ValueError(f"Неизвестный тон плашки: {tone}")
        self._text = text
        self._tone = tone
        self._icon = icon
        self.setFixedSize(measure_badge(text, icon), badge_height())
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    @property
    def text(self) -> str:
        """Текст плашки."""
        return self._text

    def sizeHint(self) -> QSize:
        return self.size()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        begin(painter)
        fill, ink = tone_colors(self._tone)
        box = QRectF(0, 0, self.width(), self.height())
        fill_rounded(painter, box, theme.BADGE_RADIUS, fill)
        left = PADDING_X
        if self._icon:
            glyph = icon_pixmap(self._icon, ICON_SIZE, ink, 2.5)
            painter.drawPixmap(left, round((self.height() - ICON_SIZE) / 2), glyph)
            left += ICON_SIZE + ICON_GAP
        painter.setPen(qcolor(ink))
        painter.setFont(font("badge"))
        painter.drawText(
            QRectF(left, 0, self.width() - left, self.height()),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._text,
        )
