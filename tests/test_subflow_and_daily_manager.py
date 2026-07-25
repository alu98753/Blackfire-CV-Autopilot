import unittest
import os
import sys
import time
import json
import shutil
from datetime import datetime, timedelta

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GAME_CONFIGS, PRIMARY_MODES, SUBFLOW_CONFIGS
from utils.daily_manager import DailyManager
from main import parse_arguments

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

TEST_DATA_DIR = "user_data_test_temp"

class TestSubflowAndDailyManager(unittest.TestCase):
    """
    單元測試驗證 Clean Code 分層配置 (config.py)、
    CLI --subflow 參數解析以及 DailyManager (08:30 重置與各 Boss 獨立 CD)。
    """
    def setUp(self):
        if os.path.exists(TEST_DATA_DIR):
            shutil.rmtree(TEST_DATA_DIR)
        self.manager = DailyManager(data_dir=TEST_DATA_DIR, status_file="test_daily.json")

    def tearDown(self):
        if os.path.exists(TEST_DATA_DIR):
            shutil.rmtree(TEST_DATA_DIR)

    def test_config_clean_architecture_separation(self):
        """
        測試 config.py 中的 PRIMARY_MODES 剛好只有 4 個，且 GAME_CONFIGS 完全包含 PRIMARY_MODES 與 SUBFLOW_CONFIGS。
        """
        self.assertEqual(len(PRIMARY_MODES), 5)
        self.assertIn("mix", PRIMARY_MODES)
        self.assertIn("dungeon", PRIMARY_MODES)
        self.assertIn("stage", PRIMARY_MODES)
        self.assertIn("collect_only", PRIMARY_MODES)
        self.assertIn("daily", PRIMARY_MODES)



        self.assertIn("blood_altar", SUBFLOW_CONFIGS)
        self.assertIn("jewelry_workshop", SUBFLOW_CONFIGS)
        self.assertIn("bag_clean", SUBFLOW_CONFIGS)

        # 斷言：GAME_CONFIGS 為解包合併
        for k in PRIMARY_MODES:
            self.assertIn(k, GAME_CONFIGS)
        for k in SUBFLOW_CONFIGS:
            self.assertIn(k, GAME_CONFIGS)

    def test_daily_manager_reset_at_0830(self):
        """測試：當當前時間戳超過 next_reset_timestamp 時，自動發起清零並預算下一輪重置時間戳"""
        # 1. 記錄一次戰鬥進度
        self.manager.record_boss_fight("lord_spider")
        self.assertEqual(self.manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]["today_count"], 1)

        # 2. 模擬當前時間戳已超過 next_reset_timestamp
        past_next_reset = time.time() - 10.0
        self.manager.next_reset_timestamp = past_next_reset
        
        # 強制跳過 60 秒限流觸發檢查
        self.manager.last_check_ts = 0.0
        now_dt = datetime.now()
        was_reset = self.manager.check_and_reset_daily(force=True)
        
        self.assertTrue(was_reset)
        self.assertEqual(self.manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]["today_count"], 0)
        # next_reset_timestamp 應該已自動推算至未來的下一個 08:30
        self.assertGreater(self.manager.next_reset_timestamp, time.time())
        self.assertEqual(self.manager.status["last_daily_reset_date"], self.manager.get_today_reset_tag(now_dt))

    def test_per_boss_independent_cd_and_limit(self):
        """
        測試育母蜘蛛 (lord_spider) 與古代惡靈 (lord_spectre) 的獨立計數與冷卻。
        """
        now = time.time()
        
        # 剛初始化時，兩個 Boss 都可打
        avail_spider, msg_s = self.manager.is_boss_available("lord_spider", now_ts=now)
        avail_spectre, msg_sp = self.manager.is_boss_available("lord_spectre", now_ts=now)
        self.assertTrue(avail_spider)
        self.assertTrue(avail_spectre)

        # 1. 擊殺育母蜘蛛 1 次
        self.manager.record_boss_fight("lord_spider", now_ts=now)

        # 斷言：蜘蛛進入 2 小時 CD
        avail_spider2, msg_s2 = self.manager.is_boss_available("lord_spider", now_ts=now + 10)
        self.assertFalse(avail_spider2)
        self.assertIn("冷卻中", msg_s2)

        # 斷言：古代惡靈完全不受蜘蛛影響，依然可打！
        avail_spectre2, _ = self.manager.is_boss_available("lord_spectre", now_ts=now + 10)
        self.assertTrue(avail_spectre2)

        # 2. 模擬 2 小時後 (7205秒)，蜘蛛冷卻完畢
        avail_spider3, _ = self.manager.is_boss_available("lord_spider", now_ts=now + 7205)
        self.assertTrue(avail_spider3)

        # 3. 模擬蜘蛛連續打了 5 次滿額
        spider_info = self.manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]
        spider_info["today_count"] = 5
        self.manager.save_status()

        avail_spider_full, msg_full = self.manager.is_boss_available("lord_spider", now_ts=now + 99999)
        self.assertFalse(avail_spider_full)
        self.assertIn("打滿", msg_full)

    def test_multiple_subflows_queue_execution_and_outer_exit(self):
        """
        測試多個城鎮子流程 (如 ['blood_altar', 'jewelry_workshop']) 依序彈出消費，
        並驗證佇列全空時，Dev 模式觸發 sys.exit(0)，Prod 模式切回 STATE_NAVIGATING。
        """
        from unittest.mock import MagicMock
        from states.state_machine import GameStateMachine
        
        # 建立模擬狀態機
        capturer = MagicMock()
        matcher = MagicMock()
        mouse = MagicMock()
        sm = GameStateMachine(capturer, matcher, mouse)
        
        # 1. 模擬 Dev 測試模式注入多個子流程佇列
        sm.town_subflow_queue = ["blood_altar", "jewelry_workshop"]
        sm.is_dev_subflow_run = True

        # 第一次彈出 ➔ 應切換至 STATE_BLOOD_ALTAR
        sm.pop_and_next_town_subflow()
        self.assertEqual(sm.current_state, sm.STATE_BLOOD_ALTAR)
        self.assertTrue(sm.need_blood_altar)
        self.assertEqual(sm.town_subflow_queue, ["jewelry_workshop"])

        # 第二次彈出 ➔ 應切換至 STATE_JEWELRY_WORKSHOP
        sm.pop_and_next_town_subflow()
        self.assertEqual(sm.current_state, sm.STATE_JEWELRY_WORKSHOP)
        self.assertTrue(sm.need_jewelry_workshop)
        self.assertEqual(sm.town_subflow_queue, [])

        # 第三次彈出 ➔ 佇列全空且為 Dev 模式，應觸發 SystemExit (sys.exit(0))
        with self.assertRaises(SystemExit) as cm:
            sm.pop_and_next_town_subflow()
        self.assertEqual(cm.exception.code, 0)

        # 2. 模擬 Prod 長掛機模式 (is_dev_subflow_run = False)
        sm.is_dev_subflow_run = False
        sm.town_subflow_queue = ["blood_altar"]
        sm.pop_and_next_town_subflow() # 彈出 blood_altar
        
        # 佇列全空，Prod 模式應切回 STATE_NAVIGATING 而不拋出 SystemExit！
        sm.pop_and_next_town_subflow()
        self.assertEqual(sm.current_state, sm.STATE_NAVIGATING)

    def test_subflow_no_duplicate_execution_and_state_transition(self):
        """
        針對性測試：驗證多子流程絕對不會重複執行第一個 subflow (不會二次打血之祭壇)，
        且在 STATE_UNKNOWN 全域辨識時，不會因 config['type'] 被誤拉回舊的狀態！
        """
        from unittest.mock import MagicMock
        from states.state_machine import GameStateMachine
        from config import GAME_CONFIGS

        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        # 模擬 --subflow blood_altar jewelry_workshop
        sm.town_subflow_queue = ["blood_altar", "jewelry_workshop"]
        sm.is_dev_subflow_run = True
        sm.config = GAME_CONFIGS["blood_altar"].copy() # 預設載入首項 config

        # 1. 模擬 main.py 在啟動時彈出首個任務
        sm.pop_and_next_town_subflow()

        # 斷言 1: 首個任務已被彈出，佇列剩餘 ['jewelry_workshop']
        self.assertEqual(sm.town_subflow_queue, ["jewelry_workshop"])
        self.assertEqual(sm.current_state, sm.STATE_BLOOD_ALTAR)
        self.assertTrue(sm.need_blood_altar)
        self.assertFalse(sm.need_jewelry_workshop)

        # 2. 模擬第一站血之祭壇完工退回城鎮，呼叫 pop_and_next_town_subflow()
        sm.pop_and_next_town_subflow()

        # 斷言 2: 佇列已無血之祭壇，切換至 JEWELRY_WORKSHOP，且 config 100% 同步更新為珠寶店配置！
        self.assertEqual(sm.town_subflow_queue, [])
        self.assertEqual(sm.current_state, sm.STATE_JEWELRY_WORKSHOP)
        self.assertFalse(sm.need_blood_altar) # need_blood_altar 必須已被重置為 False！
        self.assertTrue(sm.need_jewelry_workshop)
        self.assertEqual(sm.config["type"], "jewelry_workshop")
        self.assertEqual(sm.config["building_btn"], "town_building/Jewelry_workshop/Jewelry_workshop.png")

        # 3. 模擬狀態機在第二站突然進入 STATE_UNKNOWN，並看見城鎮/大門按鈕 (common/door.png)
        # 驗證狀態機絕不會因為 sm.config['type'] == 'blood_altar' 而誤切回 BLOOD_ALTAR！
        sm.current_state = sm.STATE_UNKNOWN
        sm.matcher.match.side_effect = lambda img, name, **kw: ((50, 50), 0.90) if name == "common/door.png" else (None, 0.0)
        import numpy as np
        import os
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        # 執行全域掃描 step (在 STATE_UNKNOWN 下)
        sm.step()

        # 斷言 3: 狀態應正確轉移至 STATE_JEWELRY_WORKSHOP，絕對不能誤轉回 BLOOD_ALTAR！
        self.assertEqual(sm.current_state, sm.STATE_JEWELRY_WORKSHOP)

    def test_town_pipeline_flags_cleared_on_empty_queue(self):
        """
        [防死循環測試] 驗證城鎮流水線當最後一個子流程 (jewelry_workshop) 完成且佇列清空時，
        pop_and_next_town_subflow 能 100% 清空 need_jewelry_workshop 殘留旗標，切回 NAVIGATING 後絕不再次死循環轉移回 JEWELRY_WORKSHOP！
        """
        from unittest.mock import MagicMock
        from states.state_machine import GameStateMachine
        capturer = MagicMock()
        matcher = MagicMock()
        mouse = MagicMock()
        sm = GameStateMachine(capturer=capturer, matcher=matcher, mouse=mouse)

        sm.primary_config = {"name": "測試懸賞關卡", "type": "stage"}
        sm.town_subflow_queue = ["jewelry_workshop"]
        sm.pop_and_next_town_subflow()

        # 斷言 1: 切換至 JEWELRY_WORKSHOP，旗標被立起
        self.assertEqual(sm.current_state, sm.STATE_JEWELRY_WORKSHOP)
        self.assertTrue(sm.need_jewelry_workshop)

        # 模擬珠寶店完成，再次呼叫 pop_and_next_town_subflow() (此時佇列為空 [])
        sm.pop_and_next_town_subflow()

        # 斷言 2: 佇列已空，所有城鎮旗標必須被強制清零！
        self.assertFalse(sm.need_jewelry_workshop)
        self.assertFalse(sm.need_blood_altar)
        self.assertFalse(sm.need_bag_cleaning)
        self.assertEqual(sm.current_state, sm.STATE_NAVIGATING)

        # 模擬在大廳畫面看到 goback_town.png (全域掃描)
        sm.matcher.match.side_effect = lambda img, name, **kw: ((50, 50), 0.90) if name == "goback_town.png" else (None, 0.0)
        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        sm.capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        sm.capturer.capture.return_value = fake_img

        # 執行 step()，斷言絕不再次被拽回 STATE_JEWELRY_WORKSHOP 死循環！
        sm.step()
        self.assertNotEqual(sm.current_state, sm.STATE_JEWELRY_WORKSHOP)

    def test_match_mutually_exclusive_tabs_logic(self):
        """
        鎖定測試 1: 驗證 match_mutually_exclusive_tabs 的相對優勢算法 (margin 0.02, threshold 0.70)。
        """
        from unittest.mock import MagicMock
        from vision.matcher import TemplateMatcher
        matcher = TemplateMatcher()
        matcher.match = MagicMock()

        # 情況 A: c_a = 0.75, c_b = 0.60 (優勢高於 0.02 且高於 0.70) ➔ is_a=True, is_b=False
        matcher.match.side_effect = lambda img, temp, **kw: ((0, 0), 0.75) if temp == "temp_a" else (((0, 0), 0.60) if temp == "temp_b" else (None, 0.0))
        is_a, is_b, ca, cb = matcher.match_mutually_exclusive_tabs(None, "temp_a", "temp_b", margin=0.02, threshold=0.70)
        self.assertTrue(is_a)
        self.assertFalse(is_b)

        # 情況 B: c_a = 0.71, c_b = 0.70 (相差 0.01 低於 margin 0.02) ➔ is_a=False, is_b=False (不穩定保護)
        matcher.match.side_effect = lambda img, temp, **kw: ((0, 0), 0.71) if temp == "temp_a" else (((0, 0), 0.70) if temp == "temp_b" else (None, 0.0))
        is_a, is_b, ca, cb = matcher.match_mutually_exclusive_tabs(None, "temp_a", "temp_b", margin=0.02, threshold=0.70)
        self.assertFalse(is_a)
        self.assertFalse(is_b)

    def test_transition_to_auto_sync_config_context(self):
        """
        鎖定測試 2: 驗證當呼叫 transition_to(new_state) 時，全域 self.config 瞬間自動同步為新狀態專屬配置。
        """
        from unittest.mock import MagicMock
        from states.state_machine import GameStateMachine
        from config import GAME_CONFIGS

        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        sm.config = {} # 初始為空字典
        
        # 1. 轉移至 BLOOD_ALTAR
        sm.transition_to(sm.STATE_BLOOD_ALTAR)
        self.assertEqual(sm.config["type"], "blood_altar")
        self.assertEqual(sm.config["building_btn"], "town_building/Blood_Altar/Blood_Altar.png")

        # 2. 轉移至 JEWELRY_WORKSHOP
        sm.transition_to(sm.STATE_JEWELRY_WORKSHOP)
        self.assertEqual(sm.config["type"], "jewelry_workshop")

        # 3. 轉移至 LORD_BOSS
        sm.transition_to(sm.STATE_LORD_BOSS)
        self.assertEqual(sm.config["type"], "lord_boss")
        self.assertEqual(sm.config["entry_btn"], "load/Lord_entry.png")

    def test_pop_and_next_town_subflow_data_driven_dispatch(self):
        """測試：pop_and_next_town_subflow 能依據 TOWN_SUBFLOW_CONFIG_MAP 資料驅動派發所有子流程 (包括 lord_boss)"""
        from unittest.mock import MagicMock
        from states.state_machine import GameStateMachine
        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        
        # 彈出 lord_boss
        sm.town_subflow_queue = ["lord_boss"]
        sm.pop_and_next_town_subflow()
        self.assertEqual(sm.current_state, sm.STATE_LORD_BOSS)
        self.assertEqual(sm.config["type"], "lord_boss")

    def test_filter_navigation_path_reentrancy_prevention(self):
        """
        鎖定測試 3: 驗證 filter_navigation_path 動態過濾已開啟頁籤之父階按鈕。
        """
        from states.handlers.navigation import filter_navigation_path

        nav_path = ["common/door.png", "dungeons/dungeon.png", "dungeons/Slime_entry.png"]
        
        # 1. 當 active_tabs 包含 "dungeon" 頁籤開啟時 ➔ 自動過濾 "dungeons/dungeon.png"
        filtered = filter_navigation_path(nav_path, active_tabs=["dungeon"])
        self.assertEqual(filtered, ["common/door.png", "dungeons/Slime_entry.png"])

        # 2. 當 active_tabs 為空時 ➔ 保持原樣
        filtered_empty = filter_navigation_path(nav_path, active_tabs=[])
        self.assertEqual(filtered_empty, nav_path)

    def test_disabled_subflow_skipped(self):
        """測試：當子流程在 SUBFLOW_CONFIGS 被設為 enabled=False 時，pop_and_next_town_subflow 自動跳過它"""
        from unittest.mock import MagicMock, patch
        from states.state_machine import GameStateMachine

        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        sm.town_subflow_queue = ["test_disabled_flow", "chest"]

        fake_configs = {
            "test_disabled_flow": {"enabled": False, "type": "disabled"},
            "chest": {"enabled": True, "type": "chest"}
        }

        with patch("config.SUBFLOW_CONFIGS", fake_configs):
            sm.pop_and_next_town_subflow()

    def test_daily_reset_preserves_accepted_quests(self):
        """
        測試：每日 08:05 重置 (check_and_reset_daily) 時，
        會將 completed_today 設為 False，但【絕不抹除/重置 accepted_quests】。
        """
        # 先寫入舊任務
        self.manager.record_subflow_completed("bulletin_board", extra_data={"accepted_quests": ["清除野豬", "擊殺首領"]})
        self.assertTrue(self.manager.is_subflow_completed("bulletin_board"))
        self.assertEqual(self.manager.status["subflows"]["bulletin_board"]["accepted_quests"], ["清除野豬", "擊殺首領"])

        # 觸發強制重置 (跨日)
        self.manager.check_and_reset_daily(force=True)

        # 驗證 completed_today 重置為 False，但 accepted_quests 依然完好無損！
        self.assertFalse(self.manager.is_subflow_completed("bulletin_board"))
        self.assertEqual(self.manager.status["subflows"]["bulletin_board"]["accepted_quests"], ["清除野豬", "擊殺首領"])

    def test_bulletin_board_prepends_today_new_quests(self):
        """
        測試：每日抓取新任務時以多階梯優先級 (sort_quests) 更新佇列，
        確保確定性任務排在前、不確定性任務排在後。
        """
        # 1. 昨日殘留未完成舊任務: ["清除野豬", "擊殺首領"]
        self.manager.status["subflows"]["bulletin_board"]["accepted_quests"] = ["清除野豬", "擊殺首領"]
        self.manager.save_status()

        # 2. 今日抓取新任務: ["擊敗冰元素", "史萊姆王的毀滅"]
        today_new_quests = ["擊敗冰元素", "史萊姆王的毀滅"]
        updated = self.manager.update_bulletin_board_quests(today_new_quests)

        # 3. 驗證更新後按 sort_quests 排序：史萊姆王的毀滅 (dungeon) ➔ 擊敗冰元素 (Stage 6) ➔ 清除野豬 (Stage 1) ➔ 擊殺首領
        expected = ["史萊姆王的毀滅", "擊敗冰元素", "清除野豬", "擊殺首領"]
        self.assertEqual(updated, expected)
        self.assertEqual(self.manager.status["subflows"]["bulletin_board"]["accepted_quests"], expected)

        # 4. 測試重複項目不重複插入
        today_new_quests_2 = ["擊敗冰元素", "清除野豬"]
        updated_2 = self.manager.update_bulletin_board_quests(today_new_quests_2)
        expected_2 = ["史萊姆王的毀滅", "擊敗冰元素", "清除野豬", "擊殺首領"]
        self.assertEqual(updated_2, expected_2)

if __name__ == "__main__":
    unittest.main()


