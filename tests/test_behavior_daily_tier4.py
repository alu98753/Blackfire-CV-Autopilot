"""Daily Tier 4 player selection and route behavior."""

import unittest
from unittest.mock import MagicMock, patch

from cli.tier4_setup import setup_daily_tier4_config
from states.state_machine import GameStateMachine
from utils.tier4_config import build_tier4_fallback_config


class TestDailyTier4Behavior(unittest.TestCase):
    @patch("cli.tier4_setup.setup_stage_config")
    @patch("cli.tier4_setup.persist_mode_updates")
    @patch("builtins.input", return_value="1")
    def test_stage_mode_opens_stage_submenu_and_persists_player_choice(
        self, _input, persist, setup_stage
    ):
        config = {
            "_config_mode_key": "daily",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_stage_farming": False,
        }
        setup_stage.side_effect = lambda cfg, **_kwargs: cfg.update(
            {"stage_name": "冰凍峽谷 (final)"}
        )

        setup_daily_tier4_config(config)

        setup_stage.assert_called_once()
        persist.assert_called_once_with(
            config, {"tier4_mode": "stage", "enable_stage_farming": True}
        )
        self.assertEqual(config["tier4_mode"], "stage")
        self.assertTrue(config["enable_stage_farming"])

    @patch("cli.tier4_setup.persist_mode_updates")
    @patch("builtins.input", side_effect=["2", "1"])
    def test_domain_mode_opens_domain_submenu_and_persists_player_choice(
        self, _input, persist
    ):
        config = {
            "_config_mode_key": "daily",
            "tier4_mode": "stage",
            "tier4_stage_level": 6,
            "enable_stage_farming": True,
        }

        setup_daily_tier4_config(config)

        persist.assert_called_once_with(
            config,
            {
                "tier4_mode": "domain",
                "tier4_domain": "golden_empire",
                "enable_stage_farming": False,
            },
        )
        self.assertEqual(config["tier4_domain"], "golden_empire")
        self.assertFalse(config["enable_stage_farming"])

    def test_domain_fallback_preserves_daily_timed_activity_policy(self):
        daily = {
            "_config_mode_key": "daily",
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_dungeon": True,
            "enable_lord_boss": False,
            "keep_colors": ["purple"],
        }
        modes = {
            "golden_empire": {
                "name": "黃金古國",
                "type": "domain",
                "domain": "golden_empire",
                "navigation_path": ["domains/golden_empire/entry.png"],
                "explore_priorities": ["domains/golden_empire/explore_btn.png"],
            }
        }

        fallback = build_tier4_fallback_config(daily, modes)

        self.assertEqual(fallback["type"], "domain")
        self.assertEqual(fallback["domain"], "golden_empire")
        self.assertTrue(fallback["enable_dungeon"])
        self.assertFalse(fallback["enable_lord_boss"])
        self.assertEqual(fallback["keep_colors"], ["purple"])

    def test_domain_fallback_remains_daily_and_checks_dungeon_policy(self):
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.daily_manager = MagicMock()
        machine.runtime_config_key = "daily"
        machine.primary_config = {
            "_config_mode_key": "daily",
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_dungeon": True,
            "enable_lord_boss": True,
            "dungeon_entries": ["dungeons/Slime_entry.png"],
            "dungeon_names": ["Slime"],
            "greedy_dungeon": True,
            "greedy_allowed_indices": [0],
        }

        machine.apply_tier4_fallback_config()

        self.assertEqual(machine.config["type"], "domain")
        self.assertTrue(machine.config["is_tier4_fallback"])
        self.assertTrue(machine.is_daily_pipeline_active())
        self.assertTrue(machine.has_available_daily_dungeon())

    def test_ready_timed_dungeon_preempts_domain_route(self):
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.daily_manager = MagicMock()
        machine.daily_manager.get_pending_town_subflows.return_value = []
        machine.daily_manager.get_available_lord_bosses.return_value = []
        machine.runtime_config_key = "daily"
        machine.primary_config = {
            "_config_mode_key": "daily",
            "name": "Daily",
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_town_daily": False,
            "enable_demon_lords": False,
            "enable_lord_boss": False,
            "enable_dungeon": True,
            "dungeon_entries": ["dungeons/Slime_entry.png"],
            "dungeon_names": ["Slime"],
            "greedy_dungeon": True,
            "greedy_allowed_indices": [0],
        }
        machine.apply_tier4_fallback_config()
        machine.current_state = machine.STATE_DOMAIN_EXPLORE

        self.assertTrue(machine.evaluate_next_activity())

        self.assertEqual(machine.config["type"], "mix")
        self.assertEqual(
            machine.config["navigation_path"],
            ["common/door.png", "dungeons/dungeon.png"],
        )
        self.assertTrue(machine.config["is_tier4_fallback"])

    def test_daily_profile_can_disable_timed_lord_activity(self):
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.runtime_config_key = "daily"
        machine.primary_config = {
            "_config_mode_key": "daily",
            "enable_lord_boss": False,
            "lord_boss_targets": ["lord_spider"],
        }
        machine.config = {
            "type": "domain",
            "enable_lord_boss": False,
            "lord_boss_targets": ["lord_spider"],
        }
        machine.daily_manager = MagicMock()
        machine.daily_manager.get_available_lord_bosses.return_value = ["lord_spider"]

        self.assertEqual(machine.get_available_selected_lord_bosses(), [])
        self.assertFalse(machine.has_available_selected_lord_boss())

    @patch("cli.mode_setup.setup_daily_tier4_config")
    @patch("cli.mode_setup.setup_dungeon_config")
    def test_daily_mode_prompts_dungeon_selection_when_enabled(
        self, mock_setup_dungeon, mock_setup_tier4
    ):
        from cli.mode_setup import setup_mode_config

        args = MagicMock()
        args.subflow = None
        args.mode = "daily"
        args.backend = "win32"
        args.enable_lord_boss = None
        args.enable_dungeon = None
        args.enable_stage_farming = None
        args.enable_town_daily = None
        args.enable_demon_lords = None
        args.resume = False

        cfg = setup_mode_config(args)

        mock_setup_dungeon.assert_called_once_with(cfg, args, allow_disable=True)
        mock_setup_tier4.assert_called_once_with(cfg)

    def test_stage_fallback_has_stage_type_and_clean_navigation_path(self):
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.daily_manager = MagicMock()
        machine.runtime_config_key = "daily"
        machine.primary_config = {
            "_config_mode_key": "daily",
            "name": "每日懸賞任務",
            "type": "mix",
            "tier4_mode": "stage",
            "tier4_stage_level": 4,
            "tier4_sub_stage": "final",
            "enable_stage_farming": True,
            "enable_dungeon": False,
            "greedy_dungeon": True,
            "greedy_allowed_indices": [1, 2, 3, 4, 5, 6],
            "dungeon_entries": ["dungeons/Slime_entry.png"],
            "dungeon_names": ["Slime"],
        }
        machine.apply_tier4_fallback_config()

        self.assertEqual(machine.config["type"], "stage")
        self.assertEqual(machine.config["tier4_mode"], "stage")
        self.assertTrue(machine.config["is_tier4_fallback"])
        self.assertFalse(machine.config["greedy_dungeon"])
        self.assertNotIn("dungeons/dungeon.png", machine.config["navigation_path"])
        self.assertIn("stages/level4_desert_ruins.png", machine.config["navigation_path"])
        self.assertIn("stages/boss_skull.png", machine.config["navigation_path"])

    def test_disabled_dungeon_policy_strictly_rejects_has_available_dungeon(self):
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.primary_config = {
            "type": "mix",
            "enable_dungeon": False,
            "greedy_dungeon": True,
            "greedy_allowed_indices": [1, 2, 3],
        }
        machine.config = machine.primary_config.copy()
        machine.dungeon_cooldowns = {1: 0.0, 2: 0.0, 3: 0.0}

        self.assertFalse(machine.has_available_dungeon())
        self.assertFalse(machine.has_available_dungeon(target_config=machine.primary_config))

    def test_daily_disabled_dungeon_stage_fallback_in_navigation_alignment(self):
        from states.handlers import NavigationHandler
        from utils.scene_detector import SceneInfo, SceneType

        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.primary_config = {
            "_config_mode_key": "daily",
            "type": "mix",
            "tier4_mode": "stage",
            "tier4_stage_level": 4,
            "tier4_sub_stage": "final",
            "enable_stage_farming": True,
            "enable_dungeon": False,
        }
        machine.apply_tier4_fallback_config()

        handler = NavigationHandler(machine)
        fake_scene = SceneInfo(
            scene_type=SceneType.LOBBY_STAGE,
            is_lobby=True,
            active_tabs={"stage"},
        )
        from utils.card_navigator import CardAlignmentStatus
        with patch("utils.card_navigator.CardListNavigator.align_first_card", return_value=(CardAlignmentStatus.ALIGNED, 0, 1.0)):
            handler._handle_primary_card_alignment(None, {"left": 0, "top": 0}, fake_scene)
            self.assertEqual(handler.card_alignment_target_tab, "stage")
            self.assertEqual(handler.card_alignment_tab, "stage")


    def test_tier4_stage_with_enable_dungeon_true_exits_on_cooldown_ready(self):
        import numpy as np
        from states.handlers.result import ResultHandler

        machine = GameStateMachine(MagicMock(), MagicMock(), MagicMock(), preload_ocr=False)
        machine.primary_config = {
            "_config_mode_key": "daily",
            "type": "daily",
            "tier4_mode": "stage",
            "enable_stage_farming": True,
            "enable_dungeon": True,
            "greedy_dungeon": True,
            "greedy_allowed_indices": [1, 2],
            "dungeon_entries": ["dungeons/Ice_entry.png"],
            "dungeon_names": ["Ice"],
        }
        machine.config = {
            "name": "Tier 4 退守",
            "type": "stage",
            "is_tier4_fallback": True,
            "enable_stage_farming": True,
            "enable_dungeon": True,
            "greedy_dungeon": False,
        }
        machine.dungeon_cooldowns = {1: 0.0}
        machine.quest_scheduler = None
        machine.daily_manager = MagicMock()
        machine.daily_manager.is_subflow_completed.return_value = True
        machine.daily_manager.has_available_lord_boss.return_value = False
        machine.daily_manager.has_available_demon_lords.return_value = False
        machine.daily_manager.get_pending_town_subflows.return_value = []

        self.assertTrue(machine.has_available_daily_dungeon())

        handler = ResultHandler(machine)
        handler.subflow_step = "FINAL_MATCH"
        machine.transition_to = MagicMock()

        def match_exit_or_retry(_screen, template, **_kwargs):
            if template == "exit_battle.png":
                return (500, 500), 0.95
            if template == "stages/retry.png":
                return (700, 500), 0.95
            return None, 0.0

        machine.matcher.match.side_effect = match_exit_or_retry
        fake_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        with patch("os.path.exists", return_value=True), \
             patch.object(handler, "click_and_wait_until_gone") as mock_click:
            handler.handle(fake_screen, rect)

            mock_click.assert_called_once()
            self.assertEqual(mock_click.call_args[0][0], "exit_battle.png")
            machine.transition_to.assert_called_once_with(machine.STATE_NAVIGATING)

    def test_tier4_stage_with_enable_dungeon_false_retries_stage(self):
        import numpy as np
        from states.handlers.result import ResultHandler

        machine = GameStateMachine(MagicMock(), MagicMock(), MagicMock(), preload_ocr=False)
        machine.primary_config = {
            "_config_mode_key": "daily",
            "type": "daily",
            "tier4_mode": "stage",
            "enable_stage_farming": True,
            "enable_dungeon": False,
        }
        machine.config = {
            "name": "Tier 4 退守",
            "type": "stage",
            "is_tier4_fallback": True,
            "enable_stage_farming": True,
            "enable_dungeon": False,
        }
        machine.dungeon_cooldowns = {1: 0.0}
        machine.quest_scheduler = None
        machine.daily_manager = MagicMock()
        machine.daily_manager.is_subflow_completed.return_value = True
        machine.daily_manager.has_available_lord_boss.return_value = False
        machine.daily_manager.has_available_demon_lords.return_value = False
        machine.daily_manager.get_pending_town_subflows.return_value = []

        self.assertFalse(machine.has_available_daily_dungeon())

        handler = ResultHandler(machine)
        handler.subflow_step = "FINAL_MATCH"
        machine.transition_to = MagicMock()

        def match_exit_or_retry(_screen, template, **_kwargs):
            if template == "exit_battle.png":
                return (500, 500), 0.95
            if template == "stages/retry.png":
                return (700, 500), 0.95
            return None, 0.0

        machine.matcher.match.side_effect = match_exit_or_retry
        fake_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        with patch("os.path.exists", return_value=True), \
             patch.object(handler, "click_and_wait_until_gone") as mock_click:
            handler.handle(fake_screen, rect)

            mock_click.assert_called_once()
            self.assertEqual(mock_click.call_args[0][0], "stages/retry.png")
            machine.transition_to.assert_called_once_with(machine.STATE_LOADING)

    def test_tier4_config_preserves_enable_dungeon_in_stage_and_domain(self):
        mode_configs = {
            "stage": {"name": "關卡", "type": "stage"},
            "golden_empire": {"name": "黃金帝國", "type": "domain"},
        }
        # Stage fallback with enable_dungeon True/False
        stage_cfg_true = {"tier4_mode": "stage", "enable_dungeon": True}
        stage_fb_true = build_tier4_fallback_config(stage_cfg_true, mode_configs)
        self.assertTrue(stage_fb_true["enable_dungeon"])
        self.assertEqual(stage_fb_true["type"], "stage")

        stage_cfg_false = {"tier4_mode": "stage", "enable_dungeon": False}
        stage_fb_false = build_tier4_fallback_config(stage_cfg_false, mode_configs)
        self.assertFalse(stage_fb_false["enable_dungeon"])
        self.assertEqual(stage_fb_false["type"], "stage")

        # Domain fallback with enable_dungeon True/False
        domain_cfg_true = {"tier4_mode": "domain", "enable_dungeon": True}
        domain_fb_true = build_tier4_fallback_config(domain_cfg_true, mode_configs)
        self.assertTrue(domain_fb_true["enable_dungeon"])
        self.assertEqual(domain_fb_true["type"], "domain")

        domain_cfg_false = {"tier4_mode": "domain", "enable_dungeon": False}
        domain_fb_false = build_tier4_fallback_config(domain_cfg_false, mode_configs)
        self.assertFalse(domain_fb_false["enable_dungeon"])
        self.assertEqual(domain_fb_false["type"], "domain")


    def test_has_available_dungeon_reads_correct_cooldown_for_tier4_dungeon_index(self):
        """驗證 has_available_dungeon 正確讀取 tier4_dungeon_index 的冷卻，而非誤讀史萊姆 (index=1) 的 0.0。"""
        import time

        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        now = time.time()
        machine.primary_config = {
            "type": "mix",
            "enable_dungeon": True,
            "greedy_dungeon": False,
            "tier4_dungeon_index": 6,
            "navigation_path": [
                "common/door.png",
                "dungeons/dungeon.png",
                "dungeons/Slime_entry.png",
            ],
            "dungeon_entries": [
                "dungeons/Slime_entry.png",
                "dungeons/Ghost_entry.png",
                "dungeons/Forest_entry.png",
                "dungeons/Ruins_entry.png",
                "dungeons/dark_prison.png",
                "dungeons/Ice_entry.png",
                "dungeons/orc_bunker.png",
            ],
        }
        # 第 1 號史萊姆無冷卻 (0.0)，第 6 號冰雪洞窟冷卻中 (剩餘 28 分鐘)
        machine.dungeon_cooldowns = {1: 0.0, 6: now + 1715.0}

        # 必須正確讀取 6 號冷卻，堅決回傳 False
        self.assertFalse(
            machine.has_available_dungeon(target_config=machine.primary_config)
        )

        # 當第 6 號冰雪洞窟冷卻結束時，回傳 True
        machine.dungeon_cooldowns[6] = now - 10.0
        self.assertTrue(
            machine.has_available_dungeon(target_config=machine.primary_config)
        )

    def test_domain_explore_keeps_farming_during_dungeon_cooldown(self):
        """驗證地下城冷卻中時，領地探索不發起插隊，穩定在黃金古國中掛機。"""
        import time
        from states.handlers.domain_explore import DomainExploreHandler

        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.daily_manager = MagicMock()
        machine.daily_manager.is_subflow_completed.return_value = True
        machine.daily_manager.has_available_lord_boss.return_value = False
        machine.daily_manager.has_available_demon_lords.return_value = False
        machine.daily_manager.get_pending_town_subflows.return_value = []
        now = time.time()
        machine.runtime_config_key = "daily"
        machine.primary_config = {
            "_config_mode_key": "daily",
            "name": "Daily",
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_town_daily": False,
            "enable_demon_lords": False,
            "enable_lord_boss": False,
            "enable_dungeon": True,
            "greedy_dungeon": False,
            "tier4_dungeon_index": 6,
            "navigation_path": [
                "common/door.png",
                "dungeons/dungeon.png",
                "dungeons/Slime_entry.png",
            ],
            "dungeon_entries": [
                "dungeons/Slime_entry.png",
                "dungeons/Ghost_entry.png",
                "dungeons/Forest_entry.png",
                "dungeons/Ruins_entry.png",
                "dungeons/dark_prison.png",
                "dungeons/Ice_entry.png",
                "dungeons/orc_bunker.png",
            ],
            "dungeon_names": ["Slime", "Ghost", "Forest", "Ruins", "Prison", "Ice", "Orc"],
        }
        machine.apply_tier4_fallback_config()
        machine.current_state = machine.STATE_DOMAIN_EXPLORE
        machine.dungeon_cooldowns = {1: 0.0, 6: now + 1715.0}

        # 6 號冷卻中 ➔ 無可用地下城且無插隊活動
        self.assertFalse(machine.has_available_daily_dungeon())
        self.assertFalse(machine.has_pending_daily_activity())

        handler = DomainExploreHandler(machine)
        # 領地探索檢查插隊回傳 False (不離場)
        fake_rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        self.assertFalse(handler._check_lord_boss_preemption(None, fake_rect))
        self.assertEqual(machine.current_state, machine.STATE_DOMAIN_EXPLORE)

    def test_domain_explore_preempts_when_dungeon_cooldown_expires(self):
        """驗證地下城冷卻結束時，領地探索正常發動定時插隊退出古國。"""
        import time
        import numpy as np
        from states.handlers.domain_explore import DomainExploreHandler

        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.daily_manager = MagicMock()
        machine.daily_manager.is_subflow_completed.return_value = True
        machine.daily_manager.has_available_lord_boss.return_value = False
        machine.daily_manager.has_available_demon_lords.return_value = False
        machine.daily_manager.get_pending_town_subflows.return_value = []
        now = time.time()
        machine.runtime_config_key = "daily"
        machine.primary_config = {
            "_config_mode_key": "daily",
            "name": "Daily",
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_town_daily": False,
            "enable_demon_lords": False,
            "enable_lord_boss": False,
            "enable_dungeon": True,
            "greedy_dungeon": False,
            "tier4_dungeon_index": 6,
            "navigation_path": [
                "common/door.png",
                "dungeons/dungeon.png",
                "dungeons/Slime_entry.png",
            ],
            "dungeon_entries": [
                "dungeons/Slime_entry.png",
                "dungeons/Ghost_entry.png",
                "dungeons/Forest_entry.png",
                "dungeons/Ruins_entry.png",
                "dungeons/dark_prison.png",
                "dungeons/Ice_entry.png",
                "dungeons/orc_bunker.png",
            ],
            "dungeon_names": ["Slime", "Ghost", "Forest", "Ruins", "Prison", "Ice", "Orc"],
        }
        machine.apply_tier4_fallback_config()
        machine.current_state = machine.STATE_DOMAIN_EXPLORE
        # 6 號冷卻已結束
        machine.dungeon_cooldowns = {1: 0.0, 6: now - 10.0}

        self.assertTrue(machine.has_available_daily_dungeon())
        self.assertTrue(machine.has_pending_daily_activity())

        handler = DomainExploreHandler(machine)
        handler.click_and_wait_until_gone = MagicMock()

        def fake_match(_screen, template, **_kwargs):
            if template == "domains/common/exit_to_lobby.png":
                return (66, 724), 0.95
            return None, 0.0

        machine.matcher.match.side_effect = fake_match
        fake_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        fake_rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        with patch("os.path.exists", return_value=True):
            res = handler._check_lord_boss_preemption(fake_screen, fake_rect)
            self.assertTrue(res)
            handler.click_and_wait_until_gone.assert_called_once()
            self.assertEqual(machine.current_state, machine.STATE_NAVIGATING)

    def test_collect_only_stamina_retreat_auto_resumes_dungeon_when_tier4_is_domain(self):
        """
        驗證當 Daily 模式採用 tier4_mode = 'domain' 且處於體力退避期間，
        若地下城冷卻結束 (auto_resume_dungeon_on_cd=True)，
        CollectOnlyHandler 能正確喚醒切回地下城探索路由 (type=mix, navigation_path 包含地下城)，
        而非誤判為 domain 路由或維持在待機。
        """
        import time
        from copy import deepcopy
        from config import GAME_CONFIGS
        from states.handlers.collect_only import CollectOnlyHandler

        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.runtime_config_key = "daily"
        now = time.time()
        machine.primary_config = {
            "_config_mode_key": "daily",
            "name": "每日懸賞任務",
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "greedy_dungeon": True,
            "greedy_allowed_indices": [6, 7],
            "auto_resume_dungeon_on_cd": True,
            "enable_dungeon": True,
            "enable_bread": False,
            "enable_diamond": False,
            "dungeon_entries": [
                "dungeons/Slime_entry.png",
                "dungeons/Ghost_entry.png",
                "dungeons/Forest_entry.png",
                "dungeons/Ruins_entry.png",
                "dungeons/dark_prison.png",
                "dungeons/Ice_entry.png",
                "dungeons/orc_bunker.png",
            ],
            "dungeon_names": ["Slime", "Ghost", "Forest", "Ruins", "Prison", "Ice", "Orc"],
        }
        # 建立退守 domain 路由
        machine.apply_tier4_fallback_config()
        self.assertEqual(machine.config["type"], "domain")

        # 模擬進入體力退避
        retreat_start = now - 600.0
        machine.original_config = deepcopy(machine.config)
        machine.stamina_retreat_start_time = retreat_start
        machine.config = GAME_CONFIGS["collect_only"].copy()
        machine.current_state = machine.STATE_COLLECT_ONLY
        machine.need_diamond_collection = False
        machine.need_bread_collection = False
        machine.last_state_change = now - 2.0

        # 設定地下城 6 冷卻已結束
        machine.dungeon_cooldowns = {6: now - 50.0, 7: now + 500.0}

        fake_screen = MagicMock()
        fake_rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        machine.matcher.match.return_value = (None, 0.0)

        handler = CollectOnlyHandler(machine)
        with patch("os.path.exists", return_value=True):
            handler.handle(fake_screen, fake_rect)

        # 斷言：成功喚醒轉入 STATE_UNKNOWN，並切換為乾淨的地下城探索路由 (type=mix)
        self.assertEqual(machine.current_state, machine.STATE_UNKNOWN)
        self.assertEqual(machine.config["type"], "mix")
        self.assertTrue(machine.config.get("is_tier4_fallback"))
        self.assertEqual(
            machine.config["navigation_path"],
            ["common/door.png", "dungeons/dungeon.png"],
        )
        # 斷言：原始退避配置與時間戳持續保留
        self.assertEqual(machine.original_config["type"], "domain")
        self.assertEqual(machine.stamina_retreat_start_time, retreat_start)

    def test_collect_only_idle_auto_resumes_dungeon_when_enable_stage_farming_false(self):
        """
        驗證當 Daily 模式在 enable_stage_farming = False 且地下城全冷卻而轉入 COLLECT_ONLY 待機時，
        當地下城冷卻結束，CollectOnlyHandler 能主動喚醒轉入 NAVIGATING 前往地下城。
        """
        import time
        from config import GAME_CONFIGS
        from states.handlers.collect_only import CollectOnlyHandler

        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.runtime_config_key = "daily"
        now = time.time()
        machine.primary_config = {
            "_config_mode_key": "daily",
            "name": "每日懸賞任務",
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_stage_farming": False,
            "greedy_dungeon": True,
            "greedy_allowed_indices": [6, 7],
            "auto_resume_dungeon_on_cd": True,
            "enable_dungeon": True,
            "enable_bread": False,
            "enable_diamond": False,
            "dungeon_entries": [
                "dungeons/Slime_entry.png",
                "dungeons/Ghost_entry.png",
                "dungeons/Forest_entry.png",
                "dungeons/Ruins_entry.png",
                "dungeons/dark_prison.png",
                "dungeons/Ice_entry.png",
                "dungeons/orc_bunker.png",
            ],
            "dungeon_names": ["Slime", "Ghost", "Forest", "Ruins", "Prison", "Ice", "Orc"],
        }
        machine.quest_scheduler = None
        machine.original_config = None
        machine.stamina_retreat_start_time = None
        machine.config = GAME_CONFIGS["collect_only"].copy()
        machine.current_state = machine.STATE_COLLECT_ONLY
        machine.need_diamond_collection = False
        machine.need_bread_collection = False
        machine.last_state_change = now - 2.0

        # 地下城 7 冷卻結束
        machine.dungeon_cooldowns = {6: now + 500.0, 7: now - 20.0}

        fake_screen = MagicMock()
        fake_rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        machine.matcher.match.return_value = (None, 0.0)

        handler = CollectOnlyHandler(machine)
        with patch("os.path.exists", return_value=True):
            handler.handle(fake_screen, fake_rect)

        # 斷言：成功喚醒轉入 STATE_NAVIGATING，並已載入地下城探索路由
        self.assertEqual(machine.current_state, machine.STATE_NAVIGATING)
        self.assertEqual(machine.config["type"], "mix")
        self.assertTrue(machine.config.get("is_tier4_fallback"))
        self.assertEqual(
            machine.config["navigation_path"],
            ["common/door.png", "dungeons/dungeon.png"],
        )

    def test_has_available_dungeon_allows_domain_tier4_fallback_with_dungeon(self):
        """
        驗證 has_available_dungeon 對於 type == 'domain' 但具備地下城設定之 Daily 退守路由，
        能正確檢查冷卻狀態而非直接回傳 False。
        """
        import time
        now = time.time()
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        domain_tier4_cfg = {
            "type": "domain",
            "tier4_mode": "domain",
            "enable_dungeon": True,
            "greedy_dungeon": True,
            "greedy_allowed_indices": [6, 7],
            "dungeon_entries": [
                "dungeons/Slime_entry.png",
                "dungeons/Ghost_entry.png",
                "dungeons/Forest_entry.png",
                "dungeons/Ruins_entry.png",
                "dungeons/dark_prison.png",
                "dungeons/Ice_entry.png",
                "dungeons/orc_bunker.png",
            ],
        }

        # 冷卻中 ➔ 回傳 False
        machine.dungeon_cooldowns = {6: now + 200.0, 7: now + 300.0}
        self.assertFalse(machine.has_available_dungeon(target_config=domain_tier4_cfg))

        # 地下城 6 冷卻結束 ➔ 回傳 True
        machine.dungeon_cooldowns = {6: now - 10.0, 7: now + 300.0}
        self.assertTrue(machine.has_available_dungeon(target_config=domain_tier4_cfg))

    @patch("cli.tier4_setup.persist_mode_updates")
    @patch("builtins.input", return_value="3")
    def test_none_mode_persists_player_choice_and_disables_stage_farming(
        self, _input, persist
    ):
        config = {
            "_config_mode_key": "daily",
            "tier4_mode": "stage",
            "tier4_stage_level": 6,
            "enable_stage_farming": True,
        }

        setup_daily_tier4_config(config)

        persist.assert_called_once_with(
            config,
            {
                "tier4_mode": "none",
                "enable_stage_farming": False,
            },
        )
        self.assertEqual(config["tier4_mode"], "none")
        self.assertFalse(config["enable_stage_farming"])
        self.assertIn("無 Tier 4 長駐", config["name"])

    def test_build_tier4_fallback_config_none_mode(self):
        daily = {
            "_config_mode_key": "daily",
            "type": "mix",
            "tier4_mode": "none",
            "enable_dungeon": True,
            "enable_stage_farming": False,
        }
        modes = {}

        fallback = build_tier4_fallback_config(daily, modes)

        self.assertEqual(fallback["type"], "collect_only")
        self.assertEqual(fallback["tier4_mode"], "none")
        self.assertFalse(fallback["enable_stage_farming"])
        self.assertFalse(fallback["enable_golden_empire"])
        self.assertTrue(fallback["enable_dungeon"])

    def test_build_tier4_fallback_config_stage_coherence_and_pure_dungeon(self):
        # 測試 1: 原配置為純地下城 (type="dungeon")，退守時保持純地下城配置
        pure_dungeon = {
            "type": "dungeon",
            "name": "地下城",
            "navigation_path": ["dungeons/dungeon.png", "dungeons/Ice_entry.png"],
            "dungeon_templates": ["dungeons/Ice_entry.png"],
        }
        fallback1 = build_tier4_fallback_config(pure_dungeon, {})
        self.assertEqual(fallback1["type"], "dungeon")
        self.assertEqual(fallback1["navigation_path"], pure_dungeon["navigation_path"])

        # 測試 2: 原配置為 mix/daily，其 navigation_path 原本為地下城路徑
        # 退守為 stage 後，navigation_path 必須是 canonical stage 路由，絕不包含地下城入口！
        mix_with_dungeon_path = {
            "_config_mode_key": "daily",
            "type": "mix",
            "tier4_mode": "stage",
            "navigation_path": ["common/door.png", "dungeons/dungeon.png", "dungeons/Ice_entry.png"],
            "stage_navigation_path": [
                "common/door.png",
                "common/select_stage.png",
                "stages/level6_ice_cave.png",
                "stages/stage_label.png",
                "stages/first_stage.png",
            ],
            "enable_dungeon": True,
        }
        mode_configs = {
            "stage": {
                "name": "普通關卡",
                "type": "stage",
                "navigation_path": ["common/door.png", "common/select_stage.png", "stages/level1.png"],
                "stage_templates": ["stages/level1.png"],
            }
        }
        fallback2 = build_tier4_fallback_config(mix_with_dungeon_path, mode_configs)
        self.assertEqual(fallback2["type"], "stage")
        self.assertEqual(fallback2["tier4_mode"], "stage")
        self.assertTrue(fallback2["enable_stage_farming"])
        # Invariant 驗證：navigation_path 不得包含任何 dungeon entry，而是 canonical stage 路由
        self.assertNotIn("dungeons/dungeon.png", fallback2["navigation_path"])
        self.assertNotIn("dungeons/Ice_entry.png", fallback2["navigation_path"])
        self.assertEqual(fallback2["navigation_path"], mix_with_dungeon_path["stage_navigation_path"])

    def test_evaluate_next_activity_enters_collect_only_when_tier4_none_and_activities_on_cooldown(self):
        import time
        now = time.time()
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.daily_manager = MagicMock()
        machine.daily_manager.get_pending_town_subflows.return_value = []
        machine.daily_manager.is_demon_lords_available.return_value = (False, "已無次數")
        machine.daily_manager.get_available_lord_bosses.return_value = []
        machine.runtime_config_key = "daily"
        machine.primary_config = {
            "_config_mode_key": "daily",
            "type": "mix",
            "tier4_mode": "none",
            "enable_dungeon": True,
            "enable_town_daily": True,
            "enable_lord_boss": True,
            "greedy_dungeon": True,
            "greedy_allowed_indices": [6],
            "dungeon_entries": ["dungeons/Ice_entry.png"],
            "dungeon_names": ["Ice"],
        }
        machine.dungeon_cooldowns = {6: now + 600.0}
        machine.current_state = machine.STATE_NAVIGATING
        machine.quest_scheduler = None

        result = machine.evaluate_next_activity()

        self.assertFalse(result)
        self.assertEqual(machine.current_state, machine.STATE_COLLECT_ONLY)

    def test_collect_only_wakes_up_dungeon_when_tier4_none(self):
        import time
        from states.handlers.collect_only import CollectOnlyHandler
        now = time.time()
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.daily_manager = MagicMock()
        machine.daily_manager.get_pending_town_subflows.return_value = []
        machine.daily_manager.is_demon_lords_available.return_value = (False, "已無次數")
        machine.daily_manager.get_available_lord_bosses.return_value = []
        machine.runtime_config_key = "daily"
        daily_cfg = {
            "_config_mode_key": "daily",
            "type": "mix",
            "tier4_mode": "none",
            "enable_dungeon": True,
            "greedy_dungeon": True,
            "greedy_allowed_indices": [6],
            "dungeon_entries": ["dungeons/Ice_entry.png"],
            "dungeon_names": ["Ice"],
        }
        machine.primary_config = daily_cfg
        machine.config = {"type": "collect_only"}
        machine.current_state = machine.STATE_COLLECT_ONLY
        machine.need_diamond_collection = False
        machine.need_bread_collection = False
        machine.enable_bread = False
        # 地下城 6 冷卻已結束
        machine.dungeon_cooldowns = {6: now - 10.0}
        machine.matcher.match.return_value = (None, 0.0)

        handler = CollectOnlyHandler(machine)
        handler.handle(MagicMock(), {"left": 0, "top": 0, "width": 1920, "height": 1080})

        self.assertEqual(machine.current_state, machine.STATE_NAVIGATING)
        self.assertEqual(machine.config["type"], "mix")
        self.assertTrue(machine.config["enable_dungeon"])

    def test_navigation_enters_collect_only_after_dungeon_cooldown_when_tier4_none(self):
        from states.handlers.navigation import NavigationHandler
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.daily_manager = MagicMock()
        machine.runtime_config_key = "daily"
        daily_cfg = {
            "_config_mode_key": "daily",
            "type": "mix",
            "tier4_mode": "none",
            "enable_stage_farming": False,
            "enable_dungeon": True,
            "greedy_dungeon": True,
            "greedy_allowed_indices": [6],
            "dungeon_entries": ["dungeons/Ice_entry.png"],
            "dungeon_names": ["Ice"],
        }
        machine.primary_config = daily_cfg
        machine.config = daily_cfg.copy()
        machine.current_state = machine.STATE_NAVIGATING
        machine.matcher.match.return_value = ((100, 100), 0.95)

        handler = NavigationHandler(machine)
        handler._switch_to_stage_or_back(
            MagicMock(), {"left": 0, "top": 0, "width": 1920, "height": 1080}, "冷卻中"
        )

        self.assertEqual(machine.current_state, machine.STATE_COLLECT_ONLY)
        self.assertEqual(machine.config["type"], "collect_only")

    def test_evaluate_next_activity_pending_town_subflow_blocks_tier4(self):
        """驗證當存在待辦城鎮子流程時，evaluate_next_activity 立即回傳 True，不洩漏至 Tier 4 或懸賞"""
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.current_town_subflow = "chest"
        machine.town_subflow_queue = ["hero_draw"]
        machine.config = {
            "type": "mix",
            "name": "Daily Base",
            "enable_town_daily": True,
            "enable_dungeon": True,
        }
        machine.primary_config = machine.config.copy()

        result = machine.evaluate_next_activity()

        self.assertTrue(result)
        # config 應保持原樣，絕未切換至 Tier 4
        self.assertFalse(machine.config.get("is_tier4_fallback", False))

    def test_evaluate_next_activity_prefers_quest_scheduler_over_tier4_dungeon(self):
        """驗證只要懸賞任務排程器有可用任務，evaluate_next_activity 優先排程懸賞任務，不退守 Tier 4 地下城"""
        from utils.quest_scheduler import QuestScheduler, TaskNode
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.current_town_subflow = None
        machine.town_subflow_queue = []
        
        # 建立一個地下城懸賞任務 (Dungeon #2)
        task = TaskNode(
            quest_title="冰雪懸賞",
            mode_type="dungeon",
            counting_policy="banner_verify_only",
            target_count=20,
            dungeon_index=2,
        )
        scheduler = QuestScheduler()
        scheduler.add_task(task)
        machine.quest_scheduler = scheduler

        machine.config = {
            "type": "mix",
            "name": "Daily Base",
            "enable_town_daily": False,
            "enable_dungeon": True,
            "dungeon_entries": ["dungeons/Ice_entry.png", "dungeons/cave_entry.png"],
            "dungeon_names": ["Ice", "Cave"],
            "greedy_dungeon": True,
            "greedy_allowed_indices": [1, 2],
        }
        machine.primary_config = machine.config.copy()
        machine.has_available_dungeon = MagicMock(return_value=True)

        result = machine.evaluate_next_activity()

        self.assertTrue(result)
        # config 應切換為該懸賞任務，而非 Tier 4 fallback
        self.assertFalse(machine.config.get("is_tier4_fallback", False))
        self.assertIn("冰雪懸賞", machine.config.get("name", ""))
        self.assertEqual(machine.config.get("type"), "dungeon")
        self.assertEqual(machine.config.get("dungeon_index"), 2)


if __name__ == "__main__":
    unittest.main()


