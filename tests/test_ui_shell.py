"""Тесты оболочки главного окна, главной страницы и диалога."""

import unittest

from PySide6.QtWidgets import QLabel
from shiboken6 import isValid

from pharmacy.services.status import ProductStatus
from pharmacy.ui import sections
from pharmacy.ui.screens.dashboard import DashboardScreen
from pharmacy.ui.screens.my_kit import MyKitScreen
from pharmacy.ui.screens.notifications import NotificationsScreen
from pharmacy.ui.screens.product_card import ProductCardScreen
from pharmacy.ui.screens.shell import MainShell
from pharmacy.ui.screens.shopping import ShoppingScreen
from pharmacy.ui.widgets.badge import Badge
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.dialog import Dialog
from pharmacy.ui.widgets.link import Link
from tests.qt_helpers import ShellTestCase, click, find_all, settle


class ShellTest(ShellTestCase):
    def test_opens_on_home(self):
        self.assertIsInstance(self.shell, MainShell)
        self.assertIsInstance(self.page, DashboardScreen)

    def test_every_menu_item_has_its_own_screen(self):
        for name in sections.ALL:
            self.assertIn(name, self.shell._sections, name)
            self.open(name)
            self.assertIsNotNone(self.page)
            self.assertEqual(self.shell.section, name)

    def test_unknown_section_is_rejected(self):
        with self.assertRaises(ValueError):
            self.shell.navigate("Несуществующий")

    def test_navigation_replaces_the_screen(self):
        first = self.open(sections.HISTORY)
        self.open(sections.HOME)
        self.assertFalse(isValid(first))
        body = self.shell._scroll.body
        self.assertEqual(body.count(), 1)

    def test_menu_click_navigates(self):
        click(self.shell.sidebar.item(sections.SHOPPING))
        self.settle()
        self.assertIsInstance(self.page, ShoppingScreen)

    def test_active_menu_item_follows_the_screen(self):
        self.open(sections.NOTIFICATIONS)
        for name in sections.ALL:
            self.assertEqual(
                self.shell.sidebar.item(name).active, name == sections.NOTIFICATIONS
            )

    def test_card_keeps_my_kit_highlighted(self):
        self.shell.open_product(1)
        self.settle()
        self.assertIsInstance(self.page, ProductCardScreen)
        self.assertTrue(self.shell.sidebar.item(sections.MY_KIT).active)

    def test_unread_counter_is_shown_in_the_menu(self):
        unread = self.services.notifications.count_unread(self.app.user.id)
        self.assertGreater(unread, 0)
        self.assertEqual(self.shell.sidebar.item(sections.NOTIFICATIONS).count, unread)

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

    def test_logout_link_in_the_menu_opens_the_dialog(self):
        click(self.shell.sidebar.logout_link)
        self.settle()
        self.assertEqual(len(self.buttons("Выйти")), 1)

    def test_scroll_returns_to_top_on_a_new_screen(self):
        self.shell._scroll.verticalScrollBar().setValue(50)
        self.open(sections.HISTORY)
        self.assertEqual(self.shell._scroll.verticalScrollBar().value(), 0)


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
        marked = self.buttons("В списке")
        self.assertTrue(marked)
        self.assertTrue(all(not b.enabled for b in marked))

    def test_greets_the_user_by_name(self):
        texts = [w.text() for w in find_all(self.page, QLabel)]
        self.assertTrue(any(t.endswith("Анастасия!") for t in texts))


class DashboardAlignmentTest(ShellTestCase):
    def test_list_buttons_have_the_same_width_and_left_edge(self):
        buttons = [
            b
            for b in find_all(self.page, Button)
            if b.text() in ("В список", "В списке")
        ]
        self.assertGreater(len(buttons), 2)
        self.assertEqual({b.width() for b in buttons}, {buttons[0].width()})
        lefts = {b.mapTo(self.page, b.rect().topLeft()).x() for b in buttons}
        self.assertEqual(len(lefts), 1)

    def test_status_badges_start_at_the_same_x(self):
        names = {"Просрочен", "Скоро истекает", "Низкий остаток"}
        badges = [b for b in find_all(self.page, Badge) if b.text in names]
        self.assertGreater(len(badges), 2)
        lefts = {b.mapTo(self.page, b.rect().topLeft()).x() for b in badges}
        self.assertEqual(len(lefts), 1)


