"""Тестовые данные для демонстрации и проверки приложения.

Запуск из консоли::

    python -m pharmacy.db.seed              # демо-пользователь и товары
    python -m pharmacy.db.seed --bulk 1000  # плюс 1000 товаров для проверки скорости
    python -m pharmacy.db.seed --reset      # удалить файл базы и создать заново
"""

import argparse
import random
from datetime import date, timedelta
from typing import Optional, Sequence

from pharmacy.db.connection import Database
from pharmacy.utils.security import hash_password

DEMO_LOGIN = "nessquish"
DEMO_USERNAME = "Анастасия"
DEMO_EMAIL = "nessquish@mail.ru"
DEMO_PASSWORD = "demo12345"

# Товары из макета Figma. Срок годности задан числом дней от сегодняшней даты,
# чтобы после запуска всегда были и просроченные, и скоро истекающие товары.
# (название, категория, количество, единица, дней до конца срока или None,
#  место хранения, минимальный остаток, показания)
DEMO_PRODUCTS = (
    ("Активированный уголь", "Лекарства", 1, "упак.", -47, "Шкаф", 2, "Сорбент"),
    (
        "Ибупрофен",
        "Лекарства",
        2,
        "упак.",
        19,
        "Шкаф",
        3,
        "Жаропонижающее, обезболивающее",
    ),
    ("Витамин D", "Лекарства", 1, "упак.", 24, "Кухня", 1, "Витамины"),
    ("Хлоргексидин", "Медицинские товары", 1, "фл.", 120, "Аптечка", 1, "Антисептик"),
    (
        "Парацетамол",
        "Лекарства",
        10,
        "упак.",
        220,
        "Шкаф",
        3,
        "Жаропонижающее, болеутоляющее",
    ),
    ("Зубная паста", "Средства гигиены", 2, "шт.", 250, "Ванная", 1, ""),
    ("Средство для посуды", "Бытовая химия", 1, "шт.", 520, "Кухня", 1, ""),
    ("Бинт", "Медицинские товары", 1, "шт.", None, "Аптечка", 2, ""),
)


def _expiry_from_today(days: Optional[int]) -> Optional[str]:
    """Возвращает дату через ``days`` дней от сегодня в формате ГГГГ-ММ-ДД."""
    if days is None:
        return None
    return (date.today() + timedelta(days=days)).isoformat()


def _timestamp(days_ago: int, time_text: str) -> str:
    """Возвращает отметку времени «``days_ago`` дней назад в указанное время»."""
    day = date.today() - timedelta(days=days_ago)
    return f"{day.isoformat()} {time_text}"


