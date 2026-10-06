"""Заморозка отрисовки окна на время перестроения интерфейса.

В Tk на Windows каждый виджет это отдельное системное окно, и обычного
двойного буфера для всего окна нет. Поэтому, пока мы удаляем и создаём
виджеты, на мониторе на глазах видны пустые и полупостроенные кадры
(мерцание). Здесь окно «замораживается»: Windows не рисует его, пока
перестроение не закончится, а потом рисует готовый результат один раз.
Пользователь видит прежний экран, а затем сразу новый.

Тот же приём в других библиотеках называется Freeze/Thaw (wxPython) и
SuspendLayout (WinForms). Вне Windows ничего не делает.
"""

import ctypes
import functools
import sys
import tkinter as tk
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional

# Флаги RedrawWindow: перерисовать окно и все дочерние и сделать это сразу.
_RDW_INVALIDATE = 0x0001
_RDW_ERASE = 0x0004
_RDW_ALLCHILDREN = 0x0080
_RDW_UPDATENOW = 0x0100
_REDRAW_FLAGS = _RDW_INVALIDATE | _RDW_ERASE | _RDW_ALLCHILDREN | _RDW_UPDATENOW

_depth = 0  # сколько вложенных заморозок активно (замораживает только внешняя)


def _user32():
    """Возвращает системную библиотеку окон (только Windows)."""
    return ctypes.windll.user32


def _window_handle(widget: tk.Misc) -> Optional[int]:
    """Возвращает системный номер окна верхнего уровня для виджета."""
    try:
        return _user32().GetParent(widget.winfo_id()) or widget.winfo_id()
    except tk.TclError:
        return None  # окно уже закрыто


@contextmanager
def frozen_window(widget: tk.Misc) -> Iterator[None]:
    """Замораживает рисование окна на время блока, потом рисует результат.

    Блоки можно вкладывать: замораживает и размораживает только внешний.
    Если заморозить не удалось (другая система, окно закрыто, окно уже
    заморожено), блок просто выполняется как обычно.

    Args:
        widget: Любой виджет окна, которое нужно заморозить.
    """
    global _depth
    handle = _window_handle(widget) if sys.platform == "win32" else None
    locked = (
        handle is not None and _depth == 0 and bool(_user32().LockWindowUpdate(handle))
    )
    _depth += 1
    try:
        yield
    finally:
        _depth -= 1
        if locked:
            _thaw(widget, handle)


@contextmanager
def not_frozen() -> Iterator[None]:
    """Блок, внутри которого окно не замораживается.

    Для построения экранов про запас: они не видны, поэтому замораживать и
    перерисовывать окно ради них не нужно (это только затормозило бы его).
    """
    global _depth
    _depth += 1
    try:
        yield
    finally:
        _depth -= 1


def frozen(method: Callable[..., Any]) -> Callable[..., Any]:
    """Декоратор: метод виджета выполняется при замороженном окне.

    Применяется к методам, которые удаляют и создают виджеты (смена экрана,
    перерисовка таблицы после фильтра).
    """

    @functools.wraps(method)
    def wrapper(self: tk.Misc, *args: Any, **kwargs: Any) -> Any:
        with frozen_window(self):
            return method(self, *args, **kwargs)

    return wrapper


def redraw_window(widget: tk.Misc) -> None:
    """Перерисовывает окно целиком вместе со всеми дочерними виджетами.

    Нужно после разворачивания из свёрнутого состояния: Windows иногда
    возвращает часть виджетов (поля, подписи) нерисованными, и вместо текста
    видны тёмные прямоугольники.
    """
    if sys.platform != "win32":
        return
    handle = _window_handle(widget)
    if handle is not None:
        _user32().RedrawWindow(handle, None, None, _REDRAW_FLAGS)


def _thaw(widget: tk.Misc, handle: int) -> None:
    """Размораживает окно и перерисовывает его целиком."""
    try:
        # Tk дорисовывает всё накопленное, пока окно ещё заморожено: после
        # разморозки на экран уходит уже готовый кадр. Проверено записью кадров:
        # так остаётся меньше всего промежуточных кадров.
        widget.update()
    except tk.TclError:
        pass  # окно закрыли во время перестроения
    finally:
        _user32().LockWindowUpdate(0)
        _user32().RedrawWindow(handle, None, None, _REDRAW_FLAGS)
