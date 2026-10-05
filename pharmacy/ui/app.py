"""Окно приложения: переключение экранов и вход пользователя."""

import tkinter as tk
from typing import Callable, Optional

from pharmacy.db.connection import Database
from pharmacy.models import User
from pharmacy.services.container import Services, build_services
from pharmacy.ui import fonts, system, theme
from pharmacy.ui.screens.auth import LoginScreen, RegisterScreen
from pharmacy.ui.screens.shell import MainShell

WINDOW_TITLE = "Моя аптечка"
ScreenFactory = Callable[[tk.Misc, "App"], tk.Frame]


class App(tk.Tk):
    """Главное окно. Хранит сервисы и вошедшего пользователя.

    Attributes:
        services: Все сервисы приложения.
        user: Вошедший пользователь или None на экранах входа.
    """

    def __init__(self, services: Services) -> None:
        """Создаёт окно по размеру макета и показывает экран входа.

        Args:
            services: Сервисы приложения.
        """
        super().__init__()
        self.services = services
        self.user: Optional[User] = None
        self._screen: Optional[tk.Frame] = None
        self.title(WINDOW_TITLE)
        self.minsize(theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT)
        self._center(theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT)
        self.show_login()

    def show(self, factory: ScreenFactory) -> None:
        """Заменяет текущий экран новым.

        Args:
            factory: Класс или функция, создающие экран по (родитель, окно).
        """
        self.configure(bg=theme.palette().bg)
        if self._screen is not None:
            self._screen.destroy()
        self._screen = factory(self, self)
        self._screen.pack(fill="both", expand=True)

    def show_login(self) -> None:
        """Показывает экран входа."""
        self.show(LoginScreen)

    def show_register(self) -> None:
        """Показывает экран регистрации."""
        self.show(RegisterScreen)

    def sign_in(self, user: User) -> None:
        """Запоминает вошедшего пользователя, применяет его тему и открывает аптечку."""
        self.user = user
        theme.set_theme(user.theme)
        self.services.notifications.refresh(user.id)
        self.show(MainShell)

    def sign_out(self) -> None:
        """Выходит из аккаунта и возвращается на экран входа."""
        self.user = None
        theme.set_theme(theme.LIGHT_THEME)
        self.show_login()

    def _center(self, width: int, height: int) -> None:
        """Ставит окно по центру экрана."""
        left = max((self.winfo_screenwidth() - width) // 2, 0)
        top = max((self.winfo_screenheight() - height) // 2, 0)
        self.geometry(f"{width}x{height}+{left}+{top}")


def run(db: Optional[Database] = None) -> None:
    """Запускает приложение.

    Args:
        db: База данных. Если не задана, используется файл из настроек.
    """
    system.enable_high_dpi()
    fonts.register_fonts()
    db = db or Database()
    db.init_schema()
    App(build_services(db)).mainloop()
