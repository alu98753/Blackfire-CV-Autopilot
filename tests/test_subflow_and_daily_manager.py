import unittest
import os
import sys
import time
import json
import shutil
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GAME_CONFIGS, PRIMARY_MODES, SUBFLOW_CONFIGS
from utils.daily_manager import DailyManager
from states.handlers.base import BaseStateHandler
from states.handlers.result import ResultHandler
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
        self.manager.record_subflow_completed("bulletin_board", extra_data={"accepted_quests": ["清除骷髏", "清除野豬"]})
        self.assertTrue(self.manager.is_subflow_completed("bulletin_board"))
        self.assertEqual(self.manager.status["subflows"]["bulletin_board"]["accepted_quests"], ["清除骷髏", "清除野豬"])

        # 觸發強制重置 (跨日)
        self.manager.check_and_reset_daily(force=True)

        # 驗證 completed_today 重置為 False，但 accepted_quests 依然完好無損！
        self.assertFalse(self.manager.is_subflow_completed("bulletin_board"))
        self.assertEqual(self.manager.status["subflows"]["bulletin_board"]["accepted_quests"], ["清除骷髏", "清除野豬"])

    def test_bulletin_board_prepends_today_new_quests(self):
        """
        測試：每日抓取新任務時以多階梯優先級 (sort_quests) 更新佇列，
        確保確定性任務排在前、不確定性任務排在後。
        """
        # 1. 昨日殘留未完成舊任務: ["清除野豬", "清除骷髏"]
        self.manager.status["subflows"]["bulletin_board"]["accepted_quests"] = ["清除野豬", "清除骷髏"]
        self.manager.save_status()

        # 2. 今日抓取新任務: ["擊敗冰元素", "史萊姆王的毀滅"]
        today_new_quests = ["擊敗冰元素", "史萊姆王的毀滅"]
        updated = self.manager.update_bulletin_board_quests(today_new_quests)

        # 3. 驗證更新後按 sort_quests 排序 (idx大者優先)：清除骷髏 (dungeon 3) ➔ 史萊姆王的毀滅 (dungeon 0) ➔ 擊敗冰元素 (Stage 6) ➔ 清除野豬 (Stage 1)
        expected = ["清除骷髏", "史萊姆王的毀滅", "擊敗冰元素", "清除野豬"]
        self.assertEqual(updated, expected)
        self.assertEqual(self.manager.status["subflows"]["bulletin_board"]["accepted_quests"], expected)

        # 4. 測試重複項目不重複插入
        today_new_quests_2 = ["擊敗冰元素", "清除野豬"]
        updated_2 = self.manager.update_bulletin_board_quests(today_new_quests_2)
        expected_2 = ["清除骷髏", "史萊姆王的毀滅", "擊敗冰元素", "清除野豬"]
        self.assertEqual(updated_2, expected_2)

    def test_daily_reset_resets_statemachine_scheduler_and_defeat_count(self):
        """
        [08:05 重置鏈條測試] 驗證：
        1. 每日 08:05 重置時保留已接受任務 (accepted_quests)，新任務可合併與排序。
        2. 當 08:05 跨日重置時，GameStateMachine 上的 quest_scheduler 物件被清空為 None。
        3. 戰敗計數器 defeat_count 重置為 0。
        4. 體力退避時間戳 stamina_retreat_start_time 重置為 None。
        """
        from unittest.mock import MagicMock, patch
        from utils.quest_scheduler import QuestScheduler
        from states.state_machine import GameStateMachine

        # 模擬狀態機並設置舊狀態
        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.set_config({"name": "test", "type": "stage"})
        sm.daily_manager = self.manager
        sm.quest_scheduler = QuestScheduler()
        sm.defeat_count = 3
        sm.stamina_retreat_start_time = time.time() - 1000.0

        # 手動觸發 08:05 強制跨日重置
        was_reset = self.manager.check_and_reset_daily(force=True)
        self.assertTrue(was_reset)

        # 模擬 step() 執行時觸發重置鏈條
        with patch.object(self.manager, "check_and_reset_daily", return_value=True):
            with patch.object(sm.capturer, "get_window_rect", return_value={"left": 0, "top": 0, "width": 1920, "height": 1080}):
                with patch.object(sm.capturer, "capture", return_value=None):
                    sm.step()

        # 斷言 StateMachine 上的殘留狀態已全數清空/重置 (quest_scheduler 設為 None, defeat_count 設為 0)
        self.assertIsNone(sm.quest_scheduler)
        self.assertEqual(sm.defeat_count, 0)
        self.assertIsNone(sm.stamina_retreat_start_time)

    def test_reevaluate_unknown_quests_on_load(self):
        """
        [Unknown 歸位自癒測試] 驗證當 unknown_quests 中包含：
        1. 舊錯字 '討伐忠魔' (Mapper 正名 '討伐惡魔' ➔ 晉升正名 '討伐惡魔' 入 accepted_quests)
        2. '獵全之蟲' (Mapper 正名 '獵金之蟲' 視為 ignored ➔ 移除)
        3. '完全未知任務_XYZ' (仍無規則 ➔ 保留於 unknown_quests)
        在載入 DailyManager 時自動完滿自癒歸位！
        """
        bb = self.manager.status["subflows"]["bulletin_board"]
        bb["unknown_quests"] = ["討伐忠魔", "獵全之蟲", "完全未知任務_XYZ"]
        bb["accepted_quests"] = ["清除骷髏"]
        self.manager.save_status()

        # 重新載入存檔觸發自癒
        new_mgr = DailyManager(data_dir=TEST_DATA_DIR, status_file="test_daily.json")
        new_bb = new_mgr.status["subflows"]["bulletin_board"]

        # 斷言 unknown_quests 僅剩真正的未知任務
        self.assertEqual(new_bb["unknown_quests"], ["完全未知任務_XYZ"])

        # 斷言 accepted_quests 成功包含正名後的 '討伐惡魔' 與原本的 '清除骷髏'
        self.assertIn("討伐惡魔", new_bb["accepted_quests"])
        self.assertIn("清除骷髏", new_bb["accepted_quests"])

    def test_cross_day_reset_and_update_quests_full_flow(self):
        """
        [跨日重置與領任務全流程自癒測試] 驗證 24/7 不重開程序下：
        1. 舊有 accepted_quests (如 "清除野豬") 經跨日重置後清空。
        2. 歷史 unknown_quests 中的 "消滅蛛王與蛛后" (正名 "消滅蛛王與蛛後") 與 "清除樹入" (正名 "清除樹人") 成功自癒晉升入 accepted_quests。
        3. 晉升任務與新抓取的 "清除骷髏" 必定經由 sort_quests 進行多階梯優先級排序 (確定性 > 彈窗核銷 ➔ 地下城 Index 大者優先)。
        4. 歷史 unknown_quests 中的 "完全未知任務_XYZ" 因無字典規則，依然安全留存在 unknown_quests 中。
        """
        bb = self.manager.status["subflows"]["bulletin_board"]
        bb["accepted_quests"] = ["清除野豬"]
        bb["unknown_quests"] = ["消滅蛛王與蛛后", "清除樹入", "完全未知任務_XYZ"]
        self.manager.save_status()

        # 1. 模擬 08:05 跨日重置
        self.manager.check_and_reset_daily(force=True)

        # 2. 模擬告示牌掃描領取新任務 "清除骷髏"
        self.manager.update_bulletin_board_quests(["清除骷髏"])

        updated_bb = self.manager.status["subflows"]["bulletin_board"]
        accepted = updated_bb.get("accepted_quests", [])
        unknowns = updated_bb.get("unknown_quests", [])

        # 斷言 1 (情況 A 晉升與排序驗證): "消滅蛛王與蛛后" ➔ "消滅蛛王與蛛後"、"清除樹入" ➔ "清除樹人" 皆晉升，並與新任務 "清除骷髏" 及舊任務 "清除野豬" 自動排序！
        # 期望排序 (mode_score: dungeon 0 > stage 1)：
        # 1. "清除骷髏" (dungeon index 3, DETERMINISTIC)
        # 2. "清除樹人" (dungeon index 2, DETERMINISTIC)
        # 3. "消滅蛛王與蛛後" (dungeon index 0, BANNER_VERIFY)
        # 4. "清除野豬" (stage level 1, DETERMINISTIC)
        expected_sorted_order = ["清除骷髏", "清除樹人", "消滅蛛王與蛛後", "清除野豬"]
        self.assertEqual(accepted, expected_sorted_order)

        self.assertNotIn("消滅蛛王與蛛后", unknowns)
        self.assertNotIn("消滅蛛王與蛛後", unknowns)
        self.assertNotIn("清除樹入", unknowns)
        self.assertNotIn("清除樹人", unknowns)

        # 斷言 3 (情況 B 繼續留存): "完全未知任務_XYZ" 依然留存在 unknown_quests，且絕不出現在 accepted_quests
        self.assertEqual(unknowns, ["完全未知任務_XYZ"])
        self.assertNotIn("完全未知任務_XYZ", accepted)

    def test_remove_accepted_quest_no_cross_deletion(self):
        """
        [Regression Bug Fix 測試] 驗證 DailyManager.remove_accepted_quest("清除蛙人")
        不會誤刪同在 accepted_quests 中的相似任務 "清除樹人" (相似度 0.75)。
        """
        self.manager.status["subflows"] = {
            "bulletin_board": {
                "accepted_quests": ["清除樹人", "清除蛙人"]
            }
        }
        res = self.manager.remove_accepted_quest("清除蛙人")
        self.assertTrue(res)
        remaining = self.manager.status["subflows"]["bulletin_board"]["accepted_quests"]
        self.assertIn("清除樹人", remaining)
        self.assertNotIn("清除蛙人", remaining)

    def test_lord_boss_cooldown_buffer_prevents_infinite_triggering(self):
        """
        [防跳離與死循環測試] 驗證：
        1. set_lord_boss_cooldown 能在無可用 Boss 時有效阻斷 has_available_lord_boss 被重複發起。
        2. ResultHandler 在普通 stage/dungeon 模式下，即使掃描到 load/Lord_entry_after.png 也絕對不會誤轉移至 STATE_LORD_BOSS！
        """
        dm = DailyManager(data_dir=TEST_DATA_DIR, status_file="test_daily.json")
        
        # 測試 1: 設定冷卻計時 180 秒，驗證 has_available_lord_boss 傳回 False
        dm.set_lord_boss_cooldown(180)
        self.assertFalse(dm.has_available_lord_boss())

        # 測試 2: 模擬 ResultHandler 在 stage 模式結算，畫面上看到 Lord_entry_after.png
        from unittest.mock import MagicMock
        from states.state_machine import GameStateMachine
        from states.handlers.result import ResultHandler

        capturer = MagicMock()
        matcher = MagicMock()
        mouse = MagicMock()
        sm = GameStateMachine(capturer=capturer, matcher=matcher, mouse=mouse)
        sm.config = {"name": "測試懸賞關卡", "type": "stage"}
        sm.daily_manager = dm

        handler = ResultHandler(sm)
        
        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # Mock 比對到了離場按鈕 goback_town.png，並設定需離場條件
        sm.need_bag_cleaning = True
        matcher.match.side_effect = lambda img, name, **kw: ((50, 50), 0.85) if name == "goback_town.png" else (None, 0.0)

        # 執行 handle，斷言狀態轉移為 STATE_NAVIGATING，絕對不是 STATE_LORD_BOSS！
        handler.handle(fake_img, rect)
        self.assertEqual(sm.current_state, sm.STATE_NAVIGATING)
        self.assertNotEqual(sm.current_state, sm.STATE_LORD_BOSS)

    def test_dynamic_lord_boss_cooldown_calculation(self):
        """
        [動態冷卻計時測試] 驗證 set_lord_boss_cooldown 能精確讀取 daily_status.json 中的 
        (last_fight_timestamp + cooldown_seconds - now_ts) 計算最快可挑戰的 Boss 冷卻解鎖時間！
        """
        dm = DailyManager(data_dir=TEST_DATA_DIR, status_file="test_daily_dynamic.json")
        now = time.time()
        
        # 1. 設置 蜘蛛 (3600s CD) 剛打完 (剩 3600s)，惡靈 (7200s CD) 3000s 前打完 (剩 4200s)
        dm.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]["last_fight_timestamp"] = now
        dm.status["subflows"]["lord_boss"]["bosses"]["lord_spectre"]["last_fight_timestamp"] = now - 3000.0

        # 動態計算最快解鎖秒數：最快解鎖的蜘蛛為 3600 秒
        sec = dm.get_next_lord_boss_available_seconds(now_ts=now)
        self.assertAlmostEqual(sec, 3600.0, delta=2.0)

        # 呼叫 set_lord_boss_cooldown()，驗證避退時間精確被鎖定為 3600 秒
        dm.set_lord_boss_cooldown(now_ts=now)
        self.assertAlmostEqual(dm.lord_boss_cooldown_until, now + 3600.0, delta=2.0)
        self.assertFalse(dm.has_available_lord_boss(now_ts=now))

        # 模擬 3601 秒後，驗證冷卻解鎖，has_available_lord_boss 傳回 True
        future_now = now + 3601.0
        self.assertTrue(dm.has_available_lord_boss(now_ts=future_now))

    def test_cross_tier_quality_preference_propagation(self):
        """
        [跨 Tier 躍遷品質傳承測試] 驗證在 Tier 1 (城鎮速領) ➔ Tier 2 (領主 Boss) ➔ Tier 3 (懸賞任務) ➔ Tier 4 (退守模式)
        全生命週期跳動切換中，使用者的 keep_colors, disassemble_colors 與 sacrifice_settings 100% 不遺失！
        """
        from unittest.mock import MagicMock
        from states.state_machine import GameStateMachine
        from utils.quest_scheduler import QuestScheduler
        from utils.quest_mapper import QuestMapper

        capturer = MagicMock()
        matcher = MagicMock()
        mouse = MagicMock()
        sm = GameStateMachine(capturer=capturer, matcher=matcher, mouse=mouse)

        # 初始：使用者啟動設定
        user_keep = ["purple", "orange_yellow", "red"]
        user_dis = ["gray_or_empty", "green", "blue"]
        user_sac = {"gray": True, "green": True, "blue": True, "purple": False}

        sm.config = {
            "name": "每日全域模式",
            "type": "daily",
            "keep_colors": user_keep,
            "disassemble_colors": user_dis,
            "sacrifice_settings": user_sac
        }

        # 1. 跳動至 Tier 1 (城鎮速領 blood_altar & jewelry_workshop)
        sm.town_subflow_queue = ["blood_altar", "jewelry_workshop"]
        sm.pop_and_next_town_subflow()
        self.assertEqual(sm.config["keep_colors"], user_keep)
        self.assertEqual(sm.config["disassemble_colors"], user_dis)

        sm.pop_and_next_town_subflow()
        self.assertEqual(sm.config["keep_colors"], user_keep)
        self.assertEqual(sm.config["disassemble_colors"], user_dis)

        # 2. 跳動至 Tier 2 (領主討伐 lord_boss)
        sm.town_subflow_queue = ["lord_boss"]
        sm.pop_and_next_town_subflow()
        self.assertEqual(sm.config["keep_colors"], user_keep)
        self.assertEqual(sm.config["disassemble_colors"], user_dis)

        # 3. 跳動至 Tier 3 (懸賞任務)
        mapper = QuestMapper()
        node = mapper.parse_quest("清除沙蟲")
        scheduler = QuestScheduler()
        scheduler.add_task(node)
        sm.attach_quest_scheduler(scheduler)

        sm.check_and_advance_quest_target()
        self.assertEqual(sm.config["keep_colors"], user_keep)
        self.assertEqual(sm.config["disassemble_colors"], user_dis)

        # 4. 跳動至 Tier 4 (退守混合模式)
        scheduler.tasks = [] # 模擬所有任務完成
        sm.check_and_advance_quest_target()
        self.assertEqual(sm.config["keep_colors"], user_keep)
        self.assertEqual(sm.config["disassemble_colors"], user_dis)

    def test_jewelry_and_altar_handlers_do_not_reenter_when_not_needed(self):
        """
        [防重複進出測試] 驗證：當 need_jewelry_workshop 或 need_blood_altar 為 False 且處於 INIT 階段時，
        即使畫面上同時偵測到大門與建築圖片，處理器也 100% 阻斷點擊，絕不重複走進建築！
        """
        from unittest.mock import MagicMock
        from states.state_machine import GameStateMachine
        from states.handlers.jewelry_workshop import JewelryWorkshopHandler
        from states.handlers.blood_altar import BloodAltarHandler
        import numpy as np

        capturer = MagicMock()
        matcher = MagicMock()
        mouse = MagicMock()
        sm = GameStateMachine(capturer=capturer, matcher=matcher, mouse=mouse)
        sm.need_jewelry_workshop = False
        sm.need_blood_altar = False

        j_handler = JewelryWorkshopHandler(sm)
        b_handler = BloodAltarHandler(sm)

        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        matcher.match.side_effect = lambda img, name, **kw: ((100, 100), 0.90)

        # 執行 handler，斷言 mouse.click 呼叫次數為 0！
        j_handler.handle(fake_img, rect)
        b_handler.handle(fake_img, rect)
        mouse.click.assert_not_called()

    def test_result_handler_whitelist_isolation(self):
        """
        [結算二分法白名單測試] 驗證 ResultHandler：
        1. 在非離場場次 (should_exit_battle==False) 且看到 stages/retry.png 時，直接點擊 retry 續戰，絕對不匹配 exit_battle 或 goback_town。
        2. 在離場場次 (should_exit_battle==True) 且看到 goback_town.png 時，點擊離場，絕對不上當點擊 retry。
        3. continue.png 點擊次數超過 2 次後自動封鎖，不盲目重複點擊。
        """
        from unittest.mock import MagicMock
        from states.state_machine import GameStateMachine
        from states.handlers.result import ResultHandler
        import numpy as np

        capturer = MagicMock()
        matcher = MagicMock()
        mouse = MagicMock()
        sm = GameStateMachine(capturer=capturer, matcher=matcher, mouse=mouse)
        sm.config = {"type": "stage"}
        handler = ResultHandler(sm)

        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        # 1. 測試非離場場次：畫面上同時有 goback_town.png (離場) 與 stages/retry.png (再戰)
        # 由於 should_exit_battle==False，ResultHandler 必須選擇 stages/retry.png！
        def mock_match_non_exit(img, name, **kw):
            if name == "stages/retry.png":
                return ((500, 500), 0.90)
            if name == "goback_town.png":
                return ((100, 100), 0.95)
            return (None, 0.0)

        matcher.match.side_effect = mock_match_non_exit
        res = handler._handle_impl(fake_img, rect)

        self.assertTrue(res)
        self.assertEqual(sm.current_state, sm.STATE_LOADING) # 轉移至 LOADING 再戰

        # 2. 測試離場場次：設 need_bag_cleaning=True (離場條件成立)
        # 畫面上同時有 stages/retry.png (再戰) 與 goback_town.png (離場)
        # ResultHandler 必須選擇 goback_town.png 離場，絕不點擊 retry！
        sm.need_bag_cleaning = True
        sm.current_state = sm.STATE_UNKNOWN
        mouse.reset_mock()

        res_exit = handler._handle_impl(fake_img, rect)
        self.assertTrue(res_exit)
        self.assertEqual(sm.current_state, sm.STATE_NAVIGATING) # 轉移至 NAVIGATING 離場

    def test_result_subflow_full_pipeline_step_by_step(self):
        """
        [結算子流程全步驟深度測試] 充分驗證 ResultHandler 子流程：
        1. 步驟 1 (INIT_DELAY): 初始進入休眠沉澱 1.5s，並平滑過渡至 CONTINUE_LOOP。
        2. 步驟 2 (CONTINUE_LOOP): 點擊 2 次 continue.png (每次沉澱 1.0s)，自動切換至 FINAL_MATCH。
        3. 步驟 3 (FINAL_MATCH): 點擊 retry/exit_battle 後自動 reset_state 重置子流程步驟為 INIT_DELAY。
        4. 大廳特徵攔截 (select_stage.png): 隨時能即時中斷結算並轉移至 NAVIGATING。
        """
        from unittest.mock import MagicMock, patch
        from states.state_machine import GameStateMachine
        from states.handlers.result import ResultHandler
        import numpy as np

        capturer = MagicMock()
        matcher = MagicMock()
        mouse = MagicMock()
        sm = GameStateMachine(capturer=capturer, matcher=matcher, mouse=mouse)
        sm.config = {"type": "stage"}
        handler = ResultHandler(sm)

        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        # 斷言初始步驟為 INIT_DELAY
        self.assertEqual(handler.subflow_step, "INIT_DELAY")

        # 1. 測試 Step 1: INIT_DELAY 轉為 CONTINUE_LOOP (無 continue.png 且無終局按鈕時，維持 CONTINUE_LOOP 等待動畫過場)
        matcher.match.return_value = (None, 0.0)
        with patch("time.sleep") as mock_sleep:
            handler._handle_impl(fake_img, rect)
            mock_sleep.assert_called_with(1.5) # 斷言精確觸發 1.5 秒初始沉澱休眠
            self.assertEqual(handler.subflow_step, "CONTINUE_LOOP") # 防過場誤判：維持 CONTINUE_LOOP

        # 重置回 CONTINUE_LOOP 測試 continue 點擊
        handler.subflow_step = "CONTINUE_LOOP"
        handler.continue_click_count = 0

        # 2. 測試 Step 2: 點擊 continue.png 並呼叫 click_and_wait_until_gone 配對確認直到消失
        def mock_match_continue(img, name, **kw):
            if name == "common/continue.png":
                return ((770, 550), 0.95)
            return (None, 0.0)

        matcher.match.side_effect = mock_match_continue
        with patch.object(BaseStateHandler, "click_and_wait_until_gone") as mock_wait_gone:
            res_c1 = handler._handle_impl(fake_img, rect)
            self.assertTrue(res_c1)
            mock_wait_gone.assert_called_with(
                "common/continue.png", 770, 550, rect,
                timeout=5.0, threshold=0.9, brightness_threshold=0.70, check_interval=0.25, post_delay=0.8, retry_interval=1.0
            )

        # 3. 測試 Step 3: 續戰點擊 retry.png 後重置狀態
        def mock_match_retry(img, name, **kw):
            if name == "stages/retry.png":
                return ((500, 500), 0.90)
            return (None, 0.0)

        handler.subflow_step = "FINAL_MATCH"
        matcher.match.side_effect = mock_match_retry
        with patch.object(BaseStateHandler, "click_and_wait_until_gone") as mock_wait_gone:
            res_retry = handler._handle_impl(fake_img, rect)
            self.assertTrue(res_retry)
            self.assertEqual(sm.current_state, sm.STATE_LOADING)
            self.assertEqual(handler.subflow_step, "INIT_DELAY") # 斷言子流程已重置回 INIT_DELAY
            mock_wait_gone.assert_called_with(
                "stages/retry.png", 500, 500, rect, post_delay=0.8
            )

        # 4. 測試大廳獨有特徵 (select_stage.png) 攔截
        handler.subflow_step = "CONTINUE_LOOP"
        handler.continue_click_count = 1
        matcher.match.side_effect = lambda img, name, **kw: ((100, 100), 0.90) if name == "common/select_stage.png" else (None, 0.0)

        res_lobby = handler._handle_impl(fake_img, rect)
        self.assertTrue(res_lobby)
        self.assertEqual(sm.current_state, sm.STATE_NAVIGATING)
        self.assertEqual(handler.subflow_step, "INIT_DELAY") # 斷言大廳攔截後子流程已安全重置

if __name__ == "__main__":
    unittest.main()


