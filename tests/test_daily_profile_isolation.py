import os
import json
import tempfile
import shutil
import unittest
import argparse

from main import resolve_status_filename
from utils.daily_manager import DailyManager


class TestDailyProfileIsolation(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_resolve_status_filename_by_profile_arg(self):
        """驗證當傳入 --profile 時，優先使用 daily_status_{profile}.json"""
        args = argparse.Namespace(profile="account_b", target=None)
        filename = resolve_status_filename(args, target_title="Blackfire Crusade")
        self.assertEqual(filename, "daily_status_account_b.json")

    def test_resolve_status_filename_by_sandbox_target(self):
        """驗證當 --target 為 sandbox / 2 時，解析為 daily_status_sandbox.json"""
        for t in ["sandbox", "sandboxed", "box", "sb", "2"]:
            args = argparse.Namespace(profile=None, target=t)
            filename = resolve_status_filename(args, target_title="Blackfire Crusade")
            self.assertEqual(filename, "daily_status_sandbox.json", f"Failed for target: {t}")

    def test_resolve_status_filename_by_sandbox_window_title(self):
        """驗證當視窗標題包含 [#] 時，自動解析為 daily_status_sandbox.json"""
        args = argparse.Namespace(profile=None, target=None)
        filename = resolve_status_filename(args, target_title="[#] Blackfire Crusade [#]")
        self.assertEqual(filename, "daily_status_sandbox.json")

    def test_resolve_status_filename_by_native_default(self):
        """驗證當為本機或未指定時，預設解析為 daily_status_native.json"""
        args = argparse.Namespace(profile=None, target="native")
        filename = resolve_status_filename(args, target_title="Blackfire Crusade")
        self.assertEqual(filename, "daily_status_native.json")

        args_empty = argparse.Namespace(profile=None, target=None)
        filename_empty = resolve_status_filename(args_empty, target_title="Blackfire Crusade")
        self.assertEqual(filename_empty, "daily_status_native.json")

    def test_multi_account_state_isolation(self):
        """驗證 Native 與 Sandbox 兩實例分別寫入獨立 JSON 檔，進度互不干擾"""
        native_mgr = DailyManager(data_dir=self.test_dir, status_file="daily_status_native.json")
        sandbox_mgr = DailyManager(data_dir=self.test_dir, status_file="daily_status_sandbox.json")

        # 1. Native 完成寶箱領取
        native_mgr.record_subflow_completed("chest")
        self.assertTrue(native_mgr.is_subflow_completed("chest"))
        self.assertFalse(sandbox_mgr.is_subflow_completed("chest"))

        # 2. Sandbox 接取特定懸賞任務
        sandbox_mgr.update_bulletin_board_quests(["清除史萊姆"])
        self.assertEqual(sandbox_mgr.status["subflows"]["bulletin_board"]["accepted_quests"], ["清除史萊姆"])
        self.assertEqual(native_mgr.status["subflows"]["bulletin_board"]["accepted_quests"], [])

        # 3. 重新讀取驗證磁碟持久化獨立性
        new_native = DailyManager(data_dir=self.test_dir, status_file="daily_status_native.json")
        new_sandbox = DailyManager(data_dir=self.test_dir, status_file="daily_status_sandbox.json")

        self.assertTrue(new_native.is_subflow_completed("chest"))
        self.assertFalse(new_sandbox.is_subflow_completed("chest"))
        self.assertEqual(new_sandbox.status["subflows"]["bulletin_board"]["accepted_quests"], ["清除史萊姆"])
        self.assertEqual(new_native.status["subflows"]["bulletin_board"]["accepted_quests"], [])


if __name__ == "__main__":
    unittest.main()
