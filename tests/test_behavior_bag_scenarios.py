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


class TestBagScenarios(BehavioralScenarioTestCase):

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
        self.state_machine.config = GAME_CONFIGS["dungeon"]
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        mock_exists.return_value = True
        
        # Step 1: 全域攔截到 backpack_full.png，狀態跳轉並自動標記 need_bag_cleaning
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 289), 0.9) if name == "backpack_full.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BACKPACK_FULL_SORTING)
        self.assertTrue(self.state_machine.need_bag_cleaning)
        
        # Step 2: 建立模擬物品圖像數據 (黃金邊框 vs 綠色邊框)
        import cv2
        test_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        # 左側 (Col 0, Row 0): 黃金 (BGR = [0, 200, 200])，邊框畫在相對6像素處以進入極細邊帶
        cv2.rectangle(test_img, (371+6, 394+6), (371+114, 394+114), (0, 200, 200), 10)
        
        # 右側 (Col 0, Row 0): 綠色 (BGR = [0, 200, 0])，邊框畫在相對6像素處以進入極細邊帶
        cv2.rectangle(test_img, (994+6, 394+6), (994+114, 394+114), (0, 200, 0), 10)
        # 我們也在中間給一些起伏，使 std 較大，避免被當成純黑空格
        test_img[394+35:394+75, 994+35:994+75] = [50, 50, 50]
        self.mock_capturer.capture.return_value = test_img
        
        confirm_matched = [0]
        def match_side_effect_destroy_collect(img, name, threshold):
            if name == "backpack_full.png":
                return ((960, 289), 0.9)
            elif name == "common/destroy.png":
                return ((500, 500), 0.9)
            elif name == "common/confirm.png":
                if confirm_matched[0] == 0:
                    confirm_matched[0] += 1
                    return ((600, 600), 0.9)
                return (None, 0.0)
            elif name == "common/collect.png":
                return ((700, 700), 0.9)
            elif "goods" in name or "Jewelry_workshop" in name:
                return ((400, 400), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_destroy_collect
        
        # Act
        self.state_machine.step()
        
        # Assert: 整個銷毀收集鏈完成，點擊銷毀/確認按鈕 (600, 600)
        self.mock_mouse.click.assert_any_call(600, 600)

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
        self.state_machine.config = GAME_CONFIGS["dungeon"]
        self.state_machine.current_state = self.state_machine.STATE_BACKPACK_FULL_SORTING
        self.state_machine.need_bag_cleaning = True
        mock_exists.return_value = True
        
        # 模擬左側有黃金物品，右側全部為貴重藍色物品 (標準差大於 18，且顏色為 blue)，觸發滾動與安全退出
        test_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        # 左側黃金物件 (Col 0, Row 0)
        test_img[394+10:394+20, 371+10:371+98] = [0, 200, 200]
        test_img[394+88:394+98, 371+10:371+98] = [0, 200, 200]
        test_img[394+10:394+98, 371+10:371+20] = [0, 200, 200]
        test_img[394+10:394+98, 371+88:371+98] = [0, 200, 200]
        
        # 模擬右側 4x4 全是貴重藍色裝備 (不是空格，不能被銷毀)
        for r in range(4):
            for c in range(4):
                cx = 994 + c * 134
                cy = 394 + int(r * 139.5)
                test_img[cy+10:cy+20, cx+10:cx+98] = [200, 0, 0]
                test_img[cy+88:cy+98, cx+10:cx+98] = [200, 0, 0]
                test_img[cy+10:cy+98, cx+10:cx+20] = [200, 0, 0]
                test_img[cy+10:cy+98, cx+88:cx+98] = [200, 0, 0]
                test_img[cy+35:cy+75, cx+35:cx+75] = [50, 50, 50]
                
        self.mock_capturer.capture.return_value = test_img
        
        # 關閉二次確認彈窗以及定位彈窗位置
        def match_side_effect_scroll_exit(img, name, threshold):
            if name == "backpack_full.png":
                return ((960, 289), 0.9)
            elif name == "common/confirm.png":
                return ((600, 600), 0.9)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = match_side_effect_scroll_exit
        
        # Act
        self.state_machine.step()
        
        # Assert: 應點擊關閉按鈕，隨後點擊確認關閉，狀態回到 UNKNOWN，且 need_bag_cleaning 標記保持 True
        self.mock_mouse.click.assert_any_call(1558, 248) # 關閉按鈕座標
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
            ((300, 300), 0.9) if name in ["stages/start.png", "common/select_stage.png", "goback_town.png"] else (None, 0.0)
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
        
        quit_matched = [False]
        def mock_match_quit(img, name, **kw):
            if name == "common/quit.png" and not quit_matched[0]:
                quit_matched[0] = True
                return ((1000, 1000), 0.9)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = mock_match_quit

        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(1000, 1000)
        
        # 3. 驗證標記重置與轉移至血之祭壇獻祭
        self.assertFalse(self.state_machine.need_bag_cleaning)
        self.assertFalse(self.state_machine.bag_tidied)
        self.assertTrue(self.state_machine.need_blood_altar)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BLOOD_ALTAR)

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
        
        # 定位 全選按鈕 在 (676, 808) 算得 Slot A 中心 (616, 358), Slot B 中心 (750, 358)
        # 格子 A (Col 0, Row 0): 只在邊緣畫一點點金色
        screen[290:295, 549:559] = [0, 240, 240]
        
        # 格子 B (Col 1, Row 0): 中心 (750, 358)。繪製金色矩形 (683 to 817, 288 to 428)
        cv2.rectangle(screen, (683, 288), (817, 428), (0, 240, 240), 10)
        # 模擬打勾狀態：在貴重物品格子 B 的頂端打勾區 (check_x=733, check_y=332) 畫綠色實心方塊
        cv2.rectangle(screen, (733, 332), (767, 362), (0, 255, 0), -1)
        
        # 設定可分解最高品質為紫色，使橘黃色貴重物品不屬於可分解列表，從而觸發反選保護條件
        self.state_machine.config["disassemble_colors"] = ["gray_or_empty", "green", "blue", "purple"]
        
        self.mock_capturer.capture.return_value = screen
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 匹配定位點
        self.mock_matcher.match.side_effect = lambda img, name, threshold, **kwargs: (
            ((676, 808), 0.9) if name == "common/select_all.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        
        # Act
        self.state_machine.step()
        
        # Assert
        # 1. 必須點擊格子 B 進行反選
        self.mock_mouse.click.assert_any_call(750, 357)
        # 2. 絕對不能點擊格子 A
        for call in self.mock_mouse.click.call_args_list:
            self.assertNotEqual(call[0], (616, 357))
        # 3. 此時由於單步反選，bag_deselected 應為 False
        self.assertFalse(self.state_machine.bag_deselected)
        
        # 模擬下一影格：清除格子 B 的畫像，重新截圖
        clean_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = clean_screen
        
        self.state_machine.step()
        self.assertTrue(self.state_machine.bag_deselected)

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

    @patch('os.path.exists')
    def test_backpack_full_detection_threshold_override(self, mock_exists):
        """
        [行為場景 24] 背包滿彈窗高閾值比對防誤判：
        Given: 狀態機處於 NAVIGATING 狀態。
        When & Then:
          1. 畫面上出現相似度為 0.72 的 backpack_full.png (大廳誤判) ➔ 狀態機應拒絕轉移，維持 NAVIGATING。
          2. 畫面上出現相似度為 0.85 的 backpack_full.png (真實彈窗) ➔ 狀態機應正確轉移至 BACKPACK_FULL_SORTING。
        """
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        mock_exists.return_value = True

        # 模擬 match logic，如果比對分數小於 threshold，則不匹配 (回傳 None)
        def mock_match_impl(img, name, threshold):
            if name == "backpack_full.png":
                score = getattr(self, "_current_mock_score", 0.0)
                if score >= threshold:
                    return ((300, 300), score)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = mock_match_impl

        # 1. 0.72 相似度 (低於新閾值 0.80)
        self._current_mock_score = 0.72
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)

        # 2. 0.85 相似度 (高於新閾值 0.80)
        self._current_mock_score = 0.85
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BACKPACK_FULL_SORTING)

    @patch('os.path.exists')
    def test_bag_cleaning_triggers_town_subflow_pipeline(self, mock_exists):
        """
        測試完整的城鎮流水線 (Town Subflow Pipeline) 連動：
        1. 背包清理完成 ➔ 觸發 trigger_town_subflow_chain()，建佇列 ["blood_altar", "jewelry_workshop"]。
        2. 第一站轉移至 STATE_BLOOD_ALTAR 獻祭。
        3. 獻祭離場 ➔ pop_and_next_town_subflow() 接力進入 STATE_JEWELRY_WORKSHOP 出售。
        4. 出售離場 ➔ pop_and_next_town_subflow() 佇列已空 ➔ 恢復 STATE_NAVIGATING 續行掛機！
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["mix"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BAG_CLEANING
        
        bag_handler = self.state_machine.handlers[self.state_machine.STATE_BAG_CLEANING]
        if hasattr(bag_handler, 'reset_state'):
            bag_handler.reset_state()
        self.state_machine.bag_tidied = True

        def mock_match_quit(img, name, **kw):
            if name in ["common/door.png", "town_building/exitfromhouse_and_to_town.png"]:
                return ((74, 744), 0.90)
            elif name == "common/quit.png":
                return ((100, 100), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match_quit
        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = self.mock_capturer.get_window_rect()

        # Step 1: 關閉背包 ➔ 觸發流水線
        bag_handler.handle(fake_img, rect)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BLOOD_ALTAR)
        self.assertTrue(self.state_machine.need_blood_altar)
        self.assertEqual(self.state_machine.town_subflow_queue, ["jewelry_workshop"])

        # Step 2: 血之祭壇離場 ➔ 自動跳轉至珠寶加工廠
        altar_handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        altar_handler.reset_state()
        altar_handler.step_phase = "ALL_DONE_EXITING"
        altar_handler.handle(fake_img, rect)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_JEWELRY_WORKSHOP)
        self.assertTrue(self.state_machine.need_jewelry_workshop)
        self.assertEqual(self.state_machine.town_subflow_queue, [])

        # Step 3: 珠寶加工廠離場 ➔ 佇列已空 ➔ 自動恢復 STATE_NAVIGATING
        jewelry_handler = self.state_machine.handlers[self.state_machine.STATE_JEWELRY_WORKSHOP]
        jewelry_handler.reset_state()
        jewelry_handler.step_phase = "ALL_DONE_EXITING"
        jewelry_handler.handle(fake_img, rect)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        self.assertFalse(self.state_machine.need_blood_altar)
        self.assertFalse(self.state_machine.need_jewelry_workshop)


if __name__ == "__main__":
    unittest.main()
