import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GAME_CONFIGS
from states.state_machine import GameStateMachine

from tests._legacy_state_machine_test_support import StateMachineLogicTestCase


class TestDungeonStateMachine(StateMachineLogicTestCase):

    def test_exploring_transition_restores_primary_dungeon_config(self):
        """Dungeon visual recovery must not run ExploreHandler with bag_clean config."""
        self.state_machine.config = GAME_CONFIGS["bag_clean"].copy()
        self.state_machine.primary_config = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN

        self.state_machine.transition_to(self.state_machine.STATE_DUNGEON_EXPLORING)

        self.assertEqual(self.state_machine.config["type"], "dungeon")
        self.assertIn("explore_priorities", self.state_machine.config)

    @patch('os.path.exists')
    @patch('states.handlers.explore.time.sleep')
    def test_dungeon_explore_and_battle_flow(self, mock_sleep, mock_exists):
        """
        測試史萊姆地下城模式：探索事件 -> 遇怪 -> 戰鬥 -> 結算 -> 繼續探索。
        對齊全新的開啟寶箱與領取祝福子流程。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        
        mock_exists.return_value = True
        self.mock_capturer.capture.return_value = np.zeros((600, 800, 3), dtype=np.uint8)
        
        # 模擬 matcher.match，配合探索主循環與子流程內部的多階段比對
        match_call_count = 0
        def side_effect(img, name, threshold=0.8, brightness_threshold=0.0, *args, **kwargs):
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
            elif name == "dungeons/bless_combat.png" and match_call_count == 6:
                match_call_count += 1
                return (800, 200), 0.90
            elif name == "dungeons/choice_bless.png" and match_call_count == 7:
                match_call_count += 1
                return (225, 200), 0.90  # 局部座標 (225, 200)，加 x_min(575) = 800，完美對齊

            elif name == "common/ok.png" and match_call_count == 8:
                match_call_count += 1
                return (810, 210), 0.90
            elif name == "common/quit.png" and match_call_count == 9:
                match_call_count += 1
                return (820, 220), 0.90
                
            # --- 第四階段：發現戰鬥開始 auto.png 並切換為 BATTLE 狀態 ---
            elif name == "common/auto.png" and match_call_count == 10:
                match_call_count += 1
                return (800, 100), 0.90
            elif name == "common/auto.png" and match_call_count == 11:
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
        self.state_machine.config = GAME_CONFIGS["dungeon"]
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
    def test_greedy_dungeon_on_screen_cooldown_detection(self, mock_exists):
        """
        測試自動貪婪地下城模式下，藉由畫面匹配防禦性跳過正在冷卻的地下城卡片。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.config["greedy_dungeon"] = True
        self.state_machine.enable_bread = False
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        num_dungeons = len(self.state_machine.config.get("dungeon_entries", []))
        self.state_machine.dungeon_cooldowns = {i: float("inf") for i in range(num_dungeons) if i not in (0, 2)}
        
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
                    # idx = 0 (Slime): 匹配成功，起點為 200
                    return (0.0, 0.95, (0, 0), (200, 0))
                elif counts["card"] == 3:
                    # idx = 2 (Forest): 匹配成功，起點為 727
                    return (0.0, 0.95, (0, 0), (727, 0))
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
                
        def mock_imread_impl(path):
            if "entry" in path:
                return np.zeros((341, 346, 3), dtype=np.uint8)
            return np.zeros((10, 10, 3), dtype=np.uint8)
            
        with patch('cv2.imread', side_effect=mock_imread_impl), \
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
    def test_greedy_dungeon_allowed_filter(self, mock_exists):
        """
        測試自動貪婪地下城模式下，藉由 greedy_allowed_indices 限制過濾不想要的關卡。
        1. 設定只允許打 Slime (0) 與 Forest (2)。
        2. 模擬畫面中看到 Slime (0)、Ghost (1) 與 Forest (2)。
        3. 驗證：雖然 Ghost (1) 比 Slime (0) 等級高，但因為它不在允許清單中，系統應只考慮 Slime 與 Forest。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.config["greedy_dungeon"] = True
        # 僅允許打 Slime (idx 0) 與 Forest (idx 2)
        self.state_machine.config["greedy_allowed_indices"] = [0, 2]
        self.state_machine.enable_bread = False
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        
        import numpy as np
        self.mock_capturer.capture.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        mock_exists.return_value = True
        
        # 模擬 match_side_effect 用於大廳/尋路
        self.mock_matcher.match.return_value = (None, 0.0)
        self.mock_mouse.click.reset_mock()
        
        # 模擬 matchTemplate / minMaxLoc 的呼叫次數
        counts = {"card": 0}
        
        def mock_minMaxLoc_impl(res):
            if res.shape[1] > 1000:
                counts["card"] += 1
                if counts["card"] == 1:
                    # idx = 0 (Slime): 匹配成功，起點為 200
                    return (0.0, 0.95, (0, 0), (200, 0))
                elif counts["card"] == 2:
                    # idx = 1 (Ghost): 匹配成功，起點為 400 (雖然存在且未冷卻，但不應被考慮)
                    return (0.0, 0.95, (0, 0), (400, 0))
                elif counts["card"] == 3:
                    # idx = 2 (Forest): 匹配成功，起點為 700
                    return (0.0, 0.95, (0, 0), (700, 0))
                return (0.0, 0.0, (0, 0), (0, 0))
            elif 200 < res.shape[1] <= 1000:
                # 其它冷卻匹配
                return (0.0, 0.0, (0, 0), (0, 0))
            else:
                # 亮骨頭匹配 (解鎖狀態，返回 0.90 > 0.75 閾值)
                return (0.0, 0.90, (0, 0), (0, 0))
                
        def mock_imread_impl(path):
            if "entry" in path:
                return np.zeros((341, 346, 3), dtype=np.uint8)
            return np.zeros((10, 10, 3), dtype=np.uint8)
            
        with patch('cv2.imread', side_effect=mock_imread_impl), \
             patch('cv2.minMaxLoc', side_effect=mock_minMaxLoc_impl):
            self.state_machine.step()
            
        # 驗證：由於是從高到低遍歷，且僅允許 0 與 2，系統應優先點擊 index 2 (Forest) 而不是 1 (Ghost)
        # Forest 的 center x = 700 + 346//2 = 873, center y = 0 + 341//2 = 170 (以 scale=1.0 計算)
        self.mock_mouse.click.assert_called_with(873, 170)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)

    @patch('os.path.exists')
    def test_specific_dungeon_cooldown_waiting(self, mock_exists):
        """
        測試在非貪婪模式（指定特定副本）下，如果副本正在冷卻，應該直接原地等待，不執行點擊。
        1. 記憶體冷卻中：直接不執行任何點擊，退出。
        2. 畫面上有冷卻木牌：執行 OCR 時間讀取，寫入記憶體冷卻時間，並不執行任何點擊。
        """
        # 1. 測試記憶體冷卻中
        self.state_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.config["greedy_dungeon"] = False
        self.state_machine.config["navigation_path"] = ["dungeons/Slime_entry.png"]
        self.state_machine.enable_bread = False
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        
        # 設為 Slime (index 0) 正在冷卻
        self.state_machine.dungeon_cooldowns = {0: time.time() + 100.0}
        
        import numpy as np
        self.mock_capturer.capture.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        mock_exists.return_value = True
        self.mock_matcher.match.return_value = (None, 0.0)
        self.mock_mouse.click.reset_mock()
        
        def mock_minMaxLoc_impl_cooldown(res):
            if res.shape[1] > 1000:
                # 模擬 Slime 入口在畫面上
                return (0.0, 0.95, (0, 0), (200, 0))
            return (0.0, 0.0, (0, 0), (0, 0))
            
        def mock_imread_impl(path):
            return np.zeros((341, 346, 3), dtype=np.uint8)
            
        with patch('cv2.imread', side_effect=mock_imread_impl), \
             patch('cv2.minMaxLoc', side_effect=mock_minMaxLoc_impl_cooldown):
            self.state_machine.step()
            
        # 驗證：因為記憶體冷卻，不應呼叫滑動或點擊卡片
        self.mock_mouse.click.assert_not_called()
        self.mock_mouse.drag.assert_not_called()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)
        
        # 2. 測試記憶體無冷卻，但畫面上有冷卻木牌（首次偵測到冷卻）
        self.state_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.config["greedy_dungeon"] = False
        self.state_machine.config["navigation_path"] = ["dungeons/Slime_entry.png"]
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        self.state_machine.dungeon_cooldowns = {}
        self.mock_mouse.click.reset_mock()
        
        # 模擬比對到冷卻木牌的 side effect
        def mock_minMaxLoc_impl_ocr(res):
            if res.shape[1] > 1000:
                # 匹配卡片 Slime 成功
                return (0.0, 0.95, (0, 0), (200, 0))
            elif 200 < res.shape[1] <= 1000:
                # 匹配木牌成功
                return (0.0, 0.90, (0, 0), (10, 10))
            return (0.0, 0.0, (0, 0), (0, 0))
            
        # 模擬 OCR 辨識出 "00:15:30" (即 930 秒)
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [[None, "00:15:30", 0.99]]
        self.state_machine.get_ocr_reader = MagicMock(return_value=mock_reader)
        
        with patch('cv2.imread', side_effect=mock_imread_impl), \
             patch('cv2.minMaxLoc', side_effect=mock_minMaxLoc_impl_ocr):
            self.state_machine.step()
            
        # 驗證：因為畫面偵測到冷卻，不應呼叫點擊
        self.mock_mouse.click.assert_not_called()
        # 驗證：冷卻時間被成功記錄在記憶體中 (約為未來 930 秒)
        self.assertIn(0, self.state_machine.dungeon_cooldowns)
        self.assertGreater(self.state_machine.dungeon_cooldowns[0], time.time() + 900.0)

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
        # 驗證執行了 drag 拖曳，起點大約在 100 + 1000 * 0.62 = 720，終點大約在 100 + 1000 * 0.38 = 480
        # 高度為 100 + 800 * 0.3 = 340
        self.mock_mouse.drag.assert_called_with(720, 340, 480, 340, duration=0.8, inertia=False)
        
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
        # 驗證點擊座標 (100 + 500 = 600, 100 + 200 - int(160 * 800 / 1080) = 182)
        self.mock_mouse.click.assert_called_with(600, 182)

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
        self.mock_mouse.drag.assert_called_with(600, 600, 600, 400)

    @patch('os.path.exists')
    def test_dungeon_navigation_anti_reentry(self, mock_exists):
        """
        測試地下城選單防重入邏輯：
        當在尋路過程中，且地下城入口選單已開啟 (偵測到 dungeons/dungeon_after.png)，
        應自動跳過 dungeons/dungeon.png，只匹配並點擊最深層的 dungeons/Slime_entry.png。
        """
        config = GAME_CONFIGS["dungeon"].copy()
        config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png", "dungeons/Slime_entry.png"]
        self.state_machine.config = config
        self.state_machine.enable_bread = False
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 100, "top": 100, "width": 1000, "height": 800}
        
        # 模擬比對結果：dungeons/dungeon.png 與 dungeons/dungeon_after.png 同時在畫面上
        # 預期：跳過 dungeon.png 不點擊，只點擊 dungeons/Slime_entry.png (座標 200, 200)
        def match_side_effect(img, name, threshold=None, brightness_threshold=None):
            if name == "dungeons/dungeon_after.png":
                return ((300, 300), 0.95)
            elif name == "dungeons/dungeon.png":
                return ((400, 400), 0.65)
            elif name == "dungeons/Slime_entry.png":
                return ((200, 200), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect
        self.mock_mouse.click.reset_mock()
        
        self.state_machine.step()
        
        # 驗證點擊了 Slime_entry.png (100 + 200 = 300, 100 + 200 = 300)
        # 且沒有點擊過 dungeon.png (100 + 400 = 500)
        self.mock_mouse.click.assert_called_once_with(300, 300)

    @patch("os.path.exists", return_value=True)
    def test_result_exit_rescheduled_dungeon_reenters_from_open_tab(
        self, _mock_exists
    ):
        """A repeated dungeon quest must resume after RESULT without stale progress."""
        from states.navigation_intent import ActionId, IntentId, PostconditionId

        config = GAME_CONFIGS["dungeon"].copy()
        config["navigation_path"] = [
            "common/door.png",
            "dungeons/dungeon.png",
            "dungeons/Slime_entry.png",
        ]
        self.state_machine.config = config
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        self.state_machine.navigation_progress.begin(
            IntentId.PRIMARY_NAVIGATION,
            ActionId.START_PRIMARY,
            PostconditionId.LOADING_OR_BATTLE,
            frame_id=1,
            now=time.monotonic(),
        )

        self.state_machine.transition_to(self.state_machine.STATE_NAVIGATING)

        self.assertIsNone(self.state_machine.navigation_progress.in_flight)

        def match_open_dungeon_tab(_image, template, **_kwargs):
            if template == "dungeons/dungeon_after.png":
                return (300, 300), 0.95
            if template == "dungeons/Slime_entry.png":
                return (200, 200), 0.90
            return None, 0.0

        self.mock_matcher.match.side_effect = match_open_dungeon_tab
        self.mock_mouse.click.reset_mock()

        self.state_machine.step()

        self.mock_mouse.click.assert_called_once_with(200, 200)

    @patch('os.path.exists')
    @patch('cv2.imread')
    @patch('cv2.minMaxLoc')
    def test_dungeon_navigation_stuck_exit(self, mock_minMaxLoc, mock_imread, mock_exists):
        """
        測試地下城選單選關卡卡死自癒退出邏輯：
        當 `fallback_swipe_count` >= 3，且 visible_dungeons 為空時，
        應自動尋找並點擊返回按鈕 `goback_town.png`，並重置 `fallback_swipe_count` 為 0。
        """
        config = GAME_CONFIGS["dungeon"].copy()
        config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png", "dungeons/Slime_entry.png"]
        self.state_machine.config = config
        self.state_machine.enable_bread = False
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        self.state_machine.fallback_swipe_count = 3
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 100, "top": 100, "width": 1000, "height": 800}
        
        # 傳回真實 numpy array 圖片以進入 OpenCV 比對邏輯
        import numpy as np
        self.mock_capturer.capture.return_value = np.zeros((800, 1000, 3), dtype=np.uint8)
        
        # 模擬 cv2.imread 返回 dummy 影像
        mock_imread.return_value = np.zeros((10, 10, 3), dtype=np.uint8)
        
        # 模擬 cv2.minMaxLoc：最後一次比對（locked_entry）回傳高信心度，其餘回傳低信心度
        locked_entry_call_idx = len(self.state_machine.config.get("dungeon_entries", [])) + 1
        minMaxLoc_calls = [0]
        def mock_minMaxLoc_impl(res):
            minMaxLoc_calls[0] += 1
            if minMaxLoc_calls[0] == locked_entry_call_idx:
                return (0.0, 0.95, (0, 0), (0, 0))
            return (0.0, 0.1, (0, 0), (0, 0))
        mock_minMaxLoc.side_effect = mock_minMaxLoc_impl
        
        # 模擬 matcher.match 匹配 goback_town.png
        def match_side_effect(img, name, threshold=None, **kwargs):
            if name == "goback_town.png":
                return ((50, 50), 0.9)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = match_side_effect
        
        self.mock_mouse.click.reset_mock()
        
        self.state_machine.step()
        
        # 驗證點擊了返回按鈕 (100 + 50 = 150, 100 + 50 = 150)
        self.mock_mouse.click.assert_called_once_with(150, 150)
        # 驗證 `fallback_swipe_count` 已經被重置為 0
        self.assertEqual(self.state_machine.fallback_swipe_count, 0)

    @patch('os.path.exists')
    def test_auto_resume_dungeon_full_cycle_and_re_retreat(self, mock_exists):
        """
        測試完整的退避-復歸-再退避-滿時間徹底離開循環：
        1. 在 collect_only 退避期間，偵測地下城冷卻結束 ➔ 切回地下城 (STATE_UNKNOWN)
        2. 在地下城尋路/選關時，若所有地下城再次進入冷卻 ➔ 自動切回 collect_only (STATE_COLLECT_ONLY)
        3. 驗證 stamina_retreat_start_time 完全未被覆蓋，且退避滿 4 小時後徹底結束退避模式。
        """
        mock_exists.return_value = True
        orig_config = GAME_CONFIGS["dungeon"].copy()
        orig_config["auto_resume_dungeon_on_cd"] = True
        
        # 初始狀態：體力耗盡已轉入 collect_only，並退避了 0.5 小時
        t0 = time.time() - 1800.0
        self.state_machine.original_config = orig_config
        self.state_machine.stamina_retreat_start_time = t0
        self.state_machine.config = GAME_CONFIGS["collect_only"].copy()
        self.state_machine.config["stamina_retreat_duration"] = 4.0
        self.state_machine.current_state = self.state_machine.STATE_COLLECT_ONLY
        self.state_machine.need_diamond_collection = False
        self.state_machine.need_bread_collection = False
        
        # 階段 1：地下城 0 冷卻結束 (0.0) ➔ step() 觸發復歸切回地下城
        num_dungeons = len(orig_config.get("dungeon_entries", []))
        self.state_machine.dungeon_cooldowns = {i: 9999.0 for i in range(num_dungeons)}
        self.state_machine.dungeon_cooldowns[0] = 0.0
        self.state_machine.last_state_change = time.time() - 1.0
        self.mock_matcher.match.return_value = (None, 0.0)
        
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)
        self.assertEqual(self.state_machine.config, orig_config)
        self.assertEqual(self.state_machine.stamina_retreat_start_time, t0) # 起點時間未變
        
        # 階段 2：切回地下城後進到 NAVIGATING 狀態，但地下城 0 又全數進入冷卻 (t0 + 1800)
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        now = time.time()
        self.state_machine.dungeon_cooldowns = {i: now + 300 for i in range(num_dungeons)}
        self.mock_matcher.match.return_value = (None, 0.0)
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        self.state_machine.step()
        # 應自動再切回 STATE_COLLECT_ONLY
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)
        self.assertEqual(self.state_machine.config["type"], "collect_only")
        self.assertEqual(self.state_machine.original_config, orig_config)
        self.assertEqual(self.state_machine.stamina_retreat_start_time, t0) # 起點時間仍為原來的 t0！
        
        # 階段 3：動態讀取退避時間並模擬超時 (no-edit)
        retreat_duration = float(self.state_machine.config.get("stamina_retreat_duration", 4.0))
        self.state_machine.stamina_retreat_start_time = time.time() - ((retreat_duration + 0.1) * 3600.0)  # no-edit
        self.state_machine.step()
        
        # 應徹底恢復 orig_config 並清空退避狀態
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)
        self.assertEqual(self.state_machine.config, orig_config)
        self.assertIsNone(self.state_machine.original_config)
        self.assertIsNone(self.state_machine.stamina_retreat_start_time)

    @patch('os.path.exists')
    def test_normal_dungeon_mode_ignores_retreat_check(self, mock_exists):
        """
        測試單純的地下城/混合模式 (非體力退避狀態下，stamina_retreat_start_time 為 None)：
        即使所有地下城皆在冷卻中，也不會被誤判切換至 collect_only 模式。
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.original_config = None
        self.state_machine.stamina_retreat_start_time = None
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        
        # 模擬所有地下城皆在冷卻中
        now = time.time()
        self.state_machine.dungeon_cooldowns = {0: now + 300, 1: now + 300, 2: now + 300, 3: now + 300, 4: now + 300}
        self.mock_matcher.match.return_value = (None, 0.0)
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        self.state_machine.step()
        
        # 斷言：非體力退避狀態下，絕不會轉移至 STATE_COLLECT_ONLY！
        self.assertNotEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)
        self.assertEqual(self.state_machine.config["type"], "dungeon")

    @patch('os.path.exists')
    def test_dungeon_navigation_transition_corrected(self, mock_exists):
        """
        測試修正後的地下城進入狀態轉移邏輯：
        1. 看到 dungeons/dungeon_fight.png 時，狀態應保持 STATE_NAVIGATING 且執行點擊，不提早轉移。
        2. 只有看到 dungeons/leave.png（或寶箱/祝福等內部按鈕）時，才轉移至 STATE_DUNGEON_EXPLORING。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 100, "top": 100, "width": 1000, "height": 800}
        
        # 1. 模擬畫面只看到 dungeon_fight.png (無 leave.png)
        def match_fight(img, name, threshold=None, brightness_threshold=None):
            if name == "dungeons/dungeon_fight.png":
                return (200, 300), 0.9
            return None, 0.0
            
        self.mock_matcher.match.side_effect = match_fight
        self.mock_mouse.click.reset_mock()
        
        self.state_machine.step()
        # 應點擊戰鬥按鈕
        self.mock_mouse.click.assert_called_once_with(300, 400) # left=100, top=100 + offset (200, 300)
        # 狀態仍應維持 STATE_NAVIGATING 
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # 2. 模擬畫面看到 leave.png (無 dungeon_fight.png)
        def match_leave(img, name, threshold=None, brightness_threshold=None):
            if name == "dungeons/leave.png":
                return (150, 250), 0.9
            return None, 0.0
            
        self.mock_matcher.match.side_effect = match_leave
        self.mock_mouse.click.reset_mock()
        
        self.state_machine.step()
        # 不應點擊
        self.mock_mouse.click.assert_not_called()
        # 狀態轉移至 STATE_DUNGEON_EXPLORING
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)

    @patch('os.path.exists')
    def test_mix_mode_navigation_routing(self, mock_exists):
        """
        測試混合模式 (mix) 的瀑布式導航優先級：
        1. 地下城可打時，在大廳看到 dungeons/dungeon.png 優先點擊進入地下城。
        2. 地下城全冷卻時，在大廳看到 common/select_stage.png 點擊進入普通關卡。
        """
        self.state_machine.config = GAME_CONFIGS["mix"].copy()
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        mock_exists.return_value = True

        # 情況 1: 地下城可用，在大廳匹配到 dungeons/dungeon.png
        self.state_machine.dungeon_cooldowns = {0: 0.0} # 黏糊糊的石窟可用
        def mock_match_1(img, name, threshold=0.7, **kwargs):
            if name == "dungeons/dungeon.png":
                return (100, 100), 0.85
            return None, 0.0
        self.mock_matcher.match.side_effect = mock_match_1

        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(100, 100)

        # 情況 2: 所有地下城皆在冷卻中，在大廳匹配到 common/select_stage.png
        num_dungeons = len(self.state_machine.config.get("dungeon_entries", []))
        self.state_machine.dungeon_cooldowns = {i: time.time() + 1800 for i in range(num_dungeons)}
        def mock_match_2(img, name, threshold=0.7, **kwargs):
            if name == "common/select_stage.png":
                return (200, 200), 0.85
            return None, 0.0
        self.mock_matcher.match.side_effect = mock_match_2

        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(200, 200)

    @patch('os.path.exists')
    def test_mix_mode_custom_stage_selection_routing(self, mock_exists):
        """
        測試混合模式 (mix) 搭配重構後的通用關卡選擇 (例如選擇 Level 1 Final)：
        當地下城全冷卻時，正確使用自訂的 stage_navigation_path 導航至目標關卡。
        """
        self.state_machine.config = GAME_CONFIGS["mix"].copy()
        self.state_machine.config["stage_target"] = "stages/level1_final.png"
        self.state_machine.config["stage_navigation_path"] = [
            "common/door.png",
            "common/select_stage.png",
            "stages/level1_sky_plains.png",
            "stages/stage_label.png",
            "stages/level1_final.png"
        ]
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        num_dungeons = len(self.state_machine.config.get("dungeon_entries", []))
        self.state_machine.dungeon_cooldowns = {i: time.time() + 1800 for i in range(num_dungeons)}
        mock_exists.return_value = True

        # 模擬在活動大廳匹配到 common/select_stage.png
        def mock_match(img, name, threshold=0.7, **kwargs):
            if name == "common/select_stage.png":
                return (200, 200), 0.85
            return None, 0.0
        self.mock_matcher.match.side_effect = mock_match

        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(200, 200)

    def test_missing_greedy_allowed_indices_raises_error(self):
        """
        測試當 config 中缺乏 greedy_allowed_indices (或為 None) 時，
        has_available_dungeon 應主動拋出 ValueError 引導使用者設定。
        """
        self.state_machine.config = {"type": "mix", "greedy_allowed_indices": None}
        with self.assertRaises(ValueError):
            self.state_machine.has_available_dungeon()

    def test_has_available_dungeon_non_dungeon_mode_returns_false(self):
        """
        測試當 config 為 collect_only 或 stage 模式時，has_available_dungeon 應安全傳回 False 而非拋出 ValueError
        """
        self.state_machine.config = {"type": "collect_only"}
        self.assertFalse(self.state_machine.has_available_dungeon())

        self.state_machine.config = {"type": "stage"}
        self.assertFalse(self.state_machine.has_available_dungeon())

    def test_get_dungeon_cooldown_status(self):
        """
        測試 get_dungeon_cooldown_status 能正確格式化顯示各地下城冷卻狀態與可挑戰清單。
        """
        now = time.time()
        self.state_machine.config = {
            "type": "mix",
            "greedy_dungeon": True,
            "greedy_allowed_indices": [0, 1, 2, 3, 4],
            "dungeon_names": ["黏糊糊的石窟", "幽影地穴", "森林迷宮", "神秘遺跡", "冰雪洞窟"]
        }
        self.state_machine.dungeon_cooldowns = {
            0: 0.0,
            1: now + 300.0,
            2: float('inf'),
            3: 0.0,
            4: now + 600.0
        }
        status_str, avail = self.state_machine.get_dungeon_cooldown_status()
        self.assertIn("[黏糊糊的石窟]: 就緒 (可打)", status_str)
        self.assertIn("[幽影地穴]: 冷卻中", status_str)
        self.assertIn("[森林迷宮]: 永久不可打", status_str)
        self.assertIn("[神秘遺跡]: 就緒 (可打)", status_str)
        self.assertEqual(avail, ["黏糊糊的石窟", "神秘遺跡"])


if __name__ == "__main__":
    unittest.main()
