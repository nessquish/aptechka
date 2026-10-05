"""Прокручиваемая область со своей тонкой полосой прокрутки."""

import tkinter as tk

from pharmacy.ui.drawing import rounded_box
from pharmacy.ui.theme import mix, palette
from pharmacy.ui.widgets.common import parent_bg, photo

TRACK_WIDTH = 10
THUMB_WIDTH = 6
THUMB_MARGIN = 4  # отступ ползунка от правого края окна
MIN_THUMB = 28
WHEEL_STEP = 40  # на сколько пикселей сдвигается содержимое за один щелчок


class ScrollArea(tk.Frame):
    """Область, в которой содержимое прокручивается, если оно выше окна.

    Содержимое кладётся в ``body``. Прокрутка колёсиком работает, пока курсор
    над областью. Полоса прокрутки появляется только при переполнении.

    Attributes:
        body: Рамка для содержимого.
    """

    def __init__(self, master: tk.Misc, gutter: int = TRACK_WIDTH) -> None:
        """Создаёт область.

        Args:
            master: Родительский виджет.
            gutter: Ширина поля справа, в котором рисуется ползунок. Поле
                занято всегда, поэтому ширина содержимого не прыгает.
        """
        super().__init__(master, bg=parent_bg(master))
        self._gutter = gutter
        self._canvas = tk.Canvas(
            self, bd=0, highlightthickness=0, bg=self.cget("bg"), width=1, height=1
        )
        self._bar = tk.Canvas(
            self, bd=0, highlightthickness=0, bg=self.cget("bg"), width=gutter
        )
        self._bar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self._canvas, bg=self.cget("bg"))
        self._window = self._canvas.create_window(0, 0, window=self.body, anchor="nw")
        self._thumb_image = None
        self._drag_offset = 0
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self.body.bind("<Configure>", self._on_body_resize)
        self._bar.bind("<ButtonPress-1>", self._on_bar_press)
        self._bar.bind("<B1-Motion>", self._on_bar_drag)
        self.bind("<Enter>", self._bind_wheel)
        self.bind("<Leave>", self._unbind_wheel)
        self.bind("<Destroy>", self._on_destroy)

    # --- размеры ---

    def _content_height(self) -> int:
        return self.body.winfo_reqheight()

    def _overflow(self) -> int:
        return max(self._content_height() - self._canvas.winfo_height(), 0)

    def _on_canvas_resize(self, event: tk.Event) -> None:
        self._canvas.itemconfigure(self._window, width=event.width)
        self._update()

    def _on_body_resize(self, _event: tk.Event) -> None:
        self._canvas.configure(scrollregion=(0, 0, 0, self._content_height()))
        self._update()

    def _update(self) -> None:
        """Рисует ползунок при переполнении и убирает его, когда всё помещается."""
        if self._overflow():
            self._draw_thumb()
        else:
            self._bar.delete("all")
            self._canvas.yview_moveto(0)

    # --- ползунок ---

    def _thumb_span(self) -> tuple:
        height = max(self._bar.winfo_height(), 1)
        content = max(self._content_height(), 1)
        size = max(height * self._canvas.winfo_height() / content, MIN_THUMB)
        top = self._canvas.canvasy(0) / content * height
        return top, min(top + size, height)

    def _draw_thumb(self) -> None:
        pal = palette()
        top, bottom = self._thumb_span()
        self._bar.delete("all")
        if bottom - top < 2:
            return
        shape = rounded_box(
            THUMB_WIDTH,
            int(bottom - top),
            THUMB_WIDTH // 2,
            mix(pal.line, pal.ink_3, 0.55),
        )
        self._thumb_image = photo(shape, self._bar)
        self._bar.create_image(
            self._gutter - THUMB_WIDTH - THUMB_MARGIN,
            top,
            image=self._thumb_image,
            anchor="nw",
        )

    def _scroll_to(self, pixels: float) -> None:
        overflow = self._overflow()
        if not overflow:
            return
        pixels = min(max(pixels, 0), overflow)
        self._canvas.yview_moveto(pixels / self._content_height())
        self._draw_thumb()

    def _on_bar_press(self, event: tk.Event) -> None:
        top, bottom = self._thumb_span()
        if top <= event.y <= bottom:
            self._drag_offset = event.y - top
        else:
            self._drag_offset = (bottom - top) / 2
            self._on_bar_drag(event)

    def _on_bar_drag(self, event: tk.Event) -> None:
        height = max(self._bar.winfo_height(), 1)
        target = (event.y - self._drag_offset) / height * self._content_height()
        self._scroll_to(target)

    # --- колёсико ---

    def _bind_wheel(self, _event: tk.Event) -> None:
        self.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self, event: tk.Event) -> None:
        inside = self.winfo_containing(event.x_root, event.y_root)
        if inside is not None and str(inside).startswith(str(self)):
            return
        self.unbind_all("<MouseWheel>")

    def _on_wheel(self, event: tk.Event) -> None:
        step = -WHEEL_STEP if event.delta > 0 else WHEEL_STEP
        self._scroll_to(self._canvas.canvasy(0) + step)

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is self:
            self.unbind_all("<MouseWheel>")

    def scroll_to_top(self) -> None:
        """Возвращает содержимое в начало (при смене экрана)."""
        self._canvas.yview_moveto(0)
        self._update()
