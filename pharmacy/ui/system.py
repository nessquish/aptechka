"""Настройка окружения окна перед запуском интерфейса."""

import ctypes
import sys

_PER_MONITOR_AWARE = 2


def enable_high_dpi() -> None:
    """Просит Windows не растягивать окно приложения при масштабе экрана.

    Без этого при масштабе 125% и выше окно рисуется мелко и растягивается,
    из-за чего текст и скруглённые края получаются размытыми. После вызова
    размеры в пикселях равны размерам макета. Вызывать нужно до создания
    окна Tk. На других системах ничего не делает.
    """
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(_PER_MONITOR_AWARE)
    except (AttributeError, OSError):
        ctypes.windll.user32.SetProcessDPIAware()
