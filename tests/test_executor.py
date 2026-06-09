import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from desktop_agent.actions.executor import ActionExecutor


class ExecutorTests(unittest.TestCase):
    def test_windows_alias_matches_foreground_process_name(self):
        executor = ActionExecutor()
        expected = executor._expected_app_names("Microsoft Edge", "msedge")

        self.assertTrue(executor._window_matches_app("msedge.exe", expected))

    def test_app_match_ignores_paths_and_exe_suffix(self):
        executor = ActionExecutor()
        expected = executor._expected_app_names("notepad", "notepad")

        self.assertTrue(
            executor._window_matches_app(
                r"C:\Windows\System32\notepad.exe",
                expected,
            )
        )

    def test_wechat_alias_matches_weixin_process_name(self):
        executor = ActionExecutor()
        expected = executor._expected_app_names("WeChat", "Weixin.exe")

        self.assertTrue(executor._window_matches_app("Weixin.exe", expected))

    def test_start_menu_shortcut_skips_uninstall_entries(self):
        executor = ActionExecutor()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "微信"
            folder.mkdir()
            (folder / "卸载微信.lnk").write_text("", encoding="utf-8")
            shortcut = folder / "微信.lnk"
            shortcut.write_text("", encoding="utf-8")

            found = executor._windows_find_start_menu_shortcut(
                {"微信", "wechat", "weixin"},
                roots=[root],
            )

        self.assertEqual(found, shortcut)


if __name__ == "__main__":
    unittest.main()