class DashboardLinksTest(ShellTestCase):
    def click_caption(self, caption: str) -> None:
        """Нажимает на подпись счётчика (как мышью по карточке)."""
        text = next(w for w in find_all(self.page, QLabel) if w.text() == caption)
        card = text.parentWidget()
        while card not in self.page.stat_cards:
            card = card.parentWidget()
        click(card)
        self.settle()

    def name_links(self):
        return find_all(self.page, Link)

    def test_total_card_opens_the_kit(self):
        self.click_caption("Товаров в аптечке")
        self.assertIsInstance(self.page, MyKitScreen)
        self.assertIsNone(self.page._status)

    def test_expired_card_opens_the_kit_filtered_by_status(self):
        self.click_caption("Просрочено")
        kit = self.page
        self.assertIsInstance(kit, MyKitScreen)
        self.assertEqual(kit._status, ProductStatus.EXPIRED)
        self.assertEqual(kit.table.row_count, 1)

    def test_attention_card_opens_notifications(self):
        self.click_caption("Требуют внимания")
        self.assertIsInstance(self.page, NotificationsScreen)

    def test_shopping_card_opens_the_open_tab(self):
        self.click_caption("В списке покупок")
        page = self.page
        self.assertIsInstance(page, ShoppingScreen)
        self.assertEqual(page._filter, 1)
        self.assertEqual(page.tabs.active, 1)

    def test_cards_show_the_hand_cursor(self):
        for card in self.page.stat_cards:
            self.assertEqual(card.cursor().shape().name, "PointingHandCursor")

    def test_product_names_in_both_lists_are_links(self):
        names = {link.text() for link in self.name_links()}
        summary = self.services.dashboard.summary(self.app.user.id)
        for view in summary.attention + summary.recent_products:
            self.assertIn(view.product.name, names)

    def test_name_link_opens_the_right_card(self):
        link = next(w for w in self.name_links() if w.text() == "Ибупрофен")
        click(link)
        self.settle()
        card = self.page
        self.assertIsInstance(card, ProductCardScreen)
        self.assertEqual(card._view.product.name, "Ибупрофен")

    def test_recent_list_links_open_cards_too(self):
        recent = self.services.dashboard.summary(self.app.user.id).recent_products
        target = recent[0].product
        links = [w for w in self.name_links() if w.text() == target.name]
        click(links[-1])
        self.settle()
        self.assertEqual(self.page._view.product.id, target.id)


class DialogTest(ShellTestCase):
    def open_dialog(self, calls):
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
        self.open_dialog(calls)
        self.settle()
        self.buttons("Удалить")[0].invoke()
        self.settle()
        self.assertEqual(calls, [1])
        self.assertEqual(self.buttons("Удалить"), [])

    def test_cancel_closes_without_action(self):
        calls = []
        self.open_dialog(calls)
        self.settle()
        self.buttons("Отмена")[0].invoke()
        self.settle()
        self.assertEqual(calls, [])
        self.assertEqual(self.buttons("Удалить"), [])

    def test_closing_twice_is_safe(self):
        dialog = self.open_dialog([])
        dialog.close_modal()
        dialog.close_modal()
        settle()

    def test_dialog_covers_the_whole_window(self):
        dialog = self.open_dialog([])
        self.settle()
        self.assertEqual(dialog.geometry(), self.app.rect())
        self.app.resize(self.app.width() + 40, self.app.height() + 30)
        self.settle()
        self.assertEqual(dialog.geometry(), self.app.rect())

    def test_dialog_is_part_of_the_window_not_a_separate_one(self):
        dialog = self.open_dialog([])
        self.assertIs(dialog.parentWidget(), self.app)
        self.assertFalse(dialog.isWindow())

    def test_escape_closes_the_dialog(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        calls = []
        dialog = self.open_dialog(calls)
        self.settle()
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        self.settle()
        self.assertFalse(dialog.is_open)
        self.assertEqual(calls, [])

    def test_enter_confirms(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        calls = []
        dialog = self.open_dialog(calls)
        self.settle()
        QTest.keyClick(dialog, Qt.Key.Key_Return)
        self.settle()
        self.assertEqual(calls, [1])

    def test_click_on_the_dim_area_does_not_reach_the_screen(self):
        self.open_dialog([])
        self.settle()
        before = self.shell.section
        click(self.app, 5, 5)
        self.settle()
        self.assertEqual(self.shell.section, before)
        self.assertEqual(len(self.buttons("Отмена")), 1)


if __name__ == "__main__":
    unittest.main()
