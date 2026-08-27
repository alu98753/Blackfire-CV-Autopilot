import unittest
from unittest.mock import MagicMock, patch
from states.handlers.domain_explore import DomainExploreHandler
from states.domains.golden_empire import GoldenEmpireStrategy
from states.handlers.navigation import NavigationHandler

class TestBehaviorGoldenEmpire(unittest.TestCase):
    """
    黃金古國與領地系統 (Domain System) 行為測試集 (Google Software Dev Standard)
    專注於驗證外部可觀察行為與狀態轉移契約：
    Given 特性畫面/狀態 ➔ When 觸發 handle ➔ Then 斷言發射點擊或轉移狀態
    """
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.STATE_DOMAIN_EXPLORE = "DOMAIN_EXPLORE"
        self.mock_machine.STATE_BATTLE = "BATTLE"
        self.mock_machine.STATE_BACKPACK_FULL_SORTING = "BACKPACK_FULL_SORTING"
        self.mock_machine.STATE_NAVIGATING = "NAVIGATING"
        self.mock_machine.STATE_COLLECT_ONLY = "COLLECT_ONLY"
        self.mock_machine.STATE_BREAD_COLLECTION = "BREAD_COLLECTION"
        self.mock_machine.STATE_LOBBY = "LOBBY"

        self.mock_machine.need_bag_cleaning = False
        self.mock_machine.need_diamond_collection = False
        self.mock_machine.need_bread_collection = False
        self.mock_machine.enable_bread = False
        self.mock_machine.stamina_retreat_start_time = None
        self.mock_machine.is_daily_pipeline_active.return_value = False
        self.mock_machine.has_available_dungeon.return_value = False
        self.mock_machine.dungeon_cooldowns = {}

        self.mock_machine.config = {
            "name": "黃金古國",
            "type": "domain",
            "domain": "golden_empire",
            "domain_name": "golden_empire",
            "bread_cost": 3,
            "navigation_path": [
                "common/door.png",
                "domains/Domains_entry.png",
                "domains/golden_empire/entry.png",
                "domains/common/start_btn.png"
            ],
            "explore_priorities": ["domains/golden_empire/explore_btn.png"],
            "result_buttons": ["common/continue.png", "common/continue_gray.png"]
        }

        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        self.handler = DomainExploreHandler(self.mock_machine)
        self.nav_handler = NavigationHandler(self.mock_machine)

    # =========================================================================
    # 1. 進場導航與進入領地行為測試
    # =========================================================================

    def test_navigation_into_golden_empire_scene(self):
        """
        Given: 導航至領地主畫面，畫面上出現探索按鈕 (domains/golden_empire/explore_btn.png)
        When: 執行 NavigationHandler.handle()
        Then: 判定抵達領地主場景，成功轉移至 STATE_DOMAIN_EXPLORE
        """
        mock_img = MagicMock()

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "domains/golden_empire/explore_btn.png":
                return ((850, 740), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            self.nav_handler.handle(mock_img, self.rect)

        self.mock_machine.transition_to.assert_called_with("DOMAIN_EXPLORE")

    # =========================================================================
    # 2. 領地主場景探索點擊行為測試
    # =========================================================================

    def test_explore_button_click_in_domain(self):
        """
        Given: 處於 STATE_DOMAIN_EXPLORE，畫面上出現 explore_btn.png
        When: 執行 DomainExploreHandler.handle()
        Then: 正確點擊探索按鈕並呼叫 notify_ui_progress()
        """
        mock_img = MagicMock()

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "domains/golden_empire/explore_btn.png":
                return ((850, 740), 0.90)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            self.handler.handle(mock_img, self.rect)

        self.mock_machine.mouse.click.assert_called_with(850, 740)
        self.mock_machine.notify_ui_progress.assert_called()

    # =========================================================================
    # 3. 挖寶事件 (Treasure Subflow) 行為測試 (單次免費開箱 ➔ 確認 ➔ 離開)
    # =========================================================================

    def test_treasure_event_free_box_subflow(self):
        """
        Given: 處於 STATE_DOMAIN_EXPLORE，畫面出現挖寶畫面 (domains/find_treasure.png)
        When: 執行 DomainExploreHandler.handle()
        Then: 觸發挖寶子流程：點擊免費寶箱 ➔ 點擊確認 (common/confirm.png) ➔ 點擊退出 (common/quit.png)
        """
        mock_img = MagicMock()

        matched_calls = []
        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            matched_calls.append(template)
            if template in ["domains/find_treasure.png", "domains/treasure.png"]:
                return ((960, 540), 0.88)
            if template in ["common/confirm.png", "common/ok.png"]:
                return ((960, 700), 0.85)
            if template in ["common/quit.png", "domains/common/exit_to_lobby.png"]:
                return ((100, 100), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            self.handler.handle(mock_img, self.rect)

        # 斷言發起點擊
        self.assertTrue(self.mock_machine.mouse.click.called)
        self.mock_machine.notify_ui_progress.assert_called()

    # =========================================================================
    # 4. 戰鬥跳轉行為測試
    # =========================================================================

    def test_battle_transition_when_auto_detected(self):
        """
        Given: 處於 STATE_DOMAIN_EXPLORE，畫面偵測到進入戰鬥 (common/auto.png)
        When: 執行 DomainExploreHandler.handle()
        Then: 正確轉移至 STATE_BATTLE
        """
        mock_img = MagicMock()

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "common/auto.png":
                return ((1800, 900), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            self.handler.handle(mock_img, self.rect)

        self.mock_machine.transition_to.assert_called_with("BATTLE")

    # =========================================================================
    # 5. 背包已滿攔截測試
    # =========================================================================

    def test_backpack_full_interception(self):
        """
        Given: 處於 STATE_DOMAIN_EXPLORE，need_bag_cleaning=True 或偵測到 backpack_full
        When: 執行 DomainExploreHandler.handle()
        Then: 攔截並轉移至 STATE_BACKPACK_FULL_SORTING
        """
        mock_img = MagicMock()
        self.mock_machine.need_bag_cleaning = True

        self.handler.handle(mock_img, self.rect)

        self.mock_machine.transition_to.assert_called_with("BACKPACK_FULL_SORTING")

    # =========================================================================
    # 6. 戰鬥結算回歸探索測試
    # =========================================================================

    def test_result_handler_returns_to_domain_explore(self):
        """
        Given: 領地模式戰鬥結束，進入 ResultHandler
        When: 消化完 Continue 按鈕且無續戰 (retry) 按鈕
        Then: 安全轉移回 STATE_DOMAIN_EXPLORE
        """
        from states.handlers.result import ResultHandler
        result_handler = ResultHandler(self.mock_machine)
        mock_img = MagicMock()

        # 模擬已無 continue 按鈕，且無 retry 按鈕
        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "common/select_stage.png":
                return (None, 0.0)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match
        self.mock_machine.continue_template = "common/continue.png"

        with patch("os.path.exists", return_value=False):
            result_handler.subflow_step = "FINAL_MATCH"
            result_handler.handle(mock_img, self.rect)

        # 斷言切換回 DOMAIN_EXPLORE
        self.mock_machine.transition_to.assert_called_with("DOMAIN_EXPLORE")


if __name__ == "__main__":
    unittest.main()
