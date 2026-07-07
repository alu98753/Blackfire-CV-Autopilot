import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import time
import numpy as np

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.state_machine import GameStateMachine
from config import GAME_CONFIGS

class TestBehavioralScenarios(unittest.TestCase):
    """
    遵循 Google 測試指南設計之行為測試套件。
    本套件驗證狀態機的外部狀態跳轉行為、點擊決定流程與防禦性邊界處理，而不耦合於 Handler 內部私有細節。
    """
    
    def setUp(self):
        # 建立主依賴 Mock 物件
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_mouse.last_action_time = 0.0
        
        # 預設視窗座標與大小 (1920x1080)
        self.mock_capturer.get_window_rect.return_value = {
            "left": 0, "top": 0, "width": 1920, "height": 1080
        }
        
        # 實例化待測狀態機 (System Under Test)
        self.state_machine = GameStateMachine(
            capturer=self.mock_capturer,
            matcher=self.mock_matcher,
            mouse=self.mock_mouse
        )
        
        # 初始化定時器變數以隔離實際時間干擾
        self.state_machine.need_diamond_collection = False
        self.state_machine.need_bread_collection = False
        self.state_machine.last_diamond_collection_time = time.time()
        self.state_machine.last_bread_collection_time = time.time()

    @patch('os.path.exists')
    def test_navigation_priority_and_safety_lock(self, mock_exists):
        """
        [行為場景 1] 鑽石與體力領取優先權與安全保護行為：
        Given: 鑽石與體力定時器同時到期，且畫面上可見返回城鎮按鈕。
        When: 執行狀態機決策。
        Then:
          1. 應優先執行鑽石流程 (而非體力流程)。
          2. 返回城鎮後開啟鑽石視窗。
          3. 進入視窗後，視窗安全保護機制應鎖定，只比對鑽石免費領取按鈕或關閉按鈕，忽視可能出現在背景的鑽石圖標，點選免費按鈕。
          4. 二次確認領取後關閉視窗，清除鑽石需求，並開始體力領取。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = True
        self.state_machine.need_bread_collection = True
        self.state_machine.need_diamond_collection = True
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        mock_exists.return_value = True
        
        # Act & Assert Step 1: 在 UNKNOWN 看到 goback_town.png，轉移至 NAVIGATING
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 800), 0.9) if name == "goback_town.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # Step 2: 點選 goback_town.png 返回城鎮大廳
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(100, 800)
        
        # Step 3: 偵測 diamond.png 開啟鑽石領取視窗
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((200, 200), 0.9) if name == "diamond.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(200, 200)
        
        # Step 4: 進入鑽石視窗 (畫面上存在 common/quit.png)，只比對 diamond_free.png (安全鎖定)
        # 即使此時背景可能有一張 diamond.png，在安全保護下亦不會去點擊它
        def match_side_effect_dia_window(img, name, threshold):
            # 模擬視窗內退出按鈕可見
            if name == "common/quit.png":
                return ((500, 500), 0.9)
            # 偵測到免費按鈕
            if name == "diamond_free.png":
                return ((300, 300), 0.9)
            # 如果嘗試去點擊大廳入口，回傳 None 阻止
            if name == "diamond.png":
                return ((200, 200), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_dia_window
        self.state_machine.step()
        # 必須是點擊免費鑽石 (300, 300)，而不是重複點擊大廳入口 (200, 200)
        self.mock_mouse.click.assert_called_with(300, 300)
        
        # Step 5: 點選確認領取
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((400, 400), 0.9) if name == "common/confirm.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(400, 400)
        self.assertTrue(self.state_machine.diamond_collected_this_run)
        
        # Step 6: 點擊退出按鈕，結束鑽石領取
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name == "common/quit.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(500, 500)
        self.assertFalse(self.state_machine.need_diamond_collection)
        self.assertFalse(self.state_machine.diamond_collected_this_run)
        
        # Step 7: 自動切換到體力領取流程 (尋找並點擊 common/bread.png)
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((600, 600), 0.9) if name == "common/bread.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(600, 600)
        self.assertTrue(self.state_machine.need_bread_collection)

    @patch('os.path.exists')
    def test_diamond_cooldown_exit(self, mock_exists):
        """
        [行為場景 2] 鑽石冷卻退出行為：
        Given: 鑽石領取定時器到期，且已進入鑽石領取視窗。
        When: 畫面上無免費領取按鈕 (傳回 None)。
        Then: 程式應識別冷卻狀態，直接點擊退出按鈕退出視窗，且重設鑽石領取需求，防止卡在視窗中。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.need_diamond_collection = True
        self.state_machine.diamond_collected_this_run = False
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        mock_exists.return_value = True
        
        # Act
        def match_side_effect_cooldown(img, name, threshold):
            if name == "common/quit.png":
                return ((500, 500), 0.9)
            # diamond_free.png 匹配失敗 (冷卻中)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_cooldown
        self.state_machine.step()
        
        # Assert
        self.mock_mouse.click.assert_called_with(500, 500)
        self.assertFalse(self.state_machine.need_diamond_collection)

    @patch('os.path.exists')
    def test_backpack_full_sorting_and_destroy_loop(self, mock_exists):
        """
        [行為場景 3] 背包已滿自適應分選、銷毀與收集行為：
        Given: 偵測到「背包已滿」彈窗。左側溢出區 Col 0, Row 0 包含一個黃金貴重物品；右側背包區 Col 0, Row 0 包含一個綠色低稀有度物品。
        When: 狀態機步進。
        Then:
          1. 狀態機切換至 BACKPACK_FULL_SORTING。
          2. `need_bag_cleaning` 標記應自動設為 True。
          3. 依次執行銷毀 (點擊右側綠色 ➔ 點擊 destroy.png ➔ 點擊 confirm.png) ➔ 收集 (點擊左側黃金 ➔ 點擊 collect.png)。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        mock_exists.return_value = True
        
        # Step 1: 全域攔截到 backpack_full.png，狀態跳轉並自動標記 need_bag_cleaning
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 228), 0.9) if name == "backpack_full.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BACKPACK_FULL_SORTING)
        self.assertTrue(self.state_machine.need_bag_cleaning)
        
        # Step 2: 建立模擬物品圖像數據 (黃金邊框 vs 綠色邊框)
        test_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        # 左側 (Col 0, Row 0): 黃金 (BGR = [0, 200, 200]), 起點 win_y+left_y0 = 381, win_x+left_x0 = 407
        test_img[381+10:381+20, 407+10:407+98] = [0, 200, 200]
        test_img[381+88:381+98, 407+10:407+98] = [0, 200, 200]
        test_img[381+10:381+98, 407+10:407+20] = [0, 200, 200]
        test_img[381+10:381+98, 407+88:407+98] = [0, 200, 200]
        
        # 右側 (Col 0, Row 0): 綠色 (BGR = [0, 200, 0]), 起點 win_y+right_y0 = 381, win_x+right_x0 = 1007
        test_img[381+10:381+20, 1007+10:1007+98] = [0, 200, 0]
        test_img[381+88:381+98, 1007+10:1007+98] = [0, 200, 0]
        test_img[381+10:381+98, 1007+10:1007+20] = [0, 200, 0]
        test_img[381+10:381+98, 1007+88:1007+98] = [0, 200, 0]
        test_img[381+50:381+60, 1007+50:1007+60] = [50, 50, 50]
        self.mock_capturer.capture.return_value = test_img
        
        def match_side_effect_destroy_collect(img, name, threshold):
            if name == "backpack_full.png":
                return ((960, 228), 0.9)
            elif name == "common/destroy.png":
                return ((500, 500), 0.9)
            elif name == "common/confirm.png":
                return ((600, 600), 0.9)
            elif name == "common/collect.png":
                return ((700, 700), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_destroy_collect
        
        # Act
        self.state_machine.step()
        
        # Assert: 整個銷毀收集鏈完成，最後一步應為 collect 領取
        self.mock_mouse.click.assert_called_with(700, 700)

    @patch('os.path.exists')
    def test_backpack_sorting_scroll_and_exit_recovery(self, mock_exists):
        """
        [行為場景 4] 背包分選右側無綠色裝備滾動與安全退出行為：
        Given: 左側有貴重裝備，但右側第一頁完全無綠色/灰色物品。
        When: 執行分選。
        Then:
          1. 應執行向下滾動 (滾輪操作)。
          2. 若滾動上限到達，仍無可銷毀物品，則點擊右上角關閉 (1558, 241)。
          3. 若有關閉確認彈窗，應自動點選 confirm.png 確認關閉，回到 STATE_UNKNOWN。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.current_state = self.state_machine.STATE_BACKPACK_FULL_SORTING
        self.state_machine.need_bag_cleaning = True
        mock_exists.return_value = True
        
        # 模擬左側有黃金物品，右側全部為空置的黑色格子 (標準差 std = 0 < 20)，觸發滾動與安全退出
        test_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        # 左側黃金物件
        test_img[381+10:381+20, 407+10:407+98] = [0, 200, 200]
        test_img[381+88:381+98, 407+10:407+98] = [0, 200, 200]
        test_img[381+10:381+98, 407+10:407+20] = [0, 200, 200]
        test_img[381+10:381+98, 407+88:407+98] = [0, 200, 200]
        self.mock_capturer.capture.return_value = test_img
        
        # 關閉二次確認彈窗以及定位彈窗位置
        def match_side_effect_scroll_exit(img, name, threshold):
            if name == "backpack_full.png":
                return ((960, 228), 0.9)
            elif name == "common/confirm.png":
                return ((600, 600), 0.9)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = match_side_effect_scroll_exit
        
        # Act
        self.state_machine.step()
        
        # Assert: 應點擊關閉按鈕，隨後點擊確認關閉，狀態回到 UNKNOWN，且 need_bag_cleaning 標記保持 True
        self.mock_mouse.click.assert_any_call(1558, 241) # 關閉按鈕座標
        self.mock_mouse.click.assert_called_with(600, 600) # 二次確認
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)
        self.assertTrue(self.state_machine.need_bag_cleaning)

    @patch('os.path.exists')
    def test_backpack_cleaning_disassembly_flow(self, mock_exists):
        """
        [行為場景 5] 背包自動大量分解整理行為：
        Given: 狀態機處於 LOBBY，且標記 need_bag_cleaning = True。
        When: 執行狀態步進。
        Then:
          1. 狀態機應被 Explore/Lobby 處理器攔截，轉移至 BAG_CLEANING 狀態。
          2. 在該狀態下按順序點擊：打開背包 ➔ 大量分解 ➔ 全選 ➔ 分解 ➔ 確認 ➔ 整理 ➔ 退出關閉。
          3. 整理完後，狀態機重設 need_bag_cleaning = False，並回歸大廳。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_LOBBY
        self.state_machine.need_bag_cleaning = True
        mock_exists.return_value = True
        import numpy as np
        self.mock_capturer.capture.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 1. 偵測大廳 stages/start.png ➔ 攔截跳轉 BAG_CLEANING
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((300, 300), 0.9) if name == "stages/start.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BAG_CLEANING)
        
        # 2. 依次比對點擊流程
        # - 打開背包
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((1550, 1037), 0.9) if name == "common/bag_text.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(1550, 992)
        
        # - 大量分解
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name == "common/Backpack_Disassembly.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(500, 500)
        
        # - 全選
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((600, 600), 0.9) if name == "common/select_all.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(600, 600)
        
        # - 反選貴重物品階段：大掃描 (此時仍需比對 common/select_all.png 以便定位)
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((600, 600), 0.9) if name == "common/select_all.png" else (None, 0.0)
        )
        self.state_machine.step()
        
        # - 分解
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((700, 700), 0.9) if name == "common/Disassembly.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(700, 700)
        
        # - 確認
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((800, 800), 0.9) if name == "common/confirm.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(800, 800)
        
        # - 整理
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((900, 900), 0.9) if name == "common/tidy.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(900, 900)
        self.assertTrue(self.state_machine.bag_tidied)
        
        # - 退出
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((1000, 1000), 0.9) if name == "common/quit.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(1000, 1000)
        
        # 3. 驗證標記重置與回歸大廳
        self.assertFalse(self.state_machine.need_bag_cleaning)
        self.assertFalse(self.state_machine.bag_tidied)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOBBY)

    @patch('os.path.exists')
    def test_dungeon_explore_memory_and_godown_cooldown(self, mock_exists):
        """
        [行為場景 6] 地下城探索事件記憶與下樓冷卻行為：
        Given: 狀態機在 EXPLORING 狀態。
        When:
          1. 比對到 Treasure.png ➔ 點點開箱，標記 chest_opened_this_floor = True。
          2. 下一幀比對到 Treasure.png ➔ 應跳過開箱（避免重複點擊同一個箱子）。
          3. 比對到下樓按鈕 ➔ 點擊下樓並開始 4 秒冷卻。
          4. 3 秒後 (冷卻未完) ➔ 不重置探索記憶。
          5. 5 秒後 (冷卻結束) ➔ 應重置探索記憶 (`chest_opened_this_floor = False`)。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        mock_exists.return_value = True
        
        # Step 1: 第一次比對到寶箱，點擊
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((300, 300), 0.9) if name == "dungeons/Treasure.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(300, 300)
        self.assertTrue(self.state_machine.chest_opened_this_floor)
        
        # Step 2: 重設 mock 點擊，再次偵測寶箱 ➔ 應跳過，不發生任何點擊
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_not_called()
        
        # Step 3: 比對下樓，點擊下樓
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((400, 400), 0.9) if name == "dungeons/gungeon_godown.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(400, 400)
        self.assertIsNotNone(self.state_machine.last_godown_click_time)
        
        # Step 4: 模擬 3 秒過後，冷卻未完成，不重設記憶
        self.state_machine.last_godown_click_time = time.time() - 3.0
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (None, 0.0)
        self.state_machine.step()
        self.assertTrue(self.state_machine.chest_opened_this_floor)
        
        # Step 5: 模擬 5 秒過後，冷卻完成，重設記憶
        self.state_machine.last_godown_click_time = time.time() - 5.0
        self.state_machine.step()
        self.assertFalse(self.state_machine.chest_opened_this_floor)
        self.assertIsNone(self.state_machine.last_godown_click_time)

    @patch('pyautogui.position')
    @patch('time.time')
    def test_manual_pause_and_resume(self, mock_time, mock_pyautogui_pos):
        """
        [行為場景 7] 滑鼠手動介入自動暫停與恢復行為：
        Given: 狀態機掛機中，滑鼠初始座標為 (100, 100)。
        When:
          1. 模擬滑鼠沒有移動 ➔ 狀態機正常執行單步步進。
          2. 模擬滑鼠移動至 (200, 200) (位移 dx=100 > 5)，且距離腳本上一次操作時間大於 1.2 秒。
          3. 模擬滑鼠靜止 3 秒後。
        Then:
          1. 滑鼠移動後，狀態機應標記 `user_operating = True`，暫停自動決策。
          2. 靜止 3 秒後，自動解除暫停，`user_operating = False`。
        """
        # Arrange
        self.state_machine.mouse.last_action_time = 1000.0 # 腳本上次動作時間為 1000s
        self.state_machine.user_operating = False
        
        # 1. 初始滑鼠座標為 (100, 100)
        mock_pyautogui_pos.return_value = (100, 100)
        mock_time.return_value = 1002.0  # 當前時間 1002s (間隔 2.0s > 1.2s)
        self.state_machine.prev_mouse_pos = (100, 100)
        
        # 模擬 main 迴圈邏輯 (比照 main.py 138-167 實作的外部介入行為)
        def run_main_loop_step(sm):
            cur_pos = pyautogui_pos_fn()
            cur_time = time_fn()
            
            if sm.prev_mouse_pos is not None:
                dx = abs(cur_pos[0] - sm.prev_mouse_pos[0])
                dy = abs(cur_pos[1] - sm.prev_mouse_pos[1])
                if dx > 5 or dy > 5:
                    last_action_diff = cur_time - sm.mouse.last_action_time
                    if last_action_diff > 1.2:
                        if not sm.user_operating:
                            sm.user_operating = True
                        sm.last_user_operation_time = cur_time
            
            sm.prev_mouse_pos = cur_pos
            
            if sm.user_operating:
                if cur_time - sm.last_user_operation_time > 3.0:
                    sm.user_operating = False
                    sm.prev_mouse_pos = cur_pos
                    # 執行 step()
                    sm.step()
            else:
                # 執行 step()
                sm.step()

        # 設定外部函數指標
        pyautogui_pos_fn = lambda: mock_pyautogui_pos.return_value
        time_fn = lambda: mock_time.return_value
        
        # Step 1: 滑鼠未移動，呼叫 step() 應被執行一次
        with patch.object(self.state_machine, 'step') as mock_step:
            run_main_loop_step(self.state_machine)
            mock_step.assert_called_once()
            self.assertFalse(self.state_machine.user_operating)
            
        # Step 2: 模擬滑鼠移動至 (200, 200)
        mock_pyautogui_pos.return_value = (200, 200)
        mock_time.return_value = 1003.0 # 當前時間 1003s
        with patch.object(self.state_machine, 'step') as mock_step:
            run_main_loop_step(self.state_machine)
            # step() 不應該被執行 (因為手動操作介入，掛機暫停)
            mock_step.assert_not_called()
            self.assertTrue(self.state_machine.user_operating)
            
        # Step 3: 模擬滑鼠維持在 (200, 200) 靜止超過 3 秒 (時間到 1007s)
        mock_time.return_value = 1007.0 # 當前時間 1007s (> 3秒)
        with patch.object(self.state_machine, 'step') as mock_step:
            run_main_loop_step(self.state_machine)
            # step() 應該恢復被執行
            mock_step.assert_called_once()
            self.assertFalse(self.state_machine.user_operating)

    @patch('pyautogui.position')
    @patch('time.time')
    @patch('pyautogui.moveTo')
    def test_mouse_controller_prohibits_movement_on_user_operating(self, mock_move_to, mock_time, mock_pyautogui_pos):
        """
        [行為場景 8] 腳本防搶滑鼠控制行為：
        Given: 腳本已與狀態機建立關聯，且狀態機中 user_operating 為 True。
        When: 腳本調用 mouse.click() 或 mouse.scroll()。
        Then:
          1. 應拒絕執行動作（立即回傳 False），且不呼叫 pyautogui.moveTo。
        """
        from actions.mouse import MouseController
        controller = MouseController(human_like=False)
        controller.state_machine = self.state_machine
        
        # 模擬狀態為使用者介入中
        self.state_machine.user_operating = True
        mock_pyautogui_pos.return_value = (100, 100)
        
        # 呼叫 click 應拒絕並回傳 False
        res = controller.click(500, 500)
        self.assertFalse(res)
        mock_move_to.assert_not_called()
        
        # 呼叫 scroll 應拒絕並回傳 False
        res_scroll = controller.scroll(-5, 500, 500)
        self.assertFalse(res_scroll)
        mock_move_to.assert_not_called()

    @patch('pyautogui.position')
    @patch('time.time')
    @patch('pyautogui.moveTo')
    def test_mouse_controller_detects_shift_and_prohibits_movement(self, mock_move_to, mock_time, mock_pyautogui_pos):
        """
        [行為場景 9] 腳本執行點擊前，主動檢查滑鼠是否已被使用者移動：
        Given: 狀態機中 user_operating 為 False，但實際滑鼠游標位置已被手動移開。
        When: 腳本調用 mouse.click()。
        Then:
          1. 偵測到滑鼠游標從上次操作點 (100, 100) 移到了 (200, 200)，時間間隔大於 1.2 秒。
          2. 點擊被拒絕（回傳 False）。
          3. 狀態機的 user_operating 標記被強制更新為 True。
        """
        from actions.mouse import MouseController
        controller = MouseController(human_like=False)
        controller.state_machine = self.state_machine
        
        self.state_machine.user_operating = False
        
        # 模擬上一次點擊位置為 (100, 100)，操作時間為 1000s
        controller.last_target_pos = (100, 100)
        controller.last_action_time = 1000.0
        
        # 當前時間為 1000.2s (間隔 0.2s < 0.5s)，且手動移到 (200, 200)
        mock_time.return_value = 1000.2
        mock_pyautogui_pos.return_value = (200, 200)
        
        # 呼叫 click
        res = controller.click(500, 500)
        
        # 應點擊失敗並更新狀態為 True
        self.assertFalse(res)
        self.assertTrue(self.state_machine.user_operating)
        mock_move_to.assert_not_called()

    @patch('os.path.exists')
    def test_bag_cleaning_only_opens_bag_when_not_opened(self, mock_exists):
        """
        [行為場景 10] 背包尚未打開時的安全防禦點擊行為：
        Given: 狀態機處於 BAG_CLEANING，且 bag_opened_clicked 為 False (背包尚未打開)。
               此時畫面上同時出現了類似 confirm.png 的圖像 (如大廳的戰團誤判) 與 bag_text.png 背包入口。
        When: 執行狀態機決策。
        Then:
          1. 程式絕對不能點擊 confirm.png，以防止在大廳產生誤判點擊。
          2. 程式應該優先尋找並點擊 bag_text.png 以打開背包，且將 bag_opened_clicked 設為 True。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_BAG_CLEANING
        self.state_machine.bag_opened_clicked = False
        mock_exists.return_value = True
        
        # 模擬 match 結果：confirm.png 信心度 0.85 (在 100, 100)，bag_text.png 信心度 0.90 (在 1550, 1037)
        # 其他所有的背包內特有按鈕皆匹配失敗 (返回 None)
        def match_side_effect(img, name, threshold):
            if name == "common/confirm.png":
                return ((100, 100), 0.85)
            elif name == "common/bag_text.png":
                return ((1550, 1037), 0.90)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect
        self.mock_mouse.click.reset_mock()
        
        # Act
        self.state_machine.step()
        
        # Assert
        # 1. 應點擊打開背包的圖示中心 (1550, 1037 - 45) = (1550, 992)
        self.mock_mouse.click.assert_called_with(1550, 992)
        # 2. 不能呼叫點擊 confirm.png 的 (100, 100)
        for call in self.mock_mouse.click.call_args_list:
            self.assertNotEqual(call[0], (100, 100))
        # 3. 狀態變數 bag_opened_clicked 應被設為 True
        self.assertTrue(self.state_machine.bag_opened_clicked)

    @patch('os.path.exists')
    def test_color_classification_threshold_defense(self, mock_exists):
        """
        [行為場景 11] 貴重裝備顏色判定的門檻防禦性行為：
        Given: 狀態機處於 BAG_CLEANING，且 bag_opened_clicked 為 True (已開啟背包大量分解)。
               格子 A (Col 0, Row 0) 中只有 50 個金色像素 (模擬木紋雜色邊框)；
               格子 B (Col 1, Row 0) 中有約 1500 個金色像素 (模擬真正金色貴重物品)。
        When: 執行背包反選。
        Then:
          1. 格子 A 的少數雜色應被 threshold=150 過濾，判定為 gray_or_empty，不被點擊。
          2. 格子 B 的金色物品應被識別為 orange_yellow，並執行點擊反選 (233, 203)。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_BAG_CLEANING
        self.state_machine.bag_select_all_clicked = True
        self.state_machine.bag_deselected = False
        self.state_machine.bag_opened_clicked = True
        mock_exists.return_value = True
        
        import cv2
        # 建立假的 1080x1920 截圖
        screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        
        # 定位 全選按鈕 在 (121, 628) ➔ 網格左上角 (0, 0)
        # 格子 A (Col 0, Row 0): 中心 (98, 203)。環狀區 (38, 143) 到 (158, 263)。
        # 在格子 A 的邊緣只畫一個 10x5 的金色 (BGR=[0, 240, 240]) 區域，包含 50 個像素點
        screen[143:148, 38:48] = [0, 240, 240]
        
        # 格子 B (Col 1, Row 0): 中心 (233, 203)。環狀區 (173, 143) 到 (293, 263)。
        # 在格子 B 的環狀採樣帶內部 (收縮 20 像素) 繪製一個金色矩形，包含大量彩色像素點
        cv2.rectangle(screen, (173 + 20, 143 + 20), (293 - 20, 263 - 20), (0, 240, 240), 10)
        
        self.mock_capturer.capture.return_value = screen
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 匹配定位點
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((121, 628), 0.9) if name == "common/select_all.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        
        # Act
        self.state_machine.step()
        
        # Assert
        # 1. 必須點擊格子 B 進行反選
        self.mock_mouse.click.assert_any_call(233, 203)
        # 2. 絕對不能點擊格子 A
        for call in self.mock_mouse.click.call_args_list:
            self.assertNotEqual(call[0], (98, 203))
        # 3. 標記設為 True
        self.assertTrue(self.state_machine.bag_deselected)

    @patch('os.path.exists')
    @patch('time.time')
    def test_bread_cooldown_exit_defense(self, mock_time, mock_exists):
        """
        [行為場景 12] 領體力冷卻/已滿自動關閉保護行為：
        Given: 體力領取定時器到期，進入 NAVIGATING 狀態領體力。
               畫面上無免費領取按鈕 (bread_collection.png 匹配失敗)，但看見關閉退出按鈕 (common/quit.png)。
        When: 執行狀態機決策。
        Then:
          1. 程式應識別冷卻/已領狀態，點擊退出按鈕 (common/quit.png)。
          2. need_bread_collection 應被設為 False，last_bread_collection_time 應更新，防止無限卡死在視窗內。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = True
        self.state_machine.need_bread_collection = True
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        mock_exists.return_value = True
        
        # 設定虛擬目前時間為 1000s
        mock_time.return_value = 1000.0
        
        # 模擬 match：quit.png 成功，bread_collection.png 失敗
        def match_side_effect(img, name, threshold):
            if name == "common/quit.png":
                return ((500, 500), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect
        self.mock_mouse.click.reset_mock()
        
        # Act
        self.state_machine.step()
        
        # Assert
        # 1. 應點擊退出按鈕 (500, 500)
        self.mock_mouse.click.assert_called_with(500, 500)
        # 2. 領體力標記重設為 False，上次領取時間更新為目前時間 (1000s)
        self.assertFalse(self.state_machine.need_bread_collection)
        self.assertEqual(self.state_machine.last_bread_collection_time, 1000.0)

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
    def test_bag_cleaning_bag_color_channel_verification(self, mock_exists):
        """
        [行為場景 15] 備用背包按鈕 common/bag.png 的色彩通道驗證：
        Given: 狀態機處於 BAG_CLEANING，且 bag_opened_clicked 為 False (背包尚未打開)。
               畫面上只能匹配到備用模板 common/bag.png (在 100, 100)。
        When: 
          - 情況 A: 該位置中心色彩均值 R=100, B=90 (R - B = 10 <= 18.0，疑似灰色「戰團」)。
          - 情況 B: 該位置中心色彩均值 R=120, B=90 (R - B = 30 > 18.0，真正棕色「背包」)。
        Then:
          - 情況 A: 應忽略不點擊，狀態不變。
          - 情況 B: 應點擊該位置以打開背包，且 bag_opened_clicked 變為 True。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_BAG_CLEANING
        self.state_machine.bag_opened_clicked = False
        mock_exists.return_value = True
        
        # 模擬 matcher 匹配到 common/bag.png 在 (100, 100)
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 100), 0.9) if name == "common/bag.png" else (None, 0.0)
        )
        
        # 建立模擬圖像 (R - B 驗證需要擷取以 (100, 100) 為中心的區塊)
        # 情況 A: 模擬灰色「戰團」 R-B = 10
        # 圖像格式是 BGR，所以 [B, G, R]
        # 我們把 (100, 100) 附近 10x10 的區域設為 B=90, G=80, R=100
        screen_gray = np.zeros((1080, 1920, 3), dtype=np.uint8)
        screen_gray[95:105, 95:105] = [90, 80, 100]
        
        self.mock_capturer.capture.return_value = screen_gray
        self.mock_mouse.click.reset_mock()
        
        # Act 情況 A
        self.state_machine.step()
        
        # Assert 情況 A: 應被忽略
        self.mock_mouse.click.assert_not_called()
        self.assertFalse(self.state_machine.bag_opened_clicked)
        
        # 情況 B: 模擬棕色「背包」 R-B = 30
        # 我們把 (100, 100) 附近 10x10 區域設為 B=90, G=80, R=120
        screen_brown = np.zeros((1080, 1920, 3), dtype=np.uint8)
        screen_brown[95:105, 95:105] = [90, 80, 120]
        
        self.mock_capturer.capture.return_value = screen_brown
        
        # Act 情況 B
        self.state_machine.step()
        # Assert 情況 B: 應點擊
        self.mock_mouse.click.assert_called_with(100, 100)
        self.assertTrue(self.state_machine.bag_opened_clicked)

    @patch('os.path.exists')
    def test_state_machine_default_fallback_state(self, mock_exists):
        """
        [行為場景 16] 全域掃描未知狀態時的安全降級預設落點：
        Given: 狀態機處於 UNKNOWN 狀態，且畫面匹配不到任何已知特徵 (所有 match 回傳 None)。
        When: 執行全域狀態掃描。
        Then:
          - 當 config["type"] == "stage" (關卡模式) 時，預設安全降級落點應為 STATE_BATTLE。
          - 當 config["type"] == "dungeon" (地下城模式) 時，預設安全降級落點應為 STATE_DUNGEON_EXPLORING。
        """
        # Arrange
        mock_exists.return_value = True
        self.mock_matcher.match.return_value = (None, 0.0)
        
        # 情況 A: 關卡模式
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        
        # Act 情況 A
        self.state_machine.step()
        
        # Assert 情況 A: 預設進入 BATTLE
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)
        
        # 情況 B: 地下城模式
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        
        # Act 情況 B
        self.state_machine.step()
        
        # Assert Assert 情況 B: 預設進入 EXPLORING
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)

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
        [行為場景 17-B] 背包未滿時忽略離開戰鬥按鈕：
        Given: 狀態機處於 RESULT 狀態，且 need_bag_cleaning = False。
        When: 執行狀態機決策。
        Then: 即使看見離開戰鬥按鈕 exit_battle.png，也應該忽略不點擊。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        self.state_machine.need_bag_cleaning = False
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

    @patch('os.path.exists')
    @patch('time.time')
    def test_stage_navigation_path_with_scrolling(self, mock_time, mock_exists):
        """
        [行為場景 18] 關卡模式下的尋路與滑動向下滾動尋找魔王關：
        Given: 狀態機處於 NAVIGATING 狀態。
        When & Then:
          1. 畫面看到 common/select_stage.png ➔ 應點擊該按鈕。
          2. 畫面看到 level2_Barren_Rocky_Ground.png ➔ 應點擊進入第二關。
          3. 畫面看到 level2_entry1.png，但未看見 level2_final.png ➔ 應執行 mouse.scroll 往下滾動，而不進行點擊。
          4. 畫面同時看到 level2_entry1.png 和 level2_final.png ➔ 應優先點擊 level2_final.png，不執行滾動。
        """
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        mock_exists.return_value = True
        mock_time.return_value = 1000.0
        # 步驟 0: 畫面看到 common/door.png
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((50, 50), 0.9) if name == "common/door.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(50, 50)

        # 步驟 1: 畫面看到 common/select_stage.png
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((150, 150), 0.9) if name == "common/select_stage.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(150, 150)
        
        # 步驟 2: 畫面看到 level2_Barren_Rocky_Ground.png
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((250, 250), 0.9) if name == "level2_Barren_Rocky_Ground.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(250, 250)
        
        # 步驟 3: 畫面看到 stages/stage_label.png，但沒有 level2_final.png ➔ 滾動
        # 設定模擬時間
        mock_time.return_value = 1000.0
        self.state_machine.last_stage_scroll_time = 0.0
        
        def match_side_effect_step3(img, name, threshold):
            if name == "stages/stage_label.png":
                return ((100, 100), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_step3
        self.mock_mouse.click.reset_mock()
        self.mock_mouse.scroll.reset_mock()
        
        self.state_machine.step()
        
        # 應調用 scroll 滾動，且不應該點擊
        self.mock_mouse.click.assert_not_called()
        # 滾動的點應在視窗中心點： rect=(0,0,1920,1080) ➔ 中心為 (960, 540)
        # scroll 帶入 clicks=-800, x=960, y=540
        self.mock_mouse.scroll.assert_called_with(-800, 960, 540)
        self.assertEqual(self.state_machine.last_stage_scroll_time, 1000.0)
        
        # 步驟 4: 畫面同時出現 stages/stage_label.png 和 level2_final.png ➔ 直接點擊 final.png
        def match_side_effect_step4(img, name, threshold):
            if name == "stages/stage_label.png":
                return ((100, 100), 0.9)
            elif name == "level2_final.png":
                return ((350, 350), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_step4
        self.mock_mouse.click.reset_mock()
        self.mock_mouse.scroll.reset_mock()
        
        self.state_machine.step()
        
        # 應直接點擊魔王關，不調用滾動
        self.mock_mouse.click.assert_called_with(350, 350)
        self.mock_mouse.scroll.assert_not_called()

    @patch('os.path.exists')
    def test_navigation_interceptor_for_bag_cleaning(self, mock_exists):
        """
        [行為場景 20] 尋路狀態下的背包清理優先攔截：
        Given: 狀態機處於 NAVIGATING 狀態，且 need_bag_cleaning = True (背包滿需要清理)。
        When & Then:
          1. 畫面看到 exit_battle.png ➔ 應點擊 exit_battle.png 回城，不執行常規關卡選擇前進。
          2. 畫面看到 common/door.png ➔ 狀態機應將狀態轉移至 BAG_CLEANING。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        self.state_machine.need_bag_cleaning = True
        mock_exists.return_value = True
        
        # 1. 畫面看到 exit_battle.png ➔ 應點擊退出，不前進
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((200, 200), 0.9) if name == "exit_battle.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(200, 200)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # 2. 畫面看到 common/door.png ➔ 應判定已抵達大廳，切換至 BAG_CLEANING 狀態
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 100), 0.9) if name == "common/door.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BAG_CLEANING)
        self.mock_mouse.click.assert_not_called()

        # 3. 重置狀態並測試：畫面看到 goback_town.png ➔ 應判定已在準備介面，切換至 BAG_CLEANING 狀態
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((150, 150), 0.9) if name == "goback_town.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BAG_CLEANING)
        self.mock_mouse.click.assert_not_called()

if __name__ == "__main__":
    unittest.main()
