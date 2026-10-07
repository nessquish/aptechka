"""Тесты оболочки главного окна, главной страницы и диалога."""

import tkinter as tk
from typing import List, Type

from pharmacy.db.seed import seed_demo
from pharmacy.ui import sections
from pharmacy.services.status import ProductStatus
from pharmacy.ui.screens.dashboard import DashboardScreen
from pharmacy.ui.screens.my_kit import MyKitScreen
from pharmacy.ui.screens.notifications import NotificationsScreen
from pharmacy.ui.screens.product_card import ProductCardScreen
from pharmacy.ui.screens.shell import MainShell
from pharmacy.ui.screens.shopping import ShoppingScreen
from pharmacy.ui.widgets.badge import Badge
from pharmacy.ui.widgets.link import Link
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.dialog import Dialog
from tests.test_ui_app import AppTestCase


def find_all(widget: tk.Misc, kind: Type) -> List:
    """Находит в дереве виджетов все виджеты нужного класса."""
    found = [widget] if isinstance(widget, kind) else []
    for child in widget.winfo_children():
        found.extend(find_all(child, kind))
    return found


class ShellTestCase(AppTestCase):
    """Приложение с демо-данными, вход уже выполнен."""

    def setUp(self) -> None:
        super().setUp()
        seed_demo(self.db)
        self.screen._fields["login"].set("nessquish")
        self.screen._fields["password"].set("demo12345")
        self.screen._submit()
        self.settle()

    @property
    def shell(self) -> MainShell:
        return self.app._screen

    def buttons(self, text: str) -> List[Button]:
        return [b for b in find_all(self.app, Button) if b.text == text]


class ShellTest(ShellTestCase):
    def test_opens_on_home(self):
        self.assertIsInstance(self.shell, MainShell)
        self.assertIsInstance(self.shell._current, DashboardScreen)

    def test_every_menu_item_has_its_own_screen(self):
        for name in sections.ALL:
            self.assertIn(name, self.shell._sections, name)
            self.shell.navigate(name)
            self.settle()
            self.assertIsNotNone(self.shell._current)

    def test_unknown_section_is_rejected(self):
        with self.assertRaises(ValueError):
            self.shell.navigate("Несуществующий")

    def test_navigation_replaces_the_screen(self):
        self.shell.navigate(sections.HISTORY)
        self.shell.navigate(sections.HOME)
        self.settle()
        self.assertEqual(len(self.shell._content.winfo_children()), 1)

    def test_notifications_are_refreshed_on_sign_in(self):
        unread = self.services.notifications.count_unread(self.app.user.id)
        self.assertGreater(unread, 0)

    def test_logout_asks_for_confirmation(self):
        self.shell.confirm_logout()
        self.settle()
        self.assertIsNotNone(self.app.user)
        cancel = self.buttons("Отмена")
        self.assertEqual(len(cancel), 1)
        cancel[0].invoke()
        self.settle()
        self.assertIsNotNone(self.app.user)
        self.assertEqual(self.buttons("Отмена"), [])

    def test_confirmed_logout_returns_to_login(self):
        self.shell.confirm_logout()
        self.settle()
        self.buttons("Выйти")[0].invoke()
        self.settle()
        self.assertIsNone(self.app.user)


class DashboardScreenTest(ShellTestCase):
    def test_add_to_list_updates_the_screen(self):
        before = self.services.shopping.list_items(self.app.user.id, False)
        add_buttons = self.buttons("В список")
        self.assertTrue(add_buttons)
        add_buttons[0].invoke()
        self.settle()
        after = self.services.shopping.list_items(self.app.user.id, False)
        self.assertEqual(len(after), len(before) + 1)
        self.assertEqual(len(self.buttons("В список")), len(add_buttons) - 1)

    def test_products_already_in_list_are_marked(self):
        disabled = [b for b in self.buttons("В списке") if not b.enabled]
        self.assertEqual(len(disabled), len(self.buttons("В списке")))
        self.assertTrue(disabled)


