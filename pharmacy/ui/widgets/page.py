"""Заголовок страницы: название слева и действия справа."""

from typing import Optional

from PySide6.QtWidgets import QHBoxLayout, QWidget

from pharmacy.ui.widgets.common import label
from pharmacy.ui.theme import CARD_SHADOW_PAD, SHADOW_PAD

# Края карточек и кнопок отстоят от своих виджетов на разную величину,
# поэтому у кнопок в заголовке справа добавляется недостающий отступ.
ACTION_INSET = CARD_SHADOW_PAD - SHADOW_PAD


class PageHeader(QWidget):
    """Строка с названием раздела. Кнопки добавляются в ``actions``.

    Attributes:
        actions: Раскладка справа, в которую кладутся кнопки и фильтры.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        """Создаёт заголовок.

        Args:
            title: Название раздела.
        """
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(CARD_SHADOW_PAD, 0, ACTION_INSET, 0)
        row.setSpacing(0)
        self._title = label(title, "title")
        row.addWidget(self._title)
        row.addStretch(1)
        self.actions = QHBoxLayout()
        self.actions.setContentsMargins(0, 0, 0, 0)
        self.actions.setSpacing(0)
        row.addLayout(self.actions)

    def set_title(self, title: str) -> None:
        """Меняет название."""
        self._title.setText(title)
