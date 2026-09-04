import unittest
import time
from unittest.mock import MagicMock, patch
from states.handlers.domain_explore import DomainExploreHandler
from states.handlers.battle import BattleHandler
from states.domains.golden_empire import GoldenEmpireStrategy
from states.handlers.navigation import NavigationHandler
from states.state_machine import GameStateMachine
from utils.scene_detector import SceneInfo, SceneType

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
        self.mock_machine.daily_manager = None
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

    @patch("os.path.exists", return_value=True)
    def test_domain_battle_ignores_false_dungeon_recovery_anchor(
        self,
        _mock_exists,
    ):
        """Domain battle result owns the frame even if a dungeon anchor matches."""
        machine = GameStateMachine(
            capturer=MagicMock(),
            matcher=MagicMock(),
            mouse=MagicMock(),
            preload_ocr=False,
        )
        machine.config = self.mock_machine.config.copy()
        machine.current_state = machine.STATE_BATTLE
        machine.battle_start_time = time.time() - 10.0

        def fake_match(_image, template, **_kwargs):
            if template == "dungeons/gungeon_godown_confirm.png":
                return (766, 524), 0.8094
            if template == "common/continue.png":
                return (765, 525), 0.9499
            return None, 0.0

        machine.matcher.match.side_effect = fake_match

        BattleHandler(machine).handle(MagicMock(), self.rect)

        self.assertEqual(machine.current_state, machine.STATE_RESULT)
        matched_templates = [
            call.args[1] for call in machine.matcher.match.call_args_list
        ]
        self.assertNotIn(
            "dungeons/gungeon_godown_confirm.png",
            matched_templates,
        )

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

    @patch("states.handlers.navigation.time.sleep")
    @patch("states.handlers.navigation.CardListNavigator.reset_to_left")
    @patch("os.path.exists", return_value=True)
    def test_domain_tab_switch_then_resets_shared_card_position_to_left(
        self,
        _mock_exists,
        mock_reset_to_left,
        _mock_sleep,
    ):
        """After switching to Domains, a missing index-1 card triggers bounded left reset."""
        self.nav_handler.scene_detector = MagicMock()
        self.nav_handler.scene_detector.matcher = self.mock_machine.matcher
        self.nav_handler.scene_detector.detect.side_effect = [
            SceneInfo(scene_type=SceneType.LOBBY_OTHER, is_lobby=True),
            SceneInfo(
                scene_type=SceneType.DOMAIN_SELECT,
                is_lobby=True,
                active_tabs=["domain"],
            ),
        ]

        def match_side_effect(_img, template, **_kwargs):
            if template == "domains/Domains_entry.png":
                return ((500, 700), 0.95)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = match_side_effect

        self.nav_handler.handle(MagicMock(), self.rect)
        self.mock_machine.mouse.click.assert_called_once_with(500, 700)
        mock_reset_to_left.assert_not_called()

        self.mock_machine.mouse.click.reset_mock()
        self.nav_handler.handle(MagicMock(), self.rect)

        mock_reset_to_left.assert_called_once_with(
            self.mock_machine.mouse,
            self.rect,
            duration=0.8,
            inertia=False,
        )
        self.mock_machine.mouse.click.assert_not_called()
        target_calls = [
            call
            for call in self.mock_machine.matcher.match.call_args_list
            if call.args[1] == "domains/golden_empire/entry.png"
        ]
        self.assertTrue(target_calls)
        self.assertTrue(
            all(call.kwargs["brightness_threshold"] == 0.70 for call in target_calls)
        )

    @patch("states.handlers.navigation.time.sleep")
    @patch("states.handlers.navigation.CardListNavigator.reset_to_left")
    @patch("os.path.exists", return_value=True)
    def test_domain_card_alignment_retains_attempts_across_flickering_tab_frames(
        self,
        _mock_exists,
        mock_reset_to_left,
        _mock_sleep,
    ):
        """Alignment attempts are preserved across transient tab detection misses."""
        self.nav_handler.scene_detector = MagicMock()
        self.nav_handler.scene_detector.matcher = self.mock_machine.matcher
        self.mock_machine.matcher.match.return_value = (None, 0.0)

        # 幀 1: 確認處於 Domain 頁籤且找不到第一張卡 -> 觸發第 1 次向右拉回
        self.nav_handler.scene_detector.detect.return_value = SceneInfo(
            scene_type=SceneType.DOMAIN_SELECT,
            is_lobby=True,
            active_tabs=["domain"],
        )
        self.nav_handler.handle(MagicMock(), self.rect)
        self.assertEqual(self.nav_handler.card_alignment_attempts, 1)
        self.assertEqual(mock_reset_to_left.call_count, 1)

        # 幀 2: 單幀掉幀或漏判頁籤 (LOBBY_OTHER, active_tabs 為空)
        # 驗證: 絕不滑動，且嚴禁將 card_alignment_attempts 清空為 0！
        self.nav_handler.scene_detector.detect.return_value = SceneInfo(
            scene_type=SceneType.LOBBY_OTHER,
            is_lobby=True,
            active_tabs=[],
        )
        handled = self.nav_handler.handle(MagicMock(), self.rect)
        self.assertFalse(handled)
        self.assertEqual(self.nav_handler.card_alignment_attempts, 1)
        self.assertEqual(mock_reset_to_left.call_count, 1)

        # 幀 3: 再次穩定辨識為 Domain 頁籤 -> 累加執行第 2 次拉回
        self.nav_handler.scene_detector.detect.return_value = SceneInfo(
            scene_type=SceneType.DOMAIN_SELECT,
            is_lobby=True,
            active_tabs=["domain"],
        )
        self.nav_handler.handle(MagicMock(), self.rect)
        self.assertEqual(self.nav_handler.card_alignment_attempts, 2)
        self.assertEqual(mock_reset_to_left.call_count, 2)

    @patch("states.handlers.navigation.time.sleep")
    @patch("states.handlers.navigation.CardListNavigator.reset_to_left")
    @patch("os.path.exists", return_value=True)
    def test_domain_card_alignment_relaunches_after_bounded_reset_limit(
        self,
        _mock_exists,
        mock_reset_to_left,
        _mock_sleep,
    ):
        """Domain alignment reaches 7-attempt limit (EXHAUSTED), zeroes counter, and relaunches."""
        self.nav_handler.scene_detector = MagicMock()
        self.nav_handler.scene_detector.matcher = self.mock_machine.matcher
        self.nav_handler.scene_detector.detect.return_value = SceneInfo(
            scene_type=SceneType.DOMAIN_SELECT,
            is_lobby=True,
            active_tabs=["domain"],
        )
        self.mock_machine.matcher.match.return_value = (None, 0.0)
        # 設定當前 target_tab 已經是 domain，且已達到上限 7 次
        self.nav_handler.card_alignment_target_tab = "domain"
        self.nav_handler.card_alignment_attempts = 7

        self.nav_handler.handle(MagicMock(), self.rect)

        # 不再發起滑動，避免無限滑動
        mock_reset_to_left.assert_not_called()
        # 驗證達到上限後正確觸發重啟並歸零嘗試計數
        self.mock_machine.request_relaunch.assert_called_once_with(
            "domain_card_alignment_failed"
        )
        self.assertIsNone(self.nav_handler.card_alignment_tab)
        self.assertEqual(self.nav_handler.card_alignment_attempts, 0)

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
    # 7. 領域強敵 Nemesis (黃金君王) 戰鬥處置與放棄測試
    # =========================================================================

    def test_nemesis_giveup_battle_subflow(self):
        """
        Given: 戰鬥中遭遇領域強敵 Nemesis (golden_king.png) 且配置 nemesis_action = 'flee'
        When: 執行 BattleHandler.handle()
        Then: 觸發放棄流程：點擊 setting ➔ 點擊 giveup_battle ➔ 點擊 confirm ➔ 不增加戰敗計數 (維持 0) 並轉移至 NAVIGATING
        """
        from states.handlers.battle import BattleHandler
        battle_handler = BattleHandler(self.mock_machine)
        mock_img = MagicMock()

        self.mock_machine.config["nemesis_templates"] = ["domains/golden_empire/exception/golden_king.png"]
        self.mock_machine.config["nemesis_action"] = "flee"
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

    def test_nemesis_pause_action_subflow(self):
        """
        Given: 戰鬥中遭遇領域強敵 Nemesis (elf_mythril_hag.png) 且配置 nemesis_action = 'pause'
        When: 執行 BattleHandler.handle()
        Then: 呼叫 machine.pause() 暫停腳本運行，不發送任何點擊，交由使用者手動挑戰
        """
        from states.handlers.battle import BattleHandler
        battle_handler = BattleHandler(self.mock_machine)
        mock_img = MagicMock()

        self.mock_machine.config["nemesis_templates"] = ["domains/golden_empire/exception/elf_mythril_hag.png"]
        self.mock_machine.config["nemesis_action"] = "pause"
        self.mock_machine.last_auto_click_time = 0.0
        self.mock_machine.battle_start_time = 100.0

        def fake_match(img, template, threshold=0.75, *args, **kwargs):
            if template == "domains/golden_empire/exception/elf_mythril_hag.png":
                return ((500, 300), 0.85)
            if template == "common/auto.png":
                return ((1200, 55), 0.95)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            battle_handler.handle(mock_img, self.rect)

        # 斷言觸發 machine.pause()，且未發起放棄戰鬥之滑鼠點擊
        self.mock_machine.pause.assert_called_once()
        self.assertFalse(self.mock_machine.mouse.click.called)

    def test_nemesis_backward_compatibility_with_flee_bosses(self):
        """
        [向下相容測試] 驗證使用舊鍵值 flee_bosses 與 flee_boss_action 時，BattleHandler 依然能正確辨識強敵並暫停
        """
        from states.handlers.battle import BattleHandler
        battle_handler = BattleHandler(self.mock_machine)
        mock_img = MagicMock()

        self.mock_machine.config.pop("nemesis_templates", None)
        self.mock_machine.config.pop("nemesis_action", None)
        self.mock_machine.config["flee_bosses"] = ["domains/golden_empire/exception/golden_king.png"]
        self.mock_machine.config["flee_boss_action"] = "pause"
        self.mock_machine.battle_start_time = 100.0

        def fake_match(img, template, threshold=0.75, *args, **kwargs):
            if template == "domains/golden_empire/exception/golden_king.png":
                return ((500, 300), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            battle_handler.handle(mock_img, self.rect)

        self.mock_machine.pause.assert_called_once()

    # =========================================================================
    # 8. 單場常規戰鬥戰敗重試 (獨立 5 次 retry) 測試
    # =========================================================================

    def test_regular_battle_defeat_retry_uses_battle_max_defeat(self):
        """
        Given: 領地模式常規戰鬥戰敗 (defeat.png)，當前 defeat_count = 3 (< battle_max_defeat - 1 = 4)
        When: 執行 ResultHandler.handle()
        Then: 點擊重新開始按鈕，defeat_count 累加為 4，進入 STATE_LOADING 繼續重試
        """
        from states.handlers.result import ResultHandler
        result_handler = ResultHandler(self.mock_machine)
        mock_img = MagicMock()

        self.mock_machine.config["type"] = "domain"
        self.mock_machine.config["domain"] = "golden_empire"
        self.mock_machine.config["battle_max_defeat"] = 5
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


    # =========================================================================
    # 10. 黃金古國食物不足彈窗 (no_bread2.png) 觸發體力退避測試
    # =========================================================================

    def test_no_bread2_triggers_stamina_retreat(self):
        """
        Given: 處於黃金古國領地探索時，畫面彈出食物不足彈窗 (no_bread/no_bread2.png 與 common/confirm.png)
        When: 執行 handle_insufficient_stamina()
        Then: 點擊 confirm.png 關閉彈窗，並切換至 STATE_COLLECT_ONLY 進行定時領取待機
        """
        from states.stamina_flow import handle_insufficient_stamina
        mock_img = MagicMock()

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "no_bread/no_bread2.png":
                return ((960, 400), 0.90)
            if template in ["common/confirm.png", "common/ok.png"]:
                return ((960, 600), 0.95)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match
        self.mock_machine.capturer.get_window_rect.return_value = self.rect
        self.mock_machine.capturer.capture.return_value = None

        with patch("os.path.exists", return_value=True):
            triggered = handle_insufficient_stamina(self.mock_machine, mock_img, self.rect)

        self.assertTrue(triggered)
        self.mock_machine.mouse.click.assert_called()
        self.assertTrue(self.mock_machine.stamina_recovery.is_active)
        self.mock_machine.transition_to.assert_not_called()

    # =========================================================================
    # 11. 黃金古國日常領主 Boss (Lord Boss) 插隊挑戰與自動回歸測試
    # =========================================================================

    def test_golden_empire_preempts_to_lord_boss_when_cooldown_expires(self):
        """
        Given: 處於黃金古國探索 (STATE_DOMAIN_EXPLORE) 且啟用 enable_lord_boss = True，DailyManager 偵測到領主 Boss 冷卻結束可挑戰
        When: 執行 DomainExploreHandler.handle()
        Then: 主動偵測並點擊 exit_to_lobby.png 退出古國，轉移至 STATE_NAVIGATING 前往城鎮挑戰領主 Boss
        """
        mock_img = MagicMock()
        mock_dm = MagicMock()
        mock_dm.has_available_lord_boss.return_value = True
        self.mock_machine.daily_manager = mock_dm
        self.mock_machine.config["enable_lord_boss"] = True

        def fake_match(img, template, threshold=0.75, *args, **kwargs):
            if template == "domains/common/exit_to_lobby.png":
                return ((1800, 100), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True), \
             patch.object(self.handler, "click_and_wait_until_gone") as mock_click:
            self.handler.handle(mock_img, self.rect)

        mock_click.assert_called_once()
        self.assertEqual(mock_click.call_args[0][0], "domains/common/exit_to_lobby.png")
        self.mock_machine.transition_to.assert_called_with("NAVIGATING")

    def test_golden_empire_restored_after_lord_boss_finishes(self):
        """
        Given: 初始掛機主模式為黃金古國 (golden_empire)，中途插隊執行領主 Boss 討伐 (lord_boss)
        When: 領主 Boss 討伐結束，城鎮流水線隊列清空並執行 pop_and_next_town_subflow()
        Then: 狀態機自動恢復 primary_config (黃金古國)，並轉移至 STATE_NAVIGATING 以重新循徑進入古國繼續掛機
        """
        from states.state_machine import GameStateMachine
        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        golden_config = {
            "name": "黃金古國",
            "type": "domain",
            "domain": "golden_empire",
            "enable_lord_boss": True,
            "navigation_path": ["common/door.png", "domains/Domains_entry.png", "domains/golden_empire/entry.png", "domains/common/start_btn.png"]
        }
        sm.config = golden_config.copy()
        sm.primary_config = golden_config.copy()
        sm.town_subflow_queue = ["lord_boss"]

        # 模擬進入 Lord Boss 子流程
        sm.pop_and_next_town_subflow()
        self.assertEqual(sm.current_state, sm.STATE_LORD_BOSS)

        # 模擬 Lord Boss 結束，隊列清空並結尾
        sm.pop_and_next_town_subflow()
        self.assertEqual(sm.config["name"], "黃金古國")
        self.assertEqual(sm.config["type"], "domain")
        self.assertEqual(sm.current_state, sm.STATE_NAVIGATING)

    # 12. UNKNOWN 狀態辨識出黃金古國主場景 (explore_btn.png) 精確轉移至 DOMAIN_EXPLORE
    def test_unknown_state_detects_golden_empire_scene(self):
        """
        Given: 狀態機處於 UNKNOWN 全域定位，畫面出現黃金古國主場景特徵 (domains/golden_empire/explore_btn.png)
        When: 執行 detect_game_state
        Then: 精確斷言轉移至 STATE_DOMAIN_EXPLORE，絕不掉入 NAVIGATING 兜底
        """
        from states.state_machine import GameStateMachine
        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        sm.config = self.mock_machine.config.copy()
        mock_screen = MagicMock()
        
        def fake_match(screen, template, threshold=0.8, **kwargs):
            if template == "domains/golden_empire/explore_btn.png":
                return (100, 200), 0.95
            return None, 0.0

        sm.matcher.match.side_effect = fake_match
        sm.detect_current_state(mock_screen, self.rect)
        self.assertEqual(sm.current_state, sm.STATE_DOMAIN_EXPLORE)

    # 13. 戰鬥畫面結束回到黃金古國主場景時，觸發領地錨點自癒
    def test_battle_recovery_to_domain_explore(self):
        """
        Given: 戰鬥狀態 (BATTLE) 下畫面已回到黃金古國主場景 (explore_btn.png)
        When: 執行 BattleHandler.handle
        Then: 觸發 [Battle recovery] Domain anchor，立即自癒恢復至 STATE_DOMAIN_EXPLORE
        """
        battle_handler = BattleHandler(self.mock_machine)
        mock_screen = MagicMock()

        def fake_match(screen, template, threshold=0.8, **kwargs):
            if template == "domains/golden_empire/explore_btn.png":
                return (100, 200), 0.92
            return None, 0.0

        battle_handler.matcher.match.side_effect = fake_match
        battle_handler.handle(mock_screen, self.rect)
        self.mock_machine.transition_to.assert_called_with("DOMAIN_EXPLORE")

    # 14. 首領討伐在領地內部激活時，觸發退場邊 (Egress Edge) 返回大廳
    @patch("states.handlers.lord_boss.LordBossHandler.click_and_wait_until_gone")
    def test_lord_boss_handler_egress_from_domain(self, mock_click_gone):
        """
        Given: 狀態機處於 STATE_LORD_BOSS，但實體畫面仍在領地內部 (出現 domains/common/exit_to_lobby.png)
        When: 執行 LordBossHandler.handle
        Then: 觸發領地退場邊 (Egress Edge)，點擊 exit_to_lobby.png 並返回 True
        """
        from states.handlers.lord_boss import LordBossHandler
        self.mock_machine.daily_manager = MagicMock()
        self.mock_machine.get_available_selected_lord_bosses.return_value = ["lord_spider"]
        lord_handler = LordBossHandler(self.mock_machine)
        mock_screen = MagicMock()

        def fake_match(screen, template, threshold=0.8, **kwargs):
            if template == "domains/common/exit_to_lobby.png":
                return (50, 60), 0.90
            return None, 0.0

        lord_handler.matcher.match.side_effect = fake_match
        lord_handler.match_mutually_exclusive_tabs = MagicMock(return_value=(False, None, None, 0.0))
        res = lord_handler.handle(mock_screen, self.rect)
        self.assertTrue(res)
        mock_click_gone.assert_called_once()
        self.assertEqual(mock_click_gone.call_args[0][0], "domains/common/exit_to_lobby.png")


if __name__ == "__main__":
    unittest.main()
