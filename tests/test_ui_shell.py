"""Тесты оболочки главного окна, главной страницы и диалога."""

import tkinter as tk
from typing import List, Type

from pharmacy.db.seed import seed_demo
from pharmacy.ui import sections
from pharmacy.ui.screens.dashboard import DashboardScreen
from pharmacy.ui.screens.shell import MainShell, SectionStub
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

    def test_sections_without_screen_show_stub(self):
        unfinished = [n for n in sections.ALL if n not in self.shell._sections]
        for name in unfinished:
            self.shell.navigate(name)
            self.settle()
            self.assertIsInstance(self.shell._current, SectionStub, name)

    def test_every_menu_item_opens_something(self):
        for name in sections.ALL:
            self.shell.navigate(name)
            self.settle()
            self.assertIsNotNone(self.shell._current)

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
