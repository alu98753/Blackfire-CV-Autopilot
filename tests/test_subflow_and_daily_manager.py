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
        self.assertEqual(len(PRIMARY_MODES), 4)
        self.assertIn("mix", PRIMARY_MODES)
        self.assertIn("dungeon", PRIMARY_MODES)
        self.assertIn("stage", PRIMARY_MODES)
        self.assertIn("collect_only", PRIMARY_MODES)

        self.assertIn("blood_altar", SUBFLOW_CONFIGS)
        self.assertIn("jewelry_workshop", SUBFLOW_CONFIGS)
        self.assertIn("bag_clean", SUBFLOW_CONFIGS)

        # 斷言：GAME_CONFIGS 為解包合併
        for k in PRIMARY_MODES:
            self.assertIn(k, GAME_CONFIGS)
        for k in SUBFLOW_CONFIGS:
            self.assertIn(k, GAME_CONFIGS)

    def test_daily_manager_reset_at_0830(self):
        """
        測試 DailyManager 在時間跨越 08:30 時自動進行重置。
        """
        # 1. 模擬昨天的 08:30 標籤
        yesterday_dt = datetime.now() - timedelta(days=1)
        self.manager.status["last_daily_reset_date"] = "2020-01-01"
        self.manager.status["subflows"]["blood_altar"]["completed_today"] = True
        self.manager.save_status()

        # 2. 觸發重置檢查 (假設當前為今天 09:00 AM)
        now_dt = datetime.now().replace(hour=9, minute=0, second=0)
        reset_triggered = self.manager.check_and_reset_daily(now_dt=now_dt)

        self.assertTrue(reset_triggered)
        self.assertFalse(self.manager.status["subflows"]["blood_altar"]["completed_today"])
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

if __name__ == "__main__":
    unittest.main()
