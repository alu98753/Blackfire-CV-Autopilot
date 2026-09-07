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
        self.assertIn("stages/level4_final.png", machine.config["navigation_path"])

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


if __name__ == "__main__":
    unittest.main()


