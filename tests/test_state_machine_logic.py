import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import time

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.state_machine import GameStateMachine
from config import GAME_CONFIGS

class TestStateMachineLogic(unittest.TestCase):
    def setUp(self):
        # 建立 Mock 物件
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        
        # 解決 Mock match 被傳入 check_brightness 或 brightness_threshold 參數時的不相容問題，自動過濾 kwargs
        orig_call = self.mock_matcher.match._mock_call
        def patched_mock_call(*args, **kwargs):
            kwargs.pop('check_brightness', None)
            kwargs.pop('brightness_threshold', None)
            return orig_call(*args, **kwargs)
        self.mock_matcher.match._mock_call = patched_mock_call
        
        # 模擬視窗大小
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "right": 800, "bottom": 600}
        self.mock_capturer.capture.return_value = MagicMock() # 傳回假的圖片物件
        
        # 實例化狀態機
        self.state_machine = GameStateMachine(
            capturer=self.mock_capturer,
            matcher=self.mock_matcher,
            mouse=self.mock_mouse
        )
        self.state_machine.need_diamond_collection = False
        self.state_machine.last_diamond_collection_time = time.time()

    @patch('os.path.exists')
    def test_stage_mode_bread_collection_flow(self, mock_exists):
        """
        測試普通關卡模式：啟動 -> 領體力流程 -> 大廳 -> 戰鬥。
        """
        # 設定為關卡配置，啟用領體力
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.enable_bread = True
        self.state_machine.need_bread_collection = True
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        
        # 模擬所有需要的範本檔案都存在
        mock_exists.return_value = True
        
        # 1. 初始狀態為 UNKNOWN。全域掃描看到 door.png ➔ 應轉移至 NAVIGATING 領體力
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 100), 0.9) if name == "common/door.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # 2. NAVIGATING 狀態下：
        # - 看到 door.png ➔ 點擊
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 100), 0.9) if name == "common/door.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(100, 100)
        self.assertTrue(self.state_machine.need_bread_collection)
        
        # - 看到 bread.png ➔ 點擊打開體力視窗
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((200, 200), 0.9) if name == "common/bread.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(200, 200)
        
        # - 看到 common/collect.png ➔ 點擊領取
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((300, 300), 0.9) if name == "common/collect.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(300, 300)

        # - 看到 common/confirm.png ➔ 點擊確認
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((350, 350), 0.9) if name == "common/confirm.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(350, 350)
        
        # - 看到 quit_bread.png ➔ 點擊退出，結束領取體力流程
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((400, 400), 0.9) if name == "common/quit.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(400, 400)
        self.assertFalse(self.state_machine.need_bread_collection)
        
        # 3. 領完體力後，NAVIGATING 尋路結束，看到大廳的 stages/start.png ➔ 應轉移至 LOBBY
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name == "stages/start.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOBBY)
        
        # 4. LOBBY 狀態下：看到大廳 stages/start.png ➔ 點擊並轉移至 BATTLE
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name == "stages/start.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(500, 500)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)

    @patch('os.path.exists')
    @patch('states.handlers.explore.time.sleep')
    def test_dungeon_slime_explore_and_battle_flow(self, mock_sleep, mock_exists):
        """
        測試史萊姆地下城模式：探索事件 -> 遇怪 -> 戰鬥 -> 結算 -> 繼續探索。
        對齊全新的開啟寶箱與領取祝福子流程。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        
        mock_exists.return_value = True
        self.mock_capturer.capture.return_value = MagicMock()
        
        # 模擬 matcher.match，配合探索主循環與子流程內部的多階段比對
        match_call_count = 0
        def side_effect(img, name, threshold, brightness_threshold=0.0):
            nonlocal match_call_count
            # --- 第一階段：點擊 Treasure.png 並進入開啟寶箱子流程 ---
            if name == "dungeons/Treasure.png" and match_call_count == 0:
                match_call_count += 1
                return (600, 600), 0.90
            elif name == "dungeons/Get_tresure.png" and match_call_count == 1:
                match_call_count += 1
                return (610, 610), 0.90
            elif name == "dungeons/Get_tresure_comfirm.png" and match_call_count == 2:
                match_call_count += 1
                return (620, 620), 0.90
            elif name == "common/quit.png" and match_call_count == 3:
                match_call_count += 1
                return (630, 630), 0.90
                
            # --- 第二階段：探索戰鬥房入口 ---
            elif name == "dungeons/dungeon_fight.png" and match_call_count == 4:
                match_call_count += 1
                return (700, 700), 0.90
                
            # --- 第三階段：點擊 dungeon_bless.png 並進入選擇祝福子流程 ---
            elif name == "dungeons/dungeon_bless.png" and match_call_count == 5:
                match_call_count += 1
                return (750, 750), 0.90
            elif name == "dungeons/choice_bless.png" and match_call_count == 6:
                match_call_count += 1
                return (800, 200), 0.90
            elif name == "common/ok.png" and match_call_count == 7:
                match_call_count += 1
                return (810, 210), 0.90
            elif name == "common/quit.png" and match_call_count == 8:
                match_call_count += 1
                return (820, 220), 0.90
                
            # --- 第四階段：發現戰鬥開始 auto.png 並切換為 BATTLE 狀態 ---
            elif name == "common/auto.png" and match_call_count == 9:
                match_call_count += 1
                return (800, 100), 0.90
            elif name == "common/auto.png" and match_call_count == 10:
                match_call_count += 1
                return (800, 100), 0.90
                
            return None, 0.0
            
        self.mock_matcher.match.side_effect = side_effect
        self.mock_mouse.click.reset_mock()
        
        # 1. 執行第一步：應偵測到 Treasure.png，點擊並進入寶箱子流程，執行獲取、確認、退出點擊
        self.state_machine.step()
        self.mock_mouse.click.assert_any_call(600, 600)
        self.mock_mouse.click.assert_any_call(610, 610)
        self.mock_mouse.click.assert_any_call(620, 620)
        self.mock_mouse.click.assert_any_call(630, 630)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)
        
        # 2. 執行第二步：應偵測到 dungeons/dungeon_fight.png 並點擊
        self.state_machine.step()
        self.mock_mouse.click.assert_any_call(700, 700)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)
        
        # 3. 執行第三步：應偵測到 dungeons/dungeon_bless.png 并進入選擇祝福子流程，執行祝福、OK、退出點擊
        self.state_machine.step()
        self.mock_mouse.click.assert_any_call(750, 750)
        self.mock_mouse.click.assert_any_call(800, 200)
        self.mock_mouse.click.assert_any_call(810, 210)
        self.mock_mouse.click.assert_any_call(820, 220)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)
        
        # 4. 執行第四步：看到戰鬥開始 auto.png ➔ 轉移至 BATTLE
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)
        # 模擬戰鬥已經開始了 10 秒，繞過剛進戰鬥前 8 秒的結算判定安全冷卻期
        self.state_machine.battle_start_time = time.time() - 10.0
        
        # 5. BATTLE 狀態下：看到 common/auto.png ➔ 點擊啟用
        self.state_machine.step()
        self.mock_mouse.click.assert_any_call(800, 100)
        
        # 6. 戰鬥結束：看到結算 common/continue.png ➔ 點擊並轉回 EXPLORING
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((900, 500), 0.9) if name == "common/continue.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(900, 500)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)

    @patch('os.path.exists')
    @patch('states.handlers.explore.time.sleep')
    def test_dungeon_skill_event_and_descend_flow(self, mock_sleep, mock_exists):
        """
        測試地下城模式技能事件與下樓流程：
        點擊技能事件 ➔ 點擊選擇 ➔ 點擊確認/OK ➔ 點擊退出 ➔ 點擊下樓 ➔ 點擊下樓確認。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        
        mock_exists.return_value = True
        self.mock_capturer.capture.return_value = MagicMock()
        
        match_call_count = 0
        def side_effect(img, name, threshold, brightness_threshold=0.0):
            nonlocal match_call_count
            # --- 第一階段：點擊 skill_event.png 並進入技能選擇子流程 ---
            if name == "dungeons/skill_event.png" and match_call_count == 0:
                match_call_count += 1
                return (150, 150), 0.90
            elif name == "dungeons/choose.png" and match_call_count == 1:
                match_call_count += 1
                return (250, 250), 0.90
            elif name == "common/confirm.png" and match_call_count == 2:
                match_call_count += 1
                return (350, 350), 0.90
            elif name == "common/quit.png" and match_call_count == 3:
                match_call_count += 1
                return (450, 450), 0.90
                
            # --- 第二階段：點擊下樓 ---
            elif name == "dungeons/gungeon_godown.png" and match_call_count == 4:
                match_call_count += 1
                return (550, 550), 0.90
                
            # --- 第三階段：下樓確認 ---
            elif name == "dungeons/gungeon_godown_confirm.png" and match_call_count == 5:
                match_call_count += 1
                return (650, 650), 0.90
                
            return None, 0.0
            
        self.mock_matcher.match.side_effect = side_effect
        self.mock_mouse.click.reset_mock()
        
        # 1. 執行第一步：應偵測到 skill_event.png，點擊並進入技能選擇子流程，執行選擇、確認、退出點擊
        self.state_machine.step()
        self.mock_mouse.click.assert_any_call(150, 150)
        self.mock_mouse.click.assert_any_call(250, 250)
        self.mock_mouse.click.assert_any_call(350, 350)
        self.mock_mouse.click.assert_any_call(450, 450)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)
        
        # 2. 執行第二步：點擊下樓
        self.state_machine.step()
        self.mock_mouse.click.assert_any_call(550, 550)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)
        
        # 3. 執行第三步：下樓確認
        self.state_machine.step()
        self.mock_mouse.click.assert_any_call(650, 650)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)
        
        # 4. 手動將下樓點擊時間推前 7 秒，模擬冷卻時間屆滿後，重設本層記憶
        self.assertTrue(self.state_machine.skill_selected_this_floor)
        self.state_machine.last_godown_click_time -= 7.0
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (None, 0.0)
        self.state_machine.step()
        self.assertFalse(self.state_machine.skill_selected_this_floor)

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
            ((960, 228), 0.9) if name == "backpack_full.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BACKPACK_FULL_SORTING)
        self.assertTrue(self.state_machine.need_bag_cleaning)
        
        # 為了測試後續的大廳攔截與 BAG_CLEANING 流程，我們手動將狀態設置為 LOBBY (模擬已完成分選退出後回到大廳的情況)
        self.state_machine.current_state = self.state_machine.STATE_LOBBY
        
        # 3. 畫面回到大廳，看到 stages/start.png。此時因為 need_bag_cleaning 標記，大廳處理器應轉移至 BAG_CLEANING 狀態
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((300, 300), 0.9) if name == "stages/start.png" else (None, 0.0)
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
        
        # - 當 bag_tidied 為 True 時，偵測 quit 按鈕 (dungeons/quit.png) ➔ 點擊退出，結束清理並恢復 LOBBY 狀態
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((1000, 1000), 0.9) if name == "common/quit.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(1000, 1000)
        
        self.assertFalse(self.state_machine.need_bag_cleaning)
        self.assertFalse(self.state_machine.bag_tidied)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOBBY)

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
        # 定位 全選按鈕 在 (121, 628)
        # 繪製一個藍色邊框 (HSV 藍色為 H=120) 的貴重物品，使顏色完美落在 2-12 像素的極細邊緣帶中
        cv2.rectangle(screen, (9, 131), (117, 239), (255, 0, 0), 10)
        # 模擬打勾狀態：在貴重物品格子內畫上一個綠色實心方塊，代表「綠色打勾記號」
        cv2.rectangle(screen, (46, 168), (80, 202), (0, 255, 0), -1)
        
        # 繪製一個綠色垃圾裝備，使顏色完美落在 2-12 像素的極細邊緣帶中
        cv2.rectangle(screen, (144, 131), (252, 239), (0, 255, 0), 10)
        
        # 設定可分解最高品質為綠色，使藍色貴重物品不屬於可分解列表，從而觸發反選保護條件
        self.state_machine.config["disassemble_colors"] = ["gray_or_empty", "green"]
        
        self.mock_capturer.capture.return_value = screen
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 點擊過全選後，步進會執行反選掃描。此時 matcher 需要匹配 select_all.png 作為定位點
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((121, 628), 0.9) if name == "common/select_all.png" else (None, 0.0)
        )
        
        # 清除之前的點擊紀錄
        self.mock_mouse.click.reset_mock()
        
        self.state_machine.step()
        
        # 應偵測到貴重物品，並對該 slot 中心點 (63, 185) 進行反向點擊
        self.mock_mouse.click.assert_any_call(63, 185)
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
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        
        mock_exists.return_value = True
        
        # 1. 戰鬥中/結算時看到背包已滿 (backpack_full.png) ➔ 直接轉移至 BACKPACK_FULL_SORTING 並標記 need_bag_cleaning
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 228), 0.9) if name == "backpack_full.png" else (None, 0.0)
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
    def test_global_task_complete_and_confirm_interception(self, mock_exists):
        """
        測試全域彈窗攔截器：
        1. 看到 task_complete.png ➔ 點擊「領取獎勵」(相對 Y+281 的座標)
        2. 在大廳狀態下看到確認/OK 彈窗 ➔ 自動點選確認關閉
        """
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_LOBBY
        
        mock_exists.return_value = True
        
        # 模擬擷取視窗大小 (1920x1080)
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 1. 偵測到 task_complete.png 位於中心 (960, 540)
        # 預計點擊 Claim Rewards 按鈕中心: X=960, Y=540+281 = 821
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 540), 0.9) if name == "task_complete.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(960, 821)
        
        # 2. 點擊完領取獎勵後，畫面彈出 confirm.png
        # 此時在大廳狀態，通用確認攔截器應點選確認關閉
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 600), 0.9) if name == "common/confirm.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(960, 600)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOBBY)

    @patch('os.path.exists')
    def test_global_backpack_full_interception(self, mock_exists):
        """
        測試全域背包滿攔截器新邏輯：
        1. 看到 backpack_full.png ➔ 狀態切換至 STATE_BACKPACK_FULL_SORTING
        2. 在 STATE_BACKPACK_FULL_SORTING 狀態下，若左側無貴重物品 ➔ 點擊右上角關閉 (1540, 240) 且返回 STATE_UNKNOWN
        """
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_LOBBY
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        import numpy as np
        self.mock_capturer.capture.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)
        
        # 1. 全域偵測到 backpack_full.png
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 228), 0.9) if name == "backpack_full.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BACKPACK_FULL_SORTING)
        
        # 2. 執行 BackpackFullSortingHandler，由於為空畫面 (無貴重物品)，應直接點擊關閉並回到 STATE_UNKNOWN
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 228), 0.9) if name == "backpack_full.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(1558, 241)
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
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 1. 偵測到 backpack_full.png 進入狀態
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 228), 0.9) if name == "backpack_full.png" else (None, 0.0)
        )
        self.state_machine.step()
        # 2. 準備實體 numpy 圖像，畫上指定邊框顏色以供分選
        import cv2
        test_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        # 左側 Col 0, Row 0: 黃金邊框 (BGR = [0, 200, 200])，邊框畫在相對6像素處以進入極細邊帶
        cv2.rectangle(test_img, (407+6, 381+6), (407+114, 381+114), (0, 200, 200), 10)
        
        # 右側 Col 0, Row 0: 綠色邊框 (BGR = [0, 200, 0])，邊框畫在相對6像素處以進入極細邊帶
        cv2.rectangle(test_img, (1007+6, 381+6), (1007+114, 381+114), (0, 200, 0), 10)
        # 我們也在中間給一些起伏，使 std 較大，避免被當成純黑空格
        test_img[381+35:381+75, 1007+35:1007+75] = [50, 50, 50]
        
        self.mock_capturer.capture.return_value = test_img
        
        # 模擬 match 結果
        def match_side_effect(img, name, threshold):
            if name == "backpack_full.png":
                return ((960, 228), 0.9)
            elif name == "common/destroy.png":
                return ((500, 500), 0.9) # 銷毀按鈕
            elif name == "common/confirm.png":
                return ((600, 600), 0.9) # 銷毀確認按鈕
            elif name == "common/collect.png":
                return ((700, 700), 0.9) # 領取按鈕
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect
        
        # 執行 step，觸發 BackpackFullSortingHandler
        self.state_machine.step()
        # 驗證最後一個被點選的是領取按鈕，證明整個鏈式分選流程成功執行
        self.mock_mouse.click.assert_called_with(700, 700)

    @patch('os.path.exists')
    def test_global_diamond_collection_flow(self, mock_exists):
        """
        測試自動領取鑽石流程以及當體力與鑽石計時器同時到期時的優先順序 (先領鑽石，再領體力)：
        1. 看到 goback_town.png ➔ 狀態轉移至 NAVIGATING
        2. 在 NAVIGATING 狀態下看到 goback_town.png ➔ 點點返回大廳
        3. 看到 diamond.png ➔ 點點打開鑽石領取畫面
        4. 看到 free.png ➔ 點點領取免費鑽石
        5. 看到 confirm.png ➔ 點點確認並標記 diamond_collected_this_run
        6. 看到 quit_bread.png ➔ 關閉鑽石畫面，結束鑽石流程，並開始體力流程
        7. 看到 common/bread.png ➔ 開始點點進入領體力
        """
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = True
        self.state_machine.need_bread_collection = True
        self.state_machine.need_diamond_collection = True
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 1. 偵測 goback_town.png ➔ 轉移狀態 (不點擊)
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 800), 0.9) if name == "goback_town.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # 2. 進入 NAVIGATING 後 ➔ 點擊 goback_town.png
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 800), 0.9) if name == "goback_town.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(100, 800)
        
        # 3. 看到 diamond.png ➔ 點擊
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((200, 200), 0.9) if name == "diamond.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(200, 200)
        
        # 4. 看到 free.png ➔ 點擊 (此時需模擬 common/quit.png 也存在，代表處於視窗內)
        def match_side_effect_4(img, name, threshold):
            if name == "free.png":
                return ((300, 300), 0.9)
            if name == "common/quit.png":
                return ((500, 500), 0.9)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = match_side_effect_4
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(300, 300)
        
        # 5. 看到 confirm.png ➔ 點擊確認，並標記 diamond_collected_this_run
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((400, 400), 0.9) if name == "common/confirm.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(400, 400)
        self.assertTrue(self.state_machine.diamond_collected_this_run)
        
        # 6. 看到退出按鈕 ➔ 關閉鑽石，重置 need_diamond_collection 為 False，開始體力流程
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name == "common/quit.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(500, 500)
        self.assertFalse(self.state_machine.need_diamond_collection)
        self.assertFalse(self.state_machine.diamond_collected_this_run)
        
        # 7. 下一幀應自動啟動體力領取流程 (尋找 bread.png 並點擊)
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((600, 600), 0.9) if name == "common/bread.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(600, 600)
        self.assertTrue(self.state_machine.need_bread_collection)

    @patch('os.path.exists')
    def test_diamond_collection_cooldown_flow(self, mock_exists):
        """
        測試領鑽石冷卻退出流程：
        1. need_diamond_collection = True，已在大廳打開鑽石視窗。
        2. 畫面上沒有免費鑽石 (free.png 傳回 None)，但有退出按鈕 (common/quit.png) 且大廳入口 (diamond.png) 不在畫面上。
        3. 預期：應自動點擊退出按鈕，並關閉領鑽石流程 (need_diamond_collection 設為 False)。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = False
        self.state_machine.need_diamond_collection = True
        self.state_machine.diamond_collected_this_run = False
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 模擬比對：
        # - 尋找 free.png ➔ None (冷卻中)
        # - 尋找 common/quit.png ➔ (500, 500)
        # - 尋找 diamond.png ➔ None (不在大廳)
        def match_side_effect(img, name, threshold):
            if name == "common/quit.png":
                return ((500, 500), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect
        self.state_machine.step()
        
        # 斷言：應點擊退出按鈕，且 need_diamond_collection 重設為 False
        self.mock_mouse.click.assert_called_with(500, 500)
        self.assertFalse(self.state_machine.need_diamond_collection)

    @patch('os.path.exists')
    def test_defeat_restart_flow(self, mock_exists):
        """
        測試戰鬥中戰敗並重新開始的完整流轉邏輯：
        1. 處於 BATTLE 狀態下，偵測到戰敗大圖 defeat.png ➔ 轉移至 RESULT
        2. 進入 RESULT 狀態後，再次匹配 defeat.png。此時：
           - 模擬 defeat_retry.png 匹配失敗 (None)
           - 模擬 stages/retry.png 匹配失敗 (None)
           - 預期：應使用防禦性相對座標 (defeat_center_x - 140, defeat_center_y + 250) 執行點擊
           - 點擊後，狀態回到 BATTLE，run_count 累加
        3. 另一個情況：在 RESULT 狀態下且戰敗：
           - 模擬 defeat_retry.png 匹配成功 (pos)
           - 預期：直接點擊該按鈕座標，狀態回到 BATTLE
        """
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        self.state_machine.run_count = 0
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 100, "top": 100, "width": 1920, "height": 1080}
        
        # 1. 在 BATTLE 狀態，看見 defeat.png ➔ 轉移至 RESULT
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name == "defeat.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_RESULT)
        
        # 2. 在 RESULT 狀態下，匹配失敗按鈕 ➔ 觸發相對座標備份點擊 (X=100+500-140=460, Y=100+500+250=850)
        # 模擬 match：只有 defeat.png 匹配成功，其餘 None
        def match_side_effect_fallback(img, name, threshold):
            if name == "defeat.png":
                return ((500, 500), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_fallback
        self.state_machine.step()
        
        # 斷言：點擊相對座標 (460, 850)，且轉移回 BATTLE，且次數為 1
        self.mock_mouse.click.assert_called_with(460, 850)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)
        self.assertEqual(self.state_machine.run_count, 1)
        
        # 3. 再來一次，測試能成功匹配 defeat_retry.png
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        
        def match_side_effect_success(img, name, threshold):
            if name == "defeat.png":
                return ((500, 500), 0.9)
            if name == "defeat_retry.png":
                return ((400, 800), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_success
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        
        # 斷言：應點擊匹配到的按鈕座標 (100+400=500, 100+800=900)
        self.mock_mouse.click.assert_called_with(500, 900)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)
        self.assertEqual(self.state_machine.run_count, 2)

    @patch('os.path.exists')
    def test_stuck_protection_flow(self, mock_exists):
        """
        測試防卡死監控流程：
        1. 在 NAVIGATING 狀態下，若連續 15 幀狀態未轉移，則判定為卡死。
        2. 分支 A: 找到 confirm.png ➔ 點擊該確認按鈕以清除阻礙，保持原本狀態。
        3. 分支 B: 找不到任何確認按鈕 ➔ 強制轉移至 STATE_UNKNOWN 重新定位。
        """
        mock_exists.return_value = True
        
        # 準備
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        self.state_machine.consecutive_stuck_count = 0
        self.mock_capturer.capture.return_value = MagicMock()
        
        # 模擬 match，前 14 次不觸發卡死
        self.mock_matcher.match.return_value = (None, 0.0)
        
        for _ in range(14):
            self.state_machine.step()
            
        self.assertEqual(self.state_machine.consecutive_stuck_count, 14)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # 測試分支 A: 匹配成功 confirm.png
        def match_confirm(img, name, threshold):
            if name == "common/confirm.png":
                return ((800, 400), 0.9)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = match_confirm
        self.mock_mouse.click.reset_mock()
        
        # 執行第 15 次 step
        self.state_machine.step()
        
        # 斷言：應該點擊通用確認按鈕 (0+800=800, 0+400=400)，且重置 stuck 次數，且狀態依然保持 NAVIGATING
        self.mock_mouse.click.assert_called_with(800, 400)
        self.assertEqual(self.state_machine.consecutive_stuck_count, 0)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # 測試分支 B: 找不到任何確認按鈕
        self.state_machine.consecutive_stuck_count = 14  # 手動設回 14 次
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (None, 0.0)
        self.mock_mouse.click.reset_mock()
        
        # 執行第 15 次 step
        self.state_machine.step()
        
        # 斷言：無點擊，狀態被強制重設為 UNKNOWN，且 stuck 次數重置為 0
        self.mock_mouse.click.assert_not_called()
        self.assertEqual(self.state_machine.consecutive_stuck_count, 0)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)

    @patch('os.path.exists')
    def test_dungeon_slime_global_stamina_collection_trigger(self, mock_exists):
        """
        測試史萊姆地下城模式：全域定時觸發體力領取邏輯與尋路導航中的退回城鎮。
        """
        # 1. 設置為 dungeon_slime 配置，啟用領體力
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = True
        self.state_machine.need_bread_collection = False
        # 將上次領取時間設為 1900 秒之前，大於 1800 秒的 CD
        self.state_machine.last_bread_collection_time = time.time() - 1900.0
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        
        mock_exists.return_value = True
        
        # 模擬 match，沒有大門 (door.png) 的匹配，模擬在地下城探索
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (None, 0.0)
        
        # 執行 step，此時應觸發定時器將 need_bread_collection 設為 True
        self.state_machine.step()
        
        self.assertTrue(self.state_machine.need_bread_collection)
        
        # 2. 地下城結束，點擊 dungeons_complete.png ➔ 應轉移至 STATE_NAVIGATING
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((200, 200), 0.9) if name == "dungeons/dungeons_complete.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # 3. 在 NAVIGATING 狀態下：
        # - 因為 need_bread_collection 為 True，看到 goback_town.png ➔ 應點擊退回城鎮
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((300, 300), 0.9) if name == "goback_town.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(300, 300)

    @patch('os.path.exists')
    def test_greedy_dungeon_on_screen_cooldown_detection(self, mock_exists):
        """
        測試自動貪婪地下城模式下，藉由畫面匹配防禦性跳過正在冷卻的地下城卡片。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"].copy()
        self.state_machine.config["greedy_dungeon"] = True
        self.state_machine.enable_bread = False
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        
        import numpy as np
        self.mock_capturer.capture.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        mock_exists.return_value = True
        
        # 模擬 match_side_effect 用於大廳/尋路 (如果有比對的話)
        self.mock_matcher.match.return_value = (None, 0.0)
        self.mock_mouse.click.reset_mock()
        
        # 用於模擬 cv2.imread
        dummy_img = np.zeros((10, 10, 3), dtype=np.uint8)
        
        # 記錄各種類型 matchTemplate / minMaxLoc 的呼叫次數
        counts = {"card": 0, "cooldown": 0, "skull": 0}
        
        def mock_minMaxLoc_impl(res):
            if res.shape[1] > 1000:
                counts["card"] += 1
                if counts["card"] == 1:
                    # any_entry_found: 匹配 Slime 成功
                    return (0.0, 0.95, (0, 0), (200, 0))
                elif counts["card"] == 2:
                    # i = 3 (Ruins): 匹配失敗
                    return (0.0, 0.0, (0, 0), (0, 0))
                elif counts["card"] == 3:
                    # i = 2 (Forest): 匹配成功，起點為 727
                    return (0.0, 0.95, (0, 0), (727, 0))
                elif counts["card"] == 4:
                    # i = 1 (Ghost): 匹配失敗
                    return (0.0, 0.0, (0, 0), (0, 0))
                elif counts["card"] == 5:
                    # i = 0 (Slime): 匹配成功，起點為 200
                    return (0.0, 0.95, (0, 0), (200, 0))
                return (0.0, 0.0, (0, 0), (0, 0))
            elif 200 < res.shape[1] <= 1000:
                counts["cooldown"] += 1
                if counts["cooldown"] == 1:
                    # Forest cooldown_left 匹配成功 (高相似度)
                    return (0.0, 0.90, (0, 0), (10, 10))
                # 其他 (Slime 的 cooldown_left, cooldown_right) 匹配失敗
                return (0.0, 0.0, (0, 0), (0, 0))
            else:
                counts["skull"] += 1
                # Slime skull 匹配成功
                return (0.0, 0.88, (0, 0), (0, 0))
                
        with patch('cv2.imread', return_value=dummy_img), \
             patch('cv2.minMaxLoc', side_effect=mock_minMaxLoc_impl):
            # 執行 step()，由於 Forest 被偵測到冷卻，應跳過，最後選擇點擊 Slime (X=0+200+346//2=373, Y=0+341//2=170)
            self.state_machine.step()
        
        # 驗證：點擊目標應該是 Slime 入口的中心，而不是 Forest
        # Slime 的 center x = 200 + 173 = 373, center y = 170 (以 scale=1.0 計算)
        self.mock_mouse.click.assert_called_with(373, 170)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        # 確保 Forest 索引 (2) 的冷卻時間被設為未來時間
        self.assertGreater(self.state_machine.dungeon_cooldowns[2], time.time())

    @patch('os.path.exists')
    def test_stage_navigation_horizontal_drag_flow(self, mock_exists):
        """
        測試普通關卡選關左右滑動與防重入邏輯：
        1. 當在關卡選擇介面時，不應重複點選 common/select_stage.png。
        2. 當目標關卡 stages/level4_desert_ruins.png 尚未出現在畫面上時，執行拖曳動作。
        3. 當目標關卡出現時，精準點選。
        """
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        # 目標為關卡 4 (沙漠廢墟)
        self.state_machine.config["name"] = "普通關卡 - 沙漠廢墟"
        self.state_machine.config["navigation_path"] = [
            "common/door.png",
            "exit_battle.png",
            "common/select_stage.png",
            "stages/level4_desert_ruins.png",
            "stages/stage_label.png",
            "stages/level4_final.png"
        ]
        self.state_machine.enable_bread = False
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        
        mock_exists.return_value = True
        
        # 模擬視窗尺寸為 1000x800
        self.mock_capturer.get_window_rect.return_value = {"left": 100, "top": 100, "width": 1000, "height": 800}
        
        # 場景 1：在關卡選擇介面，看見 Level 1 (Sky Plains) 說明清單開啟，但沒看見目標 Level 4
        # 且畫面上同時能匹配到 common/select_stage.png
        # 預期：不點擊 select_stage.png，而是執行 mouse.drag 向左拖曳
        def match_side_effect_drag(img, name, threshold):
            if name == "common/select_stage_after.png":
                return ((300, 300), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_drag
        self.mock_mouse.click.reset_mock()
        self.mock_mouse.drag.reset_mock()
        
        # 模擬目標關卡已經缺失 2.0 秒，使等待緩衝期已過
        self.state_machine.__setattr__("missing_time_stages/level4_desert_ruins.png", time.time() - 2.0)
        
        self.state_machine.step()
        
        # 驗證沒有點擊任何按鈕 (特別是 select_stage.png)
        self.mock_mouse.click.assert_not_called()
        # 驗證執行了 drag 拖曳，起點大約在 100 + 1000 * 0.58 = 680，終點大約在 100 + 1000 * 0.42 = 520
        # 高度為 100 + 800 * 0.3 = 340
        self.mock_mouse.drag.assert_called_with(680, 340, 520, 340, duration=0.8, inertia=False)
        
        # 場景 2：清單滑動後，看見了目標關卡小島 stages/level4_desert_ruins.png
        # 預期：進行點擊小島並套用 -160 像素的點擊向上偏移 (y = 200 - 160 = 40 ➔ 絕對 y = 100 + 40 = 140)
        def match_side_effect_click(img, name, threshold):
            if name == "stages/level4_desert_ruins.png":
                return ((500, 200), 0.9)
            elif name == "common/select_stage_after.png":
                return ((300, 300), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_click
        self.mock_mouse.click.reset_mock()
        self.mock_mouse.drag.reset_mock()
        
        self.state_machine.step()
        
        # 驗證沒有拖曳
        self.mock_mouse.drag.assert_not_called()
        # 驗證點擊座標 (100 + 500 = 600, 100 + 200 - 160 = 140)
        self.mock_mouse.click.assert_called_with(600, 140)

    @patch('os.path.exists')
    def test_stage_navigation_vertical_scroll_fallback(self, mock_exists):
        """
        測試普通關卡備用滾動尋找魔王邏輯：
        當在關卡內部細節畫面，且沒有任何匹配按鈕 (包括 boss 關卡按鈕、大廳開始按鈕、城鎮按鈕、選關清單等)，
        應自動觸發 mouse.scroll 向下滾動尋找魔王關。
        """
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        self.state_machine.config["navigation_path"] = [
            "common/door.png",
            "exit_battle.png",
            "common/select_stage.png",
            "stages/level4_desert_ruins.png",
            "stages/stage_label.png",
            "stages/level4_final.png"
        ]
        self.state_machine.enable_bread = False
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        
        mock_exists.return_value = True
        
        self.mock_capturer.get_window_rect.return_value = {"left": 100, "top": 100, "width": 1000, "height": 800}
        
        # 模擬偵測到 stages/stage_label.png，代表確實在內部細節畫面，但魔王未見
        def match_side_effect(img, name, threshold=None):
            if name == "stages/stage_label.png":
                return ((100, 100), 0.9)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = match_side_effect
        self.mock_mouse.drag.reset_mock()
        self.mock_mouse.click.reset_mock()
        
        # 模擬魔王關卡已經缺失 2.0 秒，使等待緩衝期已過
        self.state_machine.__setattr__("missing_time_stages/level4_final.png", time.time() - 2.0)

        self.state_machine.step()
        
        # 驗證觸發了向下的拖曳 (center_x = 600, center_y = 500)
        self.mock_mouse.drag.assert_called_with(600, 650, 600, 300)

    @patch('os.path.exists')
    def test_backpack_full_sorting_custom_disassemble_threshold(self, mock_exists):
        """
        測試背包已滿溢出分選自訂分解閾值邏輯：
        當設定 disassemble_colors 包含藍色時，藍色裝備被判定為低稀有度（可銷毀），而紫色裝備被判定為高稀有度（需保留）。
        """
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        # 自訂只分解/銷毀 灰色、綠色、藍色 裝備
        self.state_machine.config["disassemble_colors"] = ["gray_or_empty", "green", "blue"]
        # 設定保留紫色及以上（藍色不在保留名單中，因此可以被銷毀）
        self.state_machine.config["keep_colors"] = ["purple", "orange_yellow", "red"]
        self.state_machine.current_state = self.state_machine.STATE_BACKPACK_FULL_SORTING
        
        mock_exists.return_value = True
        
        # 模擬彈窗中心在 (630, 37) ➔ 左上角 win_x = 0, win_y = 0
        def match_side_effect(img, name, threshold=None):
            if name == "backpack_full.png":
                return ((630, 37), 0.9)
            elif name == "common/destroy.png":
                return ((700, 700), 0.9)
            elif name == "common/confirm.png":
                return ((800, 800), 0.9)
            elif name == "common/collect.png":
                return ((900, 900), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect
        self.mock_mouse.click.reset_mock()
        
        # 模擬截圖中，左側溢出區 Row 0, Col 0 為紫色貴重裝備 (std > 40)，而右側背包 Row 0, Col 0 為藍色裝備 (可銷毀)
        import cv2
        import numpy as np
        screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        
        # 左側溢出區 Row 0, Col 0: cx = 77, cy = 190, cell_size = 134
        # 模擬紫色 (std > 40)
        screen[190:324, 77:211] = [200, 0, 200]  # 紫色背景
        
        # 右側背包 Row 0, Col 0: cx = 677, cy = 190, cell_size = 134
        # 模擬藍色 (std > 18)
        screen[190:324, 677:811] = [200, 100, 0]  # 藍色背景
        
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
        with patch.object(handler, 'classify_slot_color', side_effect=classify_slot_color_impl):
            self.state_machine.step()
            
        # 驗證執行了以下步驟：
        # 1. 點擊右側藍色裝備進行銷毀 (中心在 677 + 67 = 744, 190 + 67 = 257)
        # 2. 點擊銷毀按鈕 (700, 700)
        # 3. 點擊確認銷毀 (800, 800)
        # 4. 點擊左側紫色貴重裝備彈出詳情 (中心在 77 + 67 = 144, 190 + 67 = 257)
        # 5. 點擊領取按鈕 (900, 900)
        self.mock_mouse.click.assert_any_call(744, 257)
        self.mock_mouse.click.assert_any_call(700, 700)
        self.mock_mouse.click.assert_any_call(800, 800)
        self.mock_mouse.click.assert_any_call(144, 257)
        self.mock_mouse.click.assert_any_call(900, 900)

    @patch('states.state_machine.os.path.exists')
    def test_run_task_complete_subflow_success(self, mock_exists):
        """
        測試任務完成彈窗領取獎勵子流程成功跑完的狀態：
        1. 看到 common/confirm.png ➔ 點選並結束子流程
        """
        mock_exists.return_value = True
        
        # 模擬 matcher.match 尋找到 confirm.png
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((150, 150), 0.92) if name == "common/confirm.png" else (None, 0.0)
        )
        
        rect = {"left": 10, "top": 20, "width": 800, "height": 600}
        
        # 以 patch 縮短 subflow 的 sleep 時間以加快測試速度
        with patch('states.state_machine.time.sleep') as mock_sleep:
            self.state_machine._run_task_complete_subflow(rect)
            
        # 驗證是否點擊了確認按鈕，且座標加上 rect["left"] / rect["top"]
        self.mock_mouse.click.assert_called_once_with(160, 170)  # 10 + 150, 20 + 150

if __name__ == "__main__":
    unittest.main()


