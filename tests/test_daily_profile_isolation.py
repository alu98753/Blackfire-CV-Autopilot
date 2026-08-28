import os
import json
import tempfile
import shutil
import unittest
import argparse

from main import resolve_profile_name, resolve_status_filename
from utils.daily_manager import DailyManager


class TestDailyProfileIsolation(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_resolve_profile_name_by_profile_arg(self):
        """驗證當傳入 --profile 時，優先使用該 profile 名稱"""
        args = argparse.Namespace(profile="account_b", target=None)
        profile = resolve_profile_name(args, target_title="Blackfire Crusade")
        self.assertEqual(profile, "account_b")
        self.assertEqual(resolve_status_filename(args, target_title="Blackfire Crusade"), "account_b/daily_status.json")

    def test_resolve_profile_name_by_sandbox_target(self):
        """驗證當 --target 為 sandbox / 2 時，解析為 sandbox"""
        for t in ["sandbox", "sandboxed", "box", "sb", "2"]:
            args = argparse.Namespace(profile=None, target=t)
            profile = resolve_profile_name(args, target_title="Blackfire Crusade")
            self.assertEqual(profile, "sandbox", f"Failed for target: {t}")

    def test_resolve_profile_name_by_sandbox_window_title(self):
        """驗證當視窗標題包含 [#] 時，自動解析為 sandbox"""
        args = argparse.Namespace(profile=None, target=None)
        profile = resolve_profile_name(args, target_title="[#] Blackfire Crusade [#]")
        self.assertEqual(profile, "sandbox")

    def test_resolve_profile_name_by_native_default(self):
        """驗證當為本機或未指定時，預設解析為 native"""
        args = argparse.Namespace(profile=None, target="native")
        profile = resolve_profile_name(args, target_title="Blackfire Crusade")
        self.assertEqual(profile, "native")

        args_empty = argparse.Namespace(profile=None, target=None)
        profile_empty = resolve_profile_name(args_empty, target_title="Blackfire Crusade")
        self.assertEqual(profile_empty, "native")

    def test_multi_account_directory_state_isolation(self):
        """驗證 Native 與 Sandbox 兩實例分別寫入獨立目錄下的 daily_status.json，進度互不干擾"""
        native_mgr = DailyManager(data_dir=self.test_dir, profile="native")
        sandbox_mgr = DailyManager(data_dir=self.test_dir, profile="sandbox")

        self.assertTrue(native_mgr.file_path.endswith(os.path.join("native", "daily_status.json")))
        self.assertTrue(sandbox_mgr.file_path.endswith(os.path.join("sandbox", "daily_status.json")))

        # 1. Native 完成寶箱領取
        native_mgr.record_subflow_completed("chest")
        self.assertTrue(native_mgr.is_subflow_completed("chest"))
        self.assertFalse(sandbox_mgr.is_subflow_completed("chest"))

        # 2. Sandbox 接取特定懸賞任務
        sandbox_mgr.update_bulletin_board_quests(["清除史萊姆"])
        self.assertEqual(sandbox_mgr.status["subflows"]["bulletin_board"]["accepted_quests"], ["清除史萊姆"])
        self.assertEqual(native_mgr.status["subflows"]["bulletin_board"]["accepted_quests"], [])

        # 3. 重新讀取驗證磁碟持久化獨立性
        new_native = DailyManager(data_dir=self.test_dir, profile="native")
        new_sandbox = DailyManager(data_dir=self.test_dir, profile="sandbox")

        self.assertTrue(new_native.is_subflow_completed("chest"))
        self.assertFalse(new_sandbox.is_subflow_completed("chest"))
        self.assertEqual(new_sandbox.status["subflows"]["bulletin_board"]["accepted_quests"], ["清除史萊姆"])
        self.assertEqual(new_native.status["subflows"]["bulletin_board"]["accepted_quests"], [])


if __name__ == "__main__":
    unittest.main()
