"""Тесты проверки вводимых данных."""

import unittest

from pharmacy.errors import ValidationError
from pharmacy.utils.validation import (
    EMAIL_ERROR,
    is_valid_email,
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

    def test_format_error_has_the_agreed_text(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_email("abc@xyz")
        self.assertEqual(
            ctx.exception.message, "Введите корректный email, например user@gmail.com"
        )
        self.assertEqual(ctx.exception.message, EMAIL_ERROR)

    def test_empty_email_asks_to_enter_it(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_email("   ")
        self.assertEqual(ctx.exception.message, "Введите адрес электронной почты")


VALID_EMAILS = (
    "user@gmail.com",
    "anna@mail.ru",
    "ivan.petrov@yandex.ru",
    "nessquish@inbox.ru",
    "a_b-c+tag@sub.domain.co.uk",
    "x@example.org",
    "USER@GMAIL.COM",
    "user123@my-company.io",
    "  user@gmail.com  ",  # пробелы по краям не считаются ошибкой
)
INVALID_EMAILS = (
    "",
    "abc",
    "abc@",
    "abc@xyz",  # нет точки после @
    "@gmail.com",  # нет имени
    "abc@@gmail.com",  # две собаки
    "a@b@gmail.com",
    "abc @gmail.com",  # пробел
    "ab c@gmail.com",
    "abc@gma il.com",
    "abc@gmail.c",  # верхний домен короче двух букв
    "abc@gmail.c0m",  # в верхнем домене цифры
    "abc@.com",  # пустая часть домена
    "abc@gmail..com",  # две точки подряд
    "abc@-gmail.com",  # дефис в начале части домена
    "abc@gmail-.com",
    ".abc@gmail.com",  # точка в начале имени
    "abc.@gmail.com",
    "a..b@gmail.com",
    "abc@gmail.com.",  # точка в конце
    "аня@gmail.com",  # кириллица в имени
    "abc@почта.рф",  # кириллица в домене
    "ab(c)@gmail.com",  # недопустимые символы
    "ab,c@gmail.com",
    "ab<c>@gmail.com",
    "ab\tc@gmail.com",
    ("a" * 65) + "@gmail.com",  # слишком длинное имя
    "a@" + ("b" * 64) + ".com",  # слишком длинная часть домена
    "a@" + ("b." * 60) + "com",  # слишком длинный адрес
)


class EmailFormatTest(unittest.TestCase):
    """Проверка формата адреса: подходит для проверки прямо во время ввода."""

    def test_correct_addresses_pass(self):
        for email in VALID_EMAILS:
            self.assertTrue(is_valid_email(email), email)
            validate_email(email)  # и в сервисной проверке тоже

    def test_wrong_addresses_fail(self):
        for email in INVALID_EMAILS:
            self.assertFalse(is_valid_email(email), email)

    def test_service_check_rejects_the_same_addresses(self):
        for email in INVALID_EMAILS:
            with self.assertRaises(ValidationError, msg=email):
                validate_email(email)

    def test_popular_domains_are_accepted_but_not_required(self):
        for domain in ("gmail.com", "mail.ru", "yandex.ru", "inbox.ru"):
            self.assertTrue(is_valid_email(f"user@{domain}"), domain)
        for domain in ("university.edu", "firma.company", "a-b.example.co"):
            self.assertTrue(is_valid_email(f"user@{domain}"), domain)

    def test_longest_allowed_local_part(self):
        self.assertTrue(is_valid_email(("a" * 64) + "@x.ru"))


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
