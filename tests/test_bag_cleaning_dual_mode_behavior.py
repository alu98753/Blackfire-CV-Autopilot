import unittest
from unittest.mock import MagicMock, patch
from states.handlers.bag_cleaning import BagCleaningHandler

class TestBagCleaningDualModeBehavior(unittest.TestCase):
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.STATE_DUNGEON_EXPLORING = "DUNGEON_EXPLORING"
        self.mock_machine.STATE_BATTLE = "BATTLE"
        self.mock_machine.STATE_NAVIGATING = "NAVIGATING"
        self.mock_machine.STATE_BAG_CLEANING = "BAG_CLEANING"
        self.mock_machine.bag_opened_clicked = True
        self.mock_machine.config = {}


        self.handler = BagCleaningHandler(self.mock_machine)
        self.handler.matcher = MagicMock()
        self.handler.mouse = MagicMock()

    @patch('os.path.exists', return_value=True)
    def test_bag_cleaning_in_dungeon_mode_defers_town_subflows(self, mock_exists):
        """驗證地下城探索中背包滿清理完畢後，不立即觸發城鎮流水線，而是延遲並切回探索狀態"""
        self.mock_machine.bag_tidied = True
        self.mock_machine.is_in_dungeon = True
        self.mock_machine.previous_state = "DUNGEON_EXPLORING"
        self.mock_machine.config = {"type": "dungeon"}

        def mock_match_quit(img, name, **kw):
            if name == "common/quit.png":
                return ((100, 100), 0.90)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match_quit

        screen_img = MagicMock()
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        with patch('states.handlers.bag_cleaning.time.sleep'):
            self.handler.handle(screen_img, rect)

        # 驗證標記了 pending_town_subflows 為 True
        self.assertTrue(self.mock_machine.pending_town_subflows)
        # 驗證沒有立即呼叫 trigger_town_subflow_chain()
        self.mock_machine.trigger_town_subflow_chain.assert_not_called()
        # 驗證切回了原本的 DUNGEON_EXPLORING 狀態
        self.mock_machine.transition_to.assert_called_with("DUNGEON_EXPLORING")

    @patch('os.path.exists', return_value=True)
    def test_bag_cleaning_in_stage_mode_triggers_town_subflows_immediately(self, mock_exists):
        """驗證普通關卡/城鎮背包滿清理完畢後，立刻觸發城鎮流水線"""
        self.mock_machine.bag_tidied = True
        self.mock_machine.is_in_dungeon = False
        self.mock_machine.previous_state = "NAVIGATING"
        self.mock_machine.config = {"type": "stage"}
        self.mock_machine.pending_town_subflows = False

        def mock_match_quit(img, name, **kw):
            if name == "common/quit.png":
                return ((100, 100), 0.90)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match_quit


        screen_img = MagicMock()
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        with patch('states.handlers.bag_cleaning.time.sleep'):
            self.handler.handle(screen_img, rect)

        # 驗證立刻呼叫了 trigger_town_subflow_chain()
        self.mock_machine.trigger_town_subflow_chain.assert_called_once()

class TestBackpackFullDestroyableColorsDecoupling(unittest.TestCase):
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.STATE_UNKNOWN = "UNKNOWN"
        self.mock_machine.config = {
            # 大廳大量分解設定為包含紫/藍/綠/灰
            "disassemble_colors": ["gray_or_empty", "green", "blue", "purple"],
            "keep_colors": ["purple", "orange_yellow", "red"],
            # 獨立的背包已滿銷毀設定：預設僅允許 gray_or_empty
            "backpack_full_destroyable_colors": ["gray_or_empty"]
        }

    @patch('states.handlers.backpack_full_sorting.np.std')
    def test_backpack_full_restricts_destroy_target_to_gray_only(self, mock_std):
        """驗證當大廳大量分解包含了綠/藍/紫時，背包已滿分選處理器依然嚴格僅挑選 gray_or_empty 進行銷毀"""
        from states.handlers.backpack_full_sorting import BackpackFullSortingHandler
        handler = BackpackFullSortingHandler(self.mock_machine)
        handler.matcher = MagicMock()
        handler.mouse = MagicMock()
        handler.save_diagnostic_image = MagicMock()
        handler.click_close_button = MagicMock()

        # 模擬彈窗匹配 backpack_full.png 成功
        handler.matcher.match.side_effect = lambda img, tpl, **kw: ((500, 300), 0.90) if tpl == "backpack_full.png" else (None, 0.0)

        # 模擬 classify_slot_color 依呼叫順序回傳：
        # 左側 (4x4): 第 0 格為 purple，其餘 15 格為 gray_or_empty
        # 右側 (4x4): 第 0 格為 green，第 1 格為 gray_or_empty，其餘為 gray_or_empty
        classify_returns = ["purple"] + ["gray_or_empty"] * 15 + ["green", "gray_or_empty"] + ["gray_or_empty"] * 14
        handler.classify_slot_color = MagicMock(side_effect=classify_returns)
        mock_std.return_value = 25.0  # 標準差皆達標

        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        with patch('states.handlers.backpack_full_sorting.time.sleep'):
            handler.handle(fake_img, rect)

        # 驗證核心：當 destroyable_colors 為 ["gray_or_empty"] 時，右側被選中的標的 (target_right_slot) 必須是 (0, 1, 'gray_or_empty')，絕對不能是 (0, 0, 'green')！
        # 檢視 save_diagnostic_image 被呼叫時傳進去的 click_target
        self.assertTrue(handler.save_diagnostic_image.called)
        args, kwargs = handler.save_diagnostic_image.call_args
        # kwargs 中的 right_slots_data 或 debug 印出
        # 亦可檢驗 mouse.click 座標為第 1 格 (gray_or_empty) 而非第 0 格 (green)
        # 由於 right_start_dx = 34, step_x = 134，pos_full[0] = 500
        # 格子 (0, 0) x = 500 + (34 + 0*134 + 67) = 601
        # 格子 (0, 1) x = 500 + (34 + 1*134 + 67) = 735
        clicked_x = handler.mouse.click.call_args_list[0][0][0]
        # 當前舊程式碼實作中，因為借用了 disassemble_colors (含 green)，clicked_x 會命中 (0, 0) 即 green 格子！
        # 在新實作修復後，clicked_x 必須命中 (0, 1) 即 gray_or_empty 格子！
        self.assertGreater(clicked_x, 650, "未選擇 gray_or_empty 格子，誤選了 green 格子！")

if __name__ == "__main__":
    unittest.main()
