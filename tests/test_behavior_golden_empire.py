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
        self.mock_machine.STATE_LOADING = "LOADING"

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
        Given: 處於 STATE_DOMAIN_EXPLORE，畫面出現挖寶畫面 (domains/golden_empire/open.png)
        When: 執行 DomainExploreHandler.handle()
        Then: 觸發挖寶子流程：使用 click_and_wait_until_gone 閉環點擊 open.png、confirm.png 與 quit.png
        """
        mock_img = MagicMock()

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template in ["domains/golden_empire/open.png", "domains/open.png"]:
                return ((1045, 615), 0.92)
            if template in ["domains/golden_empire/find_treasure.png", "domains/golden_empire/treasure.png", "domains/find_treasure.png", "domains/treasure.png"]:
                return ((960, 540), 0.88)
            if template in ["common/confirm.png", "common/ok.png"]:
                return ((960, 700), 0.85)
            if template in ["common/quit.png", "domains/common/exit_to_lobby.png"]:
                return ((100, 100), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match
        self.handler.click_and_wait_until_gone = MagicMock()

        with patch("os.path.exists", return_value=True):
            self.handler.handle(mock_img, self.rect)

        # 斷言調用 click_and_wait_until_gone 閉環點擊 open.png、confirm.png 與 quit.png
        self.assertTrue(self.handler.click_and_wait_until_gone.called)
        called_templates = [call.args[0] for call in self.handler.click_and_wait_until_gone.call_args_list]
        self.assertIn("domains/golden_empire/open.png", called_templates)
        self.assertIn("common/confirm.png", called_templates)
        self.assertIn("common/quit.png", called_templates)

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
    # 5. 背包已滿攔截與退場測試
    # =========================================================================

    def test_backpack_full_popup_transfers_to_sorting(self):
        """
        Given: 處於 STATE_DOMAIN_EXPLORE，畫面出現背包已滿彈窗 (backpack_full.png)
        When: 執行 DomainExploreHandler.handle()
        Then: 攔截並轉移至 STATE_BACKPACK_FULL_SORTING 進行就地分選
        """
        mock_img = MagicMock()

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "backpack_full.png":
                return ((960, 200), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            self.handler.handle(mock_img, self.rect)

        self.mock_machine.transition_to.assert_called_with("BACKPACK_FULL_SORTING")

    def test_need_bag_cleaning_exits_to_lobby_and_navigates(self):
        """
        Given: 處於 STATE_DOMAIN_EXPLORE，無彈窗但已標記 need_bag_cleaning = True
        When: 執行 DomainExploreHandler.handle()
        Then: 偵測到 exit_to_lobby.png 並點擊退場，轉移至 STATE_NAVIGATING
        """
        mock_img = MagicMock()
        self.mock_machine.need_bag_cleaning = True

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "domains/common/exit_to_lobby.png":
                return ((100, 100), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match
        self.handler.click_and_wait_until_gone = MagicMock()

        with patch("os.path.exists", return_value=True):
            self.handler.handle(mock_img, self.rect)

        self.handler.click_and_wait_until_gone.assert_called()
        self.mock_machine.transition_to.assert_called_with("NAVIGATING")

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

    # =========================================================================
    # 7. 強敵 Boss (黃金君王) 戰鬥放棄測試
    # =========================================================================

    def test_flee_boss_giveup_battle_subflow(self):
        """
        Given: 戰鬥中遭遇強敵 Boss (golden_king.png)
        When: 執行 BattleHandler.handle()
        Then: 觸發放棄流程：點擊 setting ➔ 點擊 giveup_battle ➔ 點擊 confirm ➔ 不增加戰敗計數 (維持 0) 並切回 DOMAIN_EXPLORE
        """
        from states.handlers.battle import BattleHandler
        battle_handler = BattleHandler(self.mock_machine)
        mock_img = MagicMock()

        self.mock_machine.config["flee_bosses"] = ["domains/golden_empire/exception/golden_king.png"]
        self.mock_machine.config["domain_max_defeat"] = 5
        self.mock_machine.defeat_count = 0
        self.mock_machine.last_auto_click_time = 0.0
        self.mock_machine.battle_start_time = 100.0

        def fake_match(img, template, threshold=0.75, *args, **kwargs):
            if template == "domains/golden_empire/exception/golden_king.png":
                return ((500, 300), 0.85)
            if template == "battle/setting.png":
                return ((1800, 50), 0.90)
            if template == "battle/giveup_battle.png":
                return ((960, 600), 0.90)
            if template in ["common/confirm.png", "common/ok.png"]:
                return ((960, 700), 0.90)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            battle_handler.handle(mock_img, self.rect)

        # 斷言點擊過設定與放棄按鈕，且強敵放棄不增加戰敗計數，並轉移至 NAVIGATING 重新進場
        self.assertTrue(self.mock_machine.mouse.click.called)
        self.assertEqual(self.mock_machine.defeat_count, 0)
        self.mock_machine.transition_to.assert_called_with("NAVIGATING")

    # =========================================================================
    # 8. 單場常規戰鬥戰敗重試 (獨立 5 次 retry) 測試
    # =========================================================================

    def test_regular_battle_defeat_retry_uses_domain_max_defeat(self):
        """
        Given: 領地模式常規戰鬥戰敗 (defeat.png)，當前 defeat_count = 3 (< domain_max_defeat - 1 = 4)
        When: 執行 ResultHandler.handle()
        Then: 點擊重新開始按鈕，defeat_count 累加為 4，進入 STATE_LOADING 繼續重試
        """
        from states.handlers.result import ResultHandler
        result_handler = ResultHandler(self.mock_machine)
        mock_img = MagicMock()

        self.mock_machine.config["type"] = "domain"
        self.mock_machine.config["domain"] = "golden_empire"
        self.mock_machine.config["domain_max_defeat"] = 5
        self.mock_machine.is_in_dungeon = False
        self.mock_machine.defeat_count = 3

        def fake_match(img, template, threshold=0.75, *args, **kwargs):
            if template == "defeat.png":
                return ((960, 400), 0.85)
            if template in ["defeat_retry.png", "stages/retry.png"]:
                return ((960, 800), 0.90)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            result_handler.subflow_step = "CONTINUE_LOOP"
            result_handler.handle(mock_img, self.rect)

        # 斷言戰敗重試次數累加至 4，並切換至 LOADING 狀態
        self.assertEqual(self.mock_machine.defeat_count, 4)
        self.mock_machine.transition_to.assert_called_with("LOADING")

    # =========================================================================
    # 9. 領地探索處於外部選單自動導航重新進場測試
    # =========================================================================

    def test_domain_explore_navigates_when_outside_buttons_detected(self):
        """
        Given: 處於 STATE_DOMAIN_EXPLORE 但畫面處於外部選單 (例如 domains/golden_empire/entry.png)
        When: 執行 DomainExploreHandler.handle()
        Then: 正確偵測到導航按鈕，轉移至 STATE_NAVIGATING 重新進場
        """
        mock_img = MagicMock()

        def fake_match(img, template, threshold=0.75, *args, **kwargs):
            if template == "domains/golden_empire/entry.png":
                return ((500, 500), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            self.handler.handle(mock_img, self.rect)

        self.mock_machine.transition_to.assert_called_with("NAVIGATING")


if __name__ == "__main__":
    unittest.main()
