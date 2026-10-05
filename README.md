# Менеджер домашней аптечки и запасов

Локальное desktop-приложение на Python (Tkinter) для учёта лекарств, медицинских
товаров, бытовой химии и средств гигиены: сроки годности, остатки, уведомления
и список покупок. Данные хранятся в файле SQLite.

Учебный проект. Разработчик: Сергиенко А. С., группа ИСП-34.

## Быстрый старт

Нужен Python 3.9 или новее (проект проверен на 3.14).

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pre-commit install
python -m pharmacy.db.seed
python -m unittest
```

Команда `python -m pharmacy.db.seed` создаёт базу `data/aptechka.db` и наполняет её
тестовыми данными. Ключи:

| Ключ | Что делает |
|---|---|
| `--bulk 1000` | добавляет 1000 товаров для проверки скорости |
| `--reset` | удаляет файл базы и создаёт заново |

## Проверка качества кода

```powershell
python -m black .
python -m flake8
python -m unittest
```

## Структура проекта

Слои соответствуют разделу 2 ТЗ (многослойная архитектура).

| Папка | Назначение | Состояние |
|---|---|---|
| `pharmacy/db/` | схема SQLite, менеджер базы (Database Manager), тестовые данные | готово |
| `pharmacy/utils/` | вспомогательные функции (хэширование паролей) | готово |
| `pharmacy/repositories/` | запросы к таблицам (Repository) | в разработке |
| `pharmacy/services/` | бизнес-логика (Service Layer) | в разработке |
| `pharmacy/ui/` | экраны Tkinter по макету Figma | в разработке |
| `tests/` | автоматические тесты (unittest) | готово для db и utils |

## Соответствие ER-диаграмме

В ER-диаграмме ТЗ имена русские, в коде английские.

| ER-диаграмма | Таблица | Основные поля |
|---|---|---|
| Пользователи | `users` | `login`, `username`, `email`, `password_hash`, `warning_days`, `theme`, `notify_expired`, `notify_low_stock`, `created_at` |
| Категории | `categories` | `name` |
| Товары | `products` | `user_id`, `category_id`, `name`, `quantity`, `unit`, `expiry_date`, `indications`, `storage_place`, `min_quantity`, `note`, `created_at` |
| Уведомления | `notifications` | `user_id`, `product_id`, `kind`, `message`, `is_read`, `created_at` |
| Список покупок | `shopping_list` | `user_id`, `product_id`, `name`, `quantity`, `unit`, `source`, `is_bought`, `created_at` |
| История | `history` | `user_id`, `product_id`, `action`, `description`, `created_at` |

Правила удаления: при удалении пользователя все его данные удаляются каскадно.
При удалении товара его уведомления удаляются, а в истории и списке покупок
ссылка на товар обнуляется (`ON DELETE SET NULL`), сами записи остаются.

## Работа с Git

Используется Feature Branch Workflow: каждая задача разрабатывается в ветке
`feature/...` и вливается в `main` через Pull Request после ревью.
Ход разработки записан в [DEVLOG.md](DEVLOG.md).
