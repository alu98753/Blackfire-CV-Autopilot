import os
import json
import time
import tempfile
import shutil
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from states.handlers.hero_draw import HeroDrawHandler
from utils.daily_manager import DailyManager, DEFAULT_DAILY_STATUS
from states.state_machine import GameStateMachine
from utils.town_building_detector import BuildingCheckResult

class TestBehaviorTownSubflows(unittest.TestCase):
    """
    城鎮獨立子流程行為測試集 (Google Software Dev Standard)
    專注於 Given 城鎮建築與彈窗情境 ➔ When 觸發 handle ➔ Then 斷言子流程確信點擊與狀態轉移
    """
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.config = {
            "name": "抽英雄",
            "type": "hero_draw",
            "building_btn": "town_building/Tavern/Tavern.png",
            "recruitment_btn": "town_building/Tavern/free_recruitment.png"
        }
        self.mock_machine.matcher = MagicMock()
        self.mock_machine.mouse = MagicMock()
        self.mock_daily_manager = MagicMock()
        self.mock_machine.daily_manager = self.mock_daily_manager

        self.rect = {"left": 0, "top": 0, "width": 800, "height": 600}

    # =========================================================================
    # 4.1 酒館分解英雄行為測試
    # =========================================================================

    @patch("os.path.exists")
    def test_4_1_hero_draw_deassemble_hero_clicks_and_claims_fragments(self, mock_exists):
        """
        [4.1 Behavior Test]
        Given: 酒館抽英雄處於 WAITING_CONFIRM 階段，畫面出現 deassemble_hero.png 按鈕
        When: 執行 HeroDrawHandler.handle()
        Then: 呼叫 machine.click_and_wait_until_gone() 點擊分解英雄並領取碎片
        """
        handler = HeroDrawHandler(self.mock_machine)
        handler.step_phase = "WAITING_CONFIRM"

        mock_img = MagicMock()
        mock_exists.side_effect = lambda p: "deassemble_hero.png" in p.replace("\\", "/")

        def fake_match(img, template, threshold=0.75, brightness_threshold=0.0, *args, **kwargs):
            if "deassemble_hero.png" in template and brightness_threshold == 0.85:
                return ((300, 400), 0.88)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        res = handler.handle(mock_img, self.rect)

        # 斷言 handle 回傳 True
        self.assertTrue(res)
        # 帶入確信點擊與消失輪詢
        self.mock_machine.click_and_wait_until_gone.assert_called_once_with(
            "town_building/Tavern/deassemble_hero.png",
            300, 400, self.rect,
            timeout=5.0, threshold=0.75, brightness_threshold=0.85, check_interval=0.25, post_delay=0.5
        )

    # =========================================================================
    # 4.2 血之祭壇領血與獻祭離散狀態閉環測試
    # =========================================================================

    def test_4_2_blood_altar_completes_records_dm_and_pops_next_subflow(self):
        """
        [4.2 Behavior Test]
        Given: 血之祭壇處於 ALL_DONE_EXITING 階段，畫面偵測到城鎮標誌 common/door.png
        When: 執行 BloodAltarHandler.handle()
        Then: 呼叫 daily_manager.record_subflow_completed("blood_altar") 寫入紀錄，need_blood_altar 設為 False，且呼叫 pop_and_next_town_subflow() 自動跳轉下一個任務
        """
        from states.handlers.blood_altar import BloodAltarHandler
        import time

        handler = BloodAltarHandler(self.mock_machine)
        handler.step_phase = "ALL_DONE_EXITING"
        handler.last_action_time = time.time() - 2.0
        self.mock_machine.need_blood_altar = True

        mock_img = MagicMock()

        def fake_match(img, template, threshold=0.75, *args, **kwargs):
            if template == "common/door.png":
                return ((100, 100), 0.88)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        handler.handle(mock_img, self.rect)

        # 驗證 daily_manager 記錄完成
        self.mock_daily_manager.record_subflow_completed.assert_called_once_with("blood_altar")
        # 驗證 need_blood_altar 設為 False
        self.assertFalse(self.mock_machine.need_blood_altar)
        # 驗證彈出並消費下一個城鎮任務
        self.mock_machine.pop_and_next_town_subflow.assert_called_once()

    # =========================================================================
    # 4.3 懸賞告示牌與動態調度行為測試
    # =========================================================================

    def test_4_3_quest_mapper_corrects_typos_and_creates_valid_config(self):
        """
        [4.3 Behavior Test]
        Given: 懸賞 OCR 解析出包含錯字之任務名稱 "討伐忠魔"
        When: 呼叫 normalize_quest_title 正名與 QuestMapper().parse_quest("討伐忠魔") 進行轉換
        Then: 自動修正為正名 "討伐惡魔"，且產出對應之 stage 模式 TaskNode 與 config (stage_level=6, sub_stage="six")
        """
        from utils.quest_mapper import QuestMapper, normalize_quest_title

        norm_title = normalize_quest_title("討伐忠魔")
        self.assertEqual(norm_title, "討伐惡魔")

        mapper = QuestMapper()
        node = mapper.parse_quest(norm_title)
        self.assertIsNotNone(node)
        self.assertEqual(node.mode_type, "stage")
        self.assertEqual(node.stage_level, 6)
        self.assertEqual(node.sub_stage, "six")

        cfg = node.to_config_dict()
        self.assertEqual(cfg["type"], "stage")
        self.assertEqual(cfg["stage_level"], 6)


