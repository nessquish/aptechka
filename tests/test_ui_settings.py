"""Тесты экрана «Настройки»: профиль, пароль, уведомления, тема."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel

from pharmacy.errors import AuthenticationError
from pharmacy.ui import sections, theme
from pharmacy.ui.screens.settings import SAVED, SettingsScreen
from tests.qt_helpers import ShellTestCase, click, find_all, settle, type_text

PASSWORD = "demo12345"


class SettingsTestCase(ShellTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.open_settings()

    def open_settings(self) -> SettingsScreen:
        self.shell.navigate(sections.SETTINGS)
        self.settle()
        return self.page

    def field(self, key):
        return self.page.fields[key]

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
        self.assertEqual(self.page.days_field.get(), "30")

    def test_login_cannot_be_changed(self):
        field = self.field("login")
        type_text(field.entry, "x")
        self.assertEqual(field.get(), "nessquish")
        self.assertTrue(field.entry.isReadOnly())

    def test_saves_name_and_email_and_shows_notice(self):
        self.field("username").set("Настя")
        self.field("email").set("Nastya@Mail.ru")
        self.save()
        saved = self.user()
        self.assertEqual((saved.username, saved.email), ("Настя", "nastya@mail.ru"))
        self.assertEqual(self.app.user.username, "Настя")
        texts = [w.text() for w in find_all(self.shell, QLabel)]
        self.assertIn("Настя", texts)  # имя в боковом меню обновилось
        self.assertIsNotNone(self.page.notice)
        self.assertEqual(self.page.notice.text, SAVED)
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

    def test_save_button_saves(self):
        self.field("username").set("Настя")
        self.page.save_button.invoke()
        self.settle()
        self.assertEqual(self.user().username, "Настя")


class CurrentPasswordTest(SettingsTestCase):
    def clipboard(self) -> str:
        return QGuiApplication.clipboard().text()

    def test_current_password_is_shown_as_dots(self):
        field = self.field("old_password")
        self.assertEqual(field.entry.echoMode(), field.entry.EchoMode.Password)
        self.assertEqual(field.get(), PASSWORD)

    def test_eye_shows_the_real_password(self):
        field = self.field("old_password")
        click(field._trailing)
        self.assertEqual(field.entry.echoMode(), field.entry.EchoMode.Normal)
        self.assertEqual(field.entry.text(), PASSWORD)
        click(field._trailing)
        self.assertEqual(field.entry.echoMode(), field.entry.EchoMode.Password)

    def test_clicking_the_field_does_not_erase_it(self):
        field = self.field("old_password")
        click(field.frame, 40, 15)
        click(field.entry)
        self.assertEqual(field.get(), PASSWORD)

    def test_current_password_cannot_be_edited(self):
        field = self.field("old_password")
        type_text(field.entry, "x")
        QTest.keyClick(field.entry, Qt.Key.Key_Backspace)
        self.assertEqual(field.get(), PASSWORD)

    def test_it_can_be_copied_but_not_cut(self):
        field = self.field("old_password")
        field.entry.setFocus()
        field.entry.selectAll()
        QTest.keyClick(field.entry, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.clipboard(), PASSWORD)
        QGuiApplication.clipboard().setText("")
        field.entry.selectAll()
        QTest.keyClick(field.entry, Qt.Key.Key_X, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(field.get(), PASSWORD)

    def test_dots_placeholder_when_the_password_is_unknown(self):
        self.app.session_password = ""
        field = self.open_settings().fields["old_password"]
        self.assertEqual(field.get(), "")
        self.assertEqual(field.entry.placeholderText(), "••••••••")


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
        self.open_settings()
        self.change("Новый-пароль-1", "Новый-пароль-1")
        self.assertIsNotNone(self.field("old_password").error)
        self.assertEqual(
            self.services.auth.login("nessquish", PASSWORD).login, "nessquish"
        )


class NotificationSettingsTest(SettingsTestCase):
    def test_toggles_are_saved(self):
        self.page.expired_toggle.set(False)
        self.page.low_toggle.set(False)
        self.save()
        saved = self.user()
        self.assertFalse(saved.notify_expired)
        self.assertFalse(saved.notify_low_stock)

    def test_clicking_a_toggle_flips_it(self):
        toggle = self.page.expired_toggle
        before = toggle.value
        click(toggle)
        self.assertEqual(toggle.value, not before)

    def test_warning_days_are_saved_and_refresh_notifications(self):
        before = self.services.notifications.count_unread(self.app.user.id)
        self.page.days_field.set("1")
        self.save()
        self.assertEqual(self.user().warning_days, 1)
        after = self.services.notifications.count_unread(self.app.user.id)
        self.assertLessEqual(after, before)

    def test_bad_days_turn_the_hint_red(self):
        for text in ("", "abc", "0", "366"):
            self.open_settings()
            self.page.days_field.set(text)
            self.save()
            self.assertEqual(self.user().warning_days, 30, text)
            self.assertEqual(
                self.page.days_hint.palette().windowText().color().name().upper(),
                theme.LIGHT.red.upper(),
                text,
            )

    def test_typing_in_days_clears_the_error(self):
        self.page.days_field.set("0")
        self.save()
        self.page._days_edited()
        self.assertEqual(self.page.days_hint.text(), "Предупреждать заранее")

    def test_nothing_is_saved_when_one_field_is_wrong(self):
        self.page.low_toggle.set(False)
        self.page.days_field.set("0")
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
        switch = self.page.theme_switch
        left, right = switch.spans[1]
        click(switch, (left + right) // 2, switch.height() // 2)
        self.settle()
        self.assertEqual(theme.theme_name(), "dark")
        self.assertEqual(self.user().theme, "dark")
        # Окно перестроено, но открыт всё тот же раздел «Настройки».
        self.assertEqual(self.shell.section, sections.SETTINGS)
        self.assertIsInstance(self.page, SettingsScreen)

    def test_notice_has_a_timer_and_goes_away(self):
        self.field("username").set("Настя")
        self.save()
        page = self.page
        self.assertEqual(page.notice.text, SAVED)
        self.assertTrue(page._notice_timer.isActive())
        page._hide_notice()
        self.settle()
        self.assertIsNone(page.notice)

    def test_hiding_the_notice_twice_is_safe(self):
        self.field("username").set("Настя")
        self.save()
        self.page._hide_notice()
        self.page._hide_notice()
        settle()

    def test_notice_is_not_shown_without_saving(self):
        self.assertIsNone(self.page.notice)
