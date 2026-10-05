"""Тесты экрана «Настройки»: профиль, пароль, уведомления, тема."""

import tkinter as tk

from pharmacy.errors import AuthenticationError
from pharmacy.ui import sections, theme
from pharmacy.ui.screens.settings import SAVED, SettingsScreen
from pharmacy.ui.widgets.badge import Badge
from tests.test_ui_shell import ShellTestCase, find_all

PASSWORD = "demo12345"


class SettingsTestCase(ShellTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.open()

    def open(self) -> SettingsScreen:
        self.shell.navigate(sections.SETTINGS)
        self.settle()
        return self.page

    @property
    def page(self) -> SettingsScreen:
        return self.shell._current

    def field(self, key):
        return self.page._fields[key]

    def user(self):
        return self.services.settings.get_user(self.app.user.id)

    def save(self):
        self.page._save()
        self.settle()


class ProfileTest(SettingsTestCase):
    def test_shows_current_values(self):
        self.assertEqual(self.field("username").get(), "Анастасия")
        self.assertEqual(self.field("login").get(), "nessquish")
        self.assertEqual(self.field("email").get(), "nessquish@mail.ru")
        self.assertEqual(self.page._days.get(), "30")

    def test_login_cannot_be_changed(self):
        field = self.field("login")
        field.entry.insert(0, "x")
        self.assertEqual(field.get(), "nessquish")

    def test_saves_name_and_email_and_shows_notice(self):
        self.field("username").set("Настя")
        self.field("email").set("Nastya@Mail.ru")
        self.save()
        saved = self.user()
        self.assertEqual((saved.username, saved.email), ("Настя", "nastya@mail.ru"))
        self.assertEqual(self.app.user.username, "Настя")
        texts = [w.cget("text") for w in find_all(self.shell, tk.Label)]
        self.assertIn("Настя", texts)  # имя в боковом меню обновилось
        self.assertTrue(find_all(self.page._header, Badge))
        self.assertEqual(self.shell.take_notice(), "")

    def test_bad_email_is_marked(self):
        self.field("email").set("не почта")
        self.save()
        self.assertIsNotNone(self.field("email").error)
        self.assertEqual(self.user().email, "nessquish@mail.ru")

    def test_empty_name_is_marked(self):
        self.field("username").set("")
        self.save()
        self.assertIsNotNone(self.field("username").error)


class CurrentPasswordTest(SettingsTestCase):
    def test_current_password_is_shown_as_dots(self):
        field = self.field("old_password")
        self.assertEqual(field.entry.cget("show"), "•")
        self.assertEqual(field.get(), PASSWORD)

    def test_eye_shows_the_real_password(self):
        field = self.field("old_password")
        canvas = field.entry.master
        canvas.event_generate("<ButtonPress-1>", x=canvas.winfo_width() - 15, y=15)
        self.assertEqual(field.entry.cget("show"), "")
        self.assertEqual(field.entry.get(), PASSWORD)
        canvas.event_generate("<ButtonPress-1>", x=canvas.winfo_width() - 15, y=15)
        self.assertEqual(field.entry.cget("show"), "•")

    def test_clicking_the_field_does_not_erase_it(self):
        field = self.field("old_password")
        field.entry.event_generate("<FocusIn>")
        field.entry.event_generate("<FocusOut>")
        field.entry.master.event_generate("<ButtonPress-1>", x=40, y=15)
        self.assertEqual(field.get(), PASSWORD)

    def test_current_password_cannot_be_edited(self):
        field = self.field("old_password")
        field.entry.insert(0, "x")
        field.entry.delete(0, "end")
        self.assertEqual(field.get(), PASSWORD)

    def test_it_can_be_copied_but_not_cut(self):
        field = self.field("old_password")
        field.entry.focus_force()
        field.entry.selection_range(0, "end")
        field.entry.event_generate("<<Copy>>")
        self.assertEqual(self.root_clipboard(), PASSWORD)
        self.app.clipboard_clear()
        field.entry.event_generate("<<Cut>>")
        self.assertEqual(field.get(), PASSWORD)

    def root_clipboard(self) -> str:
        return self.app.clipboard_get()

    def test_dots_placeholder_when_the_password_is_unknown(self):
        self.app.session_password = ""
        field = self.open()._fields["old_password"]
        self.assertEqual(field.get(), "")
        self.assertEqual(field.entry.get(), "••••••••")


class ChangePasswordTest(SettingsTestCase):
    def change(self, new, repeat):
        self.field("new_password").set(new)
        self.field("new_password_repeat").set(repeat)
        self.save()

    def test_changes_password_without_asking_the_current_one(self):
        self.change("Новый-пароль-1", "Новый-пароль-1")
        self.assertEqual(
            self.services.auth.login("nessquish", "Новый-пароль-1").login, "nessquish"
        )
        with self.assertRaises(AuthenticationError):
            self.services.auth.login("nessquish", PASSWORD)

    def test_session_password_follows_the_change(self):
        self.change("Новый-пароль-1", "Новый-пароль-1")
        self.assertEqual(self.app.session_password, "Новый-пароль-1")
        self.assertEqual(self.field("old_password").get(), "Новый-пароль-1")

    def test_new_fields_are_empty_after_saving(self):
        self.change("Новый-пароль-1", "Новый-пароль-1")
        self.assertEqual(self.field("new_password").get(), "")

    def test_mismatch_is_marked_and_password_stays(self):
        self.change("Новый-пароль-1", "Другой-пароль-2")
        self.assertIsNotNone(self.field("new_password_repeat").error)
        self.assertEqual(
            self.services.auth.login("nessquish", PASSWORD).login, "nessquish"
        )
        self.assertEqual(self.app.session_password, PASSWORD)

    def test_short_password_is_marked(self):
        self.change("abc", "abc")
        self.assertIsNotNone(self.field("new_password").error)

    def test_empty_new_fields_leave_the_password_alone(self):
        self.save()
        self.assertEqual(
            self.services.auth.login("nessquish", PASSWORD).login, "nessquish"
        )

    def test_wrong_session_password_is_reported_on_the_current_field(self):
        self.app.session_password = "не тот"
        self.open()
        self.change("Новый-пароль-1", "Новый-пароль-1")
        self.assertIsNotNone(self.field("old_password").error)
        self.assertEqual(
            self.services.auth.login("nessquish", PASSWORD).login, "nessquish"
        )


class NotificationSettingsTest(SettingsTestCase):
    def test_toggles_are_saved(self):
        self.page._expired.set(False)
        self.page._low.set(False)
        self.save()
        saved = self.user()
        self.assertFalse(saved.notify_expired)
        self.assertFalse(saved.notify_low_stock)

    def test_warning_days_are_saved_and_refresh_notifications(self):
        before = self.services.notifications.count_unread(self.app.user.id)
        self.page._days.set("1")
        self.save()
        self.assertEqual(self.user().warning_days, 1)
        after = self.services.notifications.count_unread(self.app.user.id)
        self.assertLessEqual(after, before)

    def test_bad_days_turn_the_hint_red(self):
        for text in ("", "abc", "0", "366"):
            self.open()
            self.page._days.set(text)
            self.save()
            self.assertEqual(self.user().warning_days, 30, text)
            self.assertEqual(
                str(self.page._days_hint.cget("fg")), theme.LIGHT.red, text
            )

    def test_typing_in_days_clears_the_error(self):
        self.page._days.set("0")
        self.save()
        self.page._days_edited()
        self.assertEqual(self.page._days_hint.cget("text"), "Предупреждать заранее")

    def test_nothing_is_saved_when_one_field_is_wrong(self):
        self.page._low.set(False)
        self.page._days.set("0")
        self.save()
        self.assertTrue(self.user().notify_low_stock)


class AppearanceTest(SettingsTestCase):
    def test_cancel_drops_unsaved_edits(self):
        self.field("username").set("Другое имя")
        self.buttons("Отмена")[0].invoke()
        self.settle()
        self.assertEqual(self.field("username").get(), "Анастасия")
        self.assertEqual(self.user().username, "Анастасия")

    def test_theme_choice_applies_at_once(self):
        self.page._theme._on_click(
            type("E", (), {"x": self.page._theme._spans[1][0] + 5})()
        )
        self.settle()
        self.assertEqual(theme.theme_name(), "dark")
        self.assertEqual(self.user().theme, "dark")
        # Окно перестроено, но открыт всё тот же раздел «Настройки».
        self.assertEqual(self.app._screen.section, sections.SETTINGS)
        self.assertIsInstance(self.app._screen._current, SettingsScreen)

    def test_notice_has_a_timer_that_is_cancelled_when_the_screen_closes(self):
        self.field("username").set("Настя")
        self.save()
        page = self.page
        texts = [
            w.itemcget(i, "text")
            for w in find_all(page._header, Badge)
            for i in w.find_all()
            if w.type(i) == "text"
        ]
        self.assertIn(SAVED, texts)
        self.assertIsNotNone(page._notice_job)
        self.shell.navigate(sections.HOME)
        self.settle()
        self.assertIsNone(page._notice_job)
