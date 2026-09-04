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


class TestSafetyAndBattleScenarios(BehavioralScenarioTestCase):

    def test_manual_pause_and_resume(self):
        """
        [行為場景 7] 手動暫停與恢復行為：
        Given: 狀態機掛機中。
        When:
          1. 呼叫 state_machine.pause() ➔ is_paused 為 True，狀態機鎖定當前狀態且跳過步進。
          2. 呼叫 state_machine.resume() ➔ is_paused 為 False，狀態機恢復步進。
        """
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        self.assertFalse(self.state_machine.is_paused)
        
        # 1. 進入暫停
        self.state_machine.pause()
        self.assertTrue(self.state_machine.is_paused)
        
        # 2. 恢復執行
        self.state_machine.resume()
        self.assertFalse(self.state_machine.is_paused)
        self.assertTrue(self.state_machine.just_resumed_from_user)

    @patch('pyautogui.moveTo')
    def test_mouse_controller_prohibits_movement_on_user_operating(self, mock_move_to):
        """
        [行為場景 8] 腳本防搶滑鼠控制行為：
        Given: 狀態機處於暫停狀態 (is_paused == True)。
        When: 腳本調用 mouse.click() 或 mouse.scroll()。
        Then:
          1. 應拒絕執行動作（立即回傳 False），且不呼叫 pyautogui.moveTo。
        """
        from actions.mouse import MouseController
        controller = MouseController(
            human_like=False,
            is_paused_fn=lambda: getattr(self.state_machine, 'is_paused', False)
        )
        
        # 模擬狀態機處於手動暫停
        self.state_machine.is_paused = True
        
        # 呼叫 click 應拒絕並回傳 False
        res = controller.click(500, 500)
        self.assertFalse(res)
        mock_move_to.assert_not_called()
        
        # 呼叫 scroll 應拒絕並回傳 False
        res_scroll = controller.scroll(-5, 500, 500)
        self.assertFalse(res_scroll)
        mock_move_to.assert_not_called()

    @patch('pyautogui.moveTo')
    def test_mouse_controller_detects_shift_and_prohibits_movement(self, mock_move_to):
        """
        [行為場景 9] 狀態機恢復後，滑鼠控制器正常恢復點擊能力。
        """
        from actions.mouse import MouseController
        controller = MouseController(
            human_like=False,
            is_paused_fn=lambda: getattr(self.state_machine, 'is_paused', False)
        )
        
        self.state_machine.is_paused = False
        self.state_machine.user_operating = False
        
        # 正常狀態下 check_user_intervention 應為 False
        self.assertFalse(controller.check_user_intervention())

    @patch('os.path.exists')
    @patch('time.time')
    def test_battle_auto_click_cooldown_defense(self, mock_time, mock_exists):
        """
        [行為場景 13] 啟用自動戰鬥防重複點擊 CD 機制：
        Given: 狀態機處於 BATTLE 狀態。
        When:
          1. 時間 1000.0s，看到 auto.png (未啟用)，點擊啟用。
          2. 時間 1001.5s (間隔 1.5s < 3.0s)，即使又看到 auto.png 也不應點擊。
          3. 時間 1004.0s (間隔 4.0s > 3.0s)，看到 auto.png 應再次點擊。
        Then:
          1. 第一步應點擊，並更新 last_auto_click_time。
          2. 第二步應跳過點擊。
          3. 第三步應再次點擊。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        self.state_machine.last_auto_click_time = 0.0
        mock_exists.return_value = True
        
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((200, 200), 0.9) if name == "common/auto.png" else (None, 0.0)
        )
        
        # Step 1: 1000s 執行第一步 ➔ 應點擊
        mock_time.return_value = 1000.0
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_once_with(200, 200)
        self.assertEqual(self.state_machine.last_auto_click_time, 1000.0)
        
        # Step 2: 1000.5s 執行第二步 (間隔 0.5s < 1.0s) ➔ 應跳過點擊
        mock_time.return_value = 1000.5
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_not_called()
        self.assertEqual(self.state_machine.last_auto_click_time, 1000.0)
        
        # Step 3: 1001.5s 執行第三步 (間隔 1.5s > 1.0s) ➔ 應再次點擊
        mock_time.return_value = 1001.5
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_once_with(200, 200)
        self.assertEqual(self.state_machine.last_auto_click_time, 1001.5)

    @patch('os.path.exists')
    def test_result_continue_button_click(self, mock_exists):
        """
        [行為場景 14] 結算畫面點擊繼續按鈕：
        Given: 狀態機處於 RESULT 狀態。畫面上看見繼續按鈕 common/continue.png。
        When: 執行狀態機決策。
        Then: 程式應匹配並點擊 common/continue.png，推進結算流程。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        mock_exists.return_value = True
        
        # 設定模擬的單一繼續模板
        self.state_machine.continue_template = "common/continue.png"
        
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((300, 300), 0.9) if name == "common/continue.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        
        # Act
        self.state_machine.step()
        
        # Assert
        self.mock_mouse.click.assert_called_with(300, 300)

    @patch('os.path.exists')
    def test_state_machine_default_fallback_state(self, mock_exists):
        """
        [行為場景 16] 全域掃描未知狀態時的 bounded recovery：
        Given: 狀態機處於 UNKNOWN 狀態，且畫面匹配不到任何已知主要特徵。
        When: 執行全域狀態掃描。
        Then:
          - 無證據時保持 UNKNOWN，不以 config 猜測場景。
          - 有明確戰鬥特徵時仍進入 BATTLE。
          - UNKNOWN 達上限時要求重開。
        """
        # Arrange
        mock_exists.return_value = True
        
        # 情況 A-1: 關卡模式，且無自動戰鬥特徵
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        self.state_machine.config["unknown_scene_relaunch_attempts"] = 2
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        self.state_machine.request_relaunch = MagicMock()
        self.mock_matcher.match.return_value = (None, 0.0) # 全部回傳 None
        
        # Act 情況 A-1
        self.state_machine.step()
        
        # Assert 情況 A-1: 保持 UNKNOWN 等待下一幀
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)
        self.state_machine.request_relaunch.assert_not_called()
        
        # 情況 A-2: 關卡模式，但偵測到自動戰鬥特徵
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        self.state_machine.unknown_scene_count = 0
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 100), 0.9) if name == "common/auto.png" else (None, 0.0)
        )
        
        # Act 情況 A-2
        self.state_machine.step()
        
        # Assert 情況 A-2: 預設進入 BATTLE
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)
        
        # 情況 B: 地下城模式也不得猜成 EXPLORING，達上限後重開
        self.state_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.config["unknown_scene_relaunch_attempts"] = 2
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        self.state_machine.unknown_scene_count = 1
        self.mock_matcher.match.side_effect = None
        self.mock_matcher.match.return_value = (None, 0.0)
        
        # Act 情況 B
        self.state_machine.step()
        
        # Assert 情況 B: 不猜場景，升級至 relaunch recovery
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)
        self.state_machine.request_relaunch.assert_called_once_with(
            "unknown_scene_detection_exhausted"
        )

    @patch('os.path.exists')
    def test_result_exit_battle_click(self, mock_exists):
        """
        [行為場景 17] 結算畫面點擊離開戰鬥：
        Given: 狀態機處於 RESULT 狀態。畫面上看見離開戰鬥按鈕 exit_battle.png。
        When: 執行狀態機決策。
        Then: 程式應點擊 exit_battle.png 退出結算，返回大廳。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        self.state_machine.need_bag_cleaning = True
        mock_exists.return_value = True
        
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((200, 200), 0.9) if name == "exit_battle.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        
        # Act
        self.state_machine.step()
        
        # Assert
        self.mock_mouse.click.assert_called_with(200, 200)

    @patch('os.path.exists')
    def test_result_exit_battle_ignored_if_bag_not_full(self, mock_exists):
        """
        [行為場景 17-B] 背包未滿且無定時任務時忽略離開戰鬥按鈕：
        Given: 狀態機處於 RESULT 狀態，且 need_bag_cleaning = False、need_diamond_collection = False、need_bread_collection = False。
        When: 執行狀態機決策。
        Then: 即使看見離開戰鬥按鈕 exit_battle.png，也應該忽略不點擊。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        self.state_machine.need_bag_cleaning = False
        self.state_machine.need_diamond_collection = False
        self.state_machine.need_bread_collection = False
        mock_exists.return_value = True
        
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((200, 200), 0.9) if name == "exit_battle.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        
        # Act
        self.state_machine.step()
        
        # Assert
        self.mock_mouse.click.assert_not_called()

    @patch('os.path.exists')
    def test_result_no_match_fallback_to_unknown(self, mock_exists):
        """
        [行為場景 19] 結算畫面超時未匹配自動降級機制：
        Given: 狀態機處於 RESULT 狀態。畫面上連續多次找不到任何結算按鈕。
        When: 執行 5 次狀態機步進。
        Then:
          - 第 1 到 4 次，狀態依然是 RESULT。
          - 第 5 次，狀態轉移到 UNKNOWN。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        mock_exists.return_value = True
        
        # 模擬完全匹配不到任何東西
        self.mock_matcher.match.return_value = (None, 0.0)
        
        # Act & Assert
        # 前 4 次狀態不變
        for _ in range(4):
            self.state_machine.step()
            self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_RESULT)
            
        # 第 5 次狀態變為 UNKNOWN
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)

    def test_stuck_count_reset_on_mouse_action(self):
        """
        [行為場景 23] 鼠標操作 (點擊與滾動) 後自動重置卡死計數器：
        Given: 狀態機 stuck 計為 10。
        When & Then:
          1. 呼叫 mouse.click() ➔ consecutive_stuck_count 應重置為 0。
          2. 呼叫 mouse.scroll() ➔ consecutive_stuck_count 應重置為 0。
        """
        from actions.mouse import MouseController
        real_mouse = MouseController(
            human_like=False,
            # Callback 接線 (Issue #11)：動作成功後通知 SM 重置卡死計數
            on_action_success=lambda: setattr(self.state_machine, 'consecutive_stuck_count', 0),
            is_paused_fn=lambda: getattr(self.state_machine, 'is_paused', False),
        )
        
        self.state_machine.user_operating = False

        # 用 patch 避免發出真實滑鼠動作，並強制使用者介入檢查為 False
        with patch('pyautogui.moveTo'), \
             patch('pyautogui.mouseDown'), \
             patch('pyautogui.mouseUp'), \
             patch('pyautogui.scroll'), \
             patch.object(real_mouse, 'check_user_intervention', return_value=False):
             
            # 1. click 測試
            self.state_machine.consecutive_stuck_count = 10
            real_mouse.click(100, 100)
            self.assertEqual(self.state_machine.consecutive_stuck_count, 0)
            
            # 2. scroll 測試
            self.state_machine.consecutive_stuck_count = 10
            real_mouse.scroll(-800, 100, 100)
            self.assertEqual(self.state_machine.consecutive_stuck_count, 0)

    @patch('os.path.exists')
    def test_detect_state_auto_quit_sub_interface(self, mock_exists):
        """
        [行為場景 25] 未知狀態下在手動子介面自動點擊退出按鈕返回大廳：
        Given: 狀態機處於 UNKNOWN 狀態，且無        with patch('cv2.imread', return_value=np.zeros((10, 10, 3), dtype=np.uint8)), \
             patch('cv2.matchTemplate', side_effect=mock_matchTemplate_a):
            self.mock_mouse.drag.reset_mock()
            self.state_machine.step()
            self.mock_mouse.drag.assert_called_once_with(700, 500, 500, 500, duration=0.8, inertia=False)
             
        # 案例 B：目標是 Slime_entry (index 0)，畫面上只有 Ruins_entry (index 3) 於 X=100
        # 預期：目標 index (0) 小於當前可見 index (3)，代表目標在左側 ➔ 向右滑動 drag(500, 500, 700, 500)
        self.state_machine.config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png", "dungeons/Slime_entry.png"]
        
        call_count_b = 0
        def mock_matchTemplate_b(img_arg, templ, method):
            nonlocal call_count_b
            val = 0.95 if call_count_b == 3 else 0.0
            call_count_b += 1
            return np.array([[val]], dtype=np.float32)
            
        with patch('cv2.imread', return_value=np.zeros((10, 10, 3), dtype=np.uint8)), \
             patch('cv2.matchTemplate', side_effect=mock_matchTemplate_b):
            self.mock_mouse.drag.reset_mock()
            self.state_machine.step()
            self.mock_mouse.drag.assert_called_once_with(500, 500, 700, 500, duration=0.8, inertia=False)糊糊的石窟, index 0) 冷卻已過。
               - 畫面上匹配到基準入口 dungeons/Slime_entry.png 於 (0, 0)。
        When: 執行狀態機導航決策。
        Then:
               1. 應依序 4 -> 3 -> 2 -> 1 遍歷檢查。
               2. 第 4 關與第 3 關因為冷卻跳過。
               3. 第 2 關 (index 1) 未冷卻且偵測到亮骨頭 (解鎖)，應點擊進入第 2 關 (X=678, Y=170)。
               4. 記錄當前地下城索引 `current_dungeon_index = 1`。
        """
        mock_exists.return_value = True
        
        # 設定貪婪地下城配置
        config = GAME_CONFIGS["dungeon"].copy()
        config["greedy_dungeon"] = True
        config["greedy_allowed_indices"] = [0, 1, 2, 3, 4]
        config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png"]
        self.state_machine.config = config
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        
        # 設定冷卻時間
        self.state_machine.dungeon_cooldowns = {
            4: float('inf'),          # 第 5 關：永久不可刷
            3: float('inf'),          # 第 4 關：永久不可刷
            2: time.time() + 100.0,   # 第 3 關：冷卻中
            1: 0.0,                   # 第 2 關：就緒
            0: 0.0                    # 第 1 關：就緒
        }
        
        # Mock 視窗大小為 1920x1080 (scale = 1.0)
        self.mock_capturer.get_window_rect.return_value = {
            "left": 0, "top": 0, "width": 1920, "height": 1080
        }
        
        # Mock 截圖 (BGR格式)
        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = img
        
        # Mock 匹配邏輯
        def mock_match_impl(screen, name, threshold):
            if name == "dungeons/Slime_entry.png":
                return ((173, 170), 0.95)
            elif name == "dungeons/Ghost_entry.png":
                return ((693, 170), 0.95)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = mock_match_impl
        self.mock_mouse.click.reset_mock()
        
        # Mock cv2.imread 與 cv2.minMaxLoc 以免依賴實體圖片與黑色裁切
        mock_light_t = np.zeros((45, 45, 3), dtype=np.uint8)
        
        def mock_minMaxLoc_impl(res):
            if res.shape[1] > 500:
                # 卡片匹配：回傳 Ghost 卡片起點 X=520 (center=693)
                return (0.0, 0.95, (0, 0), (520, 0))
            elif res.shape[1] > 200:
                # 冷卻木牌匹配：回傳無冷卻
                return (0.0, 0.0, (0, 0), (0, 0))
            else:
                # 骨頭匹配
                return (0.0, 0.88, (0, 0), (0, 0))
                
        def mock_imread_impl(path):
            if "entry" in path:
                return np.zeros((341, 346, 3), dtype=np.uint8)
            return np.zeros((10, 10, 3), dtype=np.uint8)
            
        with patch('cv2.imread', side_effect=mock_imread_impl), \
             patch('cv2.minMaxLoc', side_effect=mock_minMaxLoc_impl):
            # Act
            self.state_machine.step()
        
        # Assert
        # 1. 應點擊第 2 關的中心點：
        # x = 0 + 1 * 520 + 346 // 2 = 693
        # y = 0 + 341 // 2 = 170
        self.mock_mouse.click.assert_called_with(693, 170)
        
        # 2. current_dungeon_index 應更新為 1
        self.assertEqual(self.state_machine.current_dungeon_index, 1)

    @patch('os.path.exists')
    def test_battle_unexpected_exit_protection(self, mock_exists):
        """
        [行為場景 26] 戰鬥狀態下意外退出保護與重設機制：
        Given: 狀態機處於 BATTLE 狀態下，且已過 8 秒安全期。
        When: 畫面中完全沒有任何戰鬥特徵圖與結算圖，持續 5 秒。且大廳大門 common/door.png 可見。
        Then: 狀態機應將狀態轉移至 STATE_UNKNOWN，且相關計時器重置。
        """
        self.state_machine.config = {
            "type": "stage",
            "result_buttons": ["common/continue.png"]
        }
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        self.state_machine.battle_start_time = time.time() - 10.0 # 過了 8 秒
        
        # 取得 BattleHandler 實例
        handler = self.state_machine.handlers[self.state_machine.STATE_BATTLE]
        handler.non_battle_feature_start_time = None
        
        mock_exists.return_value = True
        
        # 1. 模擬完全偵測不到戰鬥與結算特徵
        self.mock_matcher.match.return_value = (None, 0.0)
        
        # 第一步：觸發計時器啟動
        self.state_machine.step()
        self.assertIsNotNone(handler.non_battle_feature_start_time)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)
        
        # 第二步：手動將計時器調至 6 秒前，模擬超時
        handler.non_battle_feature_start_time = time.time() - 6.0
        
        # 模擬此時看見大門 common/door.png 
        def mock_match_with_door(img, name, threshold, **kwargs):
            if name == "common/door.png":
                return ((100, 100), 0.90)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = mock_match_with_door
        self.mock_mouse.click.reset_mock()
        
        # Act
        self.state_machine.step()
        
        # Assert
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)
        self.assertIsNone(handler.non_battle_feature_start_time)
        self.assertIsNone(self.state_machine.battle_start_time)
        self.mock_mouse.click.assert_not_called() # 已經在大廳，直接重設狀態，不觸發關閉點選

    @patch('os.path.exists')
    def test_battle_unexpected_exit_protection_click_quit(self, mock_exists):
        """
        [行為場景 27] 戰鬥狀態下意外退出且不在大廳，嘗試點點通用退出按鈕：
        Given: 狀態機處於 BATTLE 狀態下，且已過 8 秒安全期，無戰鬥與結算特徵持續 5 秒。
        When: 畫面中看不見大廳大門，但看見 common/quit.png。
        Then: 狀態機應點擊 common/quit.png，隨後重置狀態至 STATE_UNKNOWN。
        """
        self.state_machine.config = {
            "type": "stage",
            "result_buttons": ["common/continue.png"]
        }
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        self.state_machine.battle_start_time = time.time() - 10.0
        
        handler = self.state_machine.handlers[self.state_machine.STATE_BATTLE]
        handler.non_battle_feature_start_time = time.time() - 6.0 # 模擬已超時
        
        mock_exists.return_value = True
        
        # 模擬看不到大廳大門，但看見 common/quit.png
        def mock_match_with_quit(img, name, threshold, **kwargs):
            if name == "common/quit.png":
                return ((200, 200), 0.90)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = mock_match_with_quit
        self.mock_mouse.click.reset_mock()
        
        # Act
        self.state_machine.step()
        
        # Assert
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)
        self.assertIsNone(handler.non_battle_feature_start_time)
        self.mock_mouse.click.assert_called_with(200, 200)

    @patch('sys.exit')
    @patch('os.path.exists')
    def test_independent_modes_isolation(self, mock_exists, mock_sys_exit):
        """
        驗證獨立 CLI 模式 (jewelry_workshop, blood_altar)：
        完成後直接 sys.exit(0) 結束程式，絕不誤觸城鎮流水線與 STATE_NAVIGATING！
        """
        mock_exists.return_value = True
        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = self.mock_capturer.get_window_rect()

        def mock_match_exit(img, name, **kw):
            if name in ["common/door.png", "town_building/exitfromhouse_and_to_town.png"]:
                return ((74, 744), 0.90)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = mock_match_exit

        # 1. 獨立血之祭壇模式
        self.state_machine.is_dev_subflow_run = True
        self.state_machine.town_subflow_queue = []
        self.state_machine.config = GAME_CONFIGS["blood_altar"].copy()
        altar_handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        altar_handler.reset_state()
        altar_handler.step_phase = "ALL_DONE_EXITING"
        altar_handler.handle(fake_img, rect)
        mock_sys_exit.assert_called_with(0)

        # 2. 獨立珠寶加工廠模式
        mock_sys_exit.reset_mock()
        self.state_machine.is_dev_subflow_run = True
        self.state_machine.town_subflow_queue = []
        self.state_machine.config = GAME_CONFIGS["jewelry_workshop"].copy()
        jewelry_handler = self.state_machine.handlers[self.state_machine.STATE_JEWELRY_WORKSHOP]
        jewelry_handler.reset_state()
        jewelry_handler.step_phase = "ALL_DONE_EXITING"
        jewelry_handler.handle(fake_img, rect)
        mock_sys_exit.assert_called_with(0)

    @patch('os.path.exists')
    def test_bag_clean_dry_run_safety(self, mock_exists):
        """
        測試當開啟 dry_run_bag_clean = True 時：
        BagCleaningHandler 偵測到 common/Disassembly.png 不會進行真實分解點擊，
        而是點擊 quit 關閉視窗並標記 bag_disassembled = True，確保裝備安全且無 error 繼續走完流程！
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["mix"].copy()
        self.state_machine.config["dry_run_bag_clean"] = True
        self.state_machine.current_state = self.state_machine.STATE_BAG_CLEANING
        
        bag_handler = self.state_machine.handlers[self.state_machine.STATE_BAG_CLEANING]
        if hasattr(bag_handler, 'reset_state'):
            bag_handler.reset_state()
        self.state_machine.bag_select_all_clicked = True
        self.state_machine.bag_deselected = True
        self.state_machine.bag_disassembled = False

        dis_pos = (500, 500)
        quit_pos = (800, 200)

        quit_matched = [False]
        def mock_match(img, name, **kw):
            if name == "common/Disassembly.png":
                return (dis_pos, 0.90)
            elif name == "common/quit.png" and not quit_matched[0]:
                quit_matched[0] = True
                return (quit_pos, 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match
        self.mock_mouse.click.reset_mock()

        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = self.mock_capturer.get_window_rect()

        bag_handler.handle(fake_img, rect)
        
        # 驗證沒有點擊分解按鈕 (500, 500)
        for call_args in self.mock_mouse.click.call_args_list:
            self.assertNotEqual(call_args[0], dis_pos)
        
        # 驗證成功點擊了 quit 按鈕 (800, 200) 且 bag_disassembled 被設為 True
        self.mock_mouse.click.assert_called_once_with(quit_pos[0], quit_pos[1])
        self.assertTrue(self.state_machine.bag_disassembled)


if __name__ == "__main__":
    unittest.main()
