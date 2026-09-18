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
from utils.tier4_config import (
    build_domain_execution_route,
    build_tier4_fallback_config,
    validate_daily_domain_policy,
)
from cli.tier4_setup import setup_daily_tier4_config
from config import (
    DEFAULTS_PATH,
    DEFAULT_ACTIVITIES,
    PRIMARY_MODES,
    get_canonical_defaults,
    get_canonical_domain_mode_configs,
    get_canonical_supported_domain_ids,
    get_domain_mode_configs,
    get_supported_domain_ids,
    get_tier4_domain_options,
    is_supported_domain,
    normalize_config,
    normalize_domain_execution_config,
    validate_domain_execution_config,
    validate_profile_mode_overrides,
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
        with patch("config.get_canonical_domain_mode_configs", return_value=mock_declared_modes):
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
        with patch("config.get_canonical_domain_mode_configs", return_value=mock_declared_modes):
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
        """get_canonical_domain_mode_configs 自動動態識別所有 type == 'domain' 的模式，支援 is_supported_domain"""
        mock_canonical_modes = {
            "golden_empire": {"name": "黃金古國", "type": "domain", "domain": "golden_empire"},
            "abyss_nest": {"name": "淵獸之巢", "type": "domain", "domain": "abyss_nest"},
        }
        with patch("config.get_canonical_domain_mode_configs", return_value=mock_canonical_modes):
            domain_configs = get_domain_mode_configs()
            self.assertEqual(set(domain_configs.keys()), {"golden_empire", "abyss_nest"})
            self.assertEqual(get_canonical_supported_domain_ids(), {"golden_empire", "abyss_nest"})
            self.assertTrue(is_supported_domain("golden_empire"))
            self.assertTrue(is_supported_domain("abyss_nest"))
            self.assertFalse(is_supported_domain("stage"))
            self.assertFalse(is_supported_domain("nonexistent"))

    def test_dynamic_tier4_domain_options_discovery(self):
        """get_tier4_domain_options 動態產生選單項目，顯示名稱嚴格取自 TOML name"""
        mock_canonical_modes = {
            "golden_empire": {"name": "黃金古國", "type": "domain", "domain": "golden_empire"},
            "frost_citadel": {"name": "冷誓要塞", "type": "domain", "domain": "frost_citadel"},
        }
        with patch("config.get_canonical_domain_mode_configs", return_value=mock_canonical_modes):
            options = get_tier4_domain_options()
            self.assertEqual(
                options,
                [("golden_empire", "黃金古國"), ("frost_citadel", "冷誓要塞")],
            )

    def test_profile_injected_domain_is_rejected_and_fails_fast(self):
        """[Canonical/Effective Separation] Profile 嘗試注入未宣告領域 ➔ is_supported_domain 為 False 且 validation Fail-Fast"""
        canonical_defaults = {
            "primary_modes": {
                "golden_empire": {"name": "黃金古國", "type": "domain", "domain": "golden_empire"}
            }
        }
        illegal_profile_override = {
            "primary_modes": {
                "fake_domain": {"name": "假領域", "type": "domain", "domain": "fake_domain"}
            }
        }
        # 1. 驗證 profile structural validation 直接拒絕
        with self.assertRaises(ValueError) as ctx:
            validate_profile_mode_overrides(illegal_profile_override, canonical_defaults)
        self.assertIn("is not declared in repository defaults catalog", str(ctx.exception))

        # 2. 即使 effective PRIMARY_MODES 被外部污染，is_supported_domain 仍以 canonical defaults 為準
        with patch.dict(PRIMARY_MODES, {"fake_domain": {"type": "domain", "domain": "fake_domain"}}):
            self.assertFalse(is_supported_domain("fake_domain"))
            self.assertNotIn("fake_domain", get_domain_mode_configs())
            self.assertNotIn("fake_domain", [k for k, _ in get_tier4_domain_options()])

    def test_existing_canonical_domain_override_allowed(self):
        """[Canonical/Effective Separation] 合法 canonical 領域之數值覆寫 (如 bread_cost) ➔ 正常允許並於 effective config 生效"""
        canonical_defaults = {
            "primary_modes": {
                "golden_empire": {"name": "黃金古國", "type": "domain", "domain": "golden_empire", "bread_cost": 3}
            }
        }
        valid_profile_override = {
            "primary_modes": {
                "golden_empire": {"bread_cost": 5}
            }
        }
        # 不應拋出任何例外
        validate_profile_mode_overrides(valid_profile_override, canonical_defaults)

        # 驗證 effective values 取得 5
        with patch.dict(PRIMARY_MODES, {"golden_empire": {"name": "黃金古國", "type": "domain", "domain": "golden_empire", "bread_cost": 5}}):
            configs = get_domain_mode_configs()
            self.assertEqual(configs["golden_empire"]["bread_cost"], 5)

    def test_domain_identity_and_type_override_rejected(self):
        """[Canonical/Effective Separation] Profile 嘗試篡改 canonical domain 之 domain identity 或 structural type ➔ Fail-Fast"""
        canonical_defaults = {
            "primary_modes": {
                "golden_empire": {"name": "黃金古國", "type": "domain", "domain": "golden_empire"}
            }
        }
        # 1. 篡改 domain identity
        identity_tamper = {
            "primary_modes": {
                "golden_empire": {"domain": "fake_domain"}
            }
        }
        with self.assertRaises(ValueError) as ctx:
            validate_profile_mode_overrides(identity_tamper, canonical_defaults)
        self.assertIn("cannot alter domain identity", str(ctx.exception))

        # 2. 篡改 structural type
        type_tamper = {
            "primary_modes": {
                "golden_empire": {"type": "stage"}
            }
        }
        with self.assertRaises(ValueError) as ctx:
            validate_profile_mode_overrides(type_tamper, canonical_defaults)
        self.assertIn("cannot alter structural type", str(ctx.exception))

    def test_canonical_new_domain_without_python_strategy_dispatches_generic(self):
        """[Canonical Seam] 在 canonical defaults fixture 加入 abyss_nest ➔ supported=True 且 strategy=GenericDomainStrategy"""
        mock_canonical_modes = {
            "golden_empire": {"name": "黃金古國", "type": "domain", "domain": "golden_empire"},
            "abyss_nest": {"name": "淵獸之巢", "type": "domain", "domain": "abyss_nest"},
        }
        with patch("config.get_canonical_domain_mode_configs", return_value=mock_canonical_modes):
            self.assertTrue(is_supported_domain("abyss_nest"))
            strategy = get_domain_strategy("abyss_nest", self.mock_handler)
            self.assertIsInstance(strategy, GenericDomainStrategy)
            self.assertEqual(strategy.domain_name, "abyss_nest")

    def test_tier4_new_generic_domain_selection_has_no_keyerror(self):
        """在 primary_modes 加入新領域後，Daily Tier 4 選單互動解析該領域絕不拋出 KeyError"""
        mock_modes = {
            "golden_empire": {"name": "黃金古國", "type": "domain", "domain": "golden_empire"},
            "abyss_nest": {"name": "淵獸之巢", "type": "domain", "domain": "abyss_nest"},
        }
        with patch("config.get_canonical_domain_mode_configs", return_value=mock_modes), patch.dict(PRIMARY_MODES, mock_modes, clear=True), patch("cli.tier4_setup.persist_mode_updates"):
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
                "domain_tab_btn": "domains/Domains_entry.png",
                "domain_tab_after_btn": "domains/Domains_entry_after.png",
                "domain_entry_btn": "domains/abyss_nest/entry.png",
                "lobby_start_btn": "domains/common/start_btn.png",
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

    def test_tier4_fallback_preserves_enable_lord_boss_ownership(self):
        """Daily Tier 4 fallback 中的 enable_lord_boss 嚴格以所選領地配置為準，非 Daily 殘留"""
        modes = {
            "abyss_nest": {
                "name": "淵獸之巢",
                "type": "domain",
                "domain": "abyss_nest",
                "navigation_path": ["common/door.png", "domains/abyss_nest/entry.png"],
                "domain_tab_btn": "domains/Domains_entry.png",
                "domain_tab_after_btn": "domains/Domains_entry_after.png",
                "domain_entry_btn": "domains/abyss_nest/entry.png",
                "lobby_start_btn": "domains/common/start_btn.png",
                "enable_lord_boss": False,
            },
            "golden_empire": {
                "name": "黃金古國",
                "type": "domain",
                "domain": "golden_empire",
                "navigation_path": ["common/door.png", "domains/golden_empire/entry.png"],
                "domain_tab_btn": "domains/Domains_entry.png",
                "domain_tab_after_btn": "domains/Domains_entry_after.png",
                "domain_entry_btn": "domains/golden_empire/entry.png",
                "lobby_start_btn": "domains/common/start_btn.png",
                "enable_lord_boss": True,
            }
        }
        # 情境 1: Daily enable_lord_boss = True，領地 enable_lord_boss = False ➔ fallback 必須為 False
        daily_true = {
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "abyss_nest",
            "enable_lord_boss": True,
        }
        fallback_false = build_tier4_fallback_config(daily_true, modes)
        self.assertFalse(fallback_false["enable_lord_boss"])

        # 情境 2: Daily enable_lord_boss = False，領地 enable_lord_boss = True ➔ fallback 必須為 True
        daily_false = {
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_lord_boss": False,
        }
        fallback_true = build_tier4_fallback_config(daily_false, modes)
        self.assertTrue(fallback_true["enable_lord_boss"])

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
    # Phase 1 — Domain Policy / SSOT Preparation 測試
    # =========================================================================

    def test_enable_domain_presence_and_separation(self):
        """[Phase 1] 驗證 enable_domain 存在於 activities 與 daily，且絕不滲透至 golden_empire 或被 normalize 注入領地"""
        with open(DEFAULTS_PATH, "rb") as f:
            data = tomllib.load(f)

        # 1. defaults.activities 包含 enable_domain = true
        activities = data.get("defaults", {}).get("activities", {})
        self.assertIn("enable_domain", activities)
        self.assertTrue(activities["enable_domain"])

        # 2. primary_modes.daily 包含 enable_domain = true
        daily_cfg = data.get("primary_modes", {}).get("daily", {})
        self.assertIn("enable_domain", daily_cfg)
        self.assertTrue(daily_cfg["enable_domain"])

        # 3. primary_modes.golden_empire 不包含 enable_domain (責任分離)
        ge_cfg = data.get("primary_modes", {}).get("golden_empire", {})
        self.assertNotIn("enable_domain", ge_cfg)

        # 4. normalize_config 對 type='domain' 絕不注入 enable_domain
        norm_ge = normalize_config(ge_cfg)
        self.assertNotIn("enable_domain", norm_ge)

    def test_daily_domain_policy_contradiction_fail_fast(self):
        """[Phase 1] tier4_mode='domain' 且 enable_domain=false ➔ 必須拋出 ValueError (Fail-Fast)"""
        contradictory_cfg = {
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_domain": False,
        }
        modes = {
            "golden_empire": {"name": "黃金古國", "type": "domain", "domain": "golden_empire"}
        }
        # 透過 policy validation 驗證
        with self.assertRaises(ValueError) as ctx:
            validate_daily_domain_policy(contradictory_cfg)
        self.assertIn("Daily policy 衝突", str(ctx.exception))

        # 透過 build_tier4_fallback_config 驗證
        with self.assertRaises(ValueError) as ctx:
            build_tier4_fallback_config(contradictory_cfg, modes)
        self.assertIn("Daily policy 衝突", str(ctx.exception))

    def test_daily_domain_policy_explicit_tier4_domain_required(self):
        """[Phase 1] tier4_mode='domain' 但缺少 tier4_domain ➔ 必須 fail-fast，絕不依賴隱式預設值 fallback 至 golden_empire"""
        missing_domain_cfgs = [
            {"type": "mix", "tier4_mode": "domain", "enable_domain": True},
            {"type": "mix", "tier4_mode": "domain", "tier4_domain": None, "enable_domain": True},
            {"type": "mix", "tier4_mode": "domain", "tier4_domain": "", "enable_domain": True},
            {"type": "mix", "tier4_mode": "domain", "tier4_domain": "   ", "enable_domain": True},
        ]
        modes = {
            "golden_empire": {"name": "黃金古國", "type": "domain", "domain": "golden_empire"}
        }
        for cfg in missing_domain_cfgs:
            with self.subTest(cfg=cfg):
                with self.assertRaises(ValueError) as ctx:
                    validate_daily_domain_policy(cfg)
                self.assertIn("必須明確指定 'tier4_domain'", str(ctx.exception))

                with self.assertRaises(ValueError) as ctx:
                    build_tier4_fallback_config(cfg, modes)
                self.assertIn("必須明確指定 'tier4_domain'", str(ctx.exception))

    def test_golden_empire_execution_completeness(self):
        """[Phase 1] 驗證 defaults.toml 中的 golden_empire 具備完整之必要執行契約與合理型別"""
        with open(DEFAULTS_PATH, "rb") as f:
            data = tomllib.load(f)
        ge_cfg = data.get("primary_modes", {}).get("golden_empire", {})

        # 執行完整驗證不拋出例外
        validate_domain_execution_config(ge_cfg)

        # 核心結構欄位確認
        self.assertEqual(ge_cfg["name"], "黃金古國")
        self.assertEqual(ge_cfg["type"], "domain")
        self.assertEqual(ge_cfg["domain"], "golden_empire")
        self.assertIsInstance(ge_cfg["navigation_path"], list)
        self.assertTrue(len(ge_cfg["navigation_path"]) >= 2)
        self.assertEqual(ge_cfg["domain_tab_btn"], "domains/Domains_entry.png")
        self.assertEqual(ge_cfg["domain_tab_after_btn"], "domains/Domains_entry_after.png")
        self.assertEqual(ge_cfg["domain_entry_btn"], "domains/golden_empire/entry.png")
        self.assertEqual(ge_cfg["lobby_start_btn"], "domains/common/start_btn.png")

        # 泛型預設欄位確認
        self.assertEqual(ge_cfg["bread_cost"], 3)
        self.assertEqual(ge_cfg["domain_reset_max_attempts"], 7)
        self.assertEqual(ge_cfg["explore_priorities"], ["domains/common/explore_btn.png"])
        self.assertEqual(ge_cfg["result_buttons"], ["common/continue.png", "common/continue_gray.png"])
        self.assertIs(ge_cfg["enable_lord_boss"], True)

    def test_direct_domain_independence_from_daily(self):
        """[Phase 1] 驗證 Golden Empire direct execution config 不依賴 daily 路由配置即可自給自足"""
        with open(DEFAULTS_PATH, "rb") as f:
            data = tomllib.load(f)
        ge_cfg = data.get("primary_modes", {}).get("golden_empire", {})

        # 完全獨立：不依賴任何 daily 的欄位合成，自身即具備完整有效路徑與入口
        self.assertIn("navigation_path", ge_cfg)
        self.assertIn("domain_tab_btn", ge_cfg)
        self.assertIn("domain_entry_btn", ge_cfg)
        self.assertIn("lobby_start_btn", ge_cfg)
        self.assertNotIn("stages/start.png", ge_cfg.values())

    def test_generic_domain_execution_schema_invariant(self):
        """[Phase 1] 泛型領域執行架構契約驗證：完整配置通過，缺少必要結構欄位 fail-fast"""
        minimal_domain = {
            "name": "測試領域",
            "type": "domain",
            "domain": "test_domain",
            "navigation_path": ["common/door.png", "domains/test_domain/entry.png"],
            "domain_tab_btn": "domains/Domains_entry.png",
            "domain_tab_after_btn": "domains/Domains_entry_after.png",
            "domain_entry_btn": "domains/test_domain/entry.png",
            "lobby_start_btn": "domains/common/start_btn.png",
        }
        # 1. 驗證最小結構配置搭配標準化層能自動補全 canonical common defaults
        normalized = normalize_domain_execution_config(minimal_domain)
        self.assertEqual(normalized["bread_cost"], 3)
        self.assertEqual(normalized["domain_reset_max_attempts"], 7)
        self.assertEqual(normalized["explore_priorities"], ["domains/common/explore_btn.png"])
        self.assertEqual(normalized["result_buttons"], ["common/continue.png", "common/continue_gray.png"])
        self.assertTrue(normalized["enable_lord_boss"])

        # 2. 缺少結構欄位依序測試 fail-fast
        structural_keys = [
            "name", "type", "domain", "navigation_path",
            "domain_tab_btn", "domain_tab_after_btn", "domain_entry_btn", "lobby_start_btn"
        ]
        for key in structural_keys:
            with self.subTest(missing_key=key):
                broken_cfg = minimal_domain.copy()
                del broken_cfg[key]
                with self.assertRaises(ValueError) as ctx:
                    validate_domain_execution_config(broken_cfg)
                self.assertIn(f"缺少必要結構欄位: '{key}'", str(ctx.exception))

    def test_normalize_config_applies_domain_common_defaults(self):
        """[Phase 1 Production Seam] 驗證 normalize_config 套用於只有結構必要欄位的 Generic Domain 時，自動補齊 canonical defaults 且移除 enable_domain"""
        minimal_domain = {
            "name": "測試領域",
            "type": "domain",
            "domain": "test_domain",
            "navigation_path": ["common/door.png", "domains/test_domain/entry.png"],
            "domain_tab_btn": "domains/Domains_entry.png",
            "domain_tab_after_btn": "domains/Domains_entry_after.png",
            "domain_entry_btn": "domains/test_domain/entry.png",
            "lobby_start_btn": "domains/common/start_btn.png",
            # 模擬可能意外傳入的 enable_domain (policy leakage)
            "enable_domain": True,
        }

        normalized = normalize_config(minimal_domain)

        # 1. 驗證 canonical common defaults 由 production normalize_config 自動賦予
        self.assertEqual(normalized["bread_cost"], 3)
        self.assertEqual(normalized["explore_priorities"], ["domains/common/explore_btn.png"])
        self.assertEqual(normalized["result_buttons"], ["common/continue.png", "common/continue_gray.png"])
        self.assertEqual(normalized["domain_reset_max_attempts"], 7)
        self.assertIs(normalized["enable_lord_boss"], True)

        # 2. 驗證 enable_domain 絕不留存於 Domain execution config
        self.assertNotIn("enable_domain", normalized)

    def test_normalize_config_rejects_incomplete_domain_structure(self):
        """[Phase 1 Production Seam] 驗證 normalize_config 當 Domain 缺失任何結構必要欄位時，必須 deterministic 拋出 ValueError"""
        minimal_domain = {
            "name": "測試領域",
            "type": "domain",
            "domain": "test_domain",
            "navigation_path": ["common/door.png", "domains/test_domain/entry.png"],
            "domain_tab_btn": "domains/Domains_entry.png",
            "domain_tab_after_btn": "domains/Domains_entry_after.png",
            "domain_entry_btn": "domains/test_domain/entry.png",
            "lobby_start_btn": "domains/common/start_btn.png",
        }

        structural_keys = [
            "name", "type", "domain", "navigation_path",
            "domain_tab_btn", "domain_tab_after_btn", "domain_entry_btn", "lobby_start_btn"
        ]
        for key in structural_keys:
            with self.subTest(missing_key=key):
                broken = minimal_domain.copy()
                del broken[key]
                with self.assertRaises(ValueError) as ctx:
                    normalize_config(broken)
                self.assertIn(f"缺少必要結構欄位: '{key}'", str(ctx.exception))

    def test_ssot_generic_activity_class_invariants(self):
        """[Phase 1 SSOT Invariant] enable_domain 必須為通用活動開關，嚴禁加入 enable_<specific_domain>"""
        with open(DEFAULTS_PATH, "rb") as f:
            data = tomllib.load(f)
        activities = data.get("defaults", {}).get("activities", {})

        # 1. 確保 enable_domain 是活動配置的一部分
        self.assertIn("enable_domain", activities)

        # 2. 嚴禁任何特定領域名稱的 activity 開關存在
        for act_key in activities.keys():
            self.assertFalse(
                act_key.startswith("enable_") and act_key not in {
                    "enable_domain", "enable_dungeon", "enable_town_daily",
                    "enable_demon_lords", "enable_lord_boss", "enable_quests", "enable_stage_farming"
                },
                f"非法特定領域活動開關: '{act_key}'！活動開關必須為通用類別 (如 enable_domain)"
            )


    # =========================================================================
    # Phase 2 — Switch Domain Execution Ownership 測試
    # =========================================================================

    def test_daily_domain_route_uses_selected_domain_as_execution_base(self):
        """[Phase 2] Daily policy 選擇 Domain 時，以 selected Domain config 作為 execution base"""
        daily_policy = {
            "type": "daily",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_domain": True,
            "enable_dungeon": False,
        }
        domain_cfg = {
            "name": "黃金古國",
            "type": "domain",
            "domain": "golden_empire",
            "navigation_path": ["common/door.png", "domains/golden_empire/entry.png"],
            "domain_tab_btn": "domains/Domains_entry.png",
            "domain_tab_after_btn": "domains/Domains_entry_after.png",
            "domain_entry_btn": "domains/golden_empire/entry.png",
            "lobby_start_btn": "domains/common/start_btn.png",
            "bread_cost": 3,
            "explore_priorities": ["domains/common/explore_btn.png"],
            "result_buttons": ["common/continue.png", "common/continue_gray.png"],
            "domain_reset_max_attempts": 7,
            "enable_lord_boss": True,
            "custom_domain_tag": "ge_special",
        }
        route = build_domain_execution_route(daily_policy, domain_cfg)

        # 1. 驗證所有 Domain 執行層欄位完整保留自 domain_cfg
        self.assertEqual(route["type"], "domain")
        self.assertEqual(route["domain"], "golden_empire")
        self.assertEqual(route["navigation_path"], ["common/door.png", "domains/golden_empire/entry.png"])
        self.assertEqual(route["domain_tab_btn"], "domains/Domains_entry.png")
        self.assertEqual(route["domain_tab_after_btn"], "domains/Domains_entry_after.png")
        self.assertEqual(route["domain_entry_btn"], "domains/golden_empire/entry.png")
        self.assertEqual(route["lobby_start_btn"], "domains/common/start_btn.png")
        self.assertEqual(route["bread_cost"], 3)
        self.assertEqual(route["explore_priorities"], ["domains/common/explore_btn.png"])
        self.assertEqual(route["result_buttons"], ["common/continue.png", "common/continue_gray.png"])
        self.assertEqual(route["domain_reset_max_attempts"], 7)
        self.assertTrue(route["enable_lord_boss"])
        self.assertEqual(route["custom_domain_tag"], "ge_special")

        # 2. 驗證 Tier 4 標籤與排程上下文
        self.assertEqual(route["tier4_mode"], "domain")
        self.assertEqual(route["tier4_domain"], "golden_empire")
        self.assertTrue(route["is_tier4_fallback"])
        self.assertFalse(route["enable_stage_farming"])
        self.assertFalse(route["enable_dungeon"])

        # 3. 驗證 enable_domain 絕不滲透至 execution route
        self.assertNotIn("enable_domain", route)

    def test_daily_execution_fields_cannot_override_domain_ssot(self):
        """[Phase 2 SSOT Invariant] Daily 的執行性欄位絕不可覆蓋或污染 Domain 執行的 SSOT 契約"""
        daily_with_conflicts = {
            "type": "daily",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_domain": True,
            # 與 Domain 衝突之同名污染值
            "navigation_path": ["DAILY_WRONG_DOOR.png"],
            "lobby_start_btn": "DAILY_WRONG_START.png",
            "result_buttons": ["DAILY_WRONG_CONTINUE.png"],
            "bread_cost": 999,
            "domain_reset_max_attempts": 999,
            "domain_tab_btn": "DAILY_WRONG_TAB.png",
            "domain_entry_btn": "DAILY_WRONG_ENTRY.png",
        }
        domain_cfg = {
            "name": "黃金古國",
            "type": "domain",
            "domain": "golden_empire",
            "navigation_path": ["common/door.png", "domains/golden_empire/entry.png"],
            "domain_tab_btn": "domains/Domains_entry.png",
            "domain_tab_after_btn": "domains/Domains_entry_after.png",
            "domain_entry_btn": "domains/golden_empire/entry.png",
            "lobby_start_btn": "domains/common/start_btn.png",
            "bread_cost": 3,
            "explore_priorities": ["domains/common/explore_btn.png"],
            "result_buttons": ["common/continue.png", "common/continue_gray.png"],
            "domain_reset_max_attempts": 7,
            "enable_lord_boss": True,
        }
        route = build_domain_execution_route(daily_with_conflicts, domain_cfg)

        # 嚴格斷言：所有執行欄位均為 Domain SSOT 值，絕無 Daily 污染
        self.assertEqual(route["navigation_path"], ["common/door.png", "domains/golden_empire/entry.png"])
        self.assertEqual(route["lobby_start_btn"], "domains/common/start_btn.png")
        self.assertEqual(route["result_buttons"], ["common/continue.png", "common/continue_gray.png"])
        self.assertEqual(route["bread_cost"], 3)
        self.assertEqual(route["domain_reset_max_attempts"], 7)
        self.assertEqual(route["domain_tab_btn"], "domains/Domains_entry.png")
        self.assertEqual(route["domain_entry_btn"], "domains/golden_empire/entry.png")

    def test_domain_execution_enable_lord_boss_is_independent_from_daily_policy(self):
        """[Phase 2] enable_lord_boss 雙重所有權分離與未 mock has_pending_daily_activity 的真實整合測試 (Cases A/B/C/D)"""
        from states.handlers.domain_explore import DomainExploreHandler
        from states.state_machine import GameStateMachine

        modes_domain_boss_false = {
            "golden_empire": {
                "name": "黃金古國",
                "type": "domain",
                "domain": "golden_empire",
                "navigation_path": ["common/door.png", "domains/golden_empire/entry.png"],
                "domain_tab_btn": "domains/Domains_entry.png",
                "domain_tab_after_btn": "domains/Domains_entry_after.png",
                "domain_entry_btn": "domains/golden_empire/entry.png",
                "lobby_start_btn": "domains/common/start_btn.png",
                "enable_lord_boss": False,  # 領域執行自身關閉領主 preemption
            }
        }
        modes_domain_boss_true = {
            "golden_empire": {
                **modes_domain_boss_false["golden_empire"],
                "enable_lord_boss": True,  # 領域執行自身允許領主 preemption
            }
        }

        # 基礎狀態機設置 helper：不 mock has_pending_daily_activity，使用真實調度邏輯
        def _create_machine_and_handler(daily_cfg, domain_modes):
            route = build_tier4_fallback_config(daily_cfg, domain_modes)
            machine = GameStateMachine(MagicMock(), MagicMock(), MagicMock(), preload_ocr=False)
            machine.runtime_config_key = "daily"
            machine.primary_config = daily_cfg
            machine.config = route
            machine.quest_scheduler = None
            machine.is_daily_pipeline_active = MagicMock(return_value=True)

            # 設置 daily_manager 模擬日常狀態
            machine.daily_manager = MagicMock()
            machine.daily_manager.get_pending_town_subflows.return_value = []
            machine.daily_manager.is_demon_lords_available.return_value = (False, "")
            machine.daily_manager.has_available_dungeon.return_value = False
            machine.matcher.match.return_value = (None, 0.0)

            handler = DomainExploreHandler(machine)
            return machine, handler

        # ---------------------------------------------------------------------
        # Case A: Daily.enable_lord_boss = True, Domain.enable_lord_boss = False, Boss ready = True
        # No other Daily activity ready -> Domain MUST NOT preempt
        # ---------------------------------------------------------------------
        daily_a = {
            "_config_mode_key": "daily",
            "type": "daily",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_domain": True,
            "enable_lord_boss": True,
            "enable_town_daily": False,
            "enable_demon_lords": False,
            "enable_dungeon": False,
            "lord_boss_targets": ["lord_spider"],
        }
        mach_a, handler_a = _create_machine_and_handler(daily_a, modes_domain_boss_false)
        mach_a.daily_manager.get_available_lord_bosses.return_value = ["lord_spider"]
        self.assertFalse(mach_a.config["enable_lord_boss"], "Domain 路由之 enable_lord_boss 應為 False")
        self.assertTrue(mach_a._daily_activity_config()["enable_lord_boss"], "Daily 政策之 enable_lord_boss 應為 True")
        self.assertTrue(mach_a.has_available_selected_lord_boss(), "Boss 本身已就緒")
        # 不 mock has_pending_daily_activity，呼叫 _check_lord_boss_preemption 必須不退出領地
        self.assertFalse(
            handler_a._check_lord_boss_preemption(None, {"left": 0, "top": 0}),
            "Case A: Domain.enable_lord_boss=False 時，即便 Boss ready 且 Daily=True，絕不得插隊退出 Domain",
        )

        # ---------------------------------------------------------------------
        # Case B: Daily.enable_lord_boss = False, Domain.enable_lord_boss = True, Boss ready = True
        # No other Daily activity ready -> Domain MUST NOT preempt
        # ---------------------------------------------------------------------
        daily_b = {
            "_config_mode_key": "daily",
            "type": "daily",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_domain": True,
            "enable_lord_boss": False,
            "enable_town_daily": False,
            "enable_demon_lords": False,
            "enable_dungeon": False,
            "lord_boss_targets": ["lord_spider"],
        }
        mach_b, handler_b = _create_machine_and_handler(daily_b, modes_domain_boss_true)
        mach_b.daily_manager.get_available_lord_bosses.return_value = ["lord_spider"]
        self.assertTrue(mach_b.config["enable_lord_boss"], "Domain 路由之 enable_lord_boss 應為 True")
        self.assertFalse(mach_b._daily_activity_config()["enable_lord_boss"], "Daily 政策之 enable_lord_boss 應為 False")
        self.assertFalse(mach_b.has_available_selected_lord_boss(), "Daily 政策關閉時 has_available_selected_lord_boss 應為 False")
        self.assertFalse(
            handler_b._check_lord_boss_preemption(None, {"left": 0, "top": 0}),
            "Case B: Daily.enable_lord_boss=False 時，即便 Domain=True，亦不得插隊退出 Domain",
        )

        # ---------------------------------------------------------------------
        # Case C: Daily.enable_lord_boss = True, Domain.enable_lord_boss = True, Boss ready = True
        # -> Domain SHOULD preempt
        # ---------------------------------------------------------------------
        daily_c = {
            "_config_mode_key": "daily",
            "type": "daily",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_domain": True,
            "enable_lord_boss": True,
            "enable_town_daily": False,
            "enable_demon_lords": False,
            "enable_dungeon": False,
            "lord_boss_targets": ["lord_spider"],
        }
        mach_c, handler_c = _create_machine_and_handler(daily_c, modes_domain_boss_true)
        mach_c.daily_manager.get_available_lord_bosses.return_value = ["lord_spider"]
        self.assertTrue(mach_c.config["enable_lord_boss"])
        self.assertTrue(mach_c._daily_activity_config()["enable_lord_boss"])
        self.assertTrue(mach_c.has_available_selected_lord_boss())
        self.assertTrue(
            handler_c._check_lord_boss_preemption(None, {"left": 0, "top": 0}),
            "Case C: Daily 與 Domain 均為 True 且 Boss 就緒時，Domain 必須成功被 Lord Boss 插隊退出",
        )

        # ---------------------------------------------------------------------
        # Case D: Domain.enable_lord_boss = False, Timed Dungeon ready = True
        # -> Domain MUST still preempt (確保其他高優先 Daily 活動未被誤擋)
        # ---------------------------------------------------------------------
        daily_d = {
            "_config_mode_key": "daily",
            "type": "daily",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_domain": True,
            "enable_lord_boss": False,
            "enable_town_daily": False,
            "enable_demon_lords": False,
            "enable_dungeon": True,
            "greedy_dungeon": True,
            "greedy_allowed_indices": [0],
            "dungeon_entries": ["dungeons/Slime_entry.png"],
            "dungeon_names": ["Slime"],
        }
        mach_d, handler_d = _create_machine_and_handler(daily_d, modes_domain_boss_false)
        # 模擬定時地下城已就緒
        mach_d.daily_manager.has_available_dungeon.return_value = True
        self.assertTrue(mach_d.has_available_daily_dungeon(), "定時地下城已就緒")
        self.assertTrue(
            handler_d._check_lord_boss_preemption(None, {"left": 0, "top": 0}),
            "Case D: 即使 Domain.enable_lord_boss=False，當定時地下城就緒時 Domain 依然必須被正常插隊！",
        )

    def test_daily_scheduler_policy_survives_domain_execution_route(self):
        """[Phase 2] Daily 的地下城與排程政策在 Domain residency 期間完好保存，定時地下城可順利插隊"""
        from states.state_machine import GameStateMachine

        machine = GameStateMachine(MagicMock(), MagicMock(), MagicMock(), preload_ocr=False)
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
            "enable_domain": True,
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
        self.assertEqual(machine.config["type"], "domain")
        self.assertTrue(machine.config["is_tier4_fallback"])

        # 斷言排程政策在 _daily_activity_config() 存活且可判定定時地下城
        self.assertTrue(machine._daily_activity_config()["enable_dungeon"])
        self.assertTrue(machine.has_available_daily_dungeon())

        # 模擬進入 DOMAIN_EXPLORE 狀態，定時地下城冷卻完畢觸發插隊評估
        machine.current_state = machine.STATE_DOMAIN_EXPLORE
        self.assertTrue(machine.evaluate_next_activity())
        self.assertEqual(machine.config["type"], "mix")
        self.assertEqual(machine.config["navigation_path"], ["common/door.png", "dungeons/dungeon.png"])
        self.assertTrue(machine.config["is_tier4_fallback"])

    def test_domain_profile_override_rebuilds_active_domain_route(self):
        """[Phase 2 Hot Reload Invariant] Profile 覆寫領地欄位時 hot reload 重建 active domain route，且 Daily 污染欄位不影響"""
        from copy import deepcopy
        from states.state_machine import GameStateMachine
        import config

        machine = GameStateMachine(MagicMock(), MagicMock(), MagicMock(), preload_ocr=False)
        machine.runtime_config_key = "daily"
        machine.primary_config = {
            "_config_mode_key": "daily",
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_domain": True,
            # Daily 自帶污染值
            "navigation_path": ["DAILY_GARBAGE_NAV.png"],
        }
        machine.apply_tier4_fallback_config()
        self.assertEqual(machine.config["bread_cost"], 3)
        self.assertNotEqual(machine.config["navigation_path"], ["DAILY_GARBAGE_NAV.png"])

        # 模擬 profile override 修改 golden_empire 的 bread_cost = 5
        with patch("states.state_machine.refresh_runtime_config", return_value=True), \
             patch("states.state_machine.get_runtime_game_config", return_value=deepcopy(machine.primary_config)), \
             patch.dict(config.GAME_CONFIGS, {
                 "golden_empire": {
                     **config.GAME_CONFIGS["golden_empire"],
                     "bread_cost": 5,
                 }
             }):
            self.assertTrue(machine.refresh_config_at_safe_point())

        # 斷言 hot reload 後 active domain execution 更新為 bread_cost == 5
        self.assertEqual(machine.config["bread_cost"], 5)
        # 且 Daily 的污染欄位依然無法覆蓋 Domain 路由
        self.assertNotEqual(machine.config["navigation_path"], ["DAILY_GARBAGE_NAV.png"])
        self.assertEqual(machine.config["domain_tab_btn"], "domains/Domains_entry.png")

    def test_daily_domain_generic_strategy_route_uses_generic_domain(self):
        """[Phase 2] Daily 選定 canonical generic domain (abyss_nest) 時，採用 GenericDomainStrategy 且維持自身 identity"""
        from states.handlers.domain_explore import DomainExploreHandler
        from states.domains.generic_domain import GenericDomainStrategy
        from states.state_machine import GameStateMachine

        abyss_cfg = {
            "name": "淵獸之巢",
            "type": "domain",
            "domain": "abyss_nest",
            "navigation_path": ["common/door.png", "domains/abyss_nest/entry.png"],
            "domain_tab_btn": "domains/Domains_entry.png",
            "domain_tab_after_btn": "domains/Domains_entry_after.png",
            "domain_entry_btn": "domains/abyss_nest/entry.png",
            "lobby_start_btn": "domains/common/start_btn.png",
        }
        modes = {"abyss_nest": abyss_cfg}
        daily_cfg = {
            "type": "daily",
            "tier4_mode": "domain",
            "tier4_domain": "abyss_nest",
            "enable_domain": True,
        }
        route = build_tier4_fallback_config(daily_cfg, modes)
        self.assertEqual(route["domain"], "abyss_nest")

        machine = GameStateMachine(MagicMock(), MagicMock(), MagicMock(), preload_ocr=False)
        machine.config = route

        with patch("states.domains.is_supported_domain", return_value=True):
            handler = DomainExploreHandler(machine)
            self.assertIsInstance(handler.strategy, GenericDomainStrategy)
            self.assertEqual(handler.strategy.domain_name, "abyss_nest")

    def test_tier4_domain_and_domain_distinct_identity(self):
        """[Phase 2 Distinct Key Invariant] tier4_domain (mode key) 與 domain (strategy identity) 語意嚴格分離，絕不互相 fallback 或坍塌"""
        abyss_t6_cfg = {
            "name": "淵獸之巢 T6",
            "type": "domain",
            "domain": "abyss_nest",
            "navigation_path": ["common/door.png", "domains/abyss_nest/entry.png"],
            "domain_tab_btn": "domains/Domains_entry.png",
            "domain_tab_after_btn": "domains/Domains_entry_after.png",
            "domain_entry_btn": "domains/abyss_nest/entry.png",
            "lobby_start_btn": "domains/common/start_btn.png",
        }
        modes = {"abyss_nest_t6": abyss_t6_cfg}
        daily_cfg = {
            "_config_mode_key": "daily",
            "type": "daily",
            "tier4_mode": "domain",
            "tier4_domain": "abyss_nest_t6",
            "enable_domain": True,
        }
        route = build_tier4_fallback_config(daily_cfg, modes)
        self.assertEqual(route["tier4_domain"], "abyss_nest_t6", "tier4_domain 必須精確保持 mode selection key")
        self.assertEqual(route["domain"], "abyss_nest", "domain 必須精確保持 domain strategy identity")
        self.assertIn("淵獸之巢 T6", route["name"])

        # 驗證後續 selected mode lookup 與 rebuild 不因 identity collapse 而失效
        rebuilt = build_tier4_fallback_config(route, modes)
        self.assertEqual(rebuilt["tier4_domain"], "abyss_nest_t6")
        self.assertEqual(rebuilt["domain"], "abyss_nest")

    def test_direct_domain_execution_remains_independent(self):
        """[Phase 2 Regression] Direct Domain 模式 (如 --mode golden_empire) 執行配置完全獨立，絕無 Daily/Tier4 污染"""
        from config import GAME_CONFIGS

        ge_direct = GAME_CONFIGS.get("golden_empire")
        self.assertIsNotNone(ge_direct)

        # 斷言 direct domain 配置純淨性
        self.assertEqual(ge_direct["type"], "domain")
        self.assertEqual(ge_direct["domain"], "golden_empire")
        self.assertNotIn("tier4_mode", ge_direct)
        self.assertNotIn("tier4_domain", ge_direct)
        self.assertNotIn("enable_domain", ge_direct)
        self.assertNotIn("is_tier4_fallback", ge_direct)
        self.assertFalse(ge_direct.get("enable_stage_farming", True))
        self.assertFalse(ge_direct.get("enable_dungeon", True))

        # 斷言具備所有必要 Domain 執行屬性
        self.assertIn("navigation_path", ge_direct)
        self.assertIn("domain_tab_btn", ge_direct)
        self.assertIn("domain_entry_btn", ge_direct)
        self.assertIn("lobby_start_btn", ge_direct)
        self.assertEqual(ge_direct["bread_cost"], 3)

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

    def test_default_tier4_domain_constant_completely_removed(self):
        """[Phase 3 Invariant] DEFAULT_TIER4_DOMAIN 已完全自 production/config 移除，且任何路徑都不允許 fallback 到 golden_empire"""
        import config
        self.assertFalse(hasattr(config, "DEFAULT_TIER4_DOMAIN"), "DEFAULT_TIER4_DOMAIN 常數應已自 config 移除")

        scanned_dirs = ["states", "utils", "config", "cli"]
        for s_dir in scanned_dirs:
            for root, _, files in os.walk(s_dir):
                for f in files:
                    if f.endswith((".py", ".toml")):
                        f_path = os.path.join(root, f)
                        with open(f_path, "r", encoding="utf-8", errors="ignore") as file_obj:
                            content = file_obj.read()
                        self.assertNotIn(
                            "DEFAULT_TIER4_DOMAIN",
                            content,
                            f"Found obsolete reference 'DEFAULT_TIER4_DOMAIN' in {f_path}"
                        )

    def test_explicit_domain_selection_fails_fast_on_missing_tier4_domain(self):
        """[Phase 3 Invariant] tier4_mode == 'domain' 但缺少 tier4_domain 時一律 fail-fast，絕不自動猜測或借用 golden_empire / 第一個 domain"""
        invalid_daily = {
            "type": "daily",
            "tier4_mode": "domain",
            "enable_domain": True,
        }
        with self.assertRaises(ValueError) as ctx:
            validate_daily_domain_policy(invalid_daily)
        self.assertIn("tier4_domain", str(ctx.exception))

        with self.assertRaises(ValueError):
            build_tier4_fallback_config(invalid_daily, {})

    def test_structural_path_contract_fail_fast_without_inference(self):
        """[Phase 3 Invariant] domain_tab_btn 與 domain_entry_btn 為 structural required，缺失時 fail-fast，Navigation 絕不從 navigation_path 猜測"""
        # 1. 缺少 domain_tab_btn
        cfg_no_tab = {
            "name": "測試領地",
            "type": "domain",
            "domain": "golden_empire",
            "domain_tab_after_btn": "domains/Domains_entry_after.png",
            "domain_entry_btn": "domains/golden_empire/entry.png",
            "lobby_start_btn": "domains/common/start_btn.png",
            "navigation_path": ["common/door.png", "domains/golden_empire/entry.png"],
        }
        with self.assertRaises(ValueError) as ctx:
            validate_domain_execution_config(cfg_no_tab)
        self.assertIn("domain_tab_btn", str(ctx.exception))

        # 2. 即使 navigation_path 包含 entry.png，只要 domain_entry_btn 缺失即 fail-fast
        cfg_no_entry = {
            "name": "測試領地",
            "type": "domain",
            "domain": "golden_empire",
            "domain_tab_btn": "domains/Domains_entry.png",
            "domain_tab_after_btn": "domains/Domains_entry_after.png",
            "lobby_start_btn": "domains/common/start_btn.png",
            "navigation_path": ["common/door.png", "domains/golden_empire/entry.png"],
        }
        with self.assertRaises(ValueError) as ctx:
            validate_domain_execution_config(cfg_no_entry)
        self.assertIn("domain_entry_btn", str(ctx.exception))

        # 3. 驗證 NavigationHandler 決策層絕不從 navigation_path 猜測 entry template
        from states.handlers.navigation import NavigationHandler
        nav_machine = MagicMock()
        nav_machine.config = cfg_no_entry
        nav_handler = NavigationHandler(nav_machine)
        tab_tpl, entry_tpl = nav_handler._resolve_domain_navigation_templates()
        self.assertIsNone(entry_tpl, "NavigationHandler 不得從 navigation_path 偷猜 entry template")

    def test_domain_identity_contract_rejects_domain_name_fallback(self):
        """[Phase 3 Invariant] domain 為唯一 strategy identity；domain 缺失即使 domain_name 存在也必須 fail-fast"""
        machine = MagicMock()
        machine.config = {
            "name": "黃金古國",
            "type": "domain",
            "domain_name": "golden_empire",  # 僅有 display/legacy domain_name，缺少 domain
        }
        handler = DomainExploreHandler(machine)
        self.assertIsNone(handler.strategy, "domain 缺失時不得以 domain_name 初始化 strategy")
        with self.assertRaises(ValueError) as ctx:
            handler.handle(MagicMock(), self.rect)
        self.assertIn("domain", str(ctx.exception))

    def test_apply_tier4_fallback_fails_fast_without_primary_config(self):
        """[Phase 3 Invariant] Daily Tier4 rebuild 必須擁有合法 primary_config，缺失時立即 fail-fast，絕不偷偷切換至 Daily/Mix"""
        from states.state_machine import GameStateMachine
        machine = GameStateMachine(MagicMock(), MagicMock(), MagicMock(), preload_ocr=False)
        machine.primary_config = None
        machine.config = {"type": "daily"}

        with self.assertRaises(RuntimeError) as ctx:
            machine._build_tier4_fallback_config()
        self.assertIn("primary_config", str(ctx.exception))

        with self.assertRaises(RuntimeError) as ctx:
            machine.apply_tier4_fallback_config()
        self.assertIn("primary_config", str(ctx.exception))

    def test_domain_consumer_defaults_single_ssot_regression(self):
        """[Phase 3 Invariant] Domain 規範預設值單一 SSOT 來自 normalize_domain_execution_config，consumer 端不得硬編碼預設 fallback"""
        with open("cli/mode_setup.py", "r", encoding="utf-8") as f:
            cli_content = f.read()
        self.assertNotIn(
            'config.get("bread_cost", 3)',
            cli_content,
            "cli/mode_setup.py 不得保留 hardcoded bread_cost fallback，應直接讀取 normalized config['bread_cost']"
        )
        self.assertIn(
            'bread_cost = config["bread_cost"]',
            cli_content
        )


if __name__ == "__main__":
    unittest.main()
