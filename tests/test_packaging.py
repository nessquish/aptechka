"""Тесты упаковки: путь к данным у .exe, журнал ошибок, значок приложения."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pharmacy import config, crashlog


class DataPathTest(unittest.TestCase):
    def test_from_sources_data_lies_in_the_project(self):
        with mock.patch.object(sys, "frozen", False, create=True):
            path = config._default_db_path()
        self.assertEqual(path, config.PROJECT_ROOT / "data" / "aptechka.db")

    def test_exe_keeps_data_in_the_user_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(sys, "frozen", True, create=True):
                with mock.patch.dict(os.environ, {"LOCALAPPDATA": tmp}):
                    path = config._default_db_path()
        self.assertEqual(path, Path(tmp) / "Моя аптечка" / "data" / "aptechka.db")

    def test_exe_falls_back_to_the_home_folder(self):
        env = {k: v for k, v in os.environ.items() if k != "LOCALAPPDATA"}
        with mock.patch.object(sys, "frozen", True, create=True):
            with mock.patch.dict(os.environ, env, clear=True):
                path = config._default_db_path()
        self.assertEqual(path.parent.parent.parent, Path.home())

    def test_environment_override_still_wins(self):
        with mock.patch.dict(os.environ, {config.DB_PATH_ENV: "C:/x/test.db"}):
            self.assertEqual(config.get_db_path(), Path("C:/x/test.db"))


class CrashLogTest(unittest.TestCase):
    def folder(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def test_report_contains_error_and_time(self):
        path = crashlog.write_report(ValueError("сломалось"), self.folder() / "e.log")
        text = path.read_text(encoding="utf-8")
        self.assertIn("ValueError: сломалось", text)
        self.assertRegex(text, r"--- \d{4}-\d\d-\d\d \d\d:\d\d:\d\d ---")

    def test_reports_are_appended(self):
        path = self.folder() / "sub" / "e.log"
        crashlog.write_report(ValueError("первая"), path)
        crashlog.write_report(KeyError("вторая"), path)
        text = path.read_text(encoding="utf-8")
        self.assertIn("первая", text)
        self.assertIn("вторая", text)

    def test_log_lies_next_to_the_database(self):
        with mock.patch.dict(os.environ, {config.DB_PATH_ENV: "C:/data/aptechka.db"}):
            self.assertEqual(crashlog.log_path(), Path("C:/data/error.log"))

    def test_normal_run_is_left_alone(self):
        calls = []
        crashlog.run_with_report(lambda: calls.append(1))
        self.assertEqual(calls, [1])

    def test_failure_is_logged_shown_and_exits(self):
        log = self.folder() / "e.log"

        def broken():
            raise RuntimeError("не запустилось")

        with mock.patch.object(crashlog, "log_path", return_value=log):
            with mock.patch.object(crashlog, "show_message") as shown:
                with self.assertRaises(SystemExit) as context:
                    crashlog.run_with_report(broken)
        self.assertEqual(context.exception.code, 1)
        shown.assert_called_once()
        self.assertIn("не запустилось", log.read_text(encoding="utf-8"))

    def test_message_window_failure_is_swallowed(self):
        with mock.patch(
            "PySide6.QtWidgets.QMessageBox.critical",
            side_effect=RuntimeError("нет экрана"),
        ):
            crashlog.show_message(Path("e.log"), ValueError("x"))

    def test_message_window_shows_the_error_and_the_log_path(self):
        with mock.patch("PySide6.QtWidgets.QMessageBox.critical") as box:
            crashlog.show_message(Path("e.log"), ValueError("сломалось"))
        text = box.call_args.args[2]
        self.assertIn("сломалось", text)
        self.assertIn("e.log", text)


if __name__ == "__main__":
    unittest.main()
