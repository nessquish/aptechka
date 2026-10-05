"""Временный экран после входа.

Показывает, кто вошёл, и позволяет выйти. Заменяется оболочкой главного
окна с боковым меню в следующей ветке.
"""

import tkinter as tk
from typing import TYPE_CHECKING

from pharmacy.ui.fonts import font_spec
from pharmacy.ui.theme import palette
from pharmacy.ui.widgets.button import Button

if TYPE_CHECKING:
    from pharmacy.ui.app import App


class MainStub(tk.Frame):
    """Приветствие вошедшего пользователя с кнопкой выхода."""

    def __init__(self, master: tk.Misc, app: "App") -> None:
        pal = palette()
        super().__init__(master, bg=pal.bg)
        centre = tk.Frame(self, bg=pal.bg)
        centre.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(
            centre,
            text=f"Добрый день, {app.user.username}!",
            bg=pal.bg,
            fg=pal.ink,
            font=font_spec("title", self),
        ).pack(pady=(0, 16))
        Button(centre, "Выйти", command=app.sign_out, icon="logout").pack()
