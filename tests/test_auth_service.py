"""Тесты сервиса авторизации."""

from pharmacy.errors import AuthenticationError, NotFoundError, ValidationError
from pharmacy.services.auth_service import AuthService
from tests.helpers import DatabaseTestCase


class AuthServiceTestCase(DatabaseTestCase):
    """База с готовым сервисом и удобной регистрацией."""

    def setUp(self) -> None:
        super().setUp()
        self.auth = AuthService(self.db)

    def register(self, login="anna", email="anna@mail.ru", password="password1"):
        """Регистрирует пользователя с корректными данными."""
        return self.auth.register(login, "Анна", email, password, password)


class RegisterTest(AuthServiceTestCase):
    """Регистрация."""

    def test_register_creates_user(self):
        user = self.register()
        self.assertEqual(user.login, "anna")
        self.assertEqual(user.username, "Анна")
        self.assertEqual(self.count_rows("users"), 1)

    def test_empty_username_falls_back_to_login(self):
        for empty in ("", "   "):
            self.db.execute("DELETE FROM users")
            user = self.auth.register(
                "nessquish", empty, "n@mail.ru", "password1", "password1"
            )
            self.assertEqual(user.username, "nessquish")

    def test_email_is_lowercased(self):
        user = self.register(email="Anna@Mail.RU")
        self.assertEqual(user.email, "anna@mail.ru")

    def test_password_is_not_stored_plain(self):
        user = self.register(password="password1")
        self.assertNotIn("password1", user.password_hash)

    def test_duplicate_login_rejected_ignoring_case(self):
        self.register(login="anna")
        with self.assertRaises(ValidationError) as ctx:
            self.register(login="ANNA", email="other@mail.ru")
        self.assertEqual(ctx.exception.field, "login")

    def test_duplicate_email_rejected(self):
        self.register(email="anna@mail.ru")
        with self.assertRaises(ValidationError) as ctx:
            self.register(login="boris", email="ANNA@mail.ru")
        self.assertEqual(ctx.exception.field, "email")

    def test_invalid_data_rejected_with_field_name(self):
        cases = [
            (("", "Анна", "a@mail.ru", "password1", "password1"), "login"),
            (("anna", "а" * 51, "a@mail.ru", "password1", "password1"), "username"),
            (("anna", "Анна", "not-email", "password1", "password1"), "email"),
            (("anna", "Анна", "a@mail.ru", "short", "short"), "password"),
            (
                ("anna", "Анна", "a@mail.ru", "password1", "password2"),
                "password_repeat",
            ),
        ]
        for args, field in cases:
            with self.assertRaises(ValidationError, msg=field) as ctx:
                self.auth.register(*args)
            self.assertEqual(ctx.exception.field, field)
        self.assertEqual(self.count_rows("users"), 0)


class LoginTest(AuthServiceTestCase):
    """Вход в приложение."""

    def test_correct_credentials(self):
        registered = self.register()
        user = self.auth.login("anna", "password1")
        self.assertEqual(user.id, registered.id)

    def test_login_ignores_case_and_spaces(self):
        self.register(login="Anna")
        self.assertEqual(self.auth.login("  anna ", "password1").login, "Anna")

    def test_login_by_email(self):
        self.register(login="Anna")
        user = self.auth.login("anna@mail.ru", "password1")
        self.assertEqual(user.login, "Anna")

    def test_email_ignores_case_and_spaces(self):
        self.register(login="Anna")
        self.assertEqual(self.auth.login("  ANNA@Mail.RU ", "password1").login, "Anna")

    def test_known_email_with_wrong_password_points_to_the_password(self):
        self.register()
        with self.assertRaises(AuthenticationError) as ctx:
            self.auth.login("anna@mail.ru", "x" * 8)
        self.assertEqual(str(ctx.exception), "Неверный пароль")
        self.assertEqual(ctx.exception.field, "password")

    def test_unknown_email_or_login_points_to_the_login_field(self):
        self.register()
        for login in ("nobody@mail.ru", "nobody"):
            with self.assertRaises(AuthenticationError) as ctx:
                self.auth.login(login, "password1")
            self.assertEqual(
                str(ctx.exception), "Аккаунт с таким логином или почтой не найден"
            )
            self.assertEqual(ctx.exception.field, "login")

    def test_email_of_another_user_does_not_open_this_account(self):
        self.register()
        with self.assertRaises(AuthenticationError):
            self.auth.login("anna@mail.ru", "other-password1")

    def test_empty_login_message_mentions_email(self):
        with self.assertRaises(ValidationError) as ctx:
            self.auth.login("  ", "password1")
        self.assertEqual(ctx.exception.message, "Введите логин или эл. почту")

    def test_wrong_password(self):
        self.register()
        with self.assertRaises(AuthenticationError):
            self.auth.login("anna", "wrong-password")

    def test_wrong_password_for_a_known_login_names_the_password(self):
        self.register()
        with self.assertRaises(AuthenticationError) as ctx:
            self.auth.login("anna", "wrong-password")
        self.assertEqual(ctx.exception.field, "password")

    def test_empty_fields_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            self.auth.login("", "password1")
        self.assertEqual(ctx.exception.field, "login")
        with self.assertRaises(ValidationError) as ctx:
            self.auth.login("anna", "")
        self.assertEqual(ctx.exception.field, "password")

    def test_sql_injection_does_not_log_in(self):
        self.register()
        with self.assertRaises(AuthenticationError):
            self.auth.login("' OR '1'='1", "' OR '1'='1")


class ChangePasswordTest(AuthServiceTestCase):
    """Смена пароля."""

    def test_new_password_works_old_does_not(self):
        user = self.register(password="password1")
        self.auth.change_password(user.id, "password1", "newpassword2", "newpassword2")
        self.assertEqual(self.auth.login("anna", "newpassword2").id, user.id)
        with self.assertRaises(AuthenticationError):
            self.auth.login("anna", "password1")

    def test_wrong_old_password(self):
        user = self.register()
        with self.assertRaises(ValidationError) as ctx:
            self.auth.change_password(
                user.id, "nope-nope", "newpassword2", "newpassword2"
            )
        self.assertEqual(ctx.exception.field, "old_password")

    def test_new_password_mismatch(self):
        user = self.register()
        with self.assertRaises(ValidationError) as ctx:
            self.auth.change_password(
                user.id, "password1", "newpassword2", "different3"
            )
        self.assertEqual(ctx.exception.field, "new_password_repeat")

    def test_short_new_password(self):
        user = self.register()
        with self.assertRaises(ValidationError) as ctx:
            self.auth.change_password(user.id, "password1", "short", "short")
        self.assertEqual(ctx.exception.field, "new_password")

    def test_unknown_user(self):
        with self.assertRaises(NotFoundError):
            self.auth.change_password(999, "password1", "newpassword2", "newpassword2")
