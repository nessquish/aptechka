"""Заголовок страницы: название слева и действия справа."""

import tkinter as tk

from pharmacy.ui.fonts import font_spec
from pharmacy.ui.theme import CARD_SHADOW_PAD, SHADOW_PAD, palette
from pharmacy.ui.widgets.common import parent_bg

# Края карточек и кнопок отстоят от своих виджетов на разную величину,
# поэтому у кнопок в заголовке справа добавляется недостающий отступ.
ACTION_INSET = CARD_SHADOW_PAD - SHADOW_PAD


class PageHeader(tk.Frame):
    """Строка с названием раздела. Кнопки добавляются в ``actions``.

    Attributes:
        actions: Рамка справа, в которую кладутся кнопки и фильтры.
    """

    def __init__(self, master: tk.Misc, title: str) -> None:
        """Создаёт заголовок.

        Args:
            master: Родительский виджет.
            title: Название раздела.
        """
        super().__init__(master, bg=parent_bg(master))
        pal = palette()
        self._title = tk.Label(
            self,
            text=title,
            bg=self.cget("bg"),
            fg=pal.ink,
            font=font_spec("title", self),
            padx=0,
        )
        self._title.pack(side="left", padx=CARD_SHADOW_PAD)
        self.actions = tk.Frame(self, bg=self.cget("bg"))
        self.actions.pack(side="right", padx=(0, ACTION_INSET))

    def set_title(self, title: str) -> None:
        """Меняет название."""
        self._title.configure(text=title)
