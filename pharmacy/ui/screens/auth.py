"""Экраны входа и регистрации (макет Figma, экраны 01 и 02)."""

import tkinter as tk
from tkinter import font as tkfont
from typing import TYPE_CHECKING, Dict, Sequence, Tuple

from pharmacy.errors import AuthenticationError, ValidationError
from pharmacy.ui import theme
from pharmacy.ui.drawing import gradient_box
from pharmacy.ui.fonts import font_spec
from pharmacy.ui.icons import render_icon
from pharmacy.ui.theme import SHADOW_PAD, palette
from pharmacy.ui.widgets.banner import ErrorBanner
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.common import photo
from pharmacy.ui.widgets.field import TextField
from pharmacy.ui.widgets.link import Link

if TYPE_CHECKING:
    from pharmacy.ui.app import App

HERO_SHARE = 0.44  # какую часть окна занимает левая панель
HERO_TEXT_WIDTH = 270
HERO_ICON_SIZE = 60
FORM_WIDTH = 350
FORM_PADDING_X = 34
GRADIENT_ANGLE = 160.0


class _HeroPanel(tk.Canvas):
    """Левая панель с градиентом: знак, название, описание и преимущества."""

    def __init__(
        self, master: tk.Misc, description: str, points: Sequence[str]
    ) -> None:
        super().__init__(master, bd=0, highlightthickness=0)
        self._description = description
        self._points = points
        self._images: list = []
        self.bind("<Configure>", self._draw)

    def _draw(self, event: tk.Event) -> None:
        """Рисует панель целиком под текущий размер."""
        pal = palette()
        self.delete("all")
        self._images = [
            photo(
                gradient_box(
                    event.width,
                    event.height,
                    pal.hero_from,
                    pal.hero_to,
                    GRADIENT_ANGLE,
                ),
                self,
            ),
            photo(render_icon("cross", HERO_ICON_SIZE, pal.primary), self),
        ]
        self.create_image(0, 0, image=self._images[0], anchor="nw")
        center = event.width / 2
        y = 0
        self.create_image(center, y, image=self._images[1], anchor="n", tags="content")
        y += HERO_ICON_SIZE + 18
        title = self.create_text(
            center,
            y,
            text="Моя аптечка",
            anchor="n",
            fill=pal.brand_ink,
            font=font_spec("display", self),
            tags="content",
        )
        y = self.bbox(title)[3] + 8
        text = self.create_text(
            center,
            y,
            text=self._description,
            anchor="n",
            justify="center",
            fill=pal.ink_2,
            font=font_spec("lead", self),
            width=HERO_TEXT_WIDTH,
            tags="content",
        )
        y = self.bbox(text)[3] + 26
        self._draw_points(center, y)
        top, bottom = self.bbox("content")[1], self.bbox("content")[3]
        self.move("content", 0, (event.height - (bottom - top)) / 2 - top)

    def _draw_points(self, center: float, top: float) -> None:
        """Рисует список преимуществ с галочками, выровненный по левому краю."""
        pal = palette()
        font = tkfont.Font(self, font=font_spec("body", self))
        check = 14
        gap = 8
        row_height = font.metrics("linespace")
        widest = max(font.measure(point) for point in self._points)
        left = center - (check + gap + widest) / 2
        icon = photo(render_icon("check", check, pal.primary, 2.5), self)
        self._images.append(icon)
        y = top
        for point in self._points:
            self.create_image(
                left, y + row_height / 2, image=icon, anchor="w", tags="content"
            )
            self.create_text(
                left + check + gap,
                y,
                text=point,
                anchor="nw",
                fill=pal.ink_2,
                font=font_spec("body", self),
                tags="content",
            )
            y += row_height + 9


