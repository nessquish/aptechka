"""Форматирование значений для показа пользователю."""


def format_quantity(value: float) -> str:
    """Записывает количество без лишних нулей: ``2.0`` как «2», ``1.50`` как «1.5».

    Args:
        value: Количество товара.

    Returns:
        Строка с числом (не больше трёх знаков после точки).
    """
    return f"{value:.3f}".rstrip("0").rstrip(".")


def plural(number: int, one: str, few: str, many: str) -> str:
    """Выбирает форму слова для числа по правилам русского языка.

    Args:
        number: Число.
        one: Форма для 1, 21, 31... (например, «день»).
        few: Форма для 2-4, 22-24... (например, «дня»).
        many: Форма для 0, 5-20, 25-30... (например, «дней»).

    Returns:
        Одна из трёх форм.
    """
    number = abs(number)
    if 11 <= number % 100 <= 14:
        return many
    last = number % 10
    if last == 1:
        return one
    if 2 <= last <= 4:
        return few
    return many
