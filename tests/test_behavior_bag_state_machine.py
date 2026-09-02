import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BACKPACK_FULL_SETTINGS, GAME_CONFIGS
from states.state_machine import GameStateMachine

from tests._legacy_state_machine_test_support import StateMachineLogicTestCase


class TestBagStateMachine(StateMachineLogicTestCase):

    @patch('os.path.exists')
    def test_backpack_full_cleaning_flow(self, mock_exists):
        """
        測試背包已滿自動清理流程：戰鬥結算偵測到背包滿 ➔ 設定標記 ➔ 回大廳進入 BAG_CLEANING ➔ 執行清理步驟 ➔ 回大廳。
        """
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        
        import numpy as np
        self.mock_capturer.capture.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 1. 在結算畫面看到背包已滿 (backpack_full.png) ➔ 狀態轉移至 STATE_BACKPACK_FULL_SORTING 且設定 need_bag_cleaning = True
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 289), 0.9) if name == "backpack_full.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BACKPACK_FULL_SORTING)
        self.assertTrue(self.state_machine.need_bag_cleaning)
        
        # 為了測試後續的大廳攔截與 BAG_CLEANING 流程，我們手動將狀態設置為 LOBBY (模擬已完成分選退出後回到大廳的情況)
        self.state_machine.current_state = self.state_machine.STATE_LOBBY
        
        # 3. 畫面回到大廳，看到 stages/start.png。此時因為 need_bag_cleaning 標記，大廳處理器應轉移至 BAG_CLEANING 狀態
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((300, 300), 0.9) if name in ["stages/start.png", "common/select_stage.png"] else (None, 0.0)
        )
        self.state_machine.step()  # LobbyHandler 攔截轉移 LOBBY -> BAG_CLEANING
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BAG_CLEANING)
        
        # 4. BAG_CLEANING 狀態下順序點擊：
        # - 看到 common/bag_text.png ➔ 點擊打開背包
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((1550, 1037), 0.9) if name == "common/bag_text.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(1550, 992)
        
        # - 看到 common/Backpack_Disassembly.png ➔ 點擊進入大量分解
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name == "common/Backpack_Disassembly.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(500, 500)
        
        # - 看到 common/select_all.png ➔ 點擊全選
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
        
        # - 看到 common/Disassembly.png ➔ 點擊分解
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((700, 700), 0.9) if name == "common/Disassembly.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(700, 700)
        
        # - 看到確認彈窗 common/confirm.png ➔ 點擊確認
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((800, 800), 0.9) if name == "common/confirm.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(800, 800)
        
        # - 看到整理按鈕 common/tidy.png ➔ 點擊整理並設定標記 bag_tidied
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
        
        self.assertFalse(self.state_machine.need_bag_cleaning)
        self.assertFalse(self.state_machine.bag_tidied)
        self.assertTrue(self.state_machine.need_blood_altar)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BLOOD_ALTAR)

    @patch('os.path.exists')
    def test_backpack_cleaning_deselect_rare_items(self, mock_exists):
        """
        測試背包自動清理中的反選貴重物品邏輯：
        當全選被點擊後，掃描 6x3 網格，若發現貴重物品 (例如藍色裝備)，點擊它以取消選取，隨後才進行分解。
        """
        import numpy as np
        import cv2
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_BAG_CLEANING
        self.state_machine.bag_select_all_clicked = True
        self.state_machine.bag_deselected = False
        
        mock_exists.return_value = True
        
        # 建立假的 1080x1920 遊戲截圖
        screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        # 定位 全選按鈕 在 (676, 808)，算得 Slot A (Col 0, Row 0) 左上角 (549, 288)，中心點為 (616, 358)
        # 繪製一個藍色邊框 (HSV 藍色為 H=120) 的貴重物品 (crop: 549 to 683, 288 to 428)
        cv2.rectangle(screen, (549, 288), (683, 428), (255, 0, 0), 10)
        # 模擬打勾狀態：在貴重物品格子的頂端打勾區 (check_x=599, check_y=332) 畫上綠色實心方塊
        cv2.rectangle(screen, (599, 332), (633, 362), (0, 255, 0), -1)
        
        # 繪製一個綠色垃圾裝備
        cv2.rectangle(screen, (683, 288), (817, 428), (0, 255, 0), 10)
        
        # 設定可分解最高品質為綠色，使藍色貴重物品不屬於可分解列表，從而觸發反選保護條件
        self.state_machine.config["disassemble_colors"] = ["gray_or_empty", "green"]
        
        self.mock_capturer.capture.return_value = screen
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 點擊過全選後，步進會執行反選掃描。此時 matcher 需要匹配 select_all.png 作為定位點
        self.mock_matcher.match.side_effect = lambda img, name, threshold, **kwargs: (
            ((676, 808), 0.9) if name == "common/select_all.png" else (None, 0.0)
        )
        
        # 清除之前的點擊紀錄
        self.mock_mouse.click.reset_mock()
        
        self.state_machine.step()
        
        # 應偵測到貴重物品，並對該 slot 中心點 (616, 357) 進行反向點擊
        self.mock_mouse.click.assert_any_call(616, 357)
        self.assertFalse(self.state_machine.bag_deselected)
        
        # 模擬下一影格：清除貴重物品畫像，重新截圖掃描
        clean_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = clean_screen
        
        self.state_machine.step()
        self.assertTrue(self.state_machine.bag_deselected)

    @patch('os.path.exists')
    def test_dungeon_battle_backpack_full_cleaning_flow(self, mock_exists):
        """
        測試地下城模式下，在 BATTLE 戰鬥結束/結算時偵測到背包滿 ➔ 轉移至 BACKPACK_FULL_SORTING ➔ 模擬回到 EXPLORING ➔ 攔截進入 BAG_CLEANING。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        
        mock_exists.return_value = True
        
        # 1. 戰鬥中/結算時看到背包已滿 (backpack_full.png) ➔ 直接轉移至 BACKPACK_FULL_SORTING 並標記 need_bag_cleaning
        self.state_machine.battle_start_time = time.time() - 10.0
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 289), 0.9) if name == "backpack_full.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertTrue(self.state_machine.need_bag_cleaning)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BACKPACK_FULL_SORTING)
        
        # 2. 模擬分選處理完畢並回到 EXPLORING 狀態
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (None, 0.0)
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BAG_CLEANING)

    @patch('os.path.exists')
    def test_global_backpack_full_interception(self, mock_exists):
        """
        測試全域背包滿攔截器新邏輯：
        1. 看到 backpack_full.png ➔ 狀態切換至 STATE_BACKPACK_FULL_SORTING
        2. 在 STATE_BACKPACK_FULL_SORTING 狀態下，若左側無貴重物品 ➔ 點擊右上角關閉 (1540, 240) 且返回 STATE_UNKNOWN
        """
        self.state_machine.config = GAME_CONFIGS["dungeon"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_LOBBY
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        import numpy as np
        self.mock_capturer.capture.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)
        
        # 1. 全域偵測到 backpack_full.png
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 289), 0.9) if name == "backpack_full.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BACKPACK_FULL_SORTING)
        
        # 2. 執行 BackpackFullSortingHandler，由於為空畫面 (無貴重物品)，應直接點擊關閉並回到 STATE_UNKNOWN
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 289), 0.9) if name == "backpack_full.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(1558, 248)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)

    @patch('os.path.exists')
    def test_backpack_full_sorting_and_destroy_flow(self, mock_exists):
        """
        測試背包滿自適應分選與銷毀流：
        左側 Col 0, Row 0 有一個黃金/橘黃物品。
        右側 Col 0, Row 0 有一個綠色物品。
        1. 看到 backpack_full.png ➔ 狀態切換至 STATE_BACKPACK_FULL_SORTING
        2. 執行 BackpackFullSortingHandler，應定位到綠色物品並點擊 ➔ 點擊 destroy.png ➔ 點擊 confirm.png ➔ 點擊左側貴重物品 ➔ 完成本次分選。
        """
        import numpy as np
        self.state_machine.config = GAME_CONFIGS["dungeon"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        self.state_machine.config["backpack_full_destroyable_colors"] = ["gray_or_empty", "green"]
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 1. 偵測到 backpack_full.png 進入狀態
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 289), 0.9) if name == "backpack_full.png" else (None, 0.0)
        )
        self.state_machine.step()
        # 2. 準備實體 numpy 圖像，畫上指定邊框顏色以供分選
        import cv2
        test_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        # 左側 Col 0, Row 0: 黃金邊框 (BGR = [0, 200, 200])，邊框畫在相對6像素處以進入極細邊帶
        cv2.rectangle(test_img, (371+6, 394+6), (371+114, 394+114), (0, 200, 200), 10)
        
        # 右側 Col 0, Row 0: 綠色邊框 (BGR = [0, 200, 0])，邊框畫在相對6像素處以進入極細邊帶
        cv2.rectangle(test_img, (994+6, 394+6), (994+114, 394+114), (0, 200, 0), 10)
        # 我們也在中間給一些起伏，使 std 較大，避免被當成純黑空格
        test_img[394+35:394+75, 994+35:994+75] = [50, 50, 50]
        
        self.mock_capturer.capture.return_value = test_img
        
        # 模擬 match 結果
        def match_side_effect(img, name, threshold):
            if name == "backpack_full.png":
                return ((960, 289), 0.9)
            elif name == "common/destroy.png":
                return ((500, 500), 0.9) # 銷毀按鈕
            elif name == "common/confirm.png":
                return ((600, 600), 0.9) # 銷毀確認按鈕
            elif name == "common/collect.png":
                return ((700, 700), 0.9) # 領取按鈕
            elif "goods" in name or "Jewelry_workshop" in name:
                return ((400, 400), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect
        
        # 執行 step，觸發 BackpackFullSortingHandler
        self.state_machine.step()
        # 驗證點選了銷毀/確認按鈕，證明整個鏈式分選流程成功執行
        self.mock_mouse.click.assert_any_call(600, 600)

    @patch('os.path.exists')
    def test_backpack_full_sorting_custom_disassemble_threshold(self, mock_exists):
        """
        測試背包已滿溢出分選自訂分解閾值邏輯：
        當設定 disassemble_colors 包含藍色時，藍色裝備被判定為低稀有度（可銷毀），而紫色裝備被判定為高稀有度（需保留）。
        """
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        # 自訂只分解/銷毀 灰色、綠色、藍色 裝備
        destroy_settings = {
            "destroy_goods": {
                "gray": {"item": True},
                "green": {"item": True},
                "blue": {"item": True},
                "purple": {},
            }
        }
        # 設定保留紫色及以上（藍色不在保留名單中，因此可以被銷毀）
        self.state_machine.config["keep_colors"] = ["purple", "orange_yellow", "red"]
        self.state_machine.current_state = self.state_machine.STATE_BACKPACK_FULL_SORTING
        
        mock_exists.return_value = True
        
        # 模擬彈窗中心在 (630, 98) ➔ 左上角 win_x = 0, win_y = 7
        def match_side_effect(img, name, threshold=None):
            if name == "backpack_full.png":
                return ((630, 98), 0.9)
            elif name == "common/destroy.png":
                return ((700, 700), 0.9)
            elif name == "common/confirm.png":
                return ((800, 800), 0.9)
            elif name == "common/collect.png":
                return ((900, 900), 0.9)
            elif "goods" in name or "Jewelry_workshop" in name:
                return ((700, 250), 0.9)
            return (None, 0.0)


            
        self.mock_matcher.match.side_effect = match_side_effect
        self.mock_mouse.click.reset_mock()
        
        # 模擬截圖中，左側溢出區 Row 0, Col 0 為紫色貴重裝備 (std > 40)，而右側背包 Row 0, Col 0 為藍色裝備 (可銷毀)
        import cv2
        import numpy as np
        screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        
        # 左側溢出區 Row 0, Col 0: cx = 41, cy = 203, cell_w = 134, cell_h = 139.5
        # 模擬紫色 (std > 40)
        screen[203:342, 41:175] = [200, 0, 200]  # 紫色背景
        
        # 右側背包 Row 0, Col 0: cx = 664, cy = 203, cell_w = 134, cell_h = 139.5
        # 模擬藍色 (std > 18)
        screen[203:342, 664:798] = [200, 100, 0]  # 藍色背景
        
        self.mock_capturer.capture.return_value = screen
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 模擬 classify_slot_color 區分顏色
        # 溢出區為 purple，背包內為 blue
        def classify_slot_color_impl(crop):
            bgr_mean = np.mean(crop, axis=(0,1))
            if bgr_mean[2] > 150 and bgr_mean[0] > 150:
                return "purple"
            elif bgr_mean[0] > 150:
                return "blue"
            return "green"
            
        handler = self.state_machine.handlers[self.state_machine.STATE_BACKPACK_FULL_SORTING]
        with patch.object(handler, 'classify_slot_color', side_effect=classify_slot_color_impl), \
             patch.object(handler, 'is_item_authorized_by_goods_settings', return_value=True), \
             patch.dict(BACKPACK_FULL_SETTINGS, destroy_settings, clear=True):
            self.state_machine.step()

            
        # 驗證執行了以下步驟：
        # 1. 點擊右側藍色裝備進行銷毀 (中心在 630 + 34 + 67 = 731, 98 + 105 + 69 = 272)
        # 2. 點擊銷毀按鈕 (700, 700)
        # 3. 點擊確認銷毀 (800, 800)
        # 4. 點擊左側紫色貴重裝備彈出詳情 (中心在 630 - 589 + 67 = 108, 98 + 105 + 69 = 272)
        # 5. 點擊領取按鈕 (900, 900)
        self.mock_mouse.click.assert_any_call(731, 272)
        self.mock_mouse.click.assert_any_call(700, 700)
        self.mock_mouse.click.assert_any_call(800, 800)
        self.mock_mouse.click.assert_any_call(108, 272)
        self.mock_mouse.click.assert_any_call(900, 900)


if __name__ == "__main__":
    unittest.main()
