"""Окно приложения: переключение экранов и вход пользователя."""

import tkinter as tk
from typing import Callable, Optional

from PIL import ImageTk

from pharmacy.db.connection import Database
from pharmacy.models import User
from pharmacy.services.container import Services, build_services
from pharmacy.ui import fonts, sections, system, theme
from pharmacy.ui.appicon import render_app_icon
from pharmacy.ui.screens.auth import LoginScreen, RegisterScreen
from pharmacy.ui.freeze import frozen, redraw_window
from pharmacy.ui.preferences import Preferences
from pharmacy.ui.screens.shell import TEXT_SIZE, MainShell

WINDOW_TITLE = "Моя аптечка"
PREFERENCES_FILE = "preferences.json"  # лежит рядом с файлом базы
ScreenFactory = Callable[[tk.Misc, "App"], tk.Frame]


class App(tk.Tk):
    """Главное окно. Хранит сервисы и вошедшего пользователя.

    Attributes:
        services: Все сервисы приложения.
        user: Вошедший пользователь или None на экранах входа.
    """

    def __init__(
        self, services: Services, preferences: Optional[Preferences] = None
    ) -> None:
        """Создаёт окно по размеру макета и показывает экран входа.

        Args:
            services: Сервисы приложения.
            preferences: Предпочтения отображения (размер текста, боковая
                панель). По умолчанию хранятся только в памяти.
        """
        super().__init__()
        self.services = services
        self.preferences = preferences or Preferences()
        self.user: Optional[User] = None
        self.session_password = ""
        self._screen: Optional[tk.Frame] = None
        self.title(WINDOW_TITLE)
        self._window_icon = ImageTk.PhotoImage(render_app_icon(64), master=self)
        self.iconphoto(True, self._window_icon)
        self.minsize(theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT)
        self._center(theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT)
        self.bind("<Map>", self._on_map)
        self.show_login()

    def _on_map(self, event: tk.Event) -> None:
        """После разворачивания окна перерисовывает его целиком."""
        if event.widget is self:
            self.after_idle(self._redraw)

    def _redraw(self) -> None:
        """Перерисовывает окно, если его не успели закрыть."""
        if self.winfo_exists():
            redraw_window(self)

    @frozen
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

    def sign_in(self, user: User, password: str = "") -> None:
        """Запоминает вошедшего пользователя, применяет его тему и открывает аптечку.

        Args:
            user: Вошедший пользователь.
            password: Пароль, который он ввёл. Хранится только в памяти до
                выхода (для показа в настройках), на диск не записывается.
        """
        self.user = user
        self.session_password = password
        self._apply_view_settings(user)
        self.services.notifications.refresh(user.id)
        self.show(MainShell)

    def apply_user_changes(
        self, user: User, notice: str = "", start: str = sections.SETTINGS
    ) -> None:
        """Применяет изменённые данные или тему пользователя и перестраивает окно.

        Нужно после сохранения настроек или смены темы: имя в боковом меню и
        цвета темы читаются при создании виджетов, поэтому окно строится заново.

        Args:
            user: Пользователь с новыми данными.
            notice: Сообщение для открывшегося экрана.
            start: Раздел, который открывается после перестроения.
        """
        self.user = user
        self._apply_view_settings(user)
        self.show(
            lambda parent, app: MainShell(parent, app, start=start, notice=notice)
        )

    def _apply_view_settings(self, user: User) -> None:
        """Включает тему и размер текста пользователя до построения экранов."""
        theme.set_theme(user.theme)
        size = self.preferences.get(user.id, TEXT_SIZE, theme.DEFAULT_TEXT_SIZE)
        theme.set_text_size(
            size if size in theme.TEXT_SIZES else theme.DEFAULT_TEXT_SIZE
        )
        self._fit_window()

    def _fit_window(self) -> None:
        """Подгоняет минимальную ширину окна под размер текста.

        Если окно уже, чем нужно, оно расширяется (но не шире экрана).
        """
        width = min(theme.window_width(), self.winfo_screenwidth() - 40)
        self.minsize(width, theme.WINDOW_HEIGHT)
        if self.winfo_width() < width:
            self.geometry(f"{width}x{max(self.winfo_height(), theme.WINDOW_HEIGHT)}")

    def sign_out(self) -> None:
        """Выходит из аккаунта и возвращается на экран входа."""
        self.user = None
        self.session_password = ""
        theme.set_theme(theme.LIGHT_THEME)
        theme.set_text_size(theme.DEFAULT_TEXT_SIZE)
        self.minsize(theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT)
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
    preferences = Preferences(db.path.parent / PREFERENCES_FILE)
    App(build_services(db), preferences).mainloop()
