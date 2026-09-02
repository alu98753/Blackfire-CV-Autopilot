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


class TestDungeonScenarios(BehavioralScenarioTestCase):

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
        self.state_machine.config = GAME_CONFIGS["dungeon"]
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        mock_exists.return_value = True
        
        # Step 1: 第一次比對到寶箱，點擊
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((300, 300), 0.9) if name == "dungeons/Treasure.png" else (None, 0.0)
        )
        explore_handler = self.state_machine.handlers[
            self.state_machine.STATE_DUNGEON_EXPLORING
        ]
        with patch.object(
            explore_handler,
            "_run_treasure_subflow",
            return_value=True,
        ):
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

    @patch('os.path.exists')
    def test_dungeon_selection_with_scrolling(self, mock_exists):
        """
        [行為場景 28] 地下城模式下，目標地下城不在畫面上時，應執行左右滑動尋找：
        - 案例 A：目標在右側，應執行向左滑動。
        - 案例 B：目標在左側，應執行向右滑動。
        """
        mock_exists.return_value = True
        self.mock_matcher.match.return_value = (None, 0.0)
        config_a = GAME_CONFIGS["dungeon"].copy()
        config_a["greedy_dungeon"] = False
        config_a["navigation_path"] = ["common/door.png", "dungeons/dungeon.png", "dungeons/Ruins_entry.png"]
        self.state_machine.config = config_a
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        
        # Mock 視窗大小為 1000x800
        self.mock_capturer.get_window_rect.return_value = {
            "left": 100, "top": 100, "width": 1000, "height": 800
        }
        
        img = np.zeros((800, 1000, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = img
        
        # 案例 A：目標是 Ruins_entry (index 3)，畫面上只有 Slime_entry (index 0) 於 X=100
        # 預期：目標 index (3) 大於當前可見 index (0)，代表目標在右側 ➔ 向左滑動 drag(900, 500, 300, 500)
        call_count_a = 0
        def mock_matchTemplate_a(img_arg, templ, method):
            nonlocal call_count_a
            val = 0.95 if call_count_a == 0 else 0.0
            call_count_a += 1
            return np.array([[val]], dtype=np.float32)
            
        with patch('cv2.imread', return_value=np.zeros((10, 10, 3), dtype=np.uint8)), \
             patch('cv2.matchTemplate', side_effect=mock_matchTemplate_a):
            self.mock_mouse.drag.reset_mock()
            self.state_machine.step()
            self.mock_mouse.drag.assert_called_once_with(700, 500, 500, 500, duration=0.8, inertia=False)
            
        # 案例 B：目標是 Slime_entry (index 0)，畫面上只有 Ruins_entry (index 3) 於 X=100
        # 預期：目標 index (0) 小於當前可見 index (3)，代表目標在左側 ➔ 向右滑動 drag(300, 500, 900, 500)
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
            self.mock_mouse.drag.assert_called_once_with(500, 500, 700, 500, duration=0.8, inertia=False)

    @patch('os.path.exists')
    def test_dungeon_selection_fallback_swipe(self, mock_exists):
        """
        [行為場景 29] 地下城選關頁面無任何解鎖卡片時的防呆拉回機制：
        - 畫面上無已解鎖卡片 (Slime, Ghost, Forest, Ruins 相似度均低)，
        - 但偵測到鎖定卡片 locked_entry.png 相似度高 (>= 0.75) ➔ 判定為選關頁面。
        - 執行向右滑動拉回 (drag 0.2 -> 0.8)，連續計數遞增。
        - 連續計數達到 3 次時，停止滑動，原地等待。
        """
        mock_exists.return_value = True
        self.mock_matcher.match.return_value = (None, 0.0)
        config_fb = GAME_CONFIGS["dungeon"].copy()
        config_fb["greedy_dungeon"] = True
        self.state_machine.config = config_fb
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        self.state_machine.fallback_swipe_count = 0
        
        # Mock 視窗大小為 1000x800
        self.mock_capturer.get_window_rect.return_value = {
            "left": 100, "top": 100, "width": 1000, "height": 800
        }
        
        img = np.zeros((800, 1000, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = img
        
        # mock cv2.matchTemplate 使得前 N 次 (dungeon_entries) 均返回 0.0,
        # 第 N+1 次 (locked_entry) 返回 0.95 (匹配成功)
        entry_count = len(self.state_machine.config.get("dungeon_entries", []))
        call_count = 0
        def mock_matchTemplate(img_arg, templ, method):
            nonlocal call_count
            val = 0.95 if call_count == entry_count else 0.0
            call_count += 1
            return np.array([[val]], dtype=np.float32)
            
        with patch('cv2.imread', return_value=np.zeros((10, 10, 3), dtype=np.uint8)), \
             patch('cv2.matchTemplate', side_effect=mock_matchTemplate):
             
            # 第一次防呆滑動：預期 drag(300, 500, 900, 500)
            self.mock_mouse.drag.reset_mock()
            self.state_machine.step()
            self.mock_mouse.drag.assert_called_once_with(300, 500, 900, 500)
            self.assertEqual(self.state_machine.fallback_swipe_count, 1)
            
            # 第二次防呆滑動
            call_count = 0
            self.mock_mouse.drag.reset_mock()
            self.state_machine.step()
            self.mock_mouse.drag.assert_called_once_with(300, 500, 900, 500)
            self.assertEqual(self.state_machine.fallback_swipe_count, 2)
            
            # 第三次防呆滑動
            call_count = 0
            self.mock_mouse.drag.reset_mock()
            self.state_machine.step()
            self.mock_mouse.drag.assert_called_once_with(300, 500, 900, 500)
            self.assertEqual(self.state_machine.fallback_swipe_count, 3)
            
            # 第四次：已達到上限 3，預期不執行滑動
            call_count = 0
            self.mock_mouse.drag.reset_mock()
            self.state_machine.step()
            self.mock_mouse.drag.assert_not_called()
            self.assertEqual(self.state_machine.fallback_swipe_count, 3)

    @patch('os.path.exists')
    def test_dungeon_defeat_giveup_flow(self, mock_exists):
        """
        [行為測試 26] 測試地下城連續戰敗退出與冷卻重設邏輯：
        1. 第一次戰敗時，點選 retry，dungeon_defeat_count 遞增為 1。
        2. 第二次戰敗時，點選 defeat_giveup.png 與 confirm.png 放棄。
        3. 驗證當前地下城被設為 30 分鐘冷卻 (冰雪洞窟 idx=4)，且狀態移轉至 STATE_NAVIGATING。
        """
        # 初始化配置為地下城模式
        self.state_machine.config = GAME_CONFIGS["dungeon"].copy()
        target_idx = self.state_machine.config["dungeon_entries"].index("dungeons/Ice_entry.png")
        expected_cd = self.state_machine.config.get("cooldown_map", {}).get(target_idx, 900.0)
        self.state_machine.current_dungeon_index = target_idx  # 冰雪洞窟
        self.state_machine.dungeon_defeat_count = 0
        self.state_machine.transition_to(self.state_machine.STATE_RESULT)
        
        # Mock exists 都返回 True
        mock_exists.return_value = True
        
        # 設置視窗大小
        self.mock_capturer.get_window_rect.return_value = {
            "left": 0, "top": 0, "width": 1920, "height": 1080
        }
        
        # Mock 影像
        dummy_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = dummy_img
        
        # Mock 模板匹配
        # 1. 第一次戰敗：我們需要匹配 defeat.png 成功，以及 defeat_retry.png 成功
        # 2. 第二次戰敗：我們需要匹配 defeat.png 成功，defeat_giveup.png 成功，以及 confirm.png 成功
        def mock_match(img_arg, name, threshold=0.7, **kwargs):
            if name == "defeat.png":
                return (100, 100), 0.85
            elif name in ["defeat_retry.png", "stages/retry.png"]:
                return (200, 200), 0.88
            elif name == "defeat_giveup.png":
                return (300, 300), 0.88
            elif name == "common/confirm.png":
                return (400, 400), 0.88
            return None, 0.0
            
        self.mock_matcher.match.side_effect = mock_match
             
        # 第一次戰敗 (設定為第 19 次戰敗: count=18)
        self.state_machine.dungeon_defeat_count = 18
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.assertEqual(self.state_machine.dungeon_defeat_count, 19)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOADING)
        
        # 回歸到結算狀態準備第 20 次戰敗 (達到 20 次上限)
        self.state_machine.transition_to(self.state_machine.STATE_RESULT)
        
        # 第 20 次戰敗：這次因為 count=19 >= 20-1，會點選放棄與確認退出
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        # 驗證戰敗次數清零，狀態切回 NAVIGATING，且設定了對應的冷卻
        self.assertEqual(self.state_machine.dungeon_defeat_count, 0)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        self.assertGreater(self.state_machine.dungeon_cooldowns[target_idx], time.time() + expected_cd - 10.0)

    @patch('os.path.exists')
    def test_stage_defeat_loop_protection(self, mock_exists):
        """
        [行為測試 27] 測試普通關卡連續戰敗退避保護與子流程：
        1. 初始化配置為普通關卡 (Stage) 模式。
        2. 第一次戰敗，點選 retry，defeat_count 遞增為 1。
        3. 第二次戰敗時 (defeat_count=1 >= max_defeat-1)，觸發 _run_defeat_giveup_subflow。
        4. 驗證透過子流程搜尋並點擊 common/quit.png 或 goback_town.png， defeat_count 清零並切回 STATE_NAVIGATING。
        """
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        self.state_machine.config["stage_max_defeat"] = 2
        self.state_machine.defeat_count = 0
        self.state_machine.transition_to(self.state_machine.STATE_RESULT)
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        dummy_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = dummy_img
        
        def mock_match(img_arg, name, threshold=0.7, **kwargs):
            if name == "defeat.png":
                return (100, 100), 0.85
            elif name in ["stages/retry.png", "defeat_retry.png"]:
                return (200, 200), 0.88
            elif name == "defeat_giveup.png":
                return (300, 300), 0.88
            elif name == "common/confirm.png":
                return (400, 400), 0.88
            return None, 0.0
            
        self.mock_matcher.match.side_effect = mock_match
        
        # 第一次戰敗
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.assertEqual(self.state_machine.defeat_count, 1)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOADING)
        
        # 準備第二次戰敗 (已達上限 2 次)
        self.state_machine.transition_to(self.state_machine.STATE_RESULT)
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        
        # 驗證戰敗次數清零，狀態切回 NAVIGATING
        self.assertEqual(self.state_machine.defeat_count, 0)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)

    @patch('cv2.minMaxLoc')
    @patch('cv2.matchTemplate')
    @patch('cv2.imread')
    @patch('os.path.exists')
    def test_mix_mode_specified_dungeon_full_lifecycle(self, mock_exists, mock_imread, mock_match_temp, mock_min_max):
        """
        [行為場景 7] 混合模式 (mix) 指定副本完整生命週期測試：
        1. 城鎮開局 (door.png) ➔ 大廳 (dungeons/dungeon.png) ➔ 進入地下城選關 (Ice_entry.png)。
        2. 點擊探險 (dungeons/dungeon_fight.png) ➔ 進入戰鬥 ➔ 戰鬥結束。
        3. 冰雪洞窟進入冷卻 (300 秒) ➔ 點擊 common/select_stage.png 退守普通關卡。
        4. has_available_dungeon 傳回 False ➔ 依據 stage_navigation_path 進入 level6 first_stage 打普通關卡。
        5. 普通關卡戰鬥結算 (common/continue.png)。
        6. 快進時間 301 秒，冰雪洞窟冷卻到期，has_available_dungeon 變回 True ➔ 返抵大廳自動點擊 dungeons/dungeon.png 切回地下城！
        """
        mock_exists.return_value = True
        dummy_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = dummy_img
        
        def mock_imread_impl(filepath, *args, **kwargs):
            if "cooldown" in str(filepath) or "locked" in str(filepath):
                return np.zeros((10, 10, 3), dtype=np.uint8)
            return np.zeros((500, 500, 3), dtype=np.uint8)
        mock_imread.side_effect = mock_imread_impl
        
        def mock_match_temp_impl(image, templ, *args, **kwargs):
            if templ.shape[0] <= 20:
                return np.zeros((10, 10), dtype=np.float32)
            return np.zeros((500, 500), dtype=np.float32)
        mock_match_temp.side_effect = mock_match_temp_impl
        
        is_dungeon_page_active = [False]
        def min_max_side_effect(res_arg):
            if is_dungeon_page_active[0] and hasattr(res_arg, 'shape') and res_arg.shape[0] > 100:
                return (0.0, 0.9, (0, 0), (1400, 300))
            return (0.0, 0.0, (0, 0), (0, 0))
        mock_min_max.side_effect = min_max_side_effect
        
        from config import GAME_CONFIGS
        config = dict(GAME_CONFIGS["mix"])
        config["navigation_path"] = ["dungeons/Ice_entry.png"]
        config["stage_navigation_path"] = [
            "common/door.png",
            "common/select_stage.png",
            "stages/level6_ice_cave.png",
            "stages/stage_label.png",
            "stages/first_stage.png"
        ]
        
        def mock_match_step2(img, name, **kw):
            if kw.get("quiet"):
                return (None, 0.0)
            if name == "town_building/Blood_Altar/receive_daily.png":
                return ((400, 500), 0.9)
            return (None, 0.0)

        config["greedy_dungeon"] = False
        config["greedy_allowed_indices"] = [0, 1, 2, 3, 4]
        self.state_machine.config = config
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        
        # --- 階段 1：從城鎮大門 (door.png) 進入大廳 ---
        self.mock_matcher.match.side_effect = lambda img, name, **kw: (
            ((100, 100), 0.9) if name == "common/door.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # --- 階段 2：在大廳看到 dungeons/dungeon.png 進入地下城選關 ---
        self.assertTrue(self.state_machine.has_available_dungeon())
        
        self.mock_matcher.match.side_effect = lambda img, name, **kw: (
            ((650, 750), 0.95) if name == "dungeons/dungeon.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(650, 750)
        
        # --- 階段 3：進入地下城選關介面，看到 Ice_entry.png 選擇並點擊入場 ---
        is_dungeon_page_active[0] = True
        ice_idx = config["dungeon_entries"].index("dungeons/Ice_entry.png")
        self.mock_matcher.match.side_effect = lambda img, name, **kw: (
            ((1400, 300), 0.9) if name == "dungeons/Ice_entry.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_dungeon_index, ice_idx)
        self.mock_mouse.click.assert_called_with(1650, 550)
        
        # --- 階段 4：彈出 dungeons/dungeon_fight.png，點擊探險進入戰鬥 ---
        is_dungeon_page_active[0] = False
        self.mock_matcher.match.side_effect = lambda img, name, **kw: (
            ((900, 500), 0.9) if name == "dungeons/dungeon_fight.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(900, 500)
        
        # 模擬進入戰鬥並完成戰鬥
        self.state_machine.transition_to(self.state_machine.STATE_BATTLE)
        self.state_machine.battle_start_time = time.time() - 10.0
        
        # --- 階段 5：戰鬥結束且冰雪洞窟進入冷卻 (300 秒) ➔ 退回大廳尋路 ---
        now = time.time()
        self.state_machine.dungeon_cooldowns[ice_idx] = now + 300.0
        self.state_machine.transition_to(self.state_machine.STATE_NAVIGATING)
        
        # 斷言：目前冰雪洞窟冷卻中，has_available_dungeon 必須為 False！
        self.assertFalse(self.state_machine.has_available_dungeon())
        
        # --- 階段 6：地下城冷卻中，導向普通關卡 (select_stage.png) ---
        self.mock_matcher.match.side_effect = lambda img, name, **kw: (
            ((530, 750), 0.95) if name == "common/select_stage.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(530, 750)
        
        # --- 階段 7：快進時間 (過 301 秒)，冰雪洞窟冷卻到期！ ---
        self.state_machine.dungeon_cooldowns[ice_idx] = time.time() - 1.0  # 冷卻結束
        
        # 斷言：冰雪洞窟冷卻結束，has_available_dungeon 必須變回 True！
        self.assertTrue(self.state_machine.has_available_dungeon())
        
        # --- 階段 8：返回大廳尋路時，自動點擊 dungeons/dungeon.png 切回地下城！ ---
        self.mock_matcher.match.side_effect = lambda img, name, **kw: (
            ((650, 750), 0.95) if name == "dungeons/dungeon.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(650, 750)

    @patch('cv2.minMaxLoc')
    @patch('cv2.matchTemplate')
    @patch('cv2.imread')
    @patch('os.path.exists')
    def test_mix_mode_greedy_dungeon_full_lifecycle(self, mock_exists, mock_imread, mock_match_temp, mock_min_max):
        """
        [行為場景 8] 混合模式 (mix) 貪婪地下城多關卡冷卻與優先順序復歸測試：
        1. 貪婪模式下優先選最高階 Ice_entry (idx=4) 入場。
        2. Ice_entry 冷卻 300s ➔ 貪婪自動降階選擇 Forest_entry (idx=2) 入場。
        3. Forest_entry 亦冷卻 300s (所有允許地下城全冷卻) ➔ has_available_dungeon 傳回 False ➔ 導向普通關卡。
        4. 快進時間 301s ➔ 最高階 Ice_entry 優先冷卻結束 ➔ has_available_dungeon 變回 True ➔ 返抵大廳自動切回地下城並優先選 Ice_entry (idx=4)！
        """
        mock_exists.return_value = True
        dummy_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = dummy_img
        
        def mock_imread_impl(filepath, *args, **kwargs):
            if "cooldown" in str(filepath) or "locked" in str(filepath):
                return np.zeros((10, 10, 3), dtype=np.uint8)
            return np.zeros((500, 500, 3), dtype=np.uint8)
        mock_imread.side_effect = mock_imread_impl
        
        def mock_match_temp_impl(image, templ, *args, **kwargs):
            if templ.shape[0] <= 20:
                return np.zeros((10, 10), dtype=np.float32)
            return np.zeros((500, 500), dtype=np.float32)
        mock_match_temp.side_effect = mock_match_temp_impl
        
        is_dungeon_page_active = [False]
        def min_max_side_effect(res_arg):
            if is_dungeon_page_active[0] and hasattr(res_arg, 'shape') and res_arg.shape[0] > 100:
                return (0.0, 0.9, (0, 0), (1400, 300))
            return (0.0, 0.0, (0, 0), (0, 0))
        mock_min_max.side_effect = min_max_side_effect
        
        from config import GAME_CONFIGS
        config = dict(GAME_CONFIGS["mix"])
        config["greedy_dungeon"] = True
        config["greedy_allowed_indices"] = [0, 2, 4]  # 允許 史萊姆(0), 森林(2), 冰雪(4)
        config["stage_navigation_path"] = [
            "common/door.png",
            "common/select_stage.png",
            "stages/level6_ice_cave.png",
            "stages/first_stage.png"
        ]
        self.state_machine.config = config
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        
        # --- 階段 1：進入地下城選關，貪婪選擇最高階 Ice_entry (idx=4) ---
        self.assertTrue(self.state_machine.has_available_dungeon())
        
        # --- 階段 2：最高階 Ice_entry (idx=4) 進入冷卻 300 秒，但 Forest_entry (idx=2) 仍可用 ---
        now = time.time()
        self.state_machine.dungeon_cooldowns[4] = now + 300.0
        self.state_machine.dungeon_cooldowns[2] = 0.0  # Forest 仍可用
        self.state_machine.dungeon_cooldowns[0] = now + 300.0
        
        # 斷言：由於 Forest (idx=2) 仍可用，has_available_dungeon 必須仍為 True！
        self.assertTrue(self.state_machine.has_available_dungeon())
        
        # --- 階段 3：Forest_entry (idx=2) 亦進入冷卻 300 秒 (所有允許的地下城全冷卻) ---
        self.state_machine.dungeon_cooldowns[2] = now + 300.0
        
        # 斷言：所有允許副本全冷卻，has_available_dungeon 必須為 False！
        self.assertFalse(self.state_machine.has_available_dungeon())
        
        # --- 階段 4：地下城全冷卻，在大廳點擊 select_stage.png 導向普通關卡 ---
        self.mock_matcher.match.side_effect = lambda img, name, **kw: (
            ((530, 750), 0.95) if name == "common/select_stage.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(530, 750)
        
        # --- 階段 5：快進時間 (過 301 秒)，最高階 Ice_entry (idx=4) 優先冷卻結束！ ---
        self.state_machine.dungeon_cooldowns[4] = time.time() - 1.0  # Ice 結束
        # Forest (idx=2) 與 Slime (idx=0) 仍在冷卻中
        self.state_machine.dungeon_cooldowns[2] = time.time() + 300.0
        self.state_machine.dungeon_cooldowns[0] = time.time() + 300.0
        
        # 斷言：最高階地下城冷卻結束，has_available_dungeon 必須變回 True！
        self.assertTrue(self.state_machine.has_available_dungeon())
        
        # --- 階段 6：返抵大廳時，自動點擊 dungeons/dungeon.png 切回地下城！ ---
        self.mock_matcher.match.side_effect = lambda img, name, **kw: (
            ((650, 750), 0.95) if name == "dungeons/dungeon.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(650, 750)


if __name__ == "__main__":
    unittest.main()
