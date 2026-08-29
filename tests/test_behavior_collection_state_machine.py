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


class TestCollectionStateMachine(StateMachineLogicTestCase):

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
        
        # - 看到 quit_bread.png ➔ 點擊退出，第一步應點擊但尚未重置
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((400, 400), 0.9) if name == "common/quit.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(400, 400)
        self.assertTrue(self.state_machine.need_bread_collection)
        
        # - 模擬退出按鈕消失，第二步完成重置與退出
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (None, 0.0)
        self.state_machine.step()
        self.assertFalse(self.state_machine.need_bread_collection)
        
        # 3. 領完體力後，NAVIGATING 尋路結束，看到大廳的 stages/start.png ➔ 應轉移至 LOBBY
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name in ["stages/start.png", "common/select_stage.png", "goback_town.png"] else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOBBY)
        
        # 4. LOBBY 狀態下：看到大廳 stages/start.png ➔ 點擊並轉移至 LOADING
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name in ["stages/start.png", "common/select_stage.png", "goback_town.png"] else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(500, 500)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOBBY)

        # The click is acknowledged only once the start button disappears on a later frame.
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (None, 0.0)
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOADING)
        
        # 5. 看到戰鬥自動按鈕 ➔ 正式轉入 BATTLE
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((400, 400), 0.9) if name == "common/auto.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)

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
        self.state_machine.config = GAME_CONFIGS["dungeon"]
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
        
        # 6. 看到退出按鈕 ➔ 關閉鑽石，第一步點擊退出但尚未重置
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name == "common/quit.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(500, 500)
        self.assertTrue(self.state_machine.need_diamond_collection)
        
        # - 模擬退出按鈕消失，第二步完成重置與退出
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (None, 0.0)
        self.state_machine.step()
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
        self.state_machine.config = GAME_CONFIGS["dungeon"]
        self.state_machine.enable_bread = False
        self.state_machine.need_diamond_collection = True
        self.state_machine.diamond_collected_this_run = False
        self.state_machine.diamond_window_opened = True
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
        self.state_machine.step()
        self.state_machine.step()
        
        # 斷言：第一步應點擊退出按鈕，但尚未重置
        self.mock_mouse.click.assert_called_with(500, 500)
        self.assertTrue(self.state_machine.need_diamond_collection)
        
        # 模擬退出按鈕消失，第二步完成重置
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (None, 0.0)
        self.state_machine.step()
        self.assertFalse(self.state_machine.need_diamond_collection)

    @patch('os.path.exists')
    def test_dungeon_global_stamina_collection_trigger(self, mock_exists):
        """
        測試史萊姆地下城模式：全域定時觸發體力領取邏輯與尋路導航中的退回城鎮。
        """
        # 1. 設置為 dungeon 配置，啟用領體力
        self.state_machine.config = GAME_CONFIGS["dungeon"]
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
        # - 因為 need_bread_collection 為 True，在大廳看到 common/bread.png ➔ 應點擊打開體力視窗並跳轉至 BREAD_COLLECTION
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((300, 300), 0.9) if name == "common/bread.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(300, 300)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BREAD_COLLECTION)

    @patch('os.path.exists')
    def test_collect_only_mode_flow(self, mock_exists):
        """
        測試定時領取模式 (collect_only)：
        1. 狀態與跳轉攔截 (NAVIGATING -> COLLECT_ONLY)
        2. 定時冷卻 (體力CD改為2小時對齊)
        3. CollectOnlyHandler 導航轉移至領取或城鎮待機
        """
        self.state_machine.config = GAME_CONFIGS["collect_only"].copy()
        self.state_machine.stamina_retreat_start_time = time.time()
        self.state_machine.config["diamond_cd"] = 7200.0
        self.state_machine.config["bread_cd"] = 7200.0
        self.state_machine.enable_bread = True
        self.state_machine.need_diamond_collection = True
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        
        mock_exists.return_value = True
        
        # 1. 測試轉移攔截：
        # 當需要領取時，detect_current_state 會嘗試進入 NAVIGATING，但應被攔截並轉移至 COLLECT_ONLY
        self.mock_matcher.match.side_effect = lambda img, name, threshold=None, **kwargs: (
            ((100, 100), 0.9) if name == "common/door.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)
        
        # 2. 測試 CollectOnlyHandler 領鑽石流程：
        # 當在城鎮 (is_town=True) 且 need_diamond_collection=True 時，應轉移至 DIAMOND_COLLECTION
        self.state_machine.need_diamond_collection = True
        self.state_machine.need_bread_collection = False
        
        # 模擬在城鎮的畫面比對 (看到 door.png 且 diamond.png)
        def match_town(img, name, threshold=None, **kwargs):
            if name in ["common/door.png", "diamond.png"]:
                return ((150, 150), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_town
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DIAMOND_COLLECTION)
        
        # 3. 測試退避路由：
        # 當在體力退避期間時，根據 stamina_retreat_start_time 顯式轉移至 COLLECT_ONLY
        next_st = self.state_machine.STATE_COLLECT_ONLY if self.state_machine.stamina_retreat_start_time is not None else self.state_machine.STATE_NAVIGATING
        self.state_machine.transition_to(next_st)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)
        
        # 4. 測試 CollectOnlyHandler 領體力流程：
        # 當在城鎮且 need_bread_collection=True，應點擊門 (door.png) 進入大廳，而不是直接跳轉
        self.state_machine.need_diamond_collection = False
        self.state_machine.need_bread_collection = True
        self.mock_mouse.click.reset_mock()
        
        self.state_machine.step()
        # 點擊了 door.png 的相對座標 (150, 150)
        self.mock_mouse.click.assert_called_once_with(150, 150)
        
        # 5. 測試定時冷卻對齊 (體力在 collect_only 模式下為 2 小時 CD)
        self.state_machine.need_bread_collection = False
        
        # 5.1 經過 1 小時 (3600秒)，不應觸發領取
        self.state_machine.last_bread_collection_time = time.time() - 3600.0
        self.state_machine.check_collection_trigger(None)
        self.assertFalse(self.state_machine.need_bread_collection)
        
        # 5.2 經過 2.1 小時 (7500秒)，應該觸發領取
        self.state_machine.last_bread_collection_time = time.time() - 7500.0
        self.state_machine.check_collection_trigger(None)
        self.assertTrue(self.state_machine.need_bread_collection)

    @patch('os.path.exists')
    def test_insufficient_stamina_defense_subflow(self, mock_exists):
        """
        測試全域食物不足（體力不足）退避自癒子流程：
        1. 偵測到 no_bread/no_bread.png 時觸發
        2. 點擊 no_bread/cancel.png
        3. 進行 quit 按鈕清除循環
        4. 尋找並點擊 goback_town.png
        5. 一律切換為 collect_only 模式與狀態
        """
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        self.state_machine.current_state = self.state_machine.STATE_LOBBY
        
        # 讓 os.path.exists 對所有範本返回 True
        mock_exists.return_value = True
        
        # 模擬視窗物理範圍
        self.mock_capturer.get_window_rect.return_value = {"left": 100, "top": 100, "width": 800, "height": 600}
        
        # 我們將用一個計數器來模擬多個步驟的畫面匹配結果
        match_call_count = [0]
        
        def match_side_effect(img, name, threshold=None, **kwargs):
            match_call_count[0] += 1
            if name == "no_bread/no_bread.png":
                return ((200, 200), 0.9)
            elif name == "no_bread/cancel.png":
                return ((150, 250), 0.9)
            elif name == "common/quit.png":
                # 第一輪清除有 quit，第二輪沒有
                if match_call_count[0] <= 5: # 用呼叫計數來模擬
                    return ((300, 50), 0.9)
                return (None, 0.0)
            elif name == "goback_town.png":
                return ((50, 450), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect
        self.mock_mouse.click.reset_mock()
        self.state_machine.last_state_change = time.time()

        
        # 以 patch 縮短 stamina_flow 的 sleep 時間以加快測試速度
        with patch('states.stamina_flow.time.sleep') as mock_sleep:
            self.state_machine.step()
            
        # 驗證點擊序列：
        # 1. 點擊取消 (100 + 150 = 250, 100 + 250 = 350)
        # 2. 點擊 quit 兩次 (100 + 300 = 400, 100 + 50 = 150)
        # 3. 點擊 goback_town (100 + 50 = 150, 100 + 450 = 550)
        from unittest.mock import call
        expected_clicks = [
            call(250, 350), # 點擊取消
            call(400, 150), # 點擊 quit (第一輪)
            call(400, 150), # 點擊 quit (第二輪)
            call(150, 550)  # 點擊返回城鎮
        ]
        self.mock_mouse.click.assert_has_calls(expected_clicks)
        
        # 驗證配置已被切換為 collect_only
        self.assertEqual(self.state_machine.config["type"], "collect_only")
        # 驗證狀態已轉移至 STATE_COLLECT_ONLY
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)

    @patch('os.path.exists')
    def test_bread_collection_window_missing_self_healing(self, mock_exists):
        """
        測試領體力視窗自癒機制：
        1. bread_window_opened = True，但畫面上找不到退出按鈕 quit.png。
        2. 預期：連續 3 幀未偵測到退出按鈕後，自動將 bread_window_opened 重設為 False，以利下一輪重新打開。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.need_bread_collection = True
        self.state_machine.bread_window_opened = True
        self.state_machine.bread_window_missing_count = 0
        self.state_machine.current_state = self.state_machine.STATE_BREAD_COLLECTION
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 800, "height": 600}
        
        # 模擬比對結果：所有模板都匹配不到 (None)
        self.mock_matcher.match.return_value = (None, 0.0)
        
        # 第一幀
        self.state_machine.step()
        self.assertTrue(self.state_machine.bread_window_opened)
        self.assertEqual(self.state_machine.bread_window_missing_count, 1)
        
        # 第二幀
        self.state_machine.step()
        self.assertTrue(self.state_machine.bread_window_opened)
        self.assertEqual(self.state_machine.bread_window_missing_count, 2)
        
        # 第三幀（應觸發重設）
        self.state_machine.step()
        self.assertFalse(self.state_machine.bread_window_opened)
        self.assertEqual(self.state_machine.bread_window_missing_count, 0)

    @patch('os.path.exists')
    def test_diamond_collection_window_missing_self_healing(self, mock_exists):
        """
        測試領鑽石視窗自癒機制：
        1. diamond_window_opened = True，但畫面上找不到退出按鈕 quit.png。
        2. 預期：連續 3 幀未偵測到退出按鈕後，自動將 diamond_window_opened 重設為 False，以利下一輪重新打開。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.need_diamond_collection = True
        self.state_machine.diamond_window_opened = True
        self.state_machine.diamond_window_missing_count = 0
        self.state_machine.current_state = self.state_machine.STATE_DIAMOND_COLLECTION
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 800, "height": 600}
        
        # 模擬比對結果：所有模板都匹配不到 (None)
        self.mock_matcher.match.return_value = (None, 0.0)
        
        # 第一幀
        self.state_machine.step()
        self.assertTrue(self.state_machine.diamond_window_opened)
        self.assertEqual(self.state_machine.diamond_window_missing_count, 1)
        
        # 第二幀
        self.state_machine.step()
        self.assertTrue(self.state_machine.diamond_window_opened)
        self.assertEqual(self.state_machine.diamond_window_missing_count, 2)
        
        # 第三幀（應觸發重設）
        self.state_machine.step()
        self.assertFalse(self.state_machine.diamond_window_opened)
        self.assertEqual(self.state_machine.diamond_window_missing_count, 0)

    @patch('os.path.exists')
    def test_stamina_insufficient_retreat_and_restoration(self, mock_exists):
        """
        測試體力不足退避與定時恢復機制：
        1. 觸發體力不足時，應備份原始配置並設定開始時間。
        2. 當在 COLLECT_ONLY 狀態下，若未滿設定時間，維持 COLLECT_ONLY。
        3. 若時間已滿，自動還原原始配置，重置時間，並轉移至 STATE_UNKNOWN 以重新尋路。
        """
        # 設定原始配置為史萊姆地下城
        orig_config = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.config = orig_config
        self.state_machine.current_state = self.state_machine.STATE_LOBBY
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 100, "top": 100, "width": 1000, "height": 800}
        
        # 1. 模擬偵測到 no_bread.png，觸發體力不足
        def mock_match_nobread(img, name, threshold):
            if name == "no_bread/no_bread.png":
                return ((150, 250), 0.9)
            elif name == "no_bread/cancel.png":
                return ((150, 250), 0.9)
            elif name == "common/quit.png":
                return (None, 0.0)
            elif name == "goback_town.png":
                return ((50, 450), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = mock_match_nobread
        
        with patch('states.stamina_flow.time.sleep') as mock_sleep:
            self.state_machine.step()
            
        # 驗證 original_config 與 stamina_retreat_start_time 已設定
        self.assertEqual(self.state_machine.original_config, orig_config)
        self.assertIsNotNone(self.state_machine.stamina_retreat_start_time)
        self.assertEqual(self.state_machine.config["type"], "collect_only")
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)
        
        # 2. 模擬處於 COLLECT_ONLY，時間未到 4.0 小時
        # 預期：維持 COLLECT_ONLY
        self.mock_matcher.match.side_effect = None
        self.mock_matcher.match.return_value = (None, 0.0) # 模擬無領取鑽石/體力需求
        
        # 暫時設定 retreat_duration 為 4.0 小時，並模擬只過了 1.0 小時
        self.state_machine.config["stamina_retreat_duration"] = 4.0
        self.state_machine.stamina_retreat_start_time = time.time() - 3600.0
        
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)
        self.assertEqual(self.state_machine.config["type"], "collect_only")
        
        # 3. 模擬時間已滿 4.0 小時 (例如已過 4.1 小時)
        # 預期：恢復為 orig_config，時間清空，轉移至 STATE_UNKNOWN
        self.state_machine.stamina_retreat_start_time = time.time() - (4.1 * 3600.0)
        
        self.state_machine.step()
        self.assertEqual(self.state_machine.config, orig_config)
        self.assertIsNone(self.state_machine.original_config)
        self.assertIsNone(self.state_machine.stamina_retreat_start_time)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)

    @patch('os.path.exists')
    def test_auto_resume_dungeon_during_stamina_retreat(self, mock_exists):
        """
        測試體力退避期間，若地下城冷卻結束，自動切回地下城，且退避起點時間戳絕不被重置。
        """
        mock_exists.return_value = True
        orig_config = GAME_CONFIGS["mix"].copy()
        orig_config["auto_resume_dungeon_on_cd"] = True
        
        self.state_machine.config = orig_config
        self.state_machine.original_config = orig_config
        initial_retreat_start = time.time() - 1800.0 # 已經退避 0.5 小時
        self.state_machine.stamina_retreat_start_time = initial_retreat_start
        self.state_machine.config = GAME_CONFIGS["collect_only"].copy()
        self.state_machine.current_state = self.state_machine.STATE_COLLECT_ONLY
        self.state_machine.need_diamond_collection = False
        self.state_machine.need_bread_collection = False
        
        # 模擬地下城冷卻已結束 (dungeon 0 可刷)
        num_dungeons = len(orig_config.get("dungeon_entries", []))
        self.state_machine.dungeon_cooldowns = {i: 9999.0 for i in range(num_dungeons)}
        self.state_machine.dungeon_cooldowns[0] = 0.0
        self.state_machine.last_state_change = time.time() - 1.0
        self.mock_matcher.match.return_value = (None, 0.0)
        
        self.state_machine.step()
        
        # 預期：動態偵測到地下城冷卻結束，恢復配置為 orig_config，並轉移至 STATE_UNKNOWN
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)
        self.assertEqual(self.state_machine.config, orig_config)
        # 斷言：original_config 與 initial_retreat_start 絕不被重置清空！
        self.assertEqual(self.state_machine.original_config, orig_config)
        self.assertEqual(self.state_machine.stamina_retreat_start_time, initial_retreat_start)

    @patch('os.path.exists')
    def test_auto_resume_dungeon_disabled_stays_in_collect_only(self, mock_exists):
        """
        測試當 auto_resume_dungeon_on_cd 設定為 False 時：
        即使體力退避期間地下城冷卻結束，也絕不提前切回地下城，維持純定時領取直到滿 4 小時。
        """
        mock_exists.return_value = True
        orig_config = GAME_CONFIGS["dungeon"].copy()
        orig_config["auto_resume_dungeon_on_cd"] = False  # 關閉冷卻結束自動復歸
        
        t0 = time.time() - 1800.0  # 已退避 0.5 小時
        self.state_machine.original_config = orig_config
        self.state_machine.stamina_retreat_start_time = t0
        self.state_machine.config = GAME_CONFIGS["collect_only"].copy()
        self.state_machine.config["stamina_retreat_duration"] = 4.0
        self.state_machine.current_state = self.state_machine.STATE_COLLECT_ONLY
        self.state_machine.need_diamond_collection = False
        self.state_machine.need_bread_collection = False
        
        # 模擬地下城 0 冷卻已結束 (0.0)
        self.state_machine.dungeon_cooldowns = {0: 0.0, 1: 9999.0, 2: 9999.0, 3: 9999.0, 4: 9999.0}
        self.mock_matcher.match.return_value = (None, 0.0)
        
        self.state_machine.step()
        
        # 斷言 1：因 auto_resume_dungeon_on_cd == False，即便冷卻結束也維持在 STATE_COLLECT_ONLY 待機！
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)
        self.assertEqual(self.state_machine.config["type"], "collect_only")
        self.assertEqual(self.state_machine.original_config, orig_config)
        
        # 模擬退避滿 4.0 小時
        self.state_machine.stamina_retreat_start_time = time.time() - (4.1 * 3600.0)
        self.state_machine.step()
        
        # 斷言 2：滿 4 小時後，順利恢復原配置 orig_config 並離場
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)
        self.assertEqual(self.state_machine.config, orig_config)
        self.assertIsNone(self.state_machine.original_config)
        self.assertIsNone(self.state_machine.stamina_retreat_start_time)

    @patch('os.path.exists')
    def test_diamond_cooldown_ocr_detection(self, mock_exists):
        """
        測試領鑽石流程中，當偵測到冷卻（無免費按鈕）時，藉由 OCR 讀取時間並精確推遲下一次觸發。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.current_state = self.state_machine.STATE_DIAMOND_COLLECTION
        self.state_machine.diamond_window_opened = True
        self.state_machine.diamond_collected_this_run = False
        self.state_machine.diamond_cooldown_confirm_count = 2 # 下一次會是 3 ➔ 觸發 OCR
        self.state_machine.last_diamond_collection_time = 0.0
        
        import numpy as np
        self.mock_capturer.capture.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        mock_exists.return_value = True
        
        # 模擬 match_side_effect
        def mock_match_impl(img, name, threshold=None, **kwargs):
            if name == "common/quit.png":
                # 退出按鈕在 (1638, 235)
                return (1638, 235), 0.95
            # 找不到 free.png 及其它
            return None, 0.0
            
        self.mock_matcher.match.side_effect = mock_match_impl
        
        # Mock OCR reader
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [[None, "00:18:43", 0.99]]
        self.state_machine.get_ocr_reader = MagicMock(return_value=mock_reader)
        
        # Mock cv2.imread 與 cv2.imwrite
        dummy_img = np.zeros((10, 10, 3), dtype=np.uint8)
        with patch('cv2.imread', return_value=dummy_img), \
             patch('cv2.imwrite') as mock_write:
            self.state_machine.step()
            
        # 驗證 1: 標記冷卻中應為 True
        self.assertTrue(self.state_machine.diamond_cooldown_detected)
        self.assertTrue(self.state_machine.diamond_ocr_success)
        # 驗證 2: last_diamond_collection_time 應被寫入，且約為未來 1123 秒 (00:18:43 = 1123s) 再次觸發
        # 預設 CD 為 7200 秒，7200 - 1123 = 6077 秒前，所以 time.time() - 6077 左右
        saved_cd_time = self.state_machine.last_diamond_collection_time
        expected_time_diff = time.time() - saved_cd_time
        # 這個差值應該在 7200 - 1123 = 6077 秒左右 (容差 10 秒)
        self.assertAlmostEqual(expected_time_diff, 6077.0, delta=10.0)

        # 3. 模擬下一幀：點選退出後退出按鈕消失（quit.png 匹配失敗），視窗成功關閉
        self.mock_matcher.match.side_effect = lambda img, name, threshold=None, **kwargs: (None, 0.0)
        self.state_machine.step()

        # 驗證 4: 視窗成功關閉，所有狀態重置，且 last_diamond_collection_time 依然保留為先前計算的時間 (並未被 time.time() 覆蓋)
        self.assertFalse(self.state_machine.diamond_window_opened)
        self.assertFalse(self.state_machine.diamond_ocr_success)
        self.assertEqual(self.state_machine.last_diamond_collection_time, saved_cd_time)

    @patch('os.path.exists')
    def test_collect_only_navigation_returns_to_town_instead_of_lobby(self, mock_exists):
        """
        測試當在 collect_only 模式下處於 NAVIGATING 狀態時：
        看見 goback_town.png 應自動點擊返回城鎮並切換至 STATE_COLLECT_ONLY，絕不誤切至 STATE_LOBBY。
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["collect_only"].copy()
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        
        def mock_match(img, tpl, threshold=0.8, quiet=False):
            if tpl == "goback_town.png":
                return (72, 757), 0.92
            return None, 0.0

        self.mock_matcher.match.side_effect = mock_match
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        self.state_machine.step()

        self.mock_mouse.click.assert_called_with(72, 757)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)


if __name__ == "__main__":
    unittest.main()
