"""Общие мелочи для виджетов: подписи, цвета по ролям, нажимаемые виджеты."""

from typing import Callable, Optional

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPalette
from PySide6.QtWidgets import QLabel, QLayout, QSizePolicy, QWidget

from pharmacy.ui.fonts import font
from pharmacy.ui.theme import palette


def role_color(role: str) -> str:
    """Цвет по роли палитры (``ink``, ``primary`` ...) или сам цвет ``#RRGGBB``."""
    return role if role.startswith("#") else getattr(palette(), role)


def label(
    text: str = "",
    style: str = "body",
    color: str = "ink",
    parent: Optional[QWidget] = None,
    wrap: bool = False,
    strike: bool = False,
) -> QLabel:
    """Создаёт подпись: текст в стиле макета нужного цвета.

    Args:
        text: Текст.
        style: Стиль из ``theme.TYPOGRAPHY``.
        color: Роль цвета палитры или ``#RRGGBB``.
        parent: Родитель.
        wrap: Переносить длинный текст на следующие строки.
        strike: Зачеркнуть текст.
    """
    result = QLabel(text, parent)
    result.setFont(font(style))
    if strike:
        struck = result.font()
        struck.setStrikeOut(True)
        result.setFont(struck)
    recolor(result, color)
    result.setWordWrap(wrap)
    result.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    result.setMargin(0)
    result.setIndent(0)
    return result


def recolor(widget: QWidget, color: str) -> None:
    """Задаёт цвет текста виджета."""
    colors = widget.palette()
    colors.setColor(QPalette.ColorRole.WindowText, QColor(role_color(color)))
    colors.setColor(QPalette.ColorRole.Text, QColor(role_color(color)))
    widget.setPalette(colors)


def clickable(widget: QWidget, command: Callable[[], None]) -> None:
    """Делает виджет нажимаемым: рука при наведении и вызов команды по клику."""
    widget.setCursor(Qt.CursorShape.PointingHandCursor)

    def press(event: QMouseEvent) -> None:
        event.accept()  # без этого нажатие уходит родителю, а отпускание теряется

    def release(event: QMouseEvent) -> None:
        inside = QRect(0, 0, widget.width(), widget.height()).contains(
            event.position().toPoint()
        )
        if event.button() == Qt.MouseButton.LeftButton and inside:
            command()

    widget.mousePressEvent = press  # type: ignore[method-assign]
    widget.mouseReleaseEvent = release  # type: ignore[method-assign]


class Line(QWidget):
    """Тонкая горизонтальная линия-разделитель."""

    def __init__(self, color: str = "line_soft", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = color
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, _event) -> None:
        QPainter(self).fillRect(self.rect(), QColor(role_color(self._color)))


def clear_layout(layout: QLayout) -> None:
    """Удаляет всё, что лежит в раскладке (виджеты и вложенные раскладки)."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


def fixed_height(widget: QWidget, height: int) -> None:
    """Фиксирует высоту виджета, ширину оставляет гибкой."""
    widget.setFixedHeight(height)
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
