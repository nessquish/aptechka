"""Тесты окна приложения и экранов входа и регистрации."""

import tkinter as tk
import unittest

from pharmacy.services.container import build_services
from pharmacy.ui import fonts, theme
from pharmacy.ui.app import App
from pharmacy.ui.screens.auth import LoginScreen, RegisterScreen
from pharmacy.ui.screens.main_stub import MainStub
from tests.helpers import DatabaseTestCase


class AppTestCase(DatabaseTestCase):
    """Приложение на временной базе с одним зарегистрированным пользователем."""

    @classmethod
    def setUpClass(cls):
        fonts.register_fonts()

    def setUp(self) -> None:
        super().setUp()
        self.services = build_services(self.db)
        self.services.auth.register(
            "anna", "Анна", "anna@mail.ru", "password1", "password1"
        )
        try:
            self.app = App(self.services)
        except tk.TclError:
            self.skipTest("нет графической среды")
        self.addCleanup(self.app.destroy)
        self.addCleanup(theme.set_theme, theme.LIGHT_THEME)
        self.app.attributes("-alpha", 0)
        self.settle()

    def settle(self):
        for _ in range(4):
            self.app.update()

    @property
    def screen(self):
        return self.app._screen


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
        self.assertEqual(self.app.winfo_width(), theme.WINDOW_WIDTH)
        self.assertEqual(self.app.winfo_height(), theme.WINDOW_HEIGHT)

    def test_successful_login(self):
        self.fill("anna", "password1")
        self.assertEqual(self.app.user.login, "anna")
        self.assertIsInstance(self.screen, MainStub)

    def test_wrong_password_shows_banner_and_marks_password(self):
        self.fill("anna", "wrong-password")
        self.assertIsInstance(self.screen, LoginScreen)
        self.assertEqual(self.screen._banner.text, "Неверный логин или пароль")
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
        self.assertIsInstance(self.screen, MainStub)

    def test_link_opens_registration(self):
        self.app.show_register()
        self.assertIsInstance(self.screen, RegisterScreen)


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
        self.assertIsInstance(self.screen, MainStub)

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


class NavigationTest(AppTestCase):
    def test_sign_out_returns_to_login_with_light_theme(self):
        self.screen._fields["login"].set("anna")
        self.screen._fields["password"].set("password1")
        self.screen._submit()
        self.db.execute("UPDATE users SET theme = 'dark'")
        self.app.sign_out()
        self.assertIsInstance(self.screen, LoginScreen)
        self.assertIsNone(self.app.user)
        self.assertEqual(theme.theme_name(), "light")

    def test_user_theme_is_applied_on_sign_in(self):
        self.db.execute("UPDATE users SET theme = 'dark'")
        self.screen._fields["login"].set("anna")
        self.screen._fields["password"].set("password1")
        self.screen._submit()
        self.assertEqual(theme.theme_name(), "dark")

    def test_screens_are_replaced_not_stacked(self):
        for _ in range(3):
            self.app.show_register()
            self.app.show_login()
        self.settle()
        self.assertEqual(len(self.app.winfo_children()), 1)


if __name__ == "__main__":
    unittest.main()
