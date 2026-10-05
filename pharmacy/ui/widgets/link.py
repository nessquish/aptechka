"""Ссылка: цветной текст, на который можно нажать."""

import tkinter as tk
from typing import Callable

from pharmacy.ui.fonts import font_spec
from pharmacy.ui.theme import palette
from pharmacy.ui.widgets.common import parent_bg


class Link(tk.Label):
    """Текст цвета акцента без подчёркивания, нажатие вызывает команду."""

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None],
        style: str = "small_medium",
    ) -> None:
        """Создаёт ссылку.

        Args:
            master: Родительский виджет.
            text: Текст ссылки.
            command: Что вызвать при нажатии.
            style: Стиль текста из ``theme.TYPOGRAPHY``.
        """
        pal = palette()
        super().__init__(
            master,
            text=text,
            bg=parent_bg(master),
            fg=pal.primary,
            font=font_spec(style, master),
            cursor="hand2",
        )
        self.bind("<Button-1>", lambda _event: command())