def seed_demo(db: Database) -> Optional[int]:
    """Добавляет демо-пользователя, его товары, список покупок и историю.

    Args:
        db: Менеджер базы данных с уже созданной схемой.

    Returns:
        Идентификатор созданного пользователя или None, если демо-пользователь
        уже есть в базе (повторный запуск ничего не дублирует).
    """
    if db.fetch_one("SELECT id FROM users WHERE login = ?", (DEMO_LOGIN,)):
        return None
    categories = {
        row["name"]: row["id"]
        for row in db.fetch_all("SELECT id, name FROM categories")
    }
    with db.transaction() as conn:
        user_id = conn.execute(
            "INSERT INTO users (login, username, email, password_hash)"
            " VALUES (?, ?, ?, ?)",
            (DEMO_LOGIN, DEMO_USERNAME, DEMO_EMAIL, hash_password(DEMO_PASSWORD)),
        ).lastrowid
        product_ids = {}
        for (
            name,
            category,
            quantity,
            unit,
            days,
            place,
            minimum,
            notes,
        ) in DEMO_PRODUCTS:
            product_ids[name] = conn.execute(
                "INSERT INTO products (user_id, category_id, name, quantity, unit,"
                " expiry_date, storage_place, min_quantity, indications)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    categories[category],
                    name,
                    quantity,
                    unit,
                    _expiry_from_today(days),
                    place,
                    minimum,
                    notes,
                ),
            ).lastrowid
        conn.executemany(
            "INSERT INTO shopping_list (user_id, product_id, name, quantity, unit,"
            " source, is_bought, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    user_id,
                    product_ids["Ибупрофен"],
                    "Ибупрофен",
                    2,
                    "упак.",
                    "notification",
                    0,
                    _timestamp(1, "10:05:00"),
                ),
                (
                    user_id,
                    product_ids["Бинт"],
                    "Бинт",
                    2,
                    "шт.",
                    "notification",
                    0,
                    _timestamp(1, "10:07:00"),
                ),
                (
                    user_id,
                    None,
                    "Пластыри",
                    1,
                    "упак.",
                    "manual",
                    0,
                    _timestamp(3, "19:20:00"),
                ),
                (
                    user_id,
                    None,
                    "Витамин C",
                    1,
                    "упак.",
                    "manual",
                    1,
                    _timestamp(6, "12:40:00"),
                ),
            ],
        )
        conn.executemany(
            "INSERT INTO history (user_id, product_id, action, description,"
            " created_at) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    user_id,
                    product_ids["Ибупрофен"],
                    "product_added",
                    "Ибупрофен · добавлен в аптечку",
                    _timestamp(6, "11:03:00"),
                ),
                (
                    user_id,
                    product_ids["Парацетамол"],
                    "product_updated",
                    "Парацетамол · количество изменено с 5 упак. до 10 упак.",
                    _timestamp(2, "18:32:00"),
                ),
                (
                    user_id,
                    product_ids["Бинт"],
                    "shopping_added",
                    "Бинт · добавлен в список покупок",
                    _timestamp(1, "10:07:00"),
                ),
            ],
        )
    return user_id


def seed_bulk(db: Database, user_id: int, count: int = 1000, seed: int = 42) -> None:
    """Добавляет много товаров, чтобы проверить работу с большим объёмом данных.

    Args:
        db: Менеджер базы данных с уже созданной схемой.
        user_id: Пользователь, которому добавляются товары.
        count: Сколько товаров добавить.
        seed: Начальное значение генератора случайных чисел: при одинаковом
            значении получаются одинаковые данные.
    """
    rng = random.Random(seed)
    category_ids = [row["id"] for row in db.fetch_all("SELECT id FROM categories")]
    rows = []
    for number in range(1, count + 1):
        days = rng.choice([None] + list(range(-120, 720)))
        rows.append(
            (
                user_id,
                rng.choice(category_ids),
                f"Тестовый товар {number}",
                rng.randint(0, 20),
                "шт.",
                _expiry_from_today(days),
                rng.randint(0, 5),
            )
        )
    with db.transaction() as conn:
        conn.executemany(
            "INSERT INTO products (user_id, category_id, name, quantity, unit,"
            " expiry_date, min_quantity) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Точка входа консольной команды ``python -m pharmacy.db.seed``."""
    parser = argparse.ArgumentParser(description="Наполнение базы тестовыми данными")
    parser.add_argument("--bulk", type=int, default=0, help="добавить N товаров")
    parser.add_argument(
        "--reset", action="store_true", help="удалить файл базы и создать заново"
    )
    args = parser.parse_args(argv)

    db = Database()
    if args.reset and db.path.exists():
        db.path.unlink()
        print(f"База {db.path} удалена")
    db.init_schema()

    user_id = seed_demo(db)
    if user_id is None:
        print("Демо-пользователь уже есть в базе")
        user_id = db.fetch_one("SELECT id FROM users WHERE login = ?", (DEMO_LOGIN,))[
            "id"
        ]
    else:
        print(f"Создан демо-пользователь {DEMO_LOGIN} (пароль: {DEMO_PASSWORD})")
    if args.bulk:
        seed_bulk(db, user_id, args.bulk)
        print(f"Добавлено товаров: {args.bulk}")
    print(f"База данных: {db.path}")


if __name__ == "__main__":
    main()
