import unittest
import time
from unittest.mock import MagicMock, patch
from states.handlers.navigation import NavigationHandler
from config import GAME_CONFIGS

class TestBehaviorStaminaRetreat(unittest.TestCase):
    """
    體力退避與狀態切換行為測試集 (Google Software Dev Standard)
    專注於 Given 體力退避與全冷卻情境 ➔ When 觸發 handle ➔ Then 斷言 collect_only 模式切換與大廳回城防死迴圈
    """
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.STATE_COLLECT_ONLY = "COLLECT_ONLY"
        self.mock_machine.STATE_LOBBY = "LOBBY"

        self.mock_machine.need_bag_cleaning = False
        self.mock_machine.diamond_window_opened = False
        self.mock_machine.bread_window_opened = False
        self.mock_machine.need_diamond_collection = False
        self.mock_machine.need_bread_collection = False
        self.mock_machine.enable_bread = False

        self.mock_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.mock_machine.original_config = GAME_CONFIGS["dungeon"].copy()
        self.mock_machine.stamina_retreat_start_time = time.time() - 30.0

        self.mock_machine.matcher.match.return_value = (None, 0.0)

        self.handler = NavigationHandler(self.mock_machine)
        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    # =========================================================================
    # 3.1 地下城全冷卻切換 Collect Only 行為測試
    # =========================================================================

    def test_3_1_all_dungeons_cooldown_during_retreat_switches_back_to_collect_only(self):
        """
        [3.1 Behavior Test]
        Given: 體力退避倒數中 (stamina_retreat_start_time 設定)，雖已暫時切回 dungeon 模式，但 has_available_dungeon() 回傳 False (全冷卻)
        When: 執行 NavigationHandler.handle()
        Then: machine.config["type"] 被自動更新為 "collect_only"，且狀態轉移至 STATE_COLLECT_ONLY
        """
        mock_img = MagicMock()
        self.mock_machine.has_available_dungeon.return_value = False

        self.handler.handle(mock_img, self.rect)

        # 斷言狀態轉移至 COLLECT_ONLY
        self.mock_machine.transition_to.assert_called_once_with("COLLECT_ONLY")
        # 斷言配置被更新為 collect_only 類型
        self.assertEqual(self.mock_machine.config["type"], "collect_only")

    # =========================================================================
    # 3.2 collect_only 模式下領完體力返回城鎮行為測試
    # =========================================================================

    def test_3_2_collect_only_mode_in_lobby_clicks_goback_town(self):
        """
        [3.2 Behavior Test]
        Given: type="collect_only" 模式下，在大廳畫面 (看得到 goback_town.png)
        When: 執行 NavigationHandler.handle()
        Then: 發射滑鼠點擊 (75, 750) 點擊 goback_town.png 退回城鎮，並維繫狀態轉移至 STATE_COLLECT_ONLY
        """
        mock_img = MagicMock()
        self.mock_machine.stamina_retreat_start_time = None
        self.mock_machine.config = {
            "name": "純領取模式",
            "type": "collect_only"
        }

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "goback_town.png":
                return ((75, 750), 0.90)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證點擊 goback_town.png
        self.mock_machine.mouse.click.assert_called_once_with(75, 750)
        # 驗證狀態維持/轉移至 COLLECT_ONLY
        self.mock_machine.transition_to.assert_called_once_with("COLLECT_ONLY")

if __name__ == "__main__":
    unittest.main()
