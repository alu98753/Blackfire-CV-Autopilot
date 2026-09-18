import os
import unittest
from unittest.mock import MagicMock, patch

from states.domains.base_domain import BaseDomainStrategy
from states.domains.golden_empire import GoldenEmpireStrategy
from states.domains.generic_domain import GenericDomainStrategy
from states.domains.treasure_subflow import DomainTreasureSubflow
from states.domains import get_domain_strategy
from states.handlers.domain_explore import DomainExploreHandler
from utils.scene_snapshot import _ELEMENT_TEMPLATE_MAP, ElementId
from utils.tier4_config import build_tier4_fallback_config
from cli.tier4_setup import setup_daily_tier4_config
from config import (
    DEFAULTS_PATH,
    PRIMARY_MODES,
    get_domain_mode_configs,
    get_supported_domain_ids,
    get_tier4_domain_options,
    is_supported_domain,
)
import tomllib


class TestDomainCommonBehavior(unittest.TestCase):
    def setUp(self):
        self.mock_handler = MagicMock()
        self.mock_machine = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_machine.matcher = self.mock_matcher
        self.mock_machine.mouse = self.mock_mouse
        self.mock_machine.config = {"type": "domain", "domain": "golden_empire"}
        self.mock_machine.stamina_retreat_start_time = None
        self.mock_machine.need_bag_cleaning = False
        self.mock_machine.capturer = None
        self.mock_handler.machine = self.mock_machine
        self.mock_handler.matcher = self.mock_matcher
        self.mock_handler.mouse = self.mock_mouse
        self.rect = {"left": 100, "top": 100, "width": 800, "height": 600}

    def test_base_domain_strategy_defaults(self):
        """BaseDomainStrategy 預設回傳通用探索按鈕路徑"""
        strategy = BaseDomainStrategy(self.mock_handler)
        self.assertEqual(strategy.get_explore_button(), "domains/common/explore_btn.png")

    def test_base_domain_handle_explore_click(self):
        """BaseDomainStrategy.handle_explore_click 在畫面上辨識到通用探索按鈕時正確點擊"""
        strategy = BaseDomainStrategy(self.mock_handler)
        mock_img = MagicMock()
        self.mock_matcher.match.return_value = ((300, 400), 0.95)

        with patch("os.path.exists", return_value=True):
            res = strategy.handle_explore_click(mock_img, self.rect)

        self.assertTrue(res)
        self.mock_matcher.match.assert_called_with(mock_img, "domains/common/explore_btn.png", threshold=0.80)
        self.mock_mouse.click.assert_called_with(400, 500)
        self.mock_handler.notify_ui_progress.assert_called_once()

    # =========================================================================
    # Generic Domain Strategy & Validation 測試
    # =========================================================================

    def test_generic_domain_strategy_for_declared_unregistered_domain(self):
        """已宣告但未註冊專屬策略之合法新領域 ➔ 實例化 GenericDomainStrategy，絕不 fallback 成 GoldenEmpireStrategy"""
        mock_declared_modes = {
            "abyss_beast_nest": {
                "name": "淵獸之巢",
                "type": "domain",
                "domain": "abyss_beast_nest",
            }
        }
        with patch.dict(PRIMARY_MODES, mock_declared_modes):
            requested_domain = "abyss_beast_nest"
            strategy = get_domain_strategy(requested_domain, self.mock_handler)

            self.assertIsInstance(strategy, GenericDomainStrategy)
            self.assertNotIsInstance(strategy, GoldenEmpireStrategy)
            self.assertEqual(strategy.domain_name, requested_domain)
            self.assertEqual(strategy.get_explore_button(), "domains/common/explore_btn.png")
            self.assertIsInstance(strategy.treasure_subflow, DomainTreasureSubflow)

    def test_undeclared_domain_fails_fast(self):
        """未在 repository defaults catalog 宣告之非法領域或打錯字 (Typo) ➔ Fail-Fast 拋出 ValueError"""
        with self.assertRaises(ValueError) as ctx:
            get_domain_strategy("nonexistent_typo_domain", self.mock_handler)
        self.assertIn("未宣告或不支援的領域識別碼", str(ctx.exception))

    def test_domain_explore_handler_strategy_stability_with_generic_domain(self):
        """DomainExploreHandler 在合法 generic domain 下不會因 domain_name 不匹配而每 tick 重建 strategy"""
        mock_declared_modes = {
            "abyss_beast_nest": {
                "name": "淵獸之巢",
                "type": "domain",
                "domain": "abyss_beast_nest",
            }
        }
        with patch.dict(PRIMARY_MODES, mock_declared_modes):
            self.mock_machine.config = {
                "type": "domain",
                "domain": "abyss_beast_nest",
                "name": "淵獸之巢",
                "navigation_path": [],
            }
            handler = DomainExploreHandler(self.mock_machine)
            initial_strategy = handler.strategy

            self.assertIsInstance(initial_strategy, GenericDomainStrategy)
            self.assertEqual(initial_strategy.domain_name, "abyss_beast_nest")

            # 模擬兩個 tick 執行 handle，確認 strategy 物件穩定未被反覆重建
            mock_img = MagicMock()
            self.mock_matcher.match.return_value = (None, 0.0)

            handler.handle(mock_img, self.rect)
            self.assertIs(handler.strategy, initial_strategy)

            handler.handle(mock_img, self.rect)
            self.assertIs(handler.strategy, initial_strategy)

    def test_domain_explore_handler_fails_fast_on_missing_domain_config(self):
        """DomainExploreHandler 在 config 缺少 domain 識別碼執行 handle 時 ➔ Fail-Fast 拋出 ValueError"""
        self.mock_machine.config = {"type": "domain"}
        handler = DomainExploreHandler(self.mock_machine)
        with self.assertRaises(ValueError) as ctx:
            handler.handle(MagicMock(), self.rect)
        self.assertIn("缺少必要的 'domain' 識別碼", str(ctx.exception))

    def test_subclass_inherits_common_behavior_without_overrides(self):
        """任何新領地繼承 BaseDomainStrategy 即可自動獲得通用探索按鈕與挖寶事件能力"""
        class MockNewDomainStrategy(BaseDomainStrategy):
            pass

        strategy = MockNewDomainStrategy(self.mock_handler)
        self.assertEqual(strategy.get_explore_button(), "domains/common/explore_btn.png")
        self.assertIsInstance(strategy.treasure_subflow, DomainTreasureSubflow)

        with patch.object(strategy.treasure_subflow, "handle", return_value=True) as mock_handle:
            res = strategy.handle_custom_events(MagicMock(), self.rect)
            self.assertTrue(res)
            mock_handle.assert_called_once()

    def test_golden_empire_inherits_base_and_identifies(self):
        """GoldenEmpireStrategy 繼承 BaseDomainStrategy 並保有古國標識"""
        strategy = GoldenEmpireStrategy(self.mock_handler)
        self.assertEqual(strategy.get_explore_button(), "domains/common/explore_btn.png")
        self.assertEqual(getattr(strategy, "domain_name", None), "golden_empire")
        self.assertIsInstance(strategy.treasure_subflow, DomainTreasureSubflow)

    # =========================================================================
    # Treasure Evidence 語意測試 (A / B / C)
    # =========================================================================

    def test_treasure_evidence_scenario_a_open_actionable(self):
        """場景 A: open.png 存在 ➔ 作為 actionable evidence 依序閉環點擊 open ➔ confirm ➔ quit"""
        subflow = DomainTreasureSubflow(self.mock_handler)
        mock_img = MagicMock()

        called_templates = []
        def fake_click_and_wait(template, x, y, rect, **kwargs):
            called_templates.append(template)
            return True

        self.mock_handler.click_and_wait_until_gone.side_effect = fake_click_and_wait

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template in ["domains/common/open.png", "common/confirm.png", "common/quit.png"]:
                return ((100, 200), 0.95)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            res = subflow.handle(mock_img, self.rect)

        self.assertTrue(res)
        self.assertIn("domains/common/open.png", called_templates)
        self.assertIn("common/confirm.png", called_templates)
        self.assertIn("common/quit.png", called_templates)

    def test_treasure_evidence_scenario_b_find_treasure_scene_evidence_only(self):
        """場景 B: find_treasure.png 存在但 open.png 缺席 ➔ 認領挖寶事件，嚴格 zero mouse/click action"""
        subflow = DomainTreasureSubflow(self.mock_handler)
        mock_img = MagicMock()

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "domains/common/find_treasure.png":
                return ((960, 200), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match
        self.mock_handler.click_and_wait_until_gone = MagicMock()

        with patch("os.path.exists", return_value=True):
            res = subflow.handle(mock_img, self.rect)

        self.assertTrue(res, "必須認領挖寶場景證據，防止底層盲點主探索按鈕")
        self.assertFalse(self.mock_handler.click_and_wait_until_gone.called)
        self.assertFalse(self.mock_mouse.click.called)

    def test_treasure_evidence_scenario_c_treasure_card_scene_evidence_only(self):
        """場景 C: treasure.png 存在但 open.png 缺席 ➔ 認領挖寶事件，嚴格 zero mouse/click action"""
        subflow = DomainTreasureSubflow(self.mock_handler)
        mock_img = MagicMock()

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "domains/common/treasure.png":
                return ((960, 500), 0.88)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match
        self.mock_handler.click_and_wait_until_gone = MagicMock()

        with patch("os.path.exists", return_value=True):
            res = subflow.handle(mock_img, self.rect)

        self.assertTrue(res, "必須認領挖寶場景證據")
        self.assertFalse(self.mock_handler.click_and_wait_until_gone.called)
        self.assertFalse(self.mock_mouse.click.called)

    # =========================================================================
    # Domain Catalog & Daily Tier 4 動態發現測試
    # =========================================================================

    def test_domain_catalog_discovers_all_declared_domain_modes(self):
        """get_domain_mode_configs 自動動態識別所有 type == 'domain' 的模式，支援 is_supported_domain"""
        mock_modes = {
            "golden_empire": {"name": "黃金古國", "type": "domain", "domain": "golden_empire"},
            "abyss_nest": {"name": "淵獸之巢", "type": "domain", "domain": "abyss_nest"},
            "stage": {"name": "普通關卡", "type": "stage"},
        }
        with patch.dict(PRIMARY_MODES, mock_modes, clear=True):
            domain_configs = get_domain_mode_configs()
            self.assertEqual(set(domain_configs.keys()), {"golden_empire", "abyss_nest"})
            self.assertEqual(get_supported_domain_ids(), {"golden_empire", "abyss_nest"})
            self.assertTrue(is_supported_domain("golden_empire"))
            self.assertTrue(is_supported_domain("abyss_nest"))
            self.assertFalse(is_supported_domain("stage"))
            self.assertFalse(is_supported_domain("nonexistent"))

    def test_dynamic_tier4_domain_options_discovery(self):
        """get_tier4_domain_options 動態產生選單項目，顯示名稱嚴格取自 TOML name"""
        mock_modes = {
            "golden_empire": {"name": "黃金古國", "type": "domain", "domain": "golden_empire"},
            "frost_citadel": {"name": "冷誓要塞", "type": "domain", "domain": "frost_citadel"},
        }
        with patch.dict(PRIMARY_MODES, mock_modes, clear=True):
            options = get_tier4_domain_options()
            self.assertEqual(
                options,
                [("golden_empire", "黃金古國"), ("frost_citadel", "冷誓要塞")],
            )

    def test_tier4_new_generic_domain_selection_has_no_keyerror(self):
        """在 primary_modes 加入新領域後，Daily Tier 4 選單互動解析該領域絕不拋出 KeyError"""
        mock_modes = {
            "golden_empire": {"name": "黃金古國", "type": "domain", "domain": "golden_empire"},
            "abyss_nest": {"name": "淵獸之巢", "type": "domain", "domain": "abyss_nest"},
        }
        with patch.dict(PRIMARY_MODES, mock_modes, clear=True), patch("cli.tier4_setup.persist_mode_updates"):
            daily_config = {
                "tier4_mode": "domain",
                "tier4_domain": "abyss_nest",
            }
            # interactive=False 模擬非互動自動載入
            res = setup_daily_tier4_config(daily_config, interactive=False)
            self.assertEqual(res["tier4_domain"], "abyss_nest")
            self.assertEqual(res["name"], "每日懸賞任務 (Tier 4: 淵獸之巢)")

    def test_cli_discovers_declared_domain_in_mode_choices(self):
        """CLI arguments 解析器 choices 動態包含 PRIMARY_MODES 中宣告的所有模式，且能正確接受新領域模式"""
        from cli.arguments import parse_arguments
        mock_modes = {
            "golden_empire": {"name": "黃金古國", "type": "domain"},
            "abyss_nest": {"name": "淵獸之巢", "type": "domain"},
        }
        with patch.dict(PRIMARY_MODES, mock_modes, clear=True):
            with patch("sys.argv", ["main.py", "--mode", "abyss_nest"]):
                args = parse_arguments()
                self.assertEqual(args.mode, "abyss_nest")

    def test_tier4_fallback_preserves_domain_route_fields(self):
        """Daily Tier 4 fallback 完整保留所選領地的起手按鈕與自訂路由欄位，且不殘留 enable_golden_empire"""
        primary = {
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "abyss_nest",
            "lobby_start_btn": "stages/start.png",  # 原 Daily 起手按鈕
            "enable_dungeon": True,
        }
        modes = {
            "abyss_nest": {
                "name": "淵獸之巢",
                "type": "domain",
                "domain": "abyss_nest",
                "bread_cost": 4,
                "navigation_path": ["common/door.png", "domains/abyss_nest/entry.png"],
                "lobby_start_btn": "domains/common/start_btn.png",
                "domain_entry_btn": "domains/abyss_nest/entry.png",
                "domain_reset_max_attempts": 5,
            }
        }
        fallback = build_tier4_fallback_config(primary, modes)

        self.assertEqual(fallback["type"], "domain")
        self.assertEqual(fallback["domain"], "abyss_nest")
        self.assertEqual(fallback["bread_cost"], 4)
        self.assertEqual(fallback["lobby_start_btn"], "domains/common/start_btn.png")
        self.assertEqual(fallback["domain_entry_btn"], "domains/abyss_nest/entry.png")
        self.assertEqual(fallback["domain_reset_max_attempts"], 5)
        self.assertNotIn("enable_golden_empire", fallback)

    def test_invalid_tier4_domain_fails_deterministically(self):
        """配置不存在之 tier4_domain 時 ➔ build_tier4_fallback_config 拋出明確 ValueError (Fail-Fast)"""
        primary = {
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "unknown_typo_domain",
        }
        modes = {
            "golden_empire": {"name": "黃金古國", "type": "domain", "domain": "golden_empire"}
        }
        with self.assertRaises(ValueError) as ctx:
            build_tier4_fallback_config(primary, modes)
        self.assertIn("無效的 Daily Tier 4 領地設定", str(ctx.exception))

    # =========================================================================
    # Strict SSOT Invariant Tests
    # =========================================================================

    def test_strict_ssot_invariant_element_map(self):
        """[SSOT Invariant] ElementId.DOMAIN_EXPLORE_BTN 嚴格映射為 domains/common/explore_btn.png"""
        self.assertEqual(_ELEMENT_TEMPLATE_MAP["domains/common/explore_btn.png"], ElementId.DOMAIN_EXPLORE_BTN)
        self.assertNotIn("domains/golden_empire/explore_btn.png", _ELEMENT_TEMPLATE_MAP)

    def test_strict_ssot_invariant_config_defaults(self):
        """[SSOT Invariant] config/defaults.toml 中的 explore_priorities 嚴格映射為 domains/common/explore_btn.png"""
        with open(DEFAULTS_PATH, "rb") as f:
            data = tomllib.load(f)
        ge_cfg = data.get("primary_modes", {}).get("golden_empire", {})
        priorities = ge_cfg.get("explore_priorities", [])
        self.assertIn("domains/common/explore_btn.png", priorities)
        self.assertNotIn("domains/golden_empire/explore_btn.png", priorities)
        self.assertEqual(priorities, ["domains/common/explore_btn.png"])

    def test_strict_ssot_invariant_disk_assets(self):
        """[SSOT Invariant] 磁碟上 4 個檔案嚴格存在於 domains/common，且不存在於 domains/golden_empire"""
        common_templates_dir = os.path.join("templates", "domains", "common")
        ge_templates_dir = os.path.join("templates", "domains", "golden_empire")

        target_files = [
            "explore_btn.png",
            "open.png",
            "find_treasure.png",
            "treasure.png",
        ]

        for fname in target_files:
            common_path = os.path.join(common_templates_dir, fname)
            ge_path = os.path.join(ge_templates_dir, fname)
            self.assertTrue(os.path.exists(common_path), f"Expected common asset {common_path} to exist")
            self.assertFalse(os.path.exists(ge_path), f"Obsolete asset {ge_path} must NOT exist")

    def test_strict_ssot_invariant_source_reference_cleanliness(self):
        """[SSOT Invariant] 程式碼與設定檔中嚴禁存在任何舊版 golden_empire 模板路徑字串與 enable_golden_empire"""
        obsolete_references = [
            "domains/golden_empire/explore_btn.png",
            "domains/golden_empire/open.png",
            "domains/golden_empire/find_treasure.png",
            "domains/golden_empire/treasure.png",
            "enable_golden_empire",
        ]
        scanned_dirs = ["states", "utils", "config"]
        for s_dir in scanned_dirs:
            for root, _, files in os.walk(s_dir):
                for f in files:
                    if f.endswith((".py", ".toml")):
                        f_path = os.path.join(root, f)
                        with open(f_path, "r", encoding="utf-8", errors="ignore") as file_obj:
                            content = file_obj.read()
                        for obsolete in obsolete_references:
                            self.assertNotIn(
                                obsolete,
                                content,
                                f"Found obsolete reference '{obsolete}' in {f_path}"
                            )


if __name__ == "__main__":
    unittest.main()
