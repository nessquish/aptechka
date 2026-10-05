"""Оболочка главного окна: боковое меню и область с выбранным разделом."""

import tkinter as tk
from typing import TYPE_CHECKING, Callable, Dict, Optional

from pharmacy.models import User
from pharmacy.services.container import Services
from pharmacy.ui import sections, theme
from pharmacy.ui.fonts import font_spec
from pharmacy.ui.screens.dashboard import DashboardScreen
from pharmacy.ui.screens.my_kit import MyKitScreen
from pharmacy.ui.screens.product_card import ProductCardScreen
from pharmacy.ui.screens.product_form import ProductFormScreen
from pharmacy.ui.screens.shopping import ShoppingScreen
from pharmacy.ui.theme import CARD_SHADOW_PAD, palette
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.dialog import Dialog
from pharmacy.ui.widgets.page import PageHeader
from pharmacy.ui.widgets.sidebar import Sidebar

if TYPE_CHECKING:
    from pharmacy.ui.app import App

ScreenFactory = Callable[[tk.Misc, "MainShell"], tk.Frame]

# Содержимое окна отступает от краёв на отступ макета минус поле под тень карточек.
CONTENT_PADDING_X = theme.CONTENT_PADDING_X - CARD_SHADOW_PAD


class SectionStub(tk.Frame):
    """Раздел, экран которого ещё не нарисован."""

    def __init__(self, master: tk.Misc, shell: "MainShell", title: str) -> None:
        pal = palette()
        super().__init__(master, bg=pal.bg)
        PageHeader(self, title).pack(fill="x")
        card = Card(self)
        card.pack(fill="x", pady=(18, 0))
        tk.Label(
            card.body,
            text="Этот раздел в разработке",
            bg=pal.card,
            fg=pal.ink_3,
            font=font_spec("body", self),
        ).pack(pady=60)


class MainShell(tk.Frame):
    """Главное окно после входа.

    Attributes:
        app: Окно приложения.
        user: Вошедший пользователь.
        services: Сервисы приложения.
    """

    def __init__(self, master: tk.Misc, app: "App") -> None:
        pal = palette()
        super().__init__(master, bg=pal.bg)
        self.app = app
        self.user: User = app.user
        self.services: Services = app.services
        self._sections: Dict[str, ScreenFactory] = {
            sections.HOME: DashboardScreen,
            sections.MY_KIT: MyKitScreen,
            sections.SHOPPING: ShoppingScreen,
        }
        self._current: tk.Frame = None
        self._sidebar = Sidebar(
            self, self.user, sections.ALL, self.navigate, self.confirm_logout
        )
        self._sidebar.pack(side="left", fill="y")
        self._content = tk.Frame(self, bg=pal.bg)
        self._content.pack(
            side="left",
            fill="both",
            expand=True,
            padx=CONTENT_PADDING_X,
            pady=(theme.CONTENT_PADDING_Y, 0),
        )
        self.navigate(sections.HOME)

    def navigate(self, name: str) -> None:
        """Открывает раздел и выделяет его в меню."""
        factory = self._sections.get(name)
        if factory is None:

            def factory(parent: tk.Misc, shell: "MainShell") -> tk.Frame:
                return SectionStub(parent, shell, name)

        self.show(factory, name)

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
        self._current.pack(fill="both", expand=True)
        self._sidebar.set_active(section)
        self.refresh_counters()

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
