"""Общие помощники виджетов."""

import tkinter as tk

from PIL import Image, ImageTk


def parent_bg(widget: tk.Misc) -> str:
    """Возвращает цвет фона родителя, чтобы нарисованные углы сливались с ним."""
    return widget.cget("bg")


def photo(image: Image.Image, master: tk.Misc) -> ImageTk.PhotoImage:
    """Превращает изображение Pillow в изображение Tk.

    Результат нужно хранить в атрибуте виджета, иначе Tk его удалит.
    """
    return ImageTk.PhotoImage(image, master=master)
