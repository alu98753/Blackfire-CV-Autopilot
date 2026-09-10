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

    # =========================================================================
    # 3.3 退避期間地下城全冷卻點擊 goback_town 回城並轉入 collect_only 行為測試
    # =========================================================================

    def test_3_3_dungeon_cooldown_exhaustion_during_retreat_clicks_goback_town_and_enters_collect_only(self):
        """
        [3.3 Behavior Test]
        Given: 體力退避倒數中 (stamina_retreat_start_time 設定)，處於臨時地下城喚醒路由 (type="mix", is_dungeon_temporary_resume=True)，
               地下城全冷卻 (has_available_dungeon() == False)，畫面上可見 goback_town.png 與 common/select_stage.png
        When: 執行 NavigationHandler.handle()
        Then: 斷言點擊 goback_town.png，絕不點擊 common/select_stage.png，狀態轉移至 COLLECT_ONLY，配置更新為 collect_only
        """
        mock_img = MagicMock()
        self.mock_machine.stamina_retreat_start_time = time.time() - 60.0
        self.mock_machine.has_available_dungeon.return_value = False
        self.mock_machine.has_dungeon_status_context.return_value = True
        self.mock_machine.get_dungeon_cooldown_status.return_value = ("全冷卻", [])
        self.mock_machine.config = {
            "name": "地下城臨時喚醒",
            "type": "mix",
            "enable_dungeon": True,
            "enable_stage_farming": False,
            "is_dungeon_temporary_resume": True,
            "dungeon_names": ["冰雪洞窟"],
            "greedy_allowed_indices": [6],
        }

        clicked_templates = []
        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "goback_town.png":
                return ((80, 800), 0.95)
            if template == "common/select_stage.png":
                return ((500, 700), 0.90)
            return (None, 0.0)

        def fake_click(x, y):
            if x == 80 and y == 800:
                clicked_templates.append("goback_town.png")
            elif x == 500 and y == 700:
                clicked_templates.append("common/select_stage.png")

        self.mock_machine.matcher.match.side_effect = fake_match
        self.mock_machine.mouse.click.side_effect = fake_click

        self.handler.handle(mock_img, self.rect)

        self.assertIn("goback_town.png", clicked_templates)
        self.assertNotIn("common/select_stage.png", clicked_templates)
        self.mock_machine.transition_to.assert_called_once_with("COLLECT_ONLY")
        self.assertEqual(self.mock_machine.config["type"], "collect_only")

    # =========================================================================
    # 3.4 體力退避期間普通關卡嚴禁啟用行為測試
    # =========================================================================

    def test_3_4_stage_farming_strictly_prohibited_during_stamina_retreat(self):
        """
        [3.4 Behavior Test]
        Given: stamina_retreat_start_time 設定，即使外部 config 帶有 enable_stage_farming=True 與 is_tier4_fallback=True
        When: 評估 _is_stage_farming_allowed()
        Then: 斷言恆為 False，且觸發 _switch_to_stage_or_back 時絕不點擊 select_stage.png，而是轉移至 COLLECT_ONLY
        """
        mock_img = MagicMock()
        self.mock_machine.stamina_retreat_start_time = time.time() - 100.0
        self.mock_machine.config = {
            "name": "被污染的路由",
            "type": "mix",
            "enable_stage_farming": True,
            "is_tier4_fallback": True,
            "dungeon_names": ["冰雪洞窟"],
            "greedy_allowed_indices": [6],
        }

        # 斷言輔助函式回傳 False
        self.assertFalse(self.handler._is_stage_farming_allowed())

        clicked = []
        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "goback_town.png":
                return ((80, 800), 0.95)
            if template == "common/select_stage.png":
                return ((500, 700), 0.90)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match
        self.mock_machine.mouse.click.side_effect = lambda x, y: clicked.append((x, y))

        self.handler._switch_to_stage_or_back(mock_img, self.rect, "測試退避")

        # 斷言點擊的是 goback_town.png (80, 800) 而非 select_stage.png (500, 700)
        self.assertIn((80, 800), clicked)
        self.assertNotIn((500, 700), clicked)
        self.mock_machine.transition_to.assert_called_once_with("COLLECT_ONLY")

if __name__ == "__main__":
    unittest.main()
