import os
import shutil
import unittest
import numpy as np
from unittest.mock import MagicMock, patch

from states.state_machine import GameStateMachine
from states.handlers.demon_lords import DemonLordsHandler, DemonSubScene
from states.handlers.battle import BattleHandler
from states.handlers.result import ResultHandler
from utils.daily_manager import DailyManager
from config import GAME_CONFIGS

class TestDemonLordsSubflow(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join("user_data", "test_demon_lords_data")
        os.makedirs(self.test_dir, exist_ok=True)
        self.daily_manager = DailyManager(data_dir=self.test_dir)

        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_matcher.match_mutually_exclusive_tabs.return_value = (False, False, 0.0, 0.0)
        self.mock_matcher.match.return_value = (None, 0.0)
        self.mock_matcher._compute_auto_scale.return_value = 1.0
        self.mock_mouse = MagicMock()

        self.state_machine = GameStateMachine(
            self.mock_capturer,
            self.mock_matcher,
            self.mock_mouse,
            preload_ocr=False
        )
        self.state_machine.daily_manager = self.daily_manager
        self.state_machine.config = GAME_CONFIGS.get("demon_lords", {
            "enabled": True,
            "type": "demon_lords",
            "entry_btn": "demon_lords/demon_lords_entry.png",
            "entry_after_btn": "demon_lords/demon_lords_entry_after.png",
            "start_btn": "stages/start.png",
            "stone_container_btn": "demon_lords/meterial/stone_slot.png",
            "empty_slot_btn": "demon_lords/meterial/slot.png",
            "stone_btn": "demon_lords/meterial/demon_seal_stone_1.png",
            "choose_btn": "common/choose.png",
            "max_daily_count": 3,
            "target_boss": "voidborn_elres",
            "bosses": {
                "voidborn_elres": {
                    "name": "虛空行者厄爾雷斯",
                    "template": "demon_lords/voidborn_elres.png"
                }
            }
        }).copy()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_daily_manager_tracking(self):
        """測試：DailyManager 正確追蹤魔王清單次數 (0/3 -> 1/3 -> 3/3 完成)"""
        avail, msg = self.daily_manager.is_demon_lords_available()
        self.assertTrue(avail)
        self.assertEqual(self.daily_manager.get_available_demon_lords(), ["voidborn_elres"])

        self.daily_manager.record_demon_lords_fight("voidborn_elres")
        avail, msg = self.daily_manager.is_demon_lords_available()
        self.assertTrue(avail)
        self.assertEqual(self.daily_manager.status["subflows"]["demon_lords"]["bosses"]["voidborn_elres"]["today_count"], 1)

        self.daily_manager.record_demon_lords_fight("voidborn_elres")
        self.daily_manager.record_demon_lords_fight("voidborn_elres")
        avail, msg = self.daily_manager.is_demon_lords_available()
        self.assertFalse(avail)
        self.assertEqual(self.daily_manager.get_available_demon_lords(), [])
        self.assertTrue(self.daily_manager.is_subflow_completed("demon_lords"))

    @patch("os.path.exists", return_value=True)
    def test_lobby_navigation(self, _mock_exists):
        """測試：未進入魔王頁籤時，先點門或點擊魔王入口按鈕"""
        handler = DemonLordsHandler(self.state_machine)
        dummy_screen = np.zeros((800, 1000, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        # 1. 互斥頁籤未開啟，在城鎮比對到 door.png
        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (False, False, 0.5, 0.5)
        self.state_machine.matcher.match.side_effect = lambda img, temp, **kw: ((500, 300), 0.90) if temp == "common/door.png" else (None, 0.0)

        ret = handler.handle(dummy_screen, rect)
        self.assertTrue(ret)
        self.mock_mouse.click.assert_called_with(500, 300)

        # 2. 互斥頁籤未開啟，在大廳比對到 demon_lords_entry.png
        self.mock_mouse.reset_mock()
        self.state_machine.matcher.match.side_effect = lambda img, temp, **kw: ((600, 400), 0.90) if temp == "demon_lords/demon_lords_entry.png" else (None, 0.0)

        ret = handler.handle(dummy_screen, rect)
        self.assertTrue(ret)
        self.mock_mouse.click.assert_called_with(600, 400)

    @patch("os.path.exists", return_value=True)
    def test_select_boss_card(self, _mock_exists):
        """測試：進入魔王頁籤後，比對並點擊目標魔王卡片 (voidborn_elres)"""
        handler = DemonLordsHandler(self.state_machine)
        dummy_screen = np.zeros((800, 1000, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        # 頁籤已開啟
        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (True, False, 0.95, 0.4)
        def fake_match(img, temp, **kw):
            if temp == "demon_lords/voidborn_elres.png":
                return ((300, 400), 0.92)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = fake_match

        ret = handler.handle(dummy_screen, rect)
        self.assertTrue(ret)
        self.mock_mouse.click.assert_called_with(300, 400)
        self.assertEqual(handler.current_target_boss, "voidborn_elres")

    @patch("states.handlers.demon_lords.time.sleep")
    @patch("os.path.exists", return_value=True)
    def test_missing_demon_lord_card_resets_to_left(self, _mock_exists, _mock_sleep):
        handler = DemonLordsHandler(self.state_machine)
        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (
            True,
            False,
            0.95,
            0.4,
        )
        self.state_machine.matcher.match.return_value = (None, 0.0)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        handled = handler.handle(np.zeros((800, 1000, 3), dtype=np.uint8), rect)

        self.assertTrue(handled)
        self.mock_mouse.drag.assert_called_once_with(
            200, 400, 800, 400, duration=0.8, inertia=False
        )
        self.assertEqual(handler.card_reset_attempts, 1)

    @patch("states.handlers.demon_lords.time.sleep")
    @patch("os.path.exists", return_value=True)
    def test_demon_lord_reset_limit_relaunches(self, _mock_exists, _mock_sleep):
        handler = DemonLordsHandler(self.state_machine)
        handler.card_reset_attempts = 7
        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (
            True,
            False,
            0.95,
            0.4,
        )
        self.state_machine.matcher.match.return_value = (None, 0.0)
        self.state_machine.request_relaunch = MagicMock()
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        handled = handler.handle(np.zeros((800, 1000, 3), dtype=np.uint8), rect)

        self.assertTrue(handled)
        self.mock_mouse.drag.assert_not_called()
        self.state_machine.request_relaunch.assert_called_once_with(
            "demon_lord_card_alignment_failed"
        )

    @patch("os.path.exists", return_value=True)
    def test_slot_filling_and_scoped_stone_selection(self, _mock_exists):
        """測試：點擊空插槽 (slot.png) 觸發選石，且 Scoped ROI 僅在左半邊比對封印石"""
        handler = DemonLordsHandler(self.state_machine)
        dummy_screen = np.zeros((800, 1000, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        # 1. 發現空插槽 slot.png，點擊插槽
        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (True, False, 0.95, 0.4)
        def match_slot(img, temp, **kw):
            if temp == "demon_lords/meterial/slot.png":
                return ((450, 350), 0.90)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = match_slot

        ret = handler.handle(dummy_screen, rect)
        self.assertTrue(ret)
        self.mock_mouse.click.assert_called_with(450, 350)

        # 2. 處於 STONE_DIALOG 階段，比對封印石 (左半邊) 與 choose.png
        self.mock_mouse.reset_mock()
        stone_matched_shape = []

        def match_choose_dialog(img, temp, **kw):
            if temp == "demon_lords/meterial/demon_seal_stone_2.png":
                stone_matched_shape.append(img.shape)
                return ((200, 300), 0.90)
            if temp == "common/choose.png":
                return ((700, 600), 0.90)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = match_choose_dialog

        ret = handler.handle(dummy_screen, rect)
        self.assertTrue(ret)
        # 斷言：封印石比對傳入的影像寬度必須是 500 (1000 的一半，Scoped ROI 生效)
        self.assertEqual(len(stone_matched_shape), 1)
        self.assertEqual(stone_matched_shape[0][1], 500)
        # 斷言：點擊封印石 (200, 300) 與確認 (700, 600)
        self.assertEqual(self.mock_mouse.click.call_count, 2)

    @patch("time.sleep")
    @patch("os.path.exists", return_value=True)
    def test_launch_battle_when_all_slots_full(self, _mock_exists, _mock_sleep):
        """測試：無空插槽時點擊 start.png，驗證進場特徵並轉移至 STATE_BATTLE"""
        handler = DemonLordsHandler(self.state_machine)
        handler.current_target_boss = "voidborn_elres"
        dummy_screen = np.zeros((800, 1000, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (True, False, 0.95, 0.4)
        def match_start(img, temp, **kw):
            if temp == "stages/start.png":
                return ((800, 700), 0.92)
            if temp == "demon_lords/meterial/stone_slot.png":
                return ((500, 300), 0.90)
            if temp == "battle/battle_features_1.png":
                return ((100, 100), 0.95)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = match_start
        self.mock_capturer.capture.return_value = dummy_screen

        ret = handler.handle(dummy_screen, rect)
        self.assertTrue(ret)
        self.mock_mouse.click.assert_called_with(800, 700)
        self.assertTrue(handler.launch_pending)

        # 第二 Tick：觀察到進入戰鬥特徵，狀態機完成後驗證進入 STATE_BATTLE
        ret2 = handler.handle(dummy_screen, rect)
        self.assertTrue(ret2)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)
        self.assertEqual(self.state_machine.current_demon_lord_key, "voidborn_elres")

    @patch("os.path.exists", return_value=True)
    def test_result_commit_demon_lords(self, _mock_exists):
        """測試：結算畫面偵測到 demon_lords_entry_after 時，commit 次數並返回 STATE_DEMON_LORDS"""
        result_handler = ResultHandler(self.state_machine)
        self.state_machine.current_demon_lord_key = "voidborn_elres"
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        dummy_screen = np.zeros((800, 1000, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        def match_res(img, temp, **kw):
            if temp == "demon_lords/demon_lords_entry_after.png":
                return ((500, 500), 0.95)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = match_res

        matched = result_handler._handle_impl(dummy_screen, rect)
        self.assertTrue(matched)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DEMON_LORDS)
        self.assertIsNone(self.state_machine.current_demon_lord_key)
        self.assertEqual(self.daily_manager.status["subflows"]["demon_lords"]["today_count"], 1)

    def test_completed_today_pops_subflow(self):
        """測試：今日打滿 3 次後，呼叫 pop_and_next_town_subflow() 結束子流程"""
        self.daily_manager.status["subflows"]["demon_lords"]["today_count"] = 3
        self.daily_manager.status["subflows"]["demon_lords"]["completed_today"] = True
        self.state_machine.pop_and_next_town_subflow = MagicMock()

        handler = DemonLordsHandler(self.state_machine)
        dummy_screen = np.zeros((800, 1000, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        ret = handler.handle(dummy_screen, rect)
        self.assertTrue(ret)
        self.state_machine.pop_and_next_town_subflow.assert_called_once()

    @patch("os.path.exists", return_value=True)
    def test_slot_click_when_tab_obscured_by_modal_popup(self, _mock_exists):
        """測試：當點開卡片後頁籤被彈窗遮蔽 (match_mutually_exclusive_tabs 為 False)，依然優先精確點擊 slot.png"""
        handler = DemonLordsHandler(self.state_machine)
        dummy_screen = np.zeros((800, 1000, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        # 頁籤被彈窗遮蔽 (False)
        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (False, False, 0.4, 0.4)
        def match_in_popup(img, temp, **kw):
            if temp == "demon_lords/meterial/stone_slot.png":
                return ((500, 300), 0.95)
            if temp == "demon_lords/meterial/slot.png":
                return ((219, 98), 0.95)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = match_in_popup

        ret = handler.handle(dummy_screen, rect)
        self.assertTrue(ret)
        self.assertTrue(self.mock_mouse.click.called)

    @patch("os.path.exists", return_value=True)
    def test_scene_classifier_pure_perception(self, _mock_exists):
        """測試 Greenfield-lite v1：classify_subscene 純感知分類器的場景排他定性"""
        handler = DemonLordsHandler(self.state_machine)
        dummy_screen = np.zeros((800, 1000, 3), dtype=np.uint8)

        # 1. 見到大門 (TOWN 錨點) 優先：即使有 0.76 的噪點亦絕對判定為 TOWN
        def match_town_with_noise(img, temp, **kw):
            if temp == "common/door.png":
                return ((500, 300), 0.90)
            if temp == "common/choose.png":
                return ((800, 700), 0.76)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = match_town_with_noise
        self.assertEqual(handler.classify_subscene(dummy_screen), DemonSubScene.TOWN)

        # 2. 非城鎮畫面：choose.png 只有在 >= 0.90 時才判定為 STONE_DIALOG (0.76 應被過濾)
        def mock_choose_match(img, temp, **kw):
            thresh = kw.get("threshold", 0.7)
            if temp == "common/choose.png":
                # 模擬 0.76 相似度：若 threshold 設為 0.90 則應回傳 (None, 0.0)
                return ((700, 600), 0.76) if 0.76 >= thresh else (None, 0.0)
            return (None, 0.0)

        self.state_machine.matcher.match.side_effect = mock_choose_match
        self.assertEqual(handler.classify_subscene(dummy_screen), DemonSubScene.UNKNOWN)

        # 模擬 0.96 相似度 (真實選石時)：大於 0.90，判定為 STONE_DIALOG
        def mock_choose_high(img, temp, **kw):
            thresh = kw.get("threshold", 0.7)
            if temp == "common/choose.png":
                return ((700, 600), 0.96) if 0.96 >= thresh else (None, 0.0)
            return (None, 0.0)

        self.state_machine.matcher.match.side_effect = mock_choose_high
        self.assertEqual(handler.classify_subscene(dummy_screen), DemonSubScene.STONE_DIALOG)

        # 3. 見到 stone_slot.png -> PREPARE_MODAL
        self.state_machine.matcher.match.side_effect = lambda img, temp, **kw: ((500, 300), 0.9) if temp == "demon_lords/meterial/stone_slot.png" else (None, 0.0)
        self.assertEqual(handler.classify_subscene(dummy_screen), DemonSubScene.PREPARE_MODAL)

        # 4. 互斥頁籤開啟 -> CARD_SELECTION
        self.state_machine.matcher.match.side_effect = lambda img, temp, **kw: (None, 0.0)
        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (True, False, 0.9, 0.3)
        self.assertEqual(handler.classify_subscene(dummy_screen), DemonSubScene.CARD_SELECTION)

        # 5. 頁籤未開啟但見到魔王入口 -> LOBBY_OTHER_TAB
        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (False, False, 0.3, 0.3)
        self.state_machine.matcher.match.side_effect = lambda img, temp, **kw: ((600, 400), 0.9) if temp == "demon_lords/demon_lords_entry.png" else (None, 0.0)
        self.assertEqual(handler.classify_subscene(dummy_screen), DemonSubScene.LOBBY_OTHER_TAB)

    @patch("os.path.exists", return_value=True)
    def test_stone_plan_queue_and_sequential_selection(self, _mock_exists):
        """測試：依據 TOML stone_selection 字典正確展開計畫佇列，並依序選取 2 階與 1 階封印石"""
        handler = DemonLordsHandler(self.state_machine)
        self.state_machine.config["stone_selection"] = {"2": 1, "1": 2}

        # 1. 驗證展開佇列為 1 個 2 階 + 2 個 1 階 (高階優先)
        queue = handler._build_stone_plan_queue()
        self.assertEqual(queue, ["2", "1", "1"])

        # 2. 第一次選取：目標為 2 階石
        dummy_screen = np.zeros((800, 1000, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}
        handler.pending_stone_queue = ["2", "1", "1"]

        selected_templates = []
        def match_dialog_1(img, temp, **kw):
            if temp == "demon_lords/meterial/demon_seal_stone_2.png":
                selected_templates.append(temp)
                return ((200, 300), 0.92)
            if temp == "common/choose.png":
                return ((700, 600), 0.90)
            return (None, 0.0)

        self.state_machine.matcher.match.side_effect = match_dialog_1
        ret = handler.handle(dummy_screen, rect)
        self.assertTrue(ret)
        self.assertIn("demon_lords/meterial/demon_seal_stone_2.png", selected_templates)
        # 佇列彈出 2 階，剩餘 2 個 1 階
        self.assertEqual(handler.pending_stone_queue, ["1", "1"])

        # 3. 第二次選取：目標為 1 階石
        selected_templates.clear()
        def match_dialog_2(img, temp, **kw):
            if temp == "demon_lords/meterial/demon_seal_stone_1.png":
                selected_templates.append(temp)
                return ((200, 300), 0.92)
            if temp == "common/choose.png":
                return ((700, 600), 0.90)
            return (None, 0.0)

        self.state_machine.matcher.match.side_effect = match_dialog_2
        ret = handler.handle(dummy_screen, rect)
        self.assertTrue(ret)
        self.assertIn("demon_lords/meterial/demon_seal_stone_1.png", selected_templates)
        self.assertEqual(handler.pending_stone_queue, ["1"])

    @patch("time.sleep")
    @patch("os.path.exists", return_value=True)
    def test_three_stones_completed_launches_battle_without_reinit(self, _mock_exists, _mock_sleep):
        """測試：當 3 顆石頭鑲嵌完畢後，絕不重新初始化鑲嵌計畫，而是直接點擊 start 進入戰鬥"""
        handler = DemonLordsHandler(self.state_machine)
        handler.current_target_boss = "voidborn_elres"
        dummy_screen = np.zeros((800, 1000, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        # 1. 模擬最後一顆石頭 (1 階) 在 STONE_DIALOG 中被點選並確認
        handler.pending_stone_queue = ["1"]
        handler.stone_insert_completed = False

        def match_choose(img, temp, **kw):
            if temp == "demon_lords/meterial/demon_seal_stone_1.png":
                return ((200, 300), 0.92)
            if temp == "common/choose.png":
                return ((700, 600), 0.95)
            return (None, 0.0)

        self.state_machine.matcher.match.side_effect = match_choose
        ret = handler.handle(dummy_screen, rect)
        self.assertTrue(ret)
        self.assertEqual(handler.pending_stone_queue, [])
        self.assertTrue(handler.stone_insert_completed)

        # 2. 回到 PREPARE_MODAL：畫面上即便有低相似度雜訊，也絕不誤判點擊 slot 或重製 queue
        def match_modal(img, temp, **kw):
            if temp == "demon_lords/meterial/stone_slot.png":
                return ((500, 300), 0.90)
            if temp == "stages/start.png":
                return ((800, 700), 0.95)
            if temp == "battle/battle_features_1.png":
                return ((100, 100), 0.95)
            return (None, 0.0)

        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (True, False, 0.95, 0.4)
        self.state_machine.matcher.match.side_effect = match_modal
        self.mock_capturer.capture.return_value = dummy_screen

        ret = handler.handle(dummy_screen, rect)
        self.assertTrue(ret)
        # 斷言：點擊的是開始戰鬥按鈕 (800, 700)
        self.mock_mouse.click.assert_called_with(800, 700)
        self.assertTrue(handler.launch_pending)

        # 第二 Tick：觀察到進入戰鬥特徵，狀態機完成後驗證進入 STATE_BATTLE
        ret2 = handler.handle(dummy_screen, rect)
        self.assertTrue(ret2)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)
        # 斷言：未被重新初始化成 ['2', '1', '1']
        self.assertIsNone(handler.pending_stone_queue)

    @patch("os.path.exists", return_value=True)
    def test_slot_no_reaction_exhausted_exits_to_navigating(self, _mock_exists):
        """測試：當連續 2 次點擊插槽無反應時，自動標記當前魔王完成，點擊 quit 退出並轉移至 NAVIGATING"""
        handler = DemonLordsHandler(self.state_machine)
        handler.current_target_boss = "voidborn_elres"
        handler.slot_no_reaction_count = 2
        dummy_screen = np.zeros((800, 1000, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        def match_modal(img, temp, **kw):
            if temp == "demon_lords/meterial/stone_slot.png":
                return ((500, 300), 0.90)
            if temp == "demon_lords/meterial/slot.png":
                return ((400, 300), 0.90)
            if temp == "common/quit.png":
                return ((900, 100), 0.95)
            return (None, 0.0)

        self.state_machine.pop_and_next_town_subflow = MagicMock()
        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (True, False, 0.90, 0.4)
        self.state_machine.matcher.match.side_effect = match_modal

        ret = handler.handle(dummy_screen, rect)
        self.assertTrue(ret)
        # 斷言：點擊 quit.png 退出彈窗
        self.mock_mouse.click.assert_called_with(900, 100)
        # 斷言：魔王已被標記完成
        self.assertTrue(self.daily_manager.status["subflows"]["demon_lords"]["bosses"]["voidborn_elres"]["completed_today"])
        # 斷言：呼叫 pop_and_next_town_subflow 推進子流程佇列
        self.state_machine.pop_and_next_town_subflow.assert_called_once()

    @patch("os.path.exists", return_value=True)
    def test_battle_transitions_to_result_for_demon_lords(self, _mock_exists):
        """測試：在深淵魔王戰鬥中，畫面上出現 continue.png 時，BattleHandler 能成功轉移至 STATE_RESULT"""
        battle_handler = BattleHandler(self.state_machine)
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        self.state_machine.current_demon_lord_key = "voidborn_elres"
        self.state_machine.battle_session.clear()

        self.state_machine.config = {"type": "demon_lords"}

        def match_battle(img, temp, **kw):
            if temp == "common/continue.png":
                return ((640, 500), 0.95)
            return (None, 0.0)

        self.state_machine.matcher.match.side_effect = match_battle
        dummy_screen = np.zeros((800, 1000, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        battle_handler.handle(dummy_screen, rect)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_RESULT)
        self.assertFalse(self.state_machine.is_in_dungeon)

    @patch("os.path.exists", return_value=True)
    def test_result_final_match_exit_commits_demon_lords(self, _mock_exists):
        """測試：ResultHandler 在 FINAL_MATCH 離場時能正確提交 demon_lords 並轉移回 STATE_DEMON_LORDS"""
        result_handler = ResultHandler(self.state_machine)
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        self.state_machine.current_demon_lord_key = "voidborn_elres"
        result_handler.subflow_step = "FINAL_MATCH"

        def match_result(img, temp, **kw):
            if temp == "goback_town.png":
                return ((100, 700), 0.90)
            return (None, 0.0)

        self.state_machine.matcher.match.side_effect = match_result
        dummy_screen = np.zeros((800, 1000, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        with patch.object(result_handler, "click_and_wait_until_gone") as mock_click:
            ret = result_handler._handle_impl(dummy_screen, rect)
            self.assertTrue(ret)
            mock_click.assert_called_once()

        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DEMON_LORDS)
        self.assertIsNone(self.state_machine.current_demon_lord_key)
        self.assertEqual(
            self.daily_manager.status["subflows"]["demon_lords"]["bosses"]["voidborn_elres"]["today_count"],
            1
        )

    def test_defaults_toml_demon_lords_has_result_buttons(self):
        """測試：defaults.toml 的 subflow_configs.demon_lords 包含 result_buttons 配置"""
        from config import SUBFLOW_CONFIGS
        dl_cfg = SUBFLOW_CONFIGS.get("demon_lords", {})
        self.assertIn("result_buttons", dl_cfg)
        self.assertIn("common/continue.png", dl_cfg["result_buttons"])