class DashboardAlignmentTest(ShellTestCase):
    def test_list_buttons_have_the_same_width_and_left_edge(self):
        buttons = [
            b
            for b in find_all(self.shell._current, Button)
            if b.text in ("В список", "В списке")
        ]
        self.assertGreater(len(buttons), 2)
        self.assertEqual({b.winfo_width() for b in buttons}, {buttons[0].winfo_width()})
        self.assertEqual({b.winfo_rootx() for b in buttons}, {buttons[0].winfo_rootx()})

    def test_status_badges_start_at_the_same_x(self):
        names = {"Просрочен", "Скоро истекает", "Низкий остаток"}
        badges = [
            b
            for b in find_all(self.shell._current, Badge)
            if self.badge_text(b) in names
        ]
        self.assertGreater(len(badges), 2)
        self.assertEqual({b.winfo_rootx() for b in badges}, {badges[0].winfo_rootx()})

    @staticmethod
    def badge_text(badge) -> str:
        for item in badge.find_all():
            if badge.type(item) == "text":
                return badge.itemcget(item, "text")
        return ""


class DashboardLinksTest(ShellTestCase):
    def click_caption(self, caption: str) -> None:
        """Нажимает на подпись счётчика (как мышью по карточке)."""
        label = next(
            w
            for w in find_all(self.shell._current, tk.Label)
            if w.cget("text") == caption
        )
        label.event_generate("<Button-1>")
        self.settle()

    def name_links(self):
        return [w for w in find_all(self.shell._current, Link)]

    def test_total_card_opens_the_kit(self):
        self.click_caption("Товаров в аптечке")
        self.assertIsInstance(self.shell._current, MyKitScreen)
        self.assertIsNone(self.shell._current._status)

    def test_expired_card_opens_the_kit_filtered_by_status(self):
        self.click_caption("Просрочено")
        kit = self.shell._current
        self.assertIsInstance(kit, MyKitScreen)
        self.assertEqual(kit._status, ProductStatus.EXPIRED)
        self.assertEqual(len(kit._table._body.winfo_children()), 2)

    def test_attention_card_opens_notifications(self):
        self.click_caption("Требуют внимания")
        self.assertIsInstance(self.shell._current, NotificationsScreen)

    def test_shopping_card_opens_the_open_tab(self):
        self.click_caption("В списке покупок")
        page = self.shell._current
        self.assertIsInstance(page, ShoppingScreen)
        self.assertEqual(page._filter, 1)
        self.assertEqual(page._tabs.active, 1)

    def test_cards_show_the_hand_cursor(self):
        label = next(
            w
            for w in find_all(self.shell._current, tk.Label)
            if w.cget("text") == "Просрочено"
        )
        self.assertEqual(str(label.cget("cursor")), "hand2")

    def test_product_names_in_both_lists_are_links(self):
        names = {link.cget("text") for link in self.name_links()}
        attention = self.services.dashboard.summary(self.app.user.id).attention
        recent = self.services.dashboard.summary(self.app.user.id).recent_products
        for view in attention + recent:
            self.assertIn(view.product.name, names)

    def test_name_link_opens_the_right_card(self):
        link = next(w for w in self.name_links() if w.cget("text") == "Ибупрофен")
        link.event_generate("<Button-1>")
        self.settle()
        card = self.shell._current
        self.assertIsInstance(card, ProductCardScreen)
        self.assertEqual(card._view.product.name, "Ибупрофен")

    def test_recent_list_links_open_cards_too(self):
        recent = self.services.dashboard.summary(self.app.user.id).recent_products
        target = recent[0].product
        links = [w for w in self.name_links() if w.cget("text") == target.name]
        links[-1].event_generate("<Button-1>")
        self.settle()
        self.assertEqual(self.shell._current._view.product.id, target.id)


class DialogTest(ShellTestCase):
    def open(self, calls):
        return Dialog(
            self.app,
            "Удалить товар?",
            "Действие нельзя отменить.",
            "Удалить",
            lambda: calls.append(1),
            confirm_variant="danger_solid",
            warning=True,
        )

    def test_confirm_runs_action_and_closes(self):
        calls = []
        self.open(calls)
        self.settle()
        self.buttons("Удалить")[0].invoke()
        self.settle()
        self.assertEqual(calls, [1])
        self.assertEqual(self.buttons("Удалить"), [])

    def test_cancel_closes_without_action(self):
        calls = []
        self.open(calls)
        self.settle()
        self.buttons("Отмена")[0].invoke()
        self.settle()
        self.assertEqual(calls, [])
        self.assertEqual(self.buttons("Удалить"), [])

    def test_closing_twice_is_safe(self):
        dialog = self.open([])
        dialog.close()
        dialog.close()
