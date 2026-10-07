"""Тесты окна приложения и экранов входа и регистрации."""

import unittest

from PySide6.QtWidgets import QWidget
from shiboken6 import isValid

from pharmacy.ui import theme
from pharmacy.ui.screens.auth import LoginScreen, RegisterScreen
from pharmacy.ui.screens.shell import MainShell
from tests.qt_helpers import AppTestCase, click, settle


class LoginScreenTest(AppTestCase):
    def fill(self, login, password):
        self.screen._fields["login"].set(login)
        self.screen._fields["password"].set(password)
        self.screen._submit()
        self.settle()

    def test_starts_on_login(self):
        self.assertIsInstance(self.screen, LoginScreen)
        self.assertIsNone(self.app.user)

    def test_window_has_design_size(self):
        self.assertEqual(self.app.minimumWidth(), theme.WINDOW_WIDTH)
        self.assertEqual(self.app.minimumHeight(), theme.WINDOW_HEIGHT)

    def test_successful_login(self):
        self.fill("anna", "password1")
        self.assertEqual(self.app.user.login, "anna")
        self.assertIsInstance(self.screen, MainShell)

    def test_wrong_password_shows_banner_and_marks_password(self):
        self.fill("anna", "wrong-password")
        self.assertIsInstance(self.screen, LoginScreen)
        self.assertEqual(self.screen._banner.text, "Неверный логин или пароль")
        self.assertTrue(self.screen._banner.isVisible())
        self.assertIsNotNone(self.screen._fields["password"].error)
        self.assertIsNone(self.app.user)

    def test_empty_login_marks_login_field(self):
        self.fill("", "password1")
        self.assertEqual(self.screen._fields["login"].error, "Введите логин")

    def test_empty_password_marks_password_field(self):
        self.fill("anna", "")
        self.assertEqual(self.screen._fields["password"].error, "Введите пароль")

    def test_new_attempt_clears_previous_error(self):
        self.fill("anna", "wrong-password")
        self.fill("anna", "password1")
        self.assertIsInstance(self.screen, MainShell)

    def test_banner_is_hidden_after_a_good_attempt_starts(self):
        self.fill("anna", "wrong-password")
        self.screen._fields["password"].set("password1")
        self.screen._reset_errors()
        self.assertFalse(self.screen._banner.isVisible())
        self.assertEqual(self.screen._banner.text, "")

    def test_link_opens_registration(self):
        click(self.screen.switch_link)
        self.settle()
        self.assertIsInstance(self.screen, RegisterScreen)

    def test_submit_button_logs_in(self):
        self.screen._fields["login"].set("anna")
        self.screen._fields["password"].set("password1")
        click(self.screen.submit_button)
        self.settle()
        self.assertIsInstance(self.screen, MainShell)

    def test_enter_in_a_field_submits(self):
        self.screen._fields["login"].set("anna")
        self.screen._fields["password"].set("password1")
        self.screen._fields["password"].entry.returnPressed.emit()
        self.settle()
        self.assertIsInstance(self.screen, MainShell)


class RegisterScreenTest(AppTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.app.show_register()
        self.settle()

    def fill(self, **values):
        data = {
            "username": "Борис",
            "login": "boris",
            "email": "boris@mail.ru",
            "password": "password1",
            "password_repeat": "password1",
        }
        data.update(values)
        for key, value in data.items():
            self.screen._fields[key].set(value)
        self.screen._submit()
        self.settle()

    def test_successful_registration_signs_in(self):
        self.fill()
        self.assertEqual(self.app.user.login, "boris")
        self.assertIsInstance(self.screen, MainShell)

    def test_username_is_optional(self):
        self.fill(username="")
        self.assertEqual(self.app.user.username, "boris")

    def test_duplicate_login_is_marked_on_the_login_field(self):
        self.fill(login="anna", email="other@mail.ru")
        self.assertIsInstance(self.screen, RegisterScreen)
        self.assertEqual(self.screen._fields["login"].error, "Этот логин уже занят")

    def test_each_error_goes_to_its_own_field(self):
        cases = {
            "login": ("login", "ab"),
            "email": ("email", "bad"),
            "password": ("password", "short"),
            "password_repeat": ("password_repeat", "different"),
        }
        for key, (field, value) in cases.items():
            self.app.show_register()
            self.settle()
            values = {field: value}
            if key == "password":
                values["password_repeat"] = value
            self.fill(**values)
            self.assertIsNotNone(self.screen._fields[key].error, key)

    def test_password_mismatch_does_not_register(self):
        self.fill(password_repeat="other-password")
        self.assertIsNone(self.app.user)
        self.assertEqual(self.count_rows("users"), 1)

    def test_required_fields_are_marked(self):
        self.assertEqual(
            set(self.screen._fields),
            {"username", "login", "email", "password", "password_repeat"},
        )

    def test_link_returns_to_login(self):
        click(self.screen.switch_link)
        self.settle()
        self.assertIsInstance(self.screen, LoginScreen)


class NavigationTest(AppTestCase):
    def sign_in(self):
        self.screen._fields["login"].set("anna")
        self.screen._fields["password"].set("password1")
        self.screen._submit()
        self.settle()

    def test_sign_out_returns_to_login_with_light_theme(self):
        self.sign_in()
        self.db.execute("UPDATE users SET theme = 'dark'")
        self.app.sign_out()
        self.assertIsInstance(self.screen, LoginScreen)
        self.assertIsNone(self.app.user)
        self.assertEqual(theme.theme_name(), "light")

    def test_user_theme_is_applied_on_sign_in(self):
        self.db.execute("UPDATE users SET theme = 'dark'")
        self.sign_in()
        self.assertEqual(theme.theme_name(), "dark")

    def test_screens_are_replaced_not_stacked(self):
        for _ in range(3):
            self.app.show_register()
            self.app.show_login()
        self.settle()
        shown = [
            w
            for w in self.app.centralWidget().findChildren(QWidget)
            if w.parent() is self.app.centralWidget()
        ]
        self.assertEqual(shown, [self.screen])

    def test_old_screen_is_deleted(self):
        old = self.screen
        self.app.show_register()
        self.settle()
        self.assertFalse(isValid(old))  # Qt удалил виджет, а не только спрятал

    def test_session_password_is_kept_only_in_memory(self):
        self.sign_in()
        self.assertEqual(self.app.session_password, "password1")
        self.app.sign_out()
        self.assertEqual(self.app.session_password, "")

    def test_window_title_and_icon(self):
        self.assertEqual(self.app.windowTitle(), "Моя аптечка")
        self.assertFalse(self.app.windowIcon().isNull())

    def test_closing_leaves_nothing_visible(self):
        self.app.close()
        settle()
        self.assertFalse(self.app.isVisible())


if __name__ == "__main__":
    unittest.main()
