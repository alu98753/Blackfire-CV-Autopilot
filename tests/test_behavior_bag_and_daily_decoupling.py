import unittest
import numpy as np
from unittest.mock import MagicMock, patch

from states.state_machine import GameStateMachine
from states.town_subflow_registry import TOWN_SUBFLOW_SPECS
from states.handlers.bulletin_board import BulletinBoardHandler
from states.handlers.navigation import NavigationHandler
from states.handlers.jewelry_workshop import JewelryWorkshopHandler


class TestBehaviorBagAndDailyDecoupling(unittest.TestCase):
    """
    背包維護與每日子流程解耦之行為測試集 (Google Software Engineering Standard)
    專注於驗證解耦契約、覆蓋層門禁以及排他性正交特徵錨點
    """

    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.STATE_NAVIGATING = "NAVIGATING"
        self.mock_machine.STATE_BLOOD_ALTAR = "BLOOD_ALTAR"
        self.mock_machine.STATE_JEWELRY_WORKSHOP = "JEWELRY_WORKSHOP"
        self.mock_machine.need_bag_cleaning = False
        self.mock_machine.config = {
            "bag_maintenance_order": ["blood_sacrifice", "jewelry_workshop"],
            "building_btn": "town_building/bulletin_board/bulletin_board.png",
            "reset_btn": "town_building/bulletin_board/reset.png",
            "quit_btn": "common/quit.png",
            "task_btn": "town_building/bulletin_board/task.png",
            "task_after_btn": "town_building/bulletin_board/task_after.png",
        }
        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        self.fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)

    # =========================================================================
    # 1. 背包清理後專屬維護佇列調度測試
    # =========================================================================

    def test_trigger_bag_maintenance_chain_queues_independent_subflows(self):
        """
        [契約 1 驗證]
        Given: 背包清理完成
        When: 觸發 trigger_bag_maintenance_chain()
        Then: 依據設定僅調度 ["blood_sacrifice", "jewelry_workshop"] 維護佇列，轉移至 NAVIGATING
        """
        machine = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        machine.current_state = machine.STATE_BAG_CLEANING
        machine.config = {"bag_maintenance_order": ["blood_sacrifice", "jewelry_workshop"]}
        machine.start_subflow_queue = MagicMock()
        machine.transition_to = MagicMock()

        machine.trigger_bag_maintenance_chain()

        machine.start_subflow_queue.assert_called_once_with(["blood_sacrifice", "jewelry_workshop"])
        machine.transition_to.assert_called_once_with(machine.STATE_NAVIGATING)

    # =========================================================================
    # 2. blood_sacrifice 領域規格與 daily_status 解耦測試
    # =========================================================================

    def test_blood_sacrifice_spec_and_completion_does_not_pollute_daily(self):
        """
        [契約 2 驗證]
        Given: blood_sacrifice 子流程規格
        Then: 1. requires_red_dot 必須為 False（不檢查紅點）
              2. 映射狀態為 STATE_BLOOD_ALTAR
              3. 完成 blood_sacrifice 時絕不寫入 DailyManager 的 daily completed 紀錄
        """
        self.assertIn("blood_sacrifice", TOWN_SUBFLOW_SPECS)
        spec = TOWN_SUBFLOW_SPECS["blood_sacrifice"]
        self.assertFalse(spec.requires_red_dot, "blood_sacrifice 絕不可要求檢查紅點！")

        machine = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        self.assertEqual(machine.state_for_town_subflow("blood_sacrifice"), machine.STATE_BLOOD_ALTAR)

        # 驗證完成時不污染 daily_status
        machine.current_town_subflow = "blood_sacrifice"
        machine.daily_manager = MagicMock()
        machine.transition_to = MagicMock()

        machine.complete_current_town_subflow()

        machine.daily_manager.record_subflow_completed.assert_not_called()

    # =========================================================================
    # 3. 告示牌在背包殘留 quit.png 時的排他性錨點防護測試
    # =========================================================================

    def test_bulletin_board_with_backpack_overlay_does_not_swallow_quests(self):
        """
        [契約 3 驗證 / bag_bug.md 根治]
        Given: 城鎮畫面上殘留未關閉的背包，此時看得到 quit.png 與 tidy.png，但非告示牌
        When: BulletinBoardHandler.handle() 執行
        Then: 1. 排他性檢查 _is_inside_bulletin_board 必須判定為 False
              2. 絕不可推進至 CHECK_RESET 或 PROCESS_ACCEPT_QUESTS
              3. 絕不可觸發 _record_completion 吞噬任務
              4. 點擊 quit.png 關閉干擾覆蓋層
        """
        handler = BulletinBoardHandler(self.mock_machine)
        handler.matcher = MagicMock()
        handler.mouse = MagicMock()
        handler.last_action_time = 0.0

        def mock_match(img, tpl, **kw):
            if tpl == "common/quit.png":
                return ((1400, 150), 0.92)
            if tpl == "common/tidy.png":
                return ((1200, 800), 0.90)
            if tpl == "common/door.png":
                return ((100, 500), 0.88)
            # 告示牌內部專屬特徵皆無
            return (None, 0.0)

        handler.matcher.match.side_effect = mock_match

        # 1. 斷言排他性檢查判定為 False
        self.assertFalse(handler._is_inside_bulletin_board(self.fake_img, self.mock_machine.config))

        # 2. 執行 handle (閉環消除覆蓋層)
        handler._record_completion = MagicMock()
        with patch.object(handler, "click_and_wait_until_gone") as mock_wait_gone:
            handler.handle(self.fake_img, self.rect)
            # 3. 斷言未標記完成且未推進到領取階段
            handler._record_completion.assert_not_called()
            self.assertNotEqual(handler.step_phase, "PROCESS_ACCEPT_QUESTS")
            # 4. 斷言發起閉環點擊關閉按鈕以自癒消除覆蓋層
            mock_wait_gone.assert_called_once_with("common/quit.png", 1400, 150, self.rect, timeout=3.0, threshold=0.80)

    # =========================================================================
    # 4. 導航層在城門遇背包覆蓋層時的攔截門禁測試
    # =========================================================================

    def test_navigation_overlay_gate_blocks_blind_door_click(self):
        """
        [契約 4 驗證 / bag_jewelry_workshop_bug.md 根治]
        Given: 導航路徑包含 common/door.png，但前景同時存在未關閉背包 (tidy.png / quit.png)
        When: NavigationHandler.handle() 執行
        Then: 優先點擊 quit.png 消除覆蓋層，絕不盲目點擊城門造成無效點擊逾時
        """
        handler = NavigationHandler(self.mock_machine)
        handler.matcher = MagicMock()
        handler.mouse = MagicMock()

        scene_mock = MagicMock()
        scene_mock.scene_type = "UNKNOWN"
        scene_mock.is_lobby = False
        scene_mock.active_tabs = set()
        scene_mock.matched_elements = {}
        handler.scene_detector = MagicMock()
        handler.scene_detector.matcher = handler.matcher
        handler.scene_detector.detect.return_value = scene_mock

        def mock_match(img, tpl, **kw):
            if tpl == "common/door.png":
                return ((80, 520), 0.94)
            if tpl == "common/quit.png":
                return ((1400, 150), 0.91)
            if tpl == "common/tidy.png":
                return ((1200, 800), 0.90)
            return (None, 0.0)

        handler.matcher.match.side_effect = mock_match

        self.mock_machine.config = {
            "type": "stage",
            "navigation_path": ["common/door.png", "stages/stage_label.png"]
        }

        with patch('states.handlers.navigation.time.sleep'), \
             patch('states.handlers.navigation.NavigationDecisionExecutor.execute', return_value=False):
            handler.handle(self.fake_img, self.rect)

        # 斷言點擊了 quit.png (1400, 150)，而絕非 door.png (80, 520)
        handler.mouse.click.assert_called_once_with(1400, 150)

    # =========================================================================
    # 5. 珠寶店 Pre-Tidy 子流程與 Scene Guard 邊緣防護測試
    # =========================================================================

    def test_jewelry_workshop_scene_guard_does_not_abort_before_shop_entry(self):
        """
        [契約 5 驗證]
        Given: 珠寶店在城鎮過渡階段 (ENTERED_BUILDING 或 SEEK_AND_ENTER_SHOP)，畫面邊緣看到 door.png
        When: JewelryWorkshopHandler.handle() 執行
        Then: 絕不可觸發 Scene Guard 逃逸
        """
        handler = JewelryWorkshopHandler(self.mock_machine)
        handler.matcher = MagicMock()
        handler.mouse = MagicMock()
        handler.step_phase = "ENTERED_BUILDING"
        handler.entered_building_time = 0.0

        def mock_match(img, tpl, **kw):
            if tpl == "common/door.png":
                return ((80, 520), 0.94)
            return (None, 0.0)

        handler.matcher.match.side_effect = mock_match

        handler.handle(self.fake_img, self.rect)

        # 斷言未中途退出或調用 pop_and_next_town_subflow
        self.mock_machine.pop_and_next_town_subflow.assert_not_called()
