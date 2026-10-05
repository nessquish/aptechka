"""Хэширование паролей: в базе хранится только хэш, а не сам пароль."""

import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 310_000
_SALT_BYTES = 16


def _derive_key(password: str, salt: bytes, iterations: int) -> bytes:
    """Вычисляет ключ из пароля и соли алгоритмом PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def hash_password(password: str) -> str:
    """Превращает пароль в строку для хранения в базе.

    Для каждого пароля генерируется случайная соль, поэтому одинаковые
    пароли дают разные хэши.

    Args:
        password: Пароль в открытом виде.

    Returns:
        Строка вида ``алгоритм$итерации$соль$хэш``.
    """
    salt = secrets.token_bytes(_SALT_BYTES)
    key = _derive_key(password, salt, _ITERATIONS)
    return "$".join((_ALGORITHM, str(_ITERATIONS), salt.hex(), key.hex()))


def verify_password(password: str, stored_hash: str) -> bool:
    """Проверяет пароль по сохранённому хэшу.

    Args:
        password: Введённый пользователем пароль.
        stored_hash: Строка, которую вернула ``hash_password``.

    Returns:
        True, если пароль верный. False, если пароль не подходит
        или строка хэша имеет неверный формат.
    """
    try:
        algorithm, iterations, salt_hex, key_hex = stored_hash.split("$")
        if algorithm != _ALGORITHM:
            return False
        expected = bytes.fromhex(key_hex)
        actual = _derive_key(password, bytes.fromhex(salt_hex), int(iterations))
    except ValueError:
        return False
    return hmac.compare_digest(actual, expected)
