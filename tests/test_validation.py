"""Тесты проверки вводимых данных."""

import unittest

from pharmacy.errors import ValidationError
from pharmacy.utils.validation import (
    validate_email,
    validate_login,
    validate_password,
    validate_username,
)


class LoginTest(unittest.TestCase):
    """Правила для логина."""

    def test_valid_login_returned_trimmed(self):
        self.assertEqual(validate_login("  nessquish "), "nessquish")

    def test_empty_login_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_login("   ")
        self.assertEqual(ctx.exception.field, "login")

    def test_login_with_spaces_inside_rejected(self):
        with self.assertRaises(ValidationError):
            validate_login("my login")

    def test_cyrillic_login_rejected(self):
        with self.assertRaises(ValidationError):
            validate_login("логин")

    def test_too_short_and_too_long_rejected(self):
        for login in ("ab", "a" * 31):
            with self.assertRaises(ValidationError):
                validate_login(login)


class UsernameTest(unittest.TestCase):
    """Правила для имени пользователя."""

    def test_valid_username(self):
        self.assertEqual(validate_username(" Анастасия "), "Анастасия")

    def test_empty_username_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_username("")
        self.assertEqual(ctx.exception.field, "username")

    def test_too_long_username_rejected(self):
        with self.assertRaises(ValidationError):
            validate_username("а" * 51)


class EmailTest(unittest.TestCase):
    """Правила для электронной почты."""

    def test_email_lowercased_and_trimmed(self):
        self.assertEqual(validate_email(" Anna@Mail.RU "), "anna@mail.ru")

    def test_invalid_emails_rejected(self):
        for email in ("", "anna", "anna@", "anna@mail", "an na@mail.ru", "@mail.ru"):
            with self.assertRaises(ValidationError, msg=email) as ctx:
                validate_email(email)
            self.assertEqual(ctx.exception.field, "email")


class PasswordTest(unittest.TestCase):
    """Правила для пароля."""

    def test_valid_password_with_repeat(self):
        validate_password("password1", "password1")

    def test_empty_password_rejected(self):
        with self.assertRaises(ValidationError):
            validate_password("")

    def test_short_password_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_password("short")
        self.assertEqual(ctx.exception.field, "password")

    def test_mismatch_points_to_repeat_field(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_password("password1", "password2")
        self.assertEqual(ctx.exception.field, "password_repeat")

    def test_repeat_is_optional(self):
        validate_password("password1")

    def test_custom_field_name(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_password("short", field="new_password")
        self.assertEqual(ctx.exception.field, "new_password")


if __name__ == "__main__":
    unittest.main()
