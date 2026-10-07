"""Оболочка главного окна: боковое меню и область с выбранным разделом."""

import tkinter as tk
from typing import TYPE_CHECKING, Callable, Dict, Optional

from pharmacy.models import User
from pharmacy.services.container import Services
from pharmacy.services.status import ProductStatus
from pharmacy.ui import sections, theme
from pharmacy.ui.freeze import frozen
from pharmacy.ui.screens.dashboard import DashboardScreen
from pharmacy.ui.screens.history import HistoryScreen
from pharmacy.ui.screens.my_kit import MyKitScreen
from pharmacy.ui.screens.notifications import NotificationsScreen
from pharmacy.ui.screens.product_card import ProductCardScreen
from pharmacy.ui.screens.product_form import ProductFormScreen
from pharmacy.ui.screens.settings import SettingsScreen
from pharmacy.ui.screens.shopping import ShoppingScreen
from pharmacy.ui.theme import CARD_SHADOW_PAD, palette
from pharmacy.ui.widgets.dialog import Dialog
from pharmacy.ui.widgets.iconbutton import IconButton
from pharmacy.ui.widgets.scroll import ScrollArea
from pharmacy.ui.widgets.sidebar import Sidebar

if TYPE_CHECKING:
    from pharmacy.ui.app import App

ScreenFactory = Callable[[tk.Misc, "MainShell"], tk.Frame]

RAIL_WIDTH = 44  # ширина полосы, которая остаётся от свёрнутой боковой панели
SIDEBAR_COLLAPSED = "sidebar_collapsed"  # ключи в предпочтениях пользователя
TEXT_SIZE = "text_size"

# Содержимое окна отступает от краёв на отступ макета минус поле под тень карточек.
CONTENT_PADDING_X = theme.CONTENT_PADDING_X - CARD_SHADOW_PAD


