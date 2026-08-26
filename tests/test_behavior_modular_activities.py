import unittest
from unittest.mock import MagicMock, patch
import time

from states.handlers.collect_only import CollectOnlyHandler
from states.handlers.navigation import NavigationHandler
from states.handlers.lobby import LobbyHandler
from states.state_machine import GameStateMachine


class TestBehaviorModularActivities(unittest.TestCase):
    """
    模組化活動組合與基底待機調度行為測試集 (Behavior-Driven Testing)
    專注於 Given 模組配置與冷卻狀態 ➔ When 觸發狀態處理 ➔ Then 斷言外部可觀察行為與狀態轉移契約
    """

    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_capturer.hwnd = 12345
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.state_machine = GameStateMachine(self.mock_capturer, self.mock_matcher, self.mock_mouse)
        self.state_machine.daily_manager = MagicMock()
        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    # =========================================================================
    # 場景 1：純領取養老行為 (Pure Collect Only Scenario)
    # =========================================================================

    def test_scenario_1_pure_collect_only_no_periodic_triggers(self):
        """
        [Scenario 1 Behavior Test]
        Given: 配置為純領取模式 (enable_lord_boss=False, enable_dungeon=False, enable_stage_farming=False)
        When: 狀態機處於 COLLECT_ONLY，且畫面在城鎮，即便日常管理器顯示 Boss/地下城就緒
        Then: 系統絕不發起 LORD_BOSS 或地下城導航，維持在城鎮待機
        """
        self.state_machine.config = {
            "name": "純領取待機",
            "type": "collect_only",
            "auto_diamond": True,
            "auto_bread": True,
            "enable_lord_boss": False,
            "enable_dungeon": False,
            "enable_stage_farming": False,
            "enable_town_daily": False,
            "enable_quests": False
        }
        self.state_machine.current_state = self.state_machine.STATE_COLLECT_ONLY
        self.state_machine.need_diamond_collection = False
        self.state_machine.need_bread_collection = False
        self.state_machine.daily_manager.has_available_lord_boss.return_value = True
        self.state_machine.has_available_dungeon = MagicMock(return_value=True)

        handler = self.state_machine.handlers[self.state_machine.STATE_COLLECT_ONLY]
        handler.matcher = MagicMock()
        # 畫面在城鎮 (door.png 存在)
        handler.matcher.match.side_effect = lambda img, temp, *args, **kwargs: ((300, 400), 0.90) if temp == "common/door.png" else (None, 0.0)

        mock_img = MagicMock()
        handler.handle(mock_img, self.rect)

        # 斷言：絕不發起 town subflow queue，狀態維持在 COLLECT_ONLY
        self.assertEqual(len(self.state_machine.town_subflow_queue), 0)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)

    # =========================================================================
    # 場景 2：Boss + 待機週期行為 (Boss + Collect Only, No Farming)
    # =========================================================================

    def test_scenario_2_boss_and_collect_only_lifecycle(self):
        """
        [Scenario 2 Behavior Test]
        Given: 啟用 enable_lord_boss=True，但關閉 enable_dungeon=False 與 enable_stage_farming=False
        When 1: 在 COLLECT_ONLY 待機中，Boss 冷卻中 (has_available_lord_boss=False)
        Then 1: 維持在城鎮待機，不觸發任何戰鬥
        When 2: Boss 冷卻結束 (has_available_lord_boss=True)
        Then 2: CollectOnlyHandler 自動被喚醒，發起 ["lord_boss"] 子流程佇列
        """
        self.state_machine.config = {
            "name": "Boss + 待機",
            "type": "collect_only",
            "auto_diamond": True,
            "auto_bread": True,
            "enable_lord_boss": True,
            "enable_dungeon": False,
            "enable_stage_farming": False,
            "enable_town_daily": False,
            "enable_quests": False
        }
        self.state_machine.current_state = self.state_machine.STATE_COLLECT_ONLY
        self.state_machine.need_diamond_collection = False
        self.state_machine.need_bread_collection = False

        handler = self.state_machine.handlers[self.state_machine.STATE_COLLECT_ONLY]
        handler.matcher = MagicMock()
        handler.matcher.match.side_effect = lambda img, temp, *args, **kwargs: ((300, 400), 0.90) if temp == "common/door.png" else (None, 0.0)
        mock_img = MagicMock()

        # Step 1: Boss 冷卻中
        self.state_machine.daily_manager.has_available_lord_boss.return_value = False
        handler.handle(mock_img, self.rect)
        self.assertEqual(len(self.state_machine.town_subflow_queue), 0)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)

        # Step 2: Boss 冷卻結束就緒
        self.state_machine.daily_manager.has_available_lord_boss.return_value = True
        self.state_machine.daily_manager.get_available_lord_bosses.return_value = ["lord_spider"]
        handler.handle(mock_img, self.rect)

        # 斷言：自動喚醒並轉移至 LORD_BOSS
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LORD_BOSS)

    # =========================================================================
    # 場景 3：地下城 + Boss + 待機行為 (Dungeon + Boss + Collect Only)
    # =========================================================================

    def test_scenario_3_dungeon_and_boss_cooldown_to_collect_only_and_wake_up(self):
        """
        [Scenario 3 Behavior Test]
        Given: 啟用 enable_dungeon=True, enable_lord_boss=True, enable_stage_farming=False
        When 1: 在導航中地下城全冷卻
        Then 1: 導航處理器點擊 goback_town.png 並轉移至 COLLECT_ONLY 待機，絕不切換到 select_stage.png
        When 2: 在 COLLECT_ONLY 待機期間，地下城冷卻結束 (has_available_dungeon=True)
        Then 2: CollectOnlyHandler 自動喚醒並轉移至 STATE_NAVIGATING
        """
        self.state_machine.config = {
            "name": "地下城+Boss+待機",
            "type": "mix",
            "dungeon_names": ["Slime", "Ghost", "Forest", "Ruins", "Ice"],
            "greedy_allowed_indices": [0, 1, 2, 3, 4],
            "enable_lord_boss": True,
            "enable_dungeon": True,
            "enable_stage_farming": False,
            "enable_town_daily": False,
            "enable_quests": False
        }
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        nav_handler = self.state_machine.handlers[self.state_machine.STATE_NAVIGATING]
        nav_handler.matcher = MagicMock()
        # 模擬地下城全冷卻，畫面上出現 goback_town.png 與 select_stage.png
        nav_handler.matcher.match.side_effect = lambda img, temp, *args, **kwargs: (
            ((100, 100), 0.90) if temp == "goback_town.png" else (
            ((200, 200), 0.90) if temp == "common/select_stage.png" else (None, 0.0))
        )

        # Step 1: 觸發地下城全冷卻處理
        mock_img = MagicMock()
        nav_handler._switch_to_stage_or_back(mock_img, self.rect, "所有地下城冷卻中")

        # 斷言：點擊 goback_town (100, 100)，絕不點擊 select_stage，並轉移至 COLLECT_ONLY
        self.mock_mouse.click.assert_called_with(100, 100)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)

        # Step 2: 待機期間地下城 CD 結束喚醒
        collect_handler = self.state_machine.handlers[self.state_machine.STATE_COLLECT_ONLY]
        collect_handler.matcher = MagicMock()
        collect_handler.matcher.match.side_effect = lambda img, temp, *args, **kwargs: ((300, 400), 0.90) if temp == "common/door.png" else (None, 0.0)
        self.state_machine.daily_manager.has_available_lord_boss.return_value = False
        self.state_machine.has_available_dungeon = MagicMock(return_value=True)

        collect_handler.handle(mock_img, self.rect)

        # 斷言：自動喚醒並轉移至 NAVIGATING
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)

    # =========================================================================
    # 場景 4：全自動耗體推圖行為 (Full Auto with Stage Farming)
    # =========================================================================

    def test_scenario_4_full_auto_with_stage_farming_fallback(self):
        """
        [Scenario 4 Behavior Test]
        Given: 啟用 enable_stage_farming=True, enable_dungeon=True, enable_lord_boss=True
        When: 地下城全冷卻時
        Then: 導航處理器正確點擊 common/select_stage.png 切換至普通關卡頁籤打怪
        """
        self.state_machine.config = {
            "name": "全自動推圖",
            "type": "mix",
            "dungeon_names": ["Slime", "Ghost", "Forest", "Ruins", "Ice"],
            "greedy_allowed_indices": [0, 1, 2, 3, 4],
            "enable_lord_boss": True,
            "enable_dungeon": True,
            "enable_stage_farming": True,
            "enable_town_daily": True,
            "enable_quests": False
        }
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        nav_handler = self.state_machine.handlers[self.state_machine.STATE_NAVIGATING]
        nav_handler.matcher = MagicMock()
        nav_handler.matcher.match.side_effect = lambda img, temp, *args, **kwargs: (
            ((250, 250), 0.90) if temp == "common/select_stage.png" else (
            ((100, 100), 0.90) if temp == "goback_town.png" else (None, 0.0))
        )

        mock_img = MagicMock()
        nav_handler._switch_to_stage_or_back(mock_img, self.rect, "所有地下城冷卻中")

        # 斷言：點擊 select_stage (250, 250) 進入普通關卡頁籤
        self.mock_mouse.click.assert_called_with(250, 250)

    # =========================================================================
    # 場景 5：08:05 跨日重置與待機喚醒行為 (Daily Reset Awakening)
    # =========================================================================

    def test_scenario_5_daily_reset_awakening_in_collect_only(self):
        """
        [Scenario 5 Behavior Test]
        Given: 系統處於 COLLECT_ONLY 待機中，且觸發了 pending_daily_reset_exit=True (跨越 08:05)
        When: CollectOnlyHandler.handle() 執行
        Then: 立即結束待機，重置標記並呼叫 trigger_town_subflow_chain() 發起全新一日城鎮流水線
        """
        self.state_machine.config = {
            "name": "待機配置",
            "type": "collect_only",
            "auto_diamond": True,
            "auto_bread": True,
            "enable_town_daily": True
        }
        self.state_machine.current_state = self.state_machine.STATE_COLLECT_ONLY
        self.state_machine.pending_daily_reset_exit = True
        self.state_machine.stamina_retreat_start_time = time.time()
        self.state_machine.original_config = {"name": "原模式", "type": "mix"}
        self.state_machine.trigger_town_subflow_chain = MagicMock()

        handler = self.state_machine.handlers[self.state_machine.STATE_COLLECT_ONLY]
        mock_img = MagicMock()
        handler.handle(mock_img, self.rect)

        # 斷言：標記清除，退避時間清空，並觸發城鎮流水線
        self.assertFalse(self.state_machine.pending_daily_reset_exit)
        self.assertIsNone(self.state_machine.stamina_retreat_start_time)
        self.state_machine.trigger_town_subflow_chain.assert_called_once()

    # =========================================================================
    # 場景 6：真實 DailyManager 整合與待機日誌格式化驗證
    # =========================================================================

    def test_scenario_6_collect_only_with_real_daily_manager_boss_cooldown_formatting(self):
        """
        [Scenario 6 Regression Test]
        Given: 啟用 enable_lord_boss=True，並搭載真實 DailyManager 物件
        When: 處於 COLLECT_ONLY 待機狀態且 Boss 在冷卻中
        Then: handle() 正常執行日誌格式化輸出，不拋出 AttributeError (get_boss_status_dict)
        """
        from utils.daily_manager import DailyManager
        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()
        try:
            real_dm = DailyManager(data_dir=temp_dir, status_file="test_status.json")
            # 模擬所有 Boss 均處於冷卻中
            now_ts = time.time()
            real_dm.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]["last_fight_timestamp"] = now_ts
            real_dm.status["subflows"]["lord_boss"]["bosses"]["lord_spectre"]["last_fight_timestamp"] = now_ts
            self.state_machine.daily_manager = real_dm
            self.state_machine.config = {
                "name": "待機Boss監控",
                "type": "collect_only",
                "auto_diamond": True,
                "auto_bread": True,
                "enable_lord_boss": True,
                "enable_dungeon": False
            }
            self.state_machine.current_state = self.state_machine.STATE_COLLECT_ONLY
            self.state_machine.need_diamond_collection = False
            self.state_machine.need_bread_collection = False

            handler = self.state_machine.handlers[self.state_machine.STATE_COLLECT_ONLY]
            handler.matcher = MagicMock()
            handler.matcher.match.side_effect = lambda img, temp, *args, **kwargs: ((300, 400), 0.90) if temp == "common/door.png" else (None, 0.0)

            mock_img = MagicMock()
            # 必須正常執行不拋出任何 AttributeError 例外
            handler.handle(mock_img, self.rect)
            self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