class _AuthScreen(tk.Frame):
    """Общая раскладка: слева панель с описанием, справа карточка с формой."""

    def __init__(
        self,
        master: tk.Misc,
        app: "App",
        description: str,
        points: Sequence[str],
        title: str,
        subtitle: str,
        padding_y: int,
        header_gaps: Tuple[int, int, int],
    ) -> None:
        pal = palette()
        super().__init__(master, bg=pal.bg)
        self._app = app
        _HeroPanel(self, description, points).place(
            relx=0, rely=0, relwidth=HERO_SHARE, relheight=1
        )
        area = tk.Frame(self, bg=pal.bg)
        area.place(relx=HERO_SHARE, rely=0, relwidth=1 - HERO_SHARE, relheight=1)
        card = Card(area, radius=theme.MODAL_RADIUS, elevated=True)
        card.place(relx=0.5, rely=0.5, anchor="center")
        # Нарисованные виджеты (поля, кнопка) шире своей видимой части на поле
        # под тень, поэтому боковой отступ уменьшен, а обычные тексты сдвинуты.
        box = tk.Frame(
            card.body, bg=pal.card, padx=FORM_PADDING_X - SHADOW_PAD, pady=padding_y
        )
        box.pack()
        tk.Frame(
            box,
            bg=pal.card,
            width=FORM_WIDTH - 2 * FORM_PADDING_X + 2 * SHADOW_PAD,
            height=1,
        ).pack()
        brand_gap, title_gap, subtitle_gap = header_gaps
        self._header(box, "Моя аптечка", "brand", pal.primary, brand_gap)
        self._header(box, title, "heading", pal.ink, title_gap)
        self._header(box, subtitle, "body", pal.ink_2, subtitle_gap)
        self._box = box
        self._banner = ErrorBanner(box)
        self._fields: Dict[str, TextField] = {}

    def _header(
        self, box: tk.Frame, text: str, style: str, color: str, gap_below: int
    ) -> None:
        """Добавляет строку заголовка формы."""
        tk.Label(
            box,
            text=text,
            bg=box.cget("bg"),
            fg=color,
            font=font_spec(style, self),
            padx=0,
        ).pack(anchor="w", padx=SHADOW_PAD, pady=(0, gap_below))

    def _add_field(self, key: str, field: TextField, gap: int) -> TextField:
        """Добавляет поле в форму и запоминает его под именем из сервиса."""
        field.pack(fill="x", pady=(0, gap))
        field.bind_submit(self._submit)
        self._fields[key] = field
        return field

    def _add_footer(self, button_text: str, question: str, link: str, command) -> None:
        """Добавляет главную кнопку и строку «Нет аккаунта? Зарегистрироваться»."""
        pal = palette()
        Button(
            self._box, button_text, command=self._submit, variant="primary", size="lg"
        ).pack(fill="x", pady=(2, 0))
        row = tk.Frame(self._box, bg=pal.card)
        row.pack(pady=(10, 0))
        tk.Label(
            row, text=question, bg=pal.card, fg=pal.ink_2, font=font_spec("small", self)
        ).pack(side="left")
        Link(row, " " + link, command).pack(side="left")

    def _reset_errors(self) -> None:
        self._banner.hide()
        self._banner.pack_forget()
        for field in self._fields.values():
            field.clear_error()

    def _show_banner(self, message: str) -> None:
        """Показывает сообщение над первым полем формы."""
        first = next(iter(self._fields.values()))
        self._banner.show(message)
        self._banner.pack(fill="x", pady=(0, 14), before=first)

    def _show_validation_error(self, error: ValidationError) -> None:
        """Показывает ошибку под нужным полем, а если поля нет, над формой."""
        field = self._fields.get(error.field or "")
        if field is None:
            self._show_banner(error.message)
            return
        field.set_error(error.message)
        field.focus_field()

    def _submit(self) -> None:
        raise NotImplementedError


class LoginScreen(_AuthScreen):
    """Вход по логину и паролю."""

    def __init__(self, master: tk.Misc, app: "App") -> None:
        super().__init__(
            master,
            app,
            description="Удобный учёт ваших запасов лекарств и бытовых средств",
            points=(
                "Контроль сроков годности",
                "Уведомления о заканчивающихся товарах",
                "Список покупок в один клик",
            ),
            title="Вход в систему",
            subtitle="Введите свои данные, чтобы продолжить",
            padding_y=30,
            header_gaps=(18, 6, 20),
        )
        self._add_field("login", TextField(self._box, "Логин"), gap=8)
        self._add_field(
            "password", TextField(self._box, "Пароль", password=True), gap=8
        )
        self._add_footer(
            "Войти", "Нет аккаунта?", "Зарегистрироваться", app.show_register
        )
        self._fields["login"].focus_field()

    def _submit(self) -> None:
        self._reset_errors()
        try:
            user = self._app.services.auth.login(
                self._fields["login"].get(), self._fields["password"].get()
            )
        except ValidationError as error:
            self._show_validation_error(error)
        except AuthenticationError as error:
            self._show_banner(str(error))
            self._fields["password"].set_error()
        else:
            self._app.sign_in(user)


class RegisterScreen(_AuthScreen):
    """Создание аккаунта."""

    def __init__(self, master: tk.Misc, app: "App") -> None:
        super().__init__(
            master,
            app,
            description="Создайте аккаунт для управления домашними запасами",
            points=(
                "Данные хранятся локально на компьютере",
                "Пароль хранится в зашифрованном виде",
            ),
            title="Создание аккаунта",
            subtitle="Заполните данные для регистрации",
            padding_y=24,
            header_gaps=(12, 6, 14),
        )
        gap = 5
        self._add_field(
            "username",
            TextField(self._box, "Имя пользователя", placeholder="Введите имя"),
            gap,
        )
        self._add_field(
            "login",
            TextField(self._box, "Логин", placeholder="Введите логин", required=True),
            gap,
        )
        self._add_field(
            "email",
            TextField(
                self._box,
                "Электронная почта",
                placeholder="example@mail.ru",
                required=True,
            ),
            gap,
        )
        self._add_field(
            "password",
            TextField(
                self._box,
                "Пароль",
                placeholder="Не менее 8 символов",
                required=True,
                password=True,
            ),
            gap,
        )
        self._add_field(
            "password_repeat",
            TextField(
                self._box,
                "Повторите пароль",
                placeholder="Повторите пароль",
                required=True,
                password=True,
            ),
            gap,
        )
        self._add_footer(
            "Зарегистрироваться", "Уже есть аккаунт?", "Войти", app.show_login
        )
        self._fields["username"].focus_field()

    def _submit(self) -> None:
        self._reset_errors()
        values = {key: field.get() for key, field in self._fields.items()}
        try:
            user = self._app.services.auth.register(
                login=values["login"],
                username=values["username"],
                email=values["email"],
                password=values["password"],
                password_repeat=values["password_repeat"],
            )
        except ValidationError as error:
            self._show_validation_error(error)
        else:
            self._app.sign_in(user)