class MainShell(tk.Frame):
    """Главное окно после входа.

    Attributes:
        app: Окно приложения.
        user: Вошедший пользователь.
        services: Сервисы приложения.
        notice: Сообщение для первого открытого экрана (например, «сохранено»).
            Экран забирает его и очищает.
    """

    def __init__(
        self,
        master: tk.Misc,
        app: "App",
        start: str = sections.HOME,
        notice: str = "",
    ) -> None:
        """Создаёт оболочку и открывает стартовый раздел.

        Args:
            master: Родительский виджет.
            app: Окно приложения.
            start: Раздел, который открывается первым.
            notice: Сообщение для стартового экрана.
        """
        pal = palette()
        super().__init__(master, bg=pal.bg)
        self.app = app
        self.user: User = app.user
        self.services: Services = app.services
        self.notice = notice
        self._sections: Dict[str, ScreenFactory] = {
            sections.HOME: DashboardScreen,
            sections.MY_KIT: MyKitScreen,
            sections.SHOPPING: ShoppingScreen,
            sections.NOTIFICATIONS: NotificationsScreen,
            sections.HISTORY: HistoryScreen,
            sections.SETTINGS: SettingsScreen,
        }
        self._current: tk.Frame = None
        self.section = start
        self._sidebar = Sidebar(
            self,
            self.user,
            sections.ALL,
            self.navigate,
            self.confirm_logout,
            self.toggle_theme,
            lambda: self.set_sidebar_collapsed(True),
        )
        self._rail = self._build_rail()
        self._scroll = ScrollArea(self, gutter=CONTENT_PADDING_X)
        self._collapsed = self.app.preferences.get(
            self.user.id, SIDEBAR_COLLAPSED, False
        )
        (self._rail if self._collapsed else self._sidebar).pack(side="left", fill="y")
        self._scroll.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(CONTENT_PADDING_X, 0),
            pady=(theme.CONTENT_PADDING_Y, 0),
        )
        self._content = self._scroll.body
        self.navigate(start)

    def _build_rail(self) -> tk.Frame:
        """Узкая полоса с кнопкой «развернуть», которая остаётся от свёрнутой панели."""
        pal = palette()
        rail = tk.Frame(self, bg=pal.side, width=RAIL_WIDTH)
        rail.pack_propagate(False)
        tk.Frame(rail, bg=pal.line, width=1).pack(side="right", fill="y")
        IconButton(rail, "panel-left", lambda: self.set_sidebar_collapsed(False)).pack(
            pady=(18, 0)
        )
        return rail

    @property
    def sidebar_collapsed(self) -> bool:
        """Свёрнута ли боковая панель."""
        return self._collapsed

    def set_sidebar_collapsed(self, collapsed: bool) -> None:
        """Сворачивает или разворачивает боковую панель и запоминает выбор."""
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        self.app.preferences.set(self.user.id, SIDEBAR_COLLAPSED, collapsed)
        shown, hidden = (
            (self._rail, self._sidebar)
            if collapsed
            else (
                self._sidebar,
                self._rail,
            )
        )
        hidden.pack_forget()
        shown.pack(side="left", fill="y", before=self._scroll)

    def set_text_size(self, name: str) -> None:
        """Запоминает размер текста и сразу применяет его (окно строится заново)."""
        if name == theme.text_size_name():
            return
        self.app.preferences.set(self.user.id, TEXT_SIZE, name)
        self.app.apply_user_changes(self.user, start=self.section)

    def navigate(self, name: str) -> None:
        """Открывает раздел и выделяет его в меню.

        Raises:
            ValueError: Если такого раздела нет.
        """
        factory = self._sections.get(name)
        if factory is None:
            raise ValueError(f"Неизвестный раздел: {name}")
        self.show(factory, name)

    @frozen
    def show(self, factory: ScreenFactory, section: str) -> None:
        """Показывает экран в области содержимого.

        Args:
            factory: Создаёт экран по (родитель, оболочка).
            section: Раздел меню, который остаётся выделенным (карточка товара
                относится к разделу «Моя аптечка»).
        """
        if self._current is not None:
            self._current.destroy()
        self._current = factory(self._content, self)
        self._current.pack(fill="both", expand=True, pady=(0, theme.CONTENT_PADDING_Y))
        self._scroll.scroll_to_top()
        self.section = section
        self._sidebar.set_active(section)
        self.refresh_counters()

    def open_kit(self, status: Optional[ProductStatus] = None) -> None:
        """Открывает «Мою аптечку», при необходимости сразу с фильтром по состоянию."""
        self.show(
            lambda parent, shell: MyKitScreen(parent, shell, status), sections.MY_KIT
        )

    def open_shopping(self, tab: int = 0) -> None:
        """Открывает список покупок на нужной вкладке."""
        self.show(
            lambda parent, shell: ShoppingScreen(parent, shell, tab), sections.SHOPPING
        )

    def open_product(self, product_id: int) -> None:
        """Открывает карточку товара."""
        self.show(
            lambda parent, shell: ProductCardScreen(parent, shell, product_id),
            sections.MY_KIT,
        )

    def open_product_form(self, product_id: Optional[int] = None) -> None:
        """Открывает форму нового товара или редактирования существующего."""
        self.show(
            lambda parent, shell: ProductFormScreen(parent, shell, product_id),
            sections.MY_KIT,
        )

    def set_theme(self, name: str) -> None:
        """Сохраняет тему в настройках пользователя и сразу применяет её.

        Окно строится заново на том же разделе: цвета читаются при создании
        виджетов.
        """
        if name == self.user.theme:
            return
        user = self.services.settings.update_settings(
            self.user.id,
            str(self.user.warning_days),
            name,
            self.user.notify_expired,
            self.user.notify_low_stock,
        )
        self.app.apply_user_changes(user, start=self.section)

    def toggle_theme(self) -> None:
        """Переключает светлую и тёмную тему."""
        dark = self.user.theme == theme.DARK_THEME
        self.set_theme(theme.LIGHT_THEME if dark else theme.DARK_THEME)

    def take_notice(self) -> str:
        """Отдаёт сообщение для экрана и очищает его."""
        notice, self.notice = self.notice, ""
        return notice

    def refresh_counters(self) -> None:
        """Обновляет счётчик непрочитанных уведомлений в меню."""
        unread = self.services.notifications.count_unread(self.user.id)
        self._sidebar.set_count(sections.NOTIFICATIONS, unread)

    def confirm_logout(self) -> None:
        """Спрашивает подтверждение и выходит из аккаунта."""
        Dialog(
            self.app,
            "Выйти из аккаунта?",
            "Чтобы снова открыть аптечку, нужно будет ввести логин и пароль.",
            "Выйти",
            self.app.sign_out,
            width=360,
        )
