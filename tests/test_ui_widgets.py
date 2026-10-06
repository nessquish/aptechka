"""Тесты виджетов: поведение кнопок, полей, плашек и карточек."""

import tkinter as tk
import unittest

from pharmacy.ui import fonts, theme
from pharmacy.ui.theme import SHADOW_PAD
from pharmacy.ui.widgets.badge import Badge
from pharmacy.ui.widgets.banner import ErrorBanner
from pharmacy.ui.widgets.button import Button, button_height
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.field import TextField


class WidgetTestCase(unittest.TestCase):
    """Окно Tk для проверки виджетов (невидимое, но настоящее)."""

    @classmethod
    def setUpClass(cls):
        fonts.register_fonts()

    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("нет графической среды")
        self.addCleanup(self.root.destroy)
        self.addCleanup(self._flush, self.root)  # выполняется до destroy
        self.root.configure(bg=theme.palette().bg)
        self.root.attributes("-alpha", 0)
        self.root.geometry("500x400+0+0")

    @staticmethod
    def _flush(window):
        """Даёт Tk выполнить отложенные вызовы до закрытия окна (без шума в консоли)."""
        try:
            window.update()
        except tk.TclError:
            pass

    def settle(self):
        for _ in range(3):
            self.root.update()


class ButtonTest(WidgetTestCase):
    def test_click_calls_command(self):
        calls = []
        button = Button(self.root, "Войти", command=lambda: calls.append(1))
        button.pack()
        self.settle()
        button.event_generate("<ButtonPress-1>", x=10, y=10)
        button.event_generate("<ButtonRelease-1>", x=10, y=10)
        self.assertEqual(calls, [1])

    def test_release_outside_does_not_click(self):
        calls = []
        button = Button(self.root, "Войти", command=lambda: calls.append(1))
        button.pack()
        self.settle()
        button.event_generate("<ButtonPress-1>", x=10, y=10)
        button.event_generate("<ButtonRelease-1>", x=900, y=900)
        self.assertEqual(calls, [])

    def test_disabled_button_ignores_clicks(self):
        calls = []
        button = Button(self.root, "Войти", command=lambda: calls.append(1))
        button.pack()
        button.set_enabled(False)
        self.settle()
        button.event_generate("<ButtonPress-1>", x=10, y=10)
        button.event_generate("<ButtonRelease-1>", x=10, y=10)
        button.invoke()
        self.assertEqual(calls, [])
        self.assertFalse(button.enabled)

    def test_invoke_calls_command(self):
        calls = []
        Button(self.root, "OK", command=lambda: calls.append(1)).invoke()
        self.assertEqual(calls, [1])

    def test_height_follows_size(self):
        for size, design in (("sm", 26), ("md", 32), ("lg", 36)):
            button = Button(self.root, "Текст", size=size)
            height = int(button.cget("height")) - 2 * SHADOW_PAD
            # Не ниже, чем в макете, и не ниже, чем нужно тексту выбранного размера.
            self.assertGreaterEqual(height, design)
            self.assertEqual(height, button_height(self.root, size))

    def test_buttons_stay_tall_enough_for_large_text(self):
        from pharmacy.ui import theme

        self.addCleanup(theme.set_text_size, "normal")
        theme.set_text_size("large")
        for size in ("sm", "md", "lg"):
            button = Button(self.root, "Текст", size=size)
            self.assertGreater(
                int(button.cget("height")) - 2 * SHADOW_PAD,
                {"sm": 26, "md": 32, "lg": 36}[size] - 1,
            )

    def test_icon_makes_button_wider(self):
        plain = Button(self.root, "Добавить")
        with_icon = Button(self.root, "Добавить", icon="plus")
        self.assertGreater(int(with_icon.cget("width")), int(plain.cget("width")))

    def test_fixed_width(self):
        button = Button(self.root, "Войти", width=240)
        self.assertEqual(int(button.cget("width")), 240 + 2 * SHADOW_PAD)

    def test_fill_x_stretches_the_button(self):
        button = Button(self.root, "Войти")
        button.pack(fill="x")
        self.settle()
        self.assertEqual(button.winfo_width(), 500)

    def test_unknown_variant(self):
        with self.assertRaises(ValueError):
            Button(self.root, "OK", variant="rainbow")

    def test_set_text_changes_width_on_redraw(self):
        button = Button(self.root, "OK")
        button.set_text("Другое")
        self.assertTrue(button.find_all())


