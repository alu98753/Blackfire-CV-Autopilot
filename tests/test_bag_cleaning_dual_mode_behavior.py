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

        self.handler.matcher.match.return_value = ((100, 100), 0.90)

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

        self.handler.matcher.match.return_value = ((100, 100), 0.90)

        screen_img = MagicMock()
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        with patch('states.handlers.bag_cleaning.time.sleep'):
            self.handler.handle(screen_img, rect)

        # 驗證立刻呼叫了 trigger_town_subflow_chain()
        self.mock_machine.trigger_town_subflow_chain.assert_called_once()

if __name__ == "__main__":
    unittest.main()
