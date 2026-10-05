"""Всплывающий список вариантов под полем (выпадающий список)."""

import tkinter as tk
from typing import Callable, Optional, Sequence, Tuple

from PIL import Image, ImageGrab

from pharmacy.ui.drawing import Shadow, rounded_box
from pharmacy.ui.fonts import font_spec, line_height, text_width
from pharmacy.ui.theme import mix, palette
from pharmacy.ui.widgets.common import photo

Option = Tuple[object, str]  # (значение, подпись)

ITEM_HEIGHT = 30
ITEM_PADDING_X = 12
LIST_PADDING = 4
SHADOW_PAD = 12
MAX_VISIBLE = 8
LIST_RADIUS = 8
GAP = 4  # расстояние от поля до списка


class PopupList(tk.Toplevel):
    """Список вариантов в отдельном окне без рамки.

    Закрывается по выбору варианта, по Esc и по нажатию вне списка.
    Длинный список прокручивается колёсиком мыши.
    """

    def __init__(
        self,
        anchor: tk.Misc,
        options: Sequence[Option],
        selected: object,
        on_pick: Callable[[object], None],
        on_close: Optional[Callable[[], None]] = None,
    ) -> None:
        """Открывает список под полем.

        Args:
            anchor: Поле, под которым появляется список.
            options: Варианты (значение, подпись).
            selected: Значение выбранного варианта (выделяется жирным).
            on_pick: Вызывается со значением выбранного варианта.
            on_close: Вызывается при закрытии списка.
        """
        super().__init__(anchor)
        self.overrideredirect(True)
        self._choices = list(options)
        self._selected = selected
        self._on_pick = on_pick
        self._on_close = on_close
        self._hover = -1
        self._offset = 0
        self._images: list = []
        self._closed = False

        font = font_spec("body", self)
        longest = max(
            (text_width(self, label, "body") for _, label in options), default=0
        )
        self._inner_width = max(anchor.winfo_width(), longest + 2 * ITEM_PADDING_X)
        visible = min(len(self._choices), MAX_VISIBLE)
        self._inner_height = visible * ITEM_HEIGHT + 2 * LIST_PADDING
        self._line = line_height(self, "body")
        self._font = font

        total_width = self._inner_width + 2 * SHADOW_PAD
        total_height = self._inner_height + 2 * SHADOW_PAD
        left = anchor.winfo_rootx() - SHADOW_PAD
        top = anchor.winfo_rooty() + anchor.winfo_height() + GAP - SHADOW_PAD
        self.geometry(f"{total_width}x{total_height}+{left}+{top}")
        self._canvas = tk.Canvas(
            self,
            width=total_width,
            height=total_height,
            bd=0,
            highlightthickness=0,
            bg=palette().bg,
        )
        self._canvas.pack()
        self._backdrop = self._grab(left, top, total_width, total_height)
        self._draw()

        self._canvas.bind("<Motion>", self._on_motion)
        self._canvas.bind("<ButtonRelease-1>", self._on_click)
        self._canvas.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Escape>", lambda _event: self.close())
        self.focus_force()
        self.grab_set()

    @staticmethod
    def _grab(left: int, top: int, width: int, height: int) -> Optional[Image.Image]:
        """Снимает то, что окажется под списком, чтобы тень легла на настоящий фон."""
        try:
            return ImageGrab.grab(bbox=(left, top, left + width, top + height)).convert(
                "RGBA"
            )
        except OSError:
            return None

    def _draw(self) -> None:
        pal = palette()
        self._canvas.delete("all")
        self._images = []
        shape = rounded_box(
            self._inner_width,
            self._inner_height,
            LIST_RADIUS,
            pal.card,
            pal.line,
            shadows=(Shadow(4, 12, pal.shadow, 0.14), Shadow(1, 3, pal.shadow, 0.06)),
            pad=SHADOW_PAD,
        )
        if self._backdrop is not None:
            base = self._backdrop.copy()
            base.alpha_composite(shape)
            shape = base
        self._images.append(photo(shape, self._canvas))
        self._canvas.create_image(0, 0, image=self._images[0], anchor="nw")
        visible = min(len(self._choices), MAX_VISIBLE)
        for row in range(visible):
            index = self._offset + row
            value, label = self._choices[index]
            top = SHADOW_PAD + LIST_PADDING + row * ITEM_HEIGHT
            if index == self._hover:
                fill = mix(pal.card, pal.primary_soft, 0.55)
                chip = rounded_box(
                    self._inner_width - 2 * LIST_PADDING, ITEM_HEIGHT - 2, 6, fill
                )
                self._images.append(photo(chip, self._canvas))
                self._canvas.create_image(
                    SHADOW_PAD + LIST_PADDING,
                    top + 1,
                    image=self._images[-1],
                    anchor="nw",
                )
            chosen = value == self._selected
            self._canvas.create_text(
                SHADOW_PAD + ITEM_PADDING_X,
                top + ITEM_HEIGHT / 2,
                text=label,
                anchor="w",
                fill=pal.primary_ink if chosen else pal.ink,
                font=font_spec("body_strong" if chosen else "body", self),
            )

    def _index_at(self, y: int) -> int:
        row = (y - SHADOW_PAD - LIST_PADDING) // ITEM_HEIGHT
        index = self._offset + row
        if 0 <= row < MAX_VISIBLE and 0 <= index < len(self._choices):
            return index
        return -1

    def _inside(self, x: int, y: int) -> bool:
        return (
            SHADOW_PAD <= x <= SHADOW_PAD + self._inner_width
            and SHADOW_PAD <= y <= SHADOW_PAD + self._inner_height
        )

    def _on_motion(self, event: tk.Event) -> None:
        index = self._index_at(event.y) if self._inside(event.x, event.y) else -1
        if index != self._hover:
            self._hover = index
            self._draw()

    def _on_click(self, event: tk.Event) -> None:
        if not self._inside(event.x, event.y):
            self.close()
            return
        index = self._index_at(event.y)
        if index >= 0:
            value = self._choices[index][0]
            self.close()
            self._on_pick(value)

    def _on_wheel(self, event: tk.Event) -> None:
        extra = len(self._choices) - MAX_VISIBLE
        if extra <= 0:
            return
        step = -1 if event.delta > 0 else 1
        self._offset = min(max(self._offset + step, 0), extra)
        self._draw()

    def close(self) -> None:
        """Закрывает список."""
        if self._closed:
            return
        self._closed = True
        self.grab_release()
        self.destroy()
        if self._on_close is not None:
            self._on_close()
