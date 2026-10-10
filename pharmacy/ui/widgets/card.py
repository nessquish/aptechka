"""Карточка: белая скруглённая область с тенью, внутри которой лежит содержимое."""

import math
from typing import Optional, Tuple

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget

from pharmacy.ui.paint import (
    Shadow,
    begin,
    draw_shadows,
    fill_rounded,
    qcolor,
    rounded_path,
)
from pharmacy.ui import theme
from pharmacy.ui.theme import CARD_SHADOW_PAD, MODAL_SHADOW_PAD, palette

BORDER = 1
CORNER_CLEARANCE = 1 - math.sqrt(0.5)  # на сколько прямоугольник вписывается в дугу


def _shadows(elevated: bool) -> Tuple[Shadow, ...]:
    """Тени карточки: обычная лёгкая или большая у окна входа и диалогов."""
    pal = palette()
    if elevated:
        return (Shadow(10, 30, pal.shadow, 0.10), Shadow(1, 3, pal.shadow, 0.05))
    return (Shadow(3, 10, pal.shadow, 0.06), Shadow(1, 2, pal.shadow, 0.04))


class Card(QWidget):
    """Карточка с рамкой и тенью.

    Содержимое добавляется в ``body``. Размер карточки определяется
    содержимым, а по ширине она занимает столько, сколько ей даст родитель.

    Attributes:
        body: Вертикальная раскладка для содержимого карточки.
        inner_inset: Отступ содержимого от видимого края карточки. Его вычитают
            из отступов макета, чтобы расстояния на экране совпали с макетом.
        backdrop_color: Цвет, на котором лежит содержимое (для выключенных виджетов).
    """

    def __init__(
        self,
        radius: int = theme.CARD_RADIUS,
        elevated: bool = False,
        flush: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Создаёт карточку.

        Args:
            radius: Радиус скругления углов.
            elevated: Большая тень (окно входа, модальные окна).
            flush: Содержимое доходит до боковых и верхнего края (таблицы).
                Скруглённые верхние углы тогда красит сама карточка (``set_band``).
            parent: Родитель.
        """
        super().__init__(parent)
        self._radius = radius
        self._elevated = elevated
        self._shadow_pad = MODAL_SHADOW_PAD if elevated else CARD_SHADOW_PAD
        self._band: Optional[Tuple[int, str]] = None
        self.backdrop_color = palette().card
        # Содержимое прямоугольное, поэтому отступаем от углов настолько,
        # чтобы оно не закрывало скруглённые края карточки.
        clearance = BORDER + math.ceil(radius * CORNER_CLEARANCE)
        self.inner_inset = BORDER if flush else clearance
        side = self._shadow_pad + self.inner_inset
        bottom = self._shadow_pad + clearance
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(side, side, side, bottom)
        self.body.setSpacing(0)

    def set_band(self, height: int, color: Optional[str]) -> None:
        """Закрашивает верхнюю полосу карточки цветом (шапка таблицы, панель).

        Полоса обрезается по внутреннему скруглению карточки, поэтому верхние
        углы получаются гладкими.

        Args:
            height: Высота полосы в пикселях (0 убирает полосу).
            color: Цвет полосы ``#RRGGBB``.
        """
        band = (height, color) if height and color else None
        if band != self._band:
            self._band = band
            self.update()

    def paintEvent(self, _event) -> None:
        pal = palette()
        painter = QPainter(self)
        begin(painter)
        pad = self._shadow_pad
        shape = QRectF(pad, pad, self.width() - 2 * pad, self.height() - 2 * pad)
        draw_shadows(painter, shape, self._radius, _shadows(self._elevated))
        fill_rounded(painter, shape, self._radius, pal.card, pal.line)
        if self._band is not None:
            height, color = self._band
            inner = shape.adjusted(BORDER, BORDER, -BORDER, -BORDER)
            painter.setClipPath(rounded_path(inner, self._radius - BORDER))
            painter.fillRect(
                QRectF(inner.left(), inner.top(), inner.width(), height), qcolor(color)
            )
