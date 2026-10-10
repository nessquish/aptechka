"""Периоды для фильтров уведомлений и истории."""

from datetime import date, timedelta
from typing import Optional, Tuple

ALL_TIME = "all"
TODAY = "today"
WEEK = "week"
MONTH = "month"

# (ключ, подпись): порядок как в выпадающем списке макета.
PERIODS: Tuple[Tuple[str, str], ...] = (
    (ALL_TIME, "За всё время"),
    (TODAY, "Сегодня"),
    (WEEK, "Последние 7 дней"),
    (MONTH, "Последние 30 дней"),
)

_DAYS = {TODAY: 0, WEEK: 6, MONTH: 29}


def since(period: str, today: Optional[date] = None) -> Optional[date]:
    """Возвращает первую дату периода (включительно) или None для «за всё время».

    Args:
        period: Ключ периода из ``PERIODS``.
        today: Сегодняшняя дата (по умолчанию из системы).

    Raises:
        KeyError: Если такого периода нет.
    """
    if period == ALL_TIME:
        return None
    return (today or date.today()) - timedelta(days=_DAYS[period])
