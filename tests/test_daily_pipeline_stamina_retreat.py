import unittest
import time
import os
import sys
import shutil
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.daily_manager import DailyManager
from utils.quest_scheduler import QuestScheduler, TaskNode
from states.state_machine import GameStateMachine
from config import GAME_CONFIGS

class TestDailyPipelineStaminaRetreat(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.status_file = os.path.join(self.test_dir, "daily_status.json")
        self.daily_manager = DailyManager(status_file=self.status_file)

        mock_capturer = MagicMock()
        mock_matcher = MagicMock()
        mock_mouse = MagicMock()
        self.state_machine = GameStateMachine(capturer=mock_capturer, matcher=mock_matcher, mouse=mock_mouse)
        self.state_machine.daily_manager = self.daily_manager

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_prohibit_accepted_quests_during_collect_only_mode(self):
        """
        [Requirement B 斷言] 驗證當 active config 為 collect_only 時 (is_in_collect_only_mode() == True)，
        is_daily_pipeline_active() 必定回傳 False，徹底禁止排程推進 accepted_quests 懸賞任務。
        """
        self.state_machine.config = GAME_CONFIGS["collect_only"].copy()
        self.state_machine.quest_scheduler = MagicMock()

        self.assertTrue(self.state_machine.is_in_collect_only_mode())
        self.assertFalse(self.state_machine.is_daily_pipeline_active())
        self.assertFalse(self.state_machine.evaluate_and_schedule_daily_pipeline())

    def test_dungeon_resume_prioritizes_accepted_quests_over_tier4_fallback(self):
        """
        [Requirement A 斷言] 驗證地下城 Resume 復歸切回 daily 模式時：
        - 若 accepted_quests 中有未完成的懸賞地下城 (Tier 3)，Daily Master Pipeline 優先執行 accepted_quests 的地下城。
        - 若 accepted_quests 已全清，才退守至 Tier 4 指定地下城。
        """
        daily_cfg = GAME_CONFIGS["daily"].copy()
        self.state_machine.config = daily_cfg
        self.state_machine.primary_config = daily_cfg

        # 1. 建立包含地下城 #1 懸賞任務的 QuestScheduler
        node1 = TaskNode("史萊姆王的毀滅", "dungeon", dungeon_index=0)
        scheduler = QuestScheduler(daily_manager=self.daily_manager)
        scheduler.add_task(node1)
        self.state_machine.quest_scheduler = scheduler

        # 模擬 Tier 1/2 皆無任務可做，觸發 evaluate_and_schedule_daily_pipeline
        for sf in self.daily_manager.status.get("subflows", {}).values():
            sf["completed_today"] = True
        for b in self.daily_manager.status["subflows"]["lord_boss"]["bosses"].values():
            b["today_count"] = 5
            b["completed_today"] = True

        scheduled = self.state_machine.evaluate_and_schedule_daily_pipeline()
        self.assertTrue(scheduled)
        self.assertEqual(self.state_machine.config["name"], "懸賞任務 - 黏糊糊的石窟 (任務: 史萊姆王的毀滅)")
        self.assertEqual(self.state_machine.config["dungeon_index"], 0)

        # 2. 懸賞全清後，再次觸發調度 ➔ 斷言退守 Tier 4 Mix 指定配置
        node1.completed_count = node1.target_count
        scheduled_fallback = self.state_machine.evaluate_and_schedule_daily_pipeline()
        self.assertFalse(scheduled_fallback) # apply_mix_fallback_config returns False
        self.assertTrue(self.state_machine.config.get("is_tier4_fallback", False))

    def test_dungeon_resume_executes_designated_tier4_fallback_dungeon_during_retreat(self):
        """
        [使用者指定退守驗證] 驗證當處於體力退避倒數期間 (stamina_retreat_start_time 存在)，
        地下城冷卻結束 (auto_resume) 切回時，Daily Master Pipeline 必定精準執行使用者設定之 Tier 4 退守地下城，
        而不是嘗試執行 accepted_quests 中的任務。
        """
        daily_cfg = GAME_CONFIGS["daily"].copy()
        # 假設使用者 CLI 選定了 Tier 4 退守地下城 #5 (冰雪洞窟, index 4)
        tier4_cfg = {
            "name": "每日懸賞任務 - 冰雪洞窟 (關卡: default)",
            "type": "mix",
            "dungeon_index": 4,
            "is_tier4_fallback": True,
            "auto_resume_dungeon_on_cd": True
        }
        self.state_machine.config = daily_cfg
        self.state_machine.primary_config = tier4_cfg.copy()

        # 設定 accepted_quests 裡面有其他懸賞任務 (例如地下城 #1 史萊姆, index 0)
        node1 = TaskNode("史萊姆王的毀滅", "dungeon", dungeon_index=0)
        scheduler = QuestScheduler(daily_manager=self.daily_manager)
        scheduler.add_task(node1)
        self.state_machine.quest_scheduler = scheduler

        # 模擬正處於體力退避倒數中
        self.state_machine.stamina_retreat_start_time = time.time() - 600.0

        # 觸發調度 ➔ 斷言必須執行 primary_config 中指定的 Tier 4 退守地下城 (#5 冰雪洞窟, index 4)，而非 accepted_quests (#1 史萊姆, index 0)
        scheduled = self.state_machine.evaluate_and_schedule_daily_pipeline()
        self.assertTrue(scheduled)
        self.assertEqual(self.state_machine.config["dungeon_index"], 4)
        self.assertTrue(self.state_machine.config.get("is_tier4_fallback", False))

    def test_stamina_retreat_timestamp_preserved_across_re_retreat(self):
        """
        [防護斷言] 驗證從 collect_only Resume 切回打地下城，但實機無體力再次撞到 no_bread 時，
        stamina_flow.py 能保留原始 stamina_retreat_start_time 倒數而不被覆蓋重置。
        """
        from states.stamina_flow import handle_insufficient_stamina

        original_ts = time.time() - 300.0  # 模擬已退避 5 分鐘
        self.state_machine.original_config = GAME_CONFIGS["daily"].copy()
        self.state_machine.stamina_retreat_start_time = original_ts
        self.state_machine.config = GAME_CONFIGS["daily"].copy()

        # 模擬 match 到 no_bread/no_bread.png
        self.state_machine.matcher.match.side_effect = lambda img, temp, **kw: ((100, 100), 0.95) if temp == "no_bread/no_bread.png" else (None, 0.0)

        with patch('os.path.exists', return_value=True):
            triggered = handle_insufficient_stamina(self.state_machine, None, {"left": 0, "top": 0, "width": 1000, "height": 800})

        self.assertTrue(triggered)
        self.assertEqual(self.state_machine.stamina_retreat_start_time, original_ts)
        self.assertTrue(self.state_machine.is_in_collect_only_mode())

if __name__ == '__main__':
    unittest.main()
