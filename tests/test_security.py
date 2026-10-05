"""Тесты хэширования паролей."""

import unittest

from pharmacy.utils.security import hash_password, verify_password


class PasswordHashTest(unittest.TestCase):
    """Пароль не хранится в открытом виде и проверяется по хэшу."""

    def test_hash_does_not_contain_password(self):
        self.assertNotIn("secret123", hash_password("secret123"))

    def test_correct_password_accepted(self):
        stored = hash_password("secret123")
        self.assertTrue(verify_password("secret123", stored))

    def test_wrong_password_rejected(self):
        stored = hash_password("secret123")
        self.assertFalse(verify_password("secret124", stored))

    def test_same_password_gives_different_hashes(self):
        self.assertNotEqual(hash_password("secret123"), hash_password("secret123"))

    def test_malformed_hash_rejected(self):
        self.assertFalse(verify_password("secret123", "это-не-хэш"))
        self.assertFalse(verify_password("secret123", "md5$1$00$00"))
        self.assertFalse(verify_password("secret123", "pbkdf2_sha256$x$zz$zz"))

    def test_non_ascii_password(self):
        stored = hash_password("пароль-Ёж-123")
        self.assertTrue(verify_password("пароль-Ёж-123", stored))


if __name__ == "__main__":
    unittest.main()