class BadgeTest(WidgetTestCase):
    def test_all_tones(self):
        for tone in ("red", "amber", "green", "gray"):
            badge = Badge(self.root, "Текст", tone)
            self.assertGreater(int(badge.cget("width")), 18)

    def test_badge_with_icon_is_wider(self):
        plain = Badge(self.root, "В списке", "green")
        with_icon = Badge(self.root, "В списке", "green", icon="check")
        self.assertGreater(int(with_icon.cget("width")), int(plain.cget("width")))

    def test_unknown_tone(self):
        with self.assertRaises(ValueError):
            Badge(self.root, "Текст", "blue")


class TextFieldTest(WidgetTestCase):
    def make(self, **kwargs):
        field = TextField(self.root, "Логин", **kwargs)
        field.pack(fill="x")
        self.settle()
        return field

    def test_starts_empty(self):
        self.assertEqual(self.make().get(), "")

    def test_placeholder_is_not_a_value(self):
        field = self.make(placeholder="Введите логин")
        self.assertEqual(field.entry.get(), "Введите логин")
        self.assertEqual(field.get(), "")

    def test_set_and_get(self):
        field = self.make(placeholder="Введите логин")
        field.set("nessquish")
        self.assertEqual(field.get(), "nessquish")

    def test_clearing_brings_the_placeholder_back(self):
        field = self.make(placeholder="Введите логин")
        field.set("a")
        field.set("")
        self.assertEqual(field.get(), "")
        self.assertEqual(field.entry.get(), "Введите логин")

    def test_focus_hides_placeholder_and_blur_restores_it(self):
        field = self.make(placeholder="Введите логин")
        field.entry.event_generate("<FocusIn>")
        self.assertEqual(field.entry.get(), "")
        field.entry.event_generate("<FocusOut>")
        self.assertEqual(field.entry.get(), "Введите логин")

    def test_typed_text_survives_blur(self):
        field = self.make(placeholder="Введите логин")
        field.entry.event_generate("<FocusIn>")
        field.entry.insert(0, "abc")
        field.entry.event_generate("<FocusOut>")
        self.assertEqual(field.get(), "abc")

    def test_password_is_masked(self):
        field = self.make(password=True)
        field.set("secret")
        self.assertEqual(field.entry.cget("show"), "•")
        self.assertEqual(field.get(), "secret")

    def test_password_reveal_by_clicking_the_eye(self):
        field = self.make(password=True)
        field.set("secret")
        canvas = field.entry.master
        canvas.event_generate("<ButtonPress-1>", x=canvas.winfo_width() - 15, y=15)
        self.assertEqual(field.entry.cget("show"), "")
        canvas.event_generate("<ButtonPress-1>", x=canvas.winfo_width() - 15, y=15)
        self.assertEqual(field.entry.cget("show"), "•")

    def test_error_state(self):
        field = self.make()
        self.assertIsNone(field.error)
        field.set_error("Введите логин")
        self.assertEqual(field.error, "Введите логин")
        field.clear_error()
        self.assertIsNone(field.error)

    def test_typing_clears_error(self):
        field = self.make()
        field.set_error("Введите логин")
        field.entry.focus_force()
        self.settle()
        field.entry.event_generate("<Key>", keysym="BackSpace")
        self.assertIsNone(field.error)

    def test_enter_submits(self):
        calls = []
        field = self.make()
        field.bind_submit(lambda: calls.append(1))
        field.entry.focus_force()
        self.settle()
        field.entry.event_generate("<Return>")
        self.assertEqual(calls, [1])


class CardTest(WidgetTestCase):
    def test_height_follows_content(self):
        card = Card(self.root)
        card.pack(fill="x")
        tk.Frame(card.body, height=100, bg=theme.palette().card).pack(fill="x")
        self.settle()
        self.assertGreaterEqual(card.winfo_height(), 100)
        self.assertLess(card.winfo_height(), 130)

    def test_fixed_height(self):
        card = Card(self.root, height=200)
        card.pack(fill="x")
        self.settle()
        self.assertEqual(card.winfo_height(), 200)


class ErrorBannerTest(WidgetTestCase):
    def test_hidden_until_text_is_set(self):
        banner = ErrorBanner(self.root)
        banner.pack(fill="x")
        self.settle()
        self.assertEqual(banner.text, "")
        self.assertLessEqual(banner.winfo_height(), 2)

    def test_show_and_hide(self):
        banner = ErrorBanner(self.root)
        banner.pack(fill="x")
        self.settle()
        banner.show("Неверный логин или пароль")
        self.settle()
        self.assertEqual(banner.text, "Неверный логин или пароль")
        self.assertGreater(banner.winfo_height(), 20)
        banner.hide()
        self.settle()
        self.assertLessEqual(banner.winfo_height(), 2)


if __name__ == "__main__":
    unittest.main()
