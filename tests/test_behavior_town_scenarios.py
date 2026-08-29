import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GAME_CONFIGS
from states.state_machine import GameStateMachine

from tests._legacy_state_machine_test_support import BehavioralScenarioTestCase


class TestTownScenarios(BehavioralScenarioTestCase):

    @patch('sys.exit')
    @patch('os.path.exists')
    def test_blood_altar_full_subflow(self, mock_exists, mock_sys_exit):
        """
        測試血之祭壇獻祭 (Blood Altar) 完整子流程：
        1. 城鎮 (door.png, Blood_Altar.png) ➔ 點擊 Blood_Altar.png
        2. 建築內 (Sacrifice.png) ➔ 點擊 Sacrifice.png
        3. 獻祭選單 (green_blood.png, alter.png) ➔ 點擊 green_blood.png ➔ 點擊 alter.png
        4. 視窗關閉 (quit.png) ➔ 點擊 quit.png
        5. 離開建築 (exitfromhouse_and_to_town.png) ➔ 點擊 exitfromhouse_and_to_town.png ➔ 流程結束 (呼叫 sys.exit(0))
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["blood_altar"].copy()
        self.state_machine.config["sacrifice_settings"] = {"gray": True, "green": True, "blue": True, "purple": False}
        self.state_machine.current_state = self.state_machine.STATE_BLOOD_ALTAR
        if self.state_machine.daily_manager:
            self.state_machine.daily_manager.is_subflow_completed = MagicMock(return_value=False)
        handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        handler.reset_state()


        # Step 1: 城鎮點擊祭壇建築 (保持在 INIT 等待 UI 渲染)
        def mock_match_step1(img, name, **kw):
            if name == "common/door.png":
                return ((100, 200), 0.9)
            elif name == "town_building/Blood_Altar/Blood_Altar.png":
                return ((550, 688), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_step1
        self.mock_mouse.click.reset_mock()

        handler.handle()
        self.mock_mouse.click.assert_called_once_with(550, 688)
        self.assertEqual(handler.step_phase, "INIT")

        # Step 1.5: 畫面完成渲染 (辨識到 exitfromhouse_and_to_town.png 或 Sacrifice.png) ➔ 切換至 ENTERED_BUILDING
        handler.last_action_time = 0.0
        def mock_match_step1_5(img, name, **kw):
            if name == "town_building/exitfromhouse_and_to_town.png":
                return ((50, 50), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_step1_5
        handler.handle()
        self.assertEqual(handler.step_phase, "ENTERED_BUILDING")

        # Step 2: 進入建築後轉移至 SACRIFICE_MENU_OPEN，並點擊 Sacrifice.png 開啟選單
        handler.last_action_time = 0.0
        sac_matched = [0]
        def mock_match_step2(img, name, **kw):
            if name == "town_building/Blood_Altar/Sacrifice.png":
                if sac_matched[0] == 0:
                    sac_matched[0] += 1
                    return ((830, 863), 0.9)
                return (None, 0.0)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_step2
        self.mock_mouse.click.reset_mock()

        handler.handle() # ENTERED_BUILDING ➔ SACRIFICE_MENU_OPEN
        self.assertEqual(handler.step_phase, "SACRIFICE_MENU_OPEN")
        handler.last_action_time = 0.0
        handler.handle() # 在 SACRIFICE_MENU_OPEN 點擊 Sacrifice.png
        self.mock_mouse.click.assert_called_once_with(830, 863)

        # Step 3: 點選 green_blood 獻祭 ➔ 點擊 sell_max.png ➔ 點擊 alter.png
        handler.last_action_time = 0.0
        def mock_match_step3(img, name, **kw):
            if name == "town_building/Blood_Altar/green_blood.png":
                return ((706, 303), 0.9)
            elif name == "town_building/sell_max.png":
                return ((1173, 539), 0.9)
            elif name == "town_building/Blood_Altar/alter.png":
                return ((917, 774), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_step3
        self.mock_mouse.click.reset_mock()

        handler.handle()
        self.assertEqual(self.mock_mouse.click.call_count, 3)
        self.assertEqual(handler.step_phase, "SACRIFICE_MENU_OPEN")

        # Step 4: 連續 3 幀無任何血水，進到 ALL_DONE_EXITING 階段並點擊 common/quit.png
        handler.last_action_time = 0.0
        self.mock_matcher.match.side_effect = None
        self.mock_matcher.match.return_value = (None, 0.0)
        handler.handle() # empty count = 1
        handler.last_action_time = 0.0
        handler.handle() # empty count = 2
        handler.last_action_time = 0.0
        handler.handle() # empty count = 3 ➔ step_phase = "ALL_DONE_EXITING"
        self.assertEqual(handler.step_phase, "ALL_DONE_EXITING")

        handler.last_action_time = 0.0
        def mock_match_step4(img, name, **kw):
            if kw.get("quiet"):
                return (None, 0.0)
            if name == "common/quit.png":
                return ((1200, 100), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_step4
        self.mock_mouse.click.reset_mock()

        handler.handle()
        self.mock_mouse.click.assert_called_once_with(1200, 100)

        # Step 5: 點擊 exitfromhouse_and_to_town.png 離開 ➔ 觸發 sys.exit(0)
        handler.last_action_time = 0.0
        step5_calls = [0]
        def mock_match_step5(img, name, **kw):
            if name == "town_building/exitfromhouse_and_to_town.png":
                step5_calls[0] += 1
                return ((50, 50), 0.9) if step5_calls[0] <= 1 else (None, 0.0)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_step5
        self.mock_mouse.click.reset_mock()

        self.state_machine.is_dev_subflow_run = True
        handler.handle()
        self.assertEqual(handler.step_phase, "INIT")
        mock_sys_exit.assert_called_once_with(0)

    @patch('os.path.exists')
    def test_blood_altar_returns_to_town_from_lobby(self, mock_exists):
        """
        測試當角色在大廳 (goback_town.png 可見) 且處於 STATE_BLOOD_ALTAR 狀態時：
        BloodAltarHandler 能透過 _ensure_in_town 自動點擊 goback_town.png 返回城鎮！
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["blood_altar"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BLOOD_ALTAR
        handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        handler.reset_state()

        calls = [0]
        def mock_match_in_lobby(img, name, **kw):
            if name == "goback_town.png":
                calls[0] += 1
                return ((72, 757), 0.92) if calls[0] <= 1 else (None, 0.0)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_in_lobby
        self.mock_mouse.click.reset_mock()

        handler.handle()
        # 斷言：必須自動點擊 goback_town.png (72, 757) 返回城鎮！
        self.mock_mouse.click.assert_called_once_with(72, 757)

    @patch('os.path.exists')
    def test_blood_altar_preserves_purple_blood(self, mock_exists):
        """
        測試當設定為【紫色保留不獻祭】(purple: False) 且畫面上僅剩紫色血水與 alter.png 時：
        1. 腳本絕不點擊 alter.png 或 purple_blood.png！
        2. 連續 3 幀確認後，順利轉移至 ALL_DONE_EXITING 並點擊 common/quit.png 退出！
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["blood_altar"].copy()
        self.state_machine.config["sacrifice_settings"]["purple"] = False
        self.state_machine.current_state = self.state_machine.STATE_BLOOD_ALTAR
        handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        handler.reset_state()
        handler.step_phase = "SACRIFICE_MENU_OPEN"

        def mock_match_only_purple(img, name, **kw):
            if name == "town_building/Blood_Altar/purple_blood.png":
                return ((500, 300), 0.9)
            elif name == "town_building/Blood_Altar/alter.png":
                return ((776, 660), 0.9)
            elif name == "town_building/sell_max.png":
                return ((975, 460), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_only_purple
        self.mock_mouse.click.reset_mock()

        # 執行 3 幀掃描
        handler.handle()
        handler.last_action_time = 0.0
        handler.handle()
        handler.last_action_time = 0.0
        handler.handle()

        # 斷言：在 SACRIFICE_MENU_OPEN 期間，絕未對 purple_blood / sell_max / alter 進行任何點擊！
        self.assertEqual(self.mock_mouse.click.call_count, 0)
        self.assertEqual(handler.step_phase, "ALL_DONE_EXITING")

    @patch('os.path.exists')
    def test_blood_altar_start_inside_building(self, mock_exists):
        """
        測試當啟動腳本時，角色已位於血之祭壇建築物內部 (Sacrifice.png 與 exitfromhouse_and_to_town.png 同時存在，conf >= 0.85)：
        BloodAltarHandler 能自動辨識並點擊 Sacrifice.png 開啟選單！
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["blood_altar"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BLOOD_ALTAR
        if self.state_machine.daily_manager:
            self.state_machine.daily_manager.is_subflow_completed = MagicMock(return_value=False)
        handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        handler.reset_state()

        def mock_match_inside(img, name, **kw):
            if name == "town_building/Blood_Altar/Sacrifice.png":
                return ((718, 745), 0.90)
            elif name == "town_building/exitfromhouse_and_to_town.png":
                return ((74, 744), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_inside
        self.mock_mouse.click.reset_mock()

        handler.handle() # INIT ➔ ENTERED_BUILDING
        handler.last_action_time = 0.0
        handler.handle() # ENTERED_BUILDING ➔ SACRIFICE_MENU_OPEN
        handler.last_action_time = 0.0
        handler.handle() # 在 SACRIFICE_MENU_OPEN 點擊 Sacrifice.png (718, 745)
        self.mock_mouse.click.assert_called_once_with(718, 745)
        self.assertEqual(handler.step_phase, "SACRIFICE_MENU_OPEN")

    @patch('os.path.exists')
    def test_bag_cleaning_triggers_blood_altar_on_completion(self, mock_exists):
        """
        測試在地下城掛機模式下，BagCleaningHandler 完成整理並關閉背包時：
        自動設置 need_blood_altar = True 並將狀態轉移至 STATE_BLOOD_ALTAR！
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BAG_CLEANING
        self.state_machine.bag_tidied = True
        self.state_machine.need_bag_cleaning = True
        self.state_machine.bag_opened_clicked = True

        handler = self.state_machine.handlers[self.state_machine.STATE_BAG_CLEANING]
        if hasattr(handler, 'reset_state'):
            handler.reset_state()
        self.state_machine.bag_opened_clicked = True



        quit_matched = [False]
        def mock_match_quit(img, name, **kw):
            if name == "common/quit.png" and not quit_matched[0]:
                quit_matched[0] = True
                return ((800, 200), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_quit
        self.mock_mouse.click.reset_mock()


        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = self.mock_capturer.get_window_rect()
        handler.handle(fake_img, rect)

        self.mock_mouse.click.assert_called_once_with(800, 200)
        self.assertTrue(self.state_machine.pending_town_subflows)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)

    @patch('os.path.exists')
    def test_blood_altar_returns_to_dungeon_after_sacrifice(self, mock_exists):
        """
        測試在地下城掛機模式下觸發的 BloodAltarHandler，完成獻祭並離開建築退回城鎮時：
        自動重置 need_blood_altar = False 並將狀態切換回 STATE_DUNGEON_EXPLORING！
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BLOOD_ALTAR
        self.state_machine.need_blood_altar = True

        handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        handler.step_phase = "ALL_DONE_EXITING"

        def mock_match_exit_building(img, name, **kw):
            if kw.get("quiet"):
                return (None, 0.0)
            if name == "town_building/exitfromhouse_and_to_town.png":
                return ((74, 744), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_exit_building
        self.mock_mouse.click.reset_mock()

        handler.handle()

        self.assertFalse(self.state_machine.need_blood_altar)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)

    def test_blood_altar_reset_state_on_reentry(self):
        """
        測試當 BloodAltarHandler 先前殘留舊狀態 (如 ALL_DONE_EXITING, empty_blood_scan_count=3) 時：
        呼叫 reset_state() 能夠正確還原為初始狀態 (INIT, 0, 0.0)！
        """
        handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        handler.step_phase = "ALL_DONE_EXITING"
        handler.empty_blood_scan_count = 3
        handler.last_action_time = 99999.0

        # 執行重置
        handler.reset_state()

        # 斷言：必須徹底還原
        self.assertEqual(handler.step_phase, "INIT")
        self.assertEqual(handler.empty_blood_scan_count, 0)
        self.assertEqual(handler.last_action_time, 0.0)

    @patch('os.path.exists', return_value=True)
    def test_blood_altar_skips_free_claim_when_completed_today(self, mock_exists):
        """
        測試當 DailyManager 中 blood_altar 今日已完成 (completed_today=True) 時：
        進入 BloodAltarHandler 會自動跳過點擊領血頁籤與領取按鈕！
        """
        handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        handler.reset_state()

        # 模擬 DailyManager 紀錄今日已完成
        mock_dm = MagicMock()
        mock_dm.is_subflow_completed.return_value = True
        self.state_machine.daily_manager = mock_dm


        def mock_match_entry(img, name, **kw):
            if name == "town_building/Blood_Altar/receive_entry.png":
                return ((500, 200), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_entry
        self.mock_mouse.click.reset_mock()

        handler.handle()

        # 驗證絕對沒有點擊領水頁籤
        self.mock_mouse.click.assert_not_called()
        self.assertNotEqual(handler.step_phase, "RECEIVE_TAB_OPEN")

    @patch('os.path.exists')
    def test_blood_altar_retrigger_cycle_integration(self, mock_exists):
        """
        測試二次連動觸發情境：
        第一次獻祭完成 ➔ 自動切換回 STATE_DUNGEON_EXPLORING ➔ 背包再次清理完成 ➔ transition_to(STATE_BLOOD_ALTAR)
        驗證 handler 的內部狀態會被自動重置為 INIT，準備下一次獻祭！
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["dungeon"].copy()
        
        # 模擬第一次獻祭完成
        handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        handler.step_phase = "ALL_DONE_EXITING"
        handler.empty_blood_scan_count = 3
        
        # 轉移回到探索狀態
        self.state_machine.transition_to(self.state_machine.STATE_DUNGEON_EXPLORING)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)

        # 模擬第二次觸發：背包清理完成後調用 transition_to(STATE_BLOOD_ALTAR)
        self.state_machine.transition_to(self.state_machine.STATE_BLOOD_ALTAR)

        # 斷言：轉移至 STATE_BLOOD_ALTAR 時，會自動調用 reset_state()，使 step_phase 乾淨還原為 INIT
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BLOOD_ALTAR)
        self.assertEqual(handler.step_phase, "INIT")
        self.assertEqual(handler.empty_blood_scan_count, 0)

    @patch('os.path.exists', return_value=True)
    def test_blood_altar_full_pipeline_receive_and_sacrifice(self, mock_exists):
        """
        [血之祭壇全流程測試] 驗證重構後單向 Pipeline 的 5 階狀態流轉：
        1. INIT ➔ ENTERED_BUILDING
        2. ENTERED_BUILDING ➔ RECEIVE_TAB_OPEN
        3. RECEIVE_TAB_OPEN ➔ HANDLING_RECEIVE_POPUPS (成功領水)
        4. HANDLING_RECEIVE_POPUPS ➔ SACRIFICE_MENU_OPEN (僅驗證彈窗全清 3 幀)
        5. SACRIFICE_MENU_OPEN ➔ ALL_DONE_EXITING (點擊 Sacrifice.png 頁籤與獻祭閉環)
        """
        self.state_machine.config = GAME_CONFIGS["blood_altar"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BLOOD_ALTAR
        if self.state_machine.daily_manager:
            self.state_machine.daily_manager.is_subflow_completed = MagicMock(return_value=False)

        handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        handler.reset_state()

        # Step 1: INIT 點擊建築進屋 (保持在 INIT 等待 UI 渲染)
        def match_step1(img, name, **kw):
            if name == "common/door.png":
                return ((100, 100), 0.90)
            elif name == "town_building/Blood_Altar/Blood_Altar.png":
                return ((500, 500), 0.90)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = match_step1
        handler.handle()
        self.assertEqual(handler.step_phase, "INIT")

        # Step 1.5: 辨識到 exitfromhouse_and_to_town.png 畫面穩定 ➔ 切換至 ENTERED_BUILDING
        handler.last_action_time = 0.0
        def match_step1_5(img, name, **kw):
            if name == "town_building/exitfromhouse_and_to_town.png":
                return ((50, 50), 0.90)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = match_step1_5
        handler.handle()
        self.assertEqual(handler.step_phase, "ENTERED_BUILDING")

        # Step 2: ENTERED_BUILDING 點擊領水頁籤切換
        handler.last_action_time = 0.0
        def match_step2(img, name, **kw):
            if name == "town_building/Blood_Altar/receive_entry.png":
                return ((400, 700), 0.90)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = match_step2
        handler.handle()
        self.assertEqual(handler.step_phase, "RECEIVE_TAB_OPEN")

        # Step 3: RECEIVE_TAB_OPEN 點擊每日領取按鈕 (帶入 brightness_threshold=0.50)
        handler.last_action_time = 0.0
        def match_step3(img, name, **kw):
            if name == "town_building/Blood_Altar/receive_daily.png":
                return ((500, 500), 0.85)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = match_step3
        handler.handle()
        self.assertEqual(handler.step_phase, "HANDLING_RECEIVE_POPUPS")

        # Step 4: HANDLING_RECEIVE_POPUPS 僅驗證彈窗全清 (無彈窗 3 幀後轉移)
        self.mock_matcher.match.side_effect = lambda img, name, **kw: (None, 0.0)
        handler.last_action_time = 0.0
        handler.handle()
        handler.last_action_time = 0.0
        handler.handle()
        handler.last_action_time = 0.0
        handler.handle()
        self.assertEqual(handler.step_phase, "SACRIFICE_MENU_OPEN")

        # Step 5: SACRIFICE_MENU_OPEN 點擊 Sacrifice.png 頁籤進入獻祭介面
        def match_step5(img, name, **kw):
            if name == "town_building/Blood_Altar/Sacrifice.png":
                return ((700, 700), 0.90)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = match_step5
        handler.last_action_time = 0.0
        handler.handle()
        self.mock_mouse.click.assert_called_with(700, 700)

    @patch('os.path.exists', return_value=True)
    def test_blood_altar_receive_daily_retry_3_frames_and_fallback(self, mock_exists):
        """
        [領血重試與降級測試] 驗證當 RECEIVE_TAB_OPEN 階段未掃描到 receive_daily.png 時：
        連續重試 3 幀後，平滑降級轉移至 SACRIFICE_MENU_OPEN！
        """
        handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        handler.reset_state()
        handler.step_phase = "RECEIVE_TAB_OPEN"

        # 畫面無 receive_daily.png
        self.mock_matcher.match.side_effect = lambda img, name, **kw: (None, 0.0)

        # 1 幀重試
        handler.handle()
        self.assertEqual(handler.step_phase, "RECEIVE_TAB_OPEN")
        self.assertEqual(handler.receive_scan_count, 1)

        # 2 幀重試
        handler.last_action_time = 0.0
        handler.handle()
        self.assertEqual(handler.step_phase, "RECEIVE_TAB_OPEN")
        self.assertEqual(handler.receive_scan_count, 2)

        # 3 幀重試觸發平滑轉移
        handler.last_action_time = 0.0
        handler.handle()
        self.assertEqual(handler.step_phase, "SACRIFICE_MENU_OPEN")

    @patch('os.path.exists')
    def test_blood_altar_to_navigating_in_mix_mode_with_available_dungeon(self, mock_exists):
        """
        測試在 mix 混合模式下，血之祭壇獻祭完畢退回城鎮轉移至 STATE_NAVIGATING 時：
        當 has_available_dungeon() == True，NavigationHandler 能自動點擊 dungeons/dungeon.png 導航進入地下城！
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["mix"].copy()
        self.state_machine.dungeon_cooldowns = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0} # 全就緒
        self.state_machine.current_state = self.state_machine.STATE_BLOOD_ALTAR
        self.state_machine.is_dev_subflow_run = False
        
        # 1. 模擬獻祭結束退出建築
        altar_handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        altar_handler.step_phase = "ALL_DONE_EXITING"
        
        def mock_match_exit(img, name, **kw):
            if name == "town_building/exitfromhouse_and_to_town.png":
                return ((74, 744), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_exit
        self.mock_mouse.click.reset_mock()
        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = self.mock_capturer.get_window_rect()
        
        altar_handler.handle(fake_img, rect)

        # 斷言 1: 血之祭壇獻祭完畢後，成功轉移至 STATE_NAVIGATING 且 need_blood_altar = False
        self.assertFalse(self.state_machine.need_blood_altar)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)

        # 2. 模擬 NavigationHandler 在城鎮進行導航決策 (看見大門與地下城入口)
        nav_handler = self.state_machine.handlers[self.state_machine.STATE_NAVIGATING]
        
        def mock_match_dungeon_entry(img, name, **kw):
            if name == "common/door.png":
                return ((76, 751), 0.95)
            elif name == "dungeons/dungeon.png":
                return ((250, 400), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_dungeon_entry
        self.mock_mouse.click.reset_mock()

        nav_handler.handle(fake_img, rect)

        # 斷言 2: 在 mix 模式且有可用地下城時，NavigationHandler 自動點擊 [common/door.png] / [dungeons/dungeon.png]
        self.mock_mouse.click.assert_called()

    @patch('os.path.exists')
    def test_blood_altar_to_navigating_in_mix_mode_with_all_dungeons_cooldown(self, mock_exists):
        """
        測試在 mix 混合模式下，血之祭壇獻祭完畢退回城鎮轉移至 STATE_NAVIGATING 時：
        當所有地下城皆在冷卻中 (has_available_dungeon() == False)，NavigationHandler 能發動關卡退守，點擊 common/select_stage.png 導航進入普通關卡！
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["mix"].copy()
        now = time.time()
        self.state_machine.dungeon_cooldowns = {0: now+1000, 1: now+1000, 2: now+1000, 3: now+1000, 4: now+1000} # 全冷卻
        self.state_machine.current_state = self.state_machine.STATE_BLOOD_ALTAR
        
        # 1. 模擬獻祭結束退出建築
        altar_handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        altar_handler.step_phase = "ALL_DONE_EXITING"
        
        def mock_match_exit(img, name, **kw):
            if name == "town_building/exitfromhouse_and_to_town.png":
                return ((74, 744), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_exit
        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = self.mock_capturer.get_window_rect()
        
        altar_handler.handle(fake_img, rect)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)

        # 2. 模擬 NavigationHandler 在城鎮進行導航決策 (看見普通關卡入口)
        nav_handler = self.state_machine.handlers[self.state_machine.STATE_NAVIGATING]
        
        def mock_match_stage_entry(img, name, **kw):
            if name == "common/door.png":
                return ((76, 751), 0.95)
            elif name == "common/select_stage.png":
                return ((300, 400), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_stage_entry
        self.mock_mouse.click.reset_mock()

        nav_handler.handle(fake_img, rect)

        # 斷言 2: 在 mix 模式且全冷卻時，NavigationHandler 發動退守點擊普通關卡入口
        self.mock_mouse.click.assert_called()

    @patch('os.path.exists')
    def test_jewelry_workshop_enters_building_and_opens_menu(self, mock_exists):
        """
        測試當角色在城鎮時 (Jewelry_workshop.png 可見)：
        JewelryWorkshopHandler 能自動辨識並點擊進入建築物，隨後點擊 sell_out.png 開啟選單！
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["jewelry_workshop"].copy()
        self.state_machine.current_state = self.state_machine.STATE_JEWELRY_WORKSHOP
        handler = self.state_machine.handlers[self.state_machine.STATE_JEWELRY_WORKSHOP]
        handler.reset_state()

        def mock_match_town(img, name, **kw):
            if name == "common/door.png":
                return ((50, 50), 0.90)
            elif name == "town_building/Jewelry_workshop/Jewelry_workshop.png":
                return ((400, 500), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_town
        self.mock_mouse.click.reset_mock()
        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = self.mock_capturer.get_window_rect()

        handler.handle(fake_img, rect)
        self.mock_mouse.click.assert_called_once_with(400, 500)
        self.assertEqual(handler.step_phase, "ENTERED_BUILDING")

    @patch('os.path.exists')
    def test_jewelry_workshop_scrolls_down_and_sells_goods(self, mock_exists):
        """
        測試在 SELL_MENU_OPEN 階段：
        當頂層未找到 goods 時，Handler 會向下滑動 2 次尋找，找到商品後順序執行點擊商品 -> sell.png -> sell_max.png -> ok.png 賣出！
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["jewelry_workshop"].copy()
        self.state_machine.current_state = self.state_machine.STATE_JEWELRY_WORKSHOP
        handler = self.state_machine.handlers[self.state_machine.STATE_JEWELRY_WORKSHOP]
        handler.reset_state()
        handler.step_phase = "SELL_MENU_OPEN"

        scales_match_count = [0]
        def mock_match_goods(img, name, **kw):
            if "Sandworm_scales.png" in name:
                if handler.goods_scroll_state == "SCROLLED_DOWN" and scales_match_count[0] == 0:
                    scales_match_count[0] += 1
                    return ((300, 300), 0.90)
                return (None, 0.0)
            elif name == "town_building/sell.png":
                return ((500, 500), 0.90)
            elif name == "town_building/sell_max.png":
                return ((600, 500), 0.90)
            elif name == "common/ok.png":
                return ((700, 500), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_goods
        self.mock_mouse.drag.reset_mock()
        self.mock_mouse.click.reset_mock()

        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = self.mock_capturer.get_window_rect()

        # 1. 第一幀：頂層未找到，執行平滑拖曳滑動
        handler.handle(fake_img, rect)
        self.mock_mouse.drag.assert_called_with(960, 810, 960, 270, duration=0.5, inertia=False)
        self.assertEqual(handler.goods_scroll_state, "SCROLLED_DOWN")

        # 2. 第二幀：滑動後找到商品，執行點選與賣出
        handler.last_action_time = 0.0
        handler.handle(fake_img, rect)
        self.assertTrue(self.mock_mouse.click.called)
        self.assertEqual(handler.current_goods_idx, 1)

    @patch('sys.exit')
    @patch('os.path.exists')
    def test_jewelry_workshop_exits_building_on_completion(self, mock_exists, mock_sys_exit):
        """
        測試當所有 goods 處置完成後進入 ALL_DONE_EXITING：
        Handler 能自動點擊 exitfromhouse_and_to_town.png 返回城鎮，並在獨立模式呼叫 sys.exit(0)！
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["jewelry_workshop"].copy()
        self.state_machine.current_state = self.state_machine.STATE_JEWELRY_WORKSHOP
        handler = self.state_machine.handlers[self.state_machine.STATE_JEWELRY_WORKSHOP]
        handler.reset_state()
        handler.step_phase = "ALL_DONE_EXITING"

        def mock_match_exit(img, name, **kw):
            if name == "town_building/exitfromhouse_and_to_town.png":
                return ((74, 744), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_exit
        self.mock_mouse.click.reset_mock()
        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = self.mock_capturer.get_window_rect()

        self.state_machine.is_dev_subflow_run = True
        handler.handle(fake_img, rect)
        self.mock_mouse.click.assert_called_once_with(74, 744)
        mock_sys_exit.assert_called_once_with(0)

    @patch('os.path.exists')
    def test_town_pipeline_in_various_modes_stage_dungeon_mix(self, mock_exists):
        """
        驗證城鎮流水線在不同掛機模式 (stage, dungeon, mix) 下：
        流水線執行完畢後標記 100% 重置為 False，且狀態恢復至 STATE_NAVIGATING 續行該模式！
        """
        mock_exists.return_value = True
        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = self.mock_capturer.get_window_rect()

        for mode_name in ["stage", "dungeon", "mix"]:
            self.state_machine.config = GAME_CONFIGS[mode_name].copy()
            
            # 手動模擬觸發流水線
            self.state_machine.trigger_town_subflow_chain()
            self.assertTrue(self.state_machine.need_blood_altar)
            self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BLOOD_ALTAR)

            # 模擬血之祭壇完成並離場
            altar_handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
            altar_handler.reset_state()
            altar_handler.step_phase = "ALL_DONE_EXITING"
            def mock_match_exit(img, name, **kw):
                if name in ["common/door.png", "town_building/exitfromhouse_and_to_town.png"]:
                    return ((74, 744), 0.90)
                return (None, 0.0)
            self.mock_matcher.match.side_effect = mock_match_exit
            altar_handler.handle(fake_img, rect)

            # 第一站完成 ➔ 切換至珠寶加工廠
            self.assertFalse(self.state_machine.need_blood_altar)
            self.assertTrue(self.state_machine.need_jewelry_workshop)
            self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_JEWELRY_WORKSHOP)

            # 模擬珠寶加工廠完成並離場
            jewelry_handler = self.state_machine.handlers[self.state_machine.STATE_JEWELRY_WORKSHOP]
            jewelry_handler.reset_state()
            jewelry_handler.step_phase = "ALL_DONE_EXITING"
            jewelry_handler.handle(fake_img, rect)

            # 佇列清空 ➔ 100% 恢復 NAVIGATING 且標記全重置
            self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
            self.assertFalse(self.state_machine.need_blood_altar)
            self.assertFalse(self.state_machine.need_jewelry_workshop)

    @patch('os.path.exists')
    def test_jewelry_workshop_multiple_sales_same_item(self, mock_exists):
        """
        驗證珠寶加工廠 (JewelryWorkshopHandler) 同一商品有多堆時，
        會在第一堆賣出後繼續二次比對並出售第二堆，售罄後才進位至下一個商品。
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["jewelry_workshop"].copy()
        self.state_machine.current_state = self.state_machine.STATE_JEWELRY_WORKSHOP
        self.state_machine.need_jewelry_workshop = True
        
        handler = self.state_machine.handlers[self.state_machine.STATE_JEWELRY_WORKSHOP]
        handler.reset_state()
        handler.step_phase = "SELL_MENU_OPEN"

        # 假設 goods_settings 中啟用 gray/Sandworm_scales 與 gray/Spider_silk
        handler._get_enabled_goods = MagicMock(return_value=["gray/Sandworm_scales", "gray/Spider_silk"])

        match_call_count = {"Sandworm_scales": 0}

        def mock_match(img, name, **kw):
            if "Sandworm_scales" in name:
                match_call_count["Sandworm_scales"] += 1
                # 前 3 次比對 (初始搜尋、賣完1後 post_sell 檢查、第 2 輪搜尋) 回傳找到
                if match_call_count["Sandworm_scales"] <= 3:
                    return ((100, 100), 0.90)
                return (None, 0.0)
            elif name == "town_building/sell.png":
                return ((200, 200), 0.90)
            elif name == "town_building/sell_max.png":
                return ((300, 300), 0.90)
            elif name == "common/confirm.png" or name == "common/ok.png":
                if img is not fake_img:
                    return ((400, 400), 0.90)
                return (None, 0.0)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = fake_img
        rect = self.mock_capturer.get_window_rect()

        # Step 1: 處理第一堆 Sandworm_scales 出售
        handler.handle(fake_img, rect)
        self.assertEqual(handler.current_goods_idx, 0)  # 仍保留在商品 0
        self.assertEqual(handler.repeat_sell_count, 1)

        # Step 2: 處理第二堆 Sandworm_scales 出售
        handler.handle(fake_img, rect)
        self.assertEqual(handler.current_goods_idx, 1)  # 第二堆售罄後進位至商品 1
        self.assertEqual(handler.repeat_sell_count, 0)


if __name__ == "__main__":
    unittest.main()
