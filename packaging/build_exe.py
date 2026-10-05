"""Сборка программы в один файл Aptechka.exe.

Запуск из папки проекта::

    .venv\\Scripts\\python.exe packaging\\build_exe.py

Результат: ``dist/Aptechka.exe``. Файл можно скопировать на другой компьютер с
Windows: Python на нём не нужен. Данные программы (база и настройки) хранятся
в ``%LOCALAPPDATA%\\Моя аптечка`` и сохраняются между запусками.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import PyInstaller.__main__  # noqa: E402

from pharmacy.ui.appicon import ICON_SIZES, render_app_icon  # noqa: E402

BUILD_DIR = ROOT / "build"
ICON_FILE = BUILD_DIR / "aptechka.ico"
ENTRY = ROOT / "packaging" / "launcher.py"
FONTS = ROOT / "pharmacy" / "ui" / "assets" / "fonts"
EXE_NAME = "Aptechka"


def make_icon() -> Path:
    """Рисует значок и сохраняет его как .ico со всеми размерами."""
    BUILD_DIR.mkdir(exist_ok=True)
    biggest = render_app_icon(max(ICON_SIZES))
    biggest.save(ICON_FILE, sizes=[(size, size) for size in ICON_SIZES])
    return ICON_FILE


def build() -> None:
    """Запускает PyInstaller."""
    icon = make_icon()
    PyInstaller.__main__.run(
        [
            str(ENTRY),
            "--name",
            EXE_NAME,
            "--onefile",
            "--noconsole",
            "--clean",
            "--noconfirm",
            "--icon",
            str(icon),
            # Библиотека иконок svg.path импортирует pkgutil, а PyInstaller этого
            # не замечает, поэтому модуль подключается явно.
            "--hidden-import",
            "pkgutil",
            "--collect-submodules",
            "svg.path",
            # Шрифт Inter читается из файлов, поэтому кладём их внутрь программы.
            "--add-data",
            f"{FONTS};pharmacy/ui/assets/fonts",
            "--paths",
            str(ROOT),
            "--distpath",
            str(ROOT / "dist"),
            "--workpath",
            str(BUILD_DIR / "work"),
            "--specpath",
            str(BUILD_DIR),
        ]
    )


if __name__ == "__main__":
    build()
