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
from config import DEFAULTS_PATH
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
    # Generic Domain Strategy 修正測試
    # =========================================================================

    def test_generic_domain_strategy_for_unregistered_domain(self):
        """未知或新領域 (abyss_beast_nest) 實例化 GenericDomainStrategy，絕不 fallback 成 GoldenEmpireStrategy"""
        requested_domain = "abyss_beast_nest"
        strategy = get_domain_strategy(requested_domain, self.mock_handler)

        self.assertIsInstance(strategy, GenericDomainStrategy)
        self.assertNotIsInstance(strategy, GoldenEmpireStrategy)
        self.assertEqual(strategy.domain_name, requested_domain)
        self.assertEqual(strategy.get_explore_button(), "domains/common/explore_btn.png")
        self.assertIsInstance(strategy.treasure_subflow, DomainTreasureSubflow)

    def test_domain_explore_handler_strategy_stability_with_generic_domain(self):
        """DomainExploreHandler 在 generic domain 下不會因 domain_name 不匹配而每 tick 重建 strategy"""
        self.mock_machine.config = {
            "type": "domain",
            "domain": "abyss_beast_nest",
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

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "domains/common/open.png":
                return ((1045, 615), 0.92)
            if template in ["common/confirm.png", "common/ok.png"]:
                return ((960, 700), 0.85)
            if template in ["common/quit.png", "domains/common/exit_to_lobby.png"]:
                return ((100, 100), 0.85)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match
        self.mock_handler.click_and_wait_until_gone = MagicMock()

        with patch("os.path.exists", return_value=True), patch("time.sleep"):
            res = subflow.handle(mock_img, self.rect)

        self.assertTrue(res)
        self.assertTrue(self.mock_handler.click_and_wait_until_gone.called)
        called_templates = [call.args[0] for call in self.mock_handler.click_and_wait_until_gone.call_args_list]
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
        # 嚴格斷言：Unknown never guesses，未出現 open.png 時嚴禁對未知寶箱發起任何點擊
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
        # 嚴格斷言：未出現 open.png 時嚴禁盲點
        self.assertFalse(self.mock_handler.click_and_wait_until_gone.called)
        self.assertFalse(self.mock_mouse.click.called)

    # =========================================================================
    # Strict SSOT Invariant Tests
    # =========================================================================

    def test_strict_ssot_invariant_element_map(self):
        """[SSOT Invariant] ElementId.DOMAIN_EXPLORE_BTN 嚴格映射為 domains/common/explore_btn.png"""
        self.assertIn("domains/common/explore_btn.png", _ELEMENT_TEMPLATE_MAP)
        self.assertEqual(_ELEMENT_TEMPLATE_MAP["domains/common/explore_btn.png"], ElementId.DOMAIN_EXPLORE_BTN)
        self.assertNotIn("domains/golden_empire/explore_btn.png", _ELEMENT_TEMPLATE_MAP)

    def test_strict_ssot_invariant_defaults_toml(self):
        """[SSOT Invariant] config/defaults.toml 中的 explore_priorities 嚴格配置 domains/common/explore_btn.png"""
        with open(DEFAULTS_PATH, "rb") as f:
            data = tomllib.load(f)
        ge_cfg = data.get("primary_modes", {}).get("golden_empire", {})
        priorities = ge_cfg.get("explore_priorities", [])
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
        """[SSOT Invariant] 程式碼與設定檔中嚴禁存在任何舊版 golden_empire 模板路徑字串"""
        obsolete_references = [
            "domains/golden_empire/explore_btn.png",
            "domains/golden_empire/open.png",
            "domains/golden_empire/find_treasure.png",
            "domains/golden_empire/treasure.png",
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