class TestTownSubflowRedDotRetryLifecycle(unittest.TestCase):
    """
    城鎮子流程紅點未消除之重試與動態調度生命週期行為測試集
    驗證使用者核心訴求：
    當退出後發現仍有紅點時不標記完成 (completed_today=False)；
    當機器人下一次回到城鎮（例如刷完關卡背包滿回城、或觸發 ActivityScheduler 定期調度）時，
    系統再次調用 daily_manager.get_pending_town_subflows()。
    由於該任務未標記完成，它會再次出現在待辦佇列中，機器人會重新走進該建築執行領取，
    直到紅點真正消失並成功結案為止。
    """
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_json_path = os.path.join(self.test_dir, "test_daily_status.json")
        sample_status = json.loads(json.dumps(DEFAULT_DAILY_STATUS))
        with open(self.test_json_path, "w", encoding="utf-8") as f:
            json.dump(sample_status, f, ensure_ascii=False, indent=2)

        self.daily_mgr = DailyManager(data_dir=self.test_dir, status_file="test_daily_status.json")

        self.mock_subflow_configs = {
            "chest": {"enabled": True, "name": "寶箱領取"},
            "hero_draw": {"enabled": True, "name": "英雄召喚"},
            "blood_altar": {"enabled": True, "name": "血之祭壇獻祭"},
            "jewelry_workshop": {"enabled": True, "name": "珠寶加工廠出售"},
            "bulletin_board": {"enabled": True, "name": "懸賞告示牌"},
        }
        self.patcher = patch("config.SUBFLOW_CONFIGS", self.mock_subflow_configs)
        self.patcher.start()

        self.mock_daily_cfg = {
            "type": "daily",
            "name": "每日全流程",
            "enable_town_daily": True,
            "enable_lord_boss": False,
            "enable_quests": False,
            "enable_dungeon": False,
            "enable_stage_farming": False,
        }

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def dispatch_after_town_precondition(self, sm, screen, rect):
        sm.current_state = sm.STATE_NAVIGATING
        sm.matcher.match.side_effect = lambda _img, name, **_kw: (
            ((200, 550), 0.95)
            if name == "common/door.png"
            else (None, 0.0)
        )
        entry = BuildingCheckResult(
            True,
            True,
            building_pos=(200, 200),
            confidence_building=0.9,
        )
        with patch(
            "states.town_subflow_perception.detect_building_with_red_dot",
            return_value=entry,
        ):
            self.assertTrue(sm.handle_town_subflow_precondition(screen, rect))

    @patch("os.path.exists", return_value=True)
    def test_activity_scheduler_re_dispatches_chest_when_red_dot_remains_until_dismissed(self, mock_exists):
        """
        [驗證 ActivityScheduler 3 分鐘 Defer 冷卻與回城觸發重試閉環]
        1. 第一次在城鎮執行 chest 領取，退出後因紅點仍存在而不標記完成 (completed_today=False)。
        2. 立即進入 180 秒 Defer 冷卻退避，斷言在 180 秒內 (10s, 60s, 179s) 100% 遮蔽，不原地重複派發。
        3. 180 秒後 (181s)，chest 自動重現於 get_pending_town_subflows()。
        4. 當回城/調度器評估時，重新走進建築重試。
        5. 第二次執行領取後退出，紅點成功消除，標記 completed_today=True 且解除 Defer。
        6. 後續再次調度時，get_pending_town_subflows() 已無 chest，達到終態結案閉環。
        """
        # 標記其他四項已完成，僅保留 chest 待辦
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
        self.daily_mgr.record_subflow_completed("bulletin_board")
        self.assertEqual(self.daily_mgr.get_pending_town_subflows(), ["chest"])

        # 初始化狀態機
        mock_matcher = MagicMock()
        mock_matcher.templates_dir = "templates"
        sm = GameStateMachine(capturer=MagicMock(), matcher=mock_matcher, mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        sm.runtime_config_key = "daily"
        sm.primary_config = self.mock_daily_cfg.copy()
        sm.set_config(self.mock_daily_cfg.copy())
        sm.get_available_selected_lord_bosses = MagicMock(return_value=[])
        sm.quest_scheduler = None

        # 第 1 輪調度：觸發城鎮流水線
        scheduled = sm.evaluate_and_schedule_daily_pipeline()
        self.assertTrue(scheduled)
        fake_screen = np.zeros((600, 800, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}
        self.dispatch_after_town_precondition(sm, fake_screen, rect)
        self.assertEqual(sm.current_state, sm.STATE_CHEST)

        # 模擬第 1 輪執行：退出後在城鎮發現寶箱正下方「仍有驚嘆號紅點」
        fake_screen = np.zeros((600, 800, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}
        chest_handler = sm.handlers[sm.STATE_CHEST]
        chest_handler.step_phase = "VERIFY_EXIT"
        chest_handler.last_action_time = 0.0

        def fake_match_with_red_dot(img, name, **kw):
            if name == "town_building/mysterious_treasure/mysterious_treasure.png":
                return ((200, 200), 0.88)
            if name == "town_building/red_dot.png":
                return ((200, 240), 0.85)  # 仍然有紅點！
            return (None, 0.0)

        mock_matcher.match.side_effect = fake_match_with_red_dot
        chest_handler.handle(fake_screen, rect)

        # 斷言 1: 未標記 completed_today，且進入 180s 退避冷卻
        self.assertFalse(self.daily_mgr.is_subflow_completed("chest"))
        self.assertTrue(self.daily_mgr.is_subflow_deferred("chest"))

        # 斷言 2: 在 3 分鐘 (180 秒) 內，get_pending_town_subflows() 100% 遮蔽該任務，狀態機保持在 NAVIGATING (絕不 0 秒重複進出建築)
        base_time = time.time()
        self.assertEqual(self.daily_mgr.get_pending_town_subflows(now_ts=base_time + 10), [])
        self.assertEqual(self.daily_mgr.get_pending_town_subflows(now_ts=base_time + 60), [])
        self.assertEqual(self.daily_mgr.get_pending_town_subflows(now_ts=base_time + 179), [])
        self.assertEqual(sm.current_state, sm.STATE_NAVIGATING)

        # 模擬 3 分鐘 (180 秒) 冷卻過後 (181s)：chest 自動解除遮蔽並重現於待辦清單中
        time_after_180s = base_time + 181
        self.assertEqual(self.daily_mgr.get_pending_town_subflows(now_ts=time_after_180s), ["chest"])

        # 觸發調度（例如機器人打完一場關卡回城，或城鎮心跳輪詢）：重新走進該建築執行領取
        with patch('time.time', return_value=time_after_180s):
            re_scheduled = sm.evaluate_and_schedule_daily_pipeline()
            self.assertTrue(re_scheduled)
            self.dispatch_after_town_precondition(sm, fake_screen, rect)
            # 斷言 3: 狀態機在 3 分鐘後成功重新派發至 STATE_CHEST！
            self.assertEqual(sm.current_state, sm.STATE_CHEST)

        # 模擬第 2 輪執行：這次成功領取，退出後在城鎮發現紅點已消除！
        chest_handler.step_phase = "VERIFY_EXIT"
        chest_handler.last_action_time = 0.0

        def fake_match_no_red_dot(img, name, **kw):
            if name == "town_building/mysterious_treasure/mysterious_treasure.png":
                return ((200, 200), 0.88)
            return (None, 0.0)  # 紅點已消失

        mock_matcher.match.side_effect = fake_match_no_red_dot
        chest_handler.handle(fake_screen, rect)

        # 斷言 4: 紅點消失後，成功標記 completed_today = True，且自動解除 defer 狀態！
        self.assertTrue(self.daily_mgr.is_subflow_completed("chest"))
        self.assertFalse(self.daily_mgr.is_subflow_deferred("chest"))

        # 斷言 5: 終態結案閉環：後續再次調度時，get_pending_town_subflows() 已無 chest，回復 NAVIGATING 且不再重複派發！
        self.assertEqual(self.daily_mgr.get_pending_town_subflows(), [])
        self.assertEqual(sm.current_state, sm.STATE_NAVIGATING)
        self.assertFalse(sm.evaluate_and_schedule_daily_pipeline())

    @patch("os.path.exists", return_value=True)
    def test_stage_or_bag_return_re_dispatches_blood_altar_until_dismissed(self, mock_exists):
        """
        [驗證關卡回城/背包整理後 3 分鐘 Defer 與動態補跑閉環]
        1. 第一次執行 blood_altar，退出後因紅點仍存在進入 180s 冷卻退避。
        2. 斷言 180s 內被過濾，不重複進出。
        3. 模擬機器人打完關卡或背包滿回城 (滿 180s 後)，觸發 evaluate_and_schedule_daily_pipeline。
        4. blood_altar 再次出現在 get_pending_town_subflows() 中並被重新派發。
        5. 第二次完成獻祭且紅點消失，成功標記 completed_today = True。
        """
        # 僅保留 blood_altar 未完成
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
        self.daily_mgr.record_subflow_completed("bulletin_board")
        self.assertEqual(self.daily_mgr.get_pending_town_subflows(), ["blood_altar"])

        mock_matcher = MagicMock()
        mock_matcher.templates_dir = "templates"
        sm = GameStateMachine(capturer=MagicMock(), matcher=mock_matcher, mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        sm.runtime_config_key = "daily"
        sm.primary_config = self.mock_daily_cfg.copy()
        sm.set_config(self.mock_daily_cfg.copy())
        sm.get_available_selected_lord_bosses = MagicMock(return_value=[])
        sm.quest_scheduler = None

        # 第 1 輪派發
        self.assertTrue(sm.evaluate_and_schedule_daily_pipeline())
        fake_screen = np.zeros((600, 800, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}
        self.dispatch_after_town_precondition(sm, fake_screen, rect)
        self.assertEqual(sm.current_state, sm.STATE_BLOOD_ALTAR)

        # 第 1 次退出城鎮：血之祭壇下方仍有紅點
        fake_screen = np.zeros((600, 800, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}
        altar_handler = sm.handlers[sm.STATE_BLOOD_ALTAR]
        altar_handler.step_phase = "ALL_DONE_EXITING"
        altar_handler.last_action_time = 0.0

        def fake_match_altar_with_red_dot(img, name, **kw):
            if name in ["common/door.png", "town_building/Blood_Altar/Blood_Altar.png"]:
                return ((150, 150), 0.88)
            if name == "town_building/red_dot.png":
                return ((150, 230), 0.85)  # 紅點仍在
            return (None, 0.0)

        mock_matcher.match.side_effect = fake_match_altar_with_red_dot
        altar_handler.handle(fake_screen, rect)

        # 斷言 1: 未標記 completed_today，且處於 defer 退避中
        self.assertFalse(self.daily_mgr.is_subflow_completed("blood_altar"))
        self.assertTrue(self.daily_mgr.is_subflow_deferred("blood_altar"))

        # 斷言 2: 180s 內保持在 NAVIGATING，不重複派發
        base_time = time.time()
        self.assertEqual(self.daily_mgr.get_pending_town_subflows(now_ts=base_time + 60), [])
        self.assertEqual(sm.current_state, sm.STATE_NAVIGATING)

        # 模擬刷完關卡或背包清理後回到城鎮 (已過 181 秒)
        time_after_180s = base_time + 181
        self.assertEqual(self.daily_mgr.get_pending_town_subflows(now_ts=time_after_180s), ["blood_altar"])

        with patch('time.time', return_value=time_after_180s):
            re_scheduled = sm.evaluate_and_schedule_daily_pipeline()
            self.assertTrue(re_scheduled)
            self.dispatch_after_town_precondition(sm, fake_screen, rect)
            # 調度器在回城時自動重新進入 STATE_BLOOD_ALTAR
            self.assertEqual(sm.current_state, sm.STATE_BLOOD_ALTAR)

        # 第 2 次退出城鎮：紅點已消除
        altar_handler.step_phase = "ALL_DONE_EXITING"
        altar_handler.last_action_time = 0.0

        def fake_match_altar_no_red_dot(img, name, **kw):
            if name in ["common/door.png", "town_building/Blood_Altar/Blood_Altar.png"]:
                return ((150, 150), 0.88)
            return (None, 0.0)  # 紅點已消除

        mock_matcher.match.side_effect = fake_match_altar_no_red_dot
        altar_handler.handle(fake_screen, rect)

        # 斷言 3: 成功標記完成且後續不再派發
        self.assertTrue(self.daily_mgr.is_subflow_completed("blood_altar"))
        self.assertEqual(self.daily_mgr.get_pending_town_subflows(), [])
        self.assertEqual(sm.current_state, sm.STATE_NAVIGATING)
        self.assertFalse(sm.evaluate_and_schedule_daily_pipeline())


if __name__ == "__main__":
    unittest.main()
