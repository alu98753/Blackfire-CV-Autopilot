import os
import unittest
from unittest.mock import MagicMock, patch

from states.domains.base_domain import BaseDomainStrategy
from states.domains.golden_empire import GoldenEmpireStrategy
from states.domains.treasure_subflow import DomainTreasureSubflow
from states.domains import get_domain_strategy
from utils.scene_snapshot import _ELEMENT_TEMPLATE_MAP, ElementId
from config import DEFAULTS_PATH
import tomllib


class TestDomainCommonBehavior(unittest.TestCase):
    def setUp(self):
        self.mock_handler = MagicMock()
        self.mock_machine = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
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

    def test_domain_treasure_subflow_execution(self):
        """DomainTreasureSubflow 辨識到通用 open.png 時依序閉環點擊 open ➔ confirm ➔ quit"""
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

    def test_subclass_inherits_common_behavior_without_overrides(self):
        """任何新領地繼承 BaseDomainStrategy 即可自動獲得通用探索按鈕與挖寶事件能力"""
        class MockNewDomainStrategy(BaseDomainStrategy):
            pass

        strategy = MockNewDomainStrategy(self.mock_handler)
        self.assertEqual(strategy.get_explore_button(), "domains/common/explore_btn.png")
        self.assertIsInstance(strategy.treasure_subflow, DomainTreasureSubflow)

        # 挖寶事件處理自動委派至 treasure_subflow
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


if __name__ == "__main__":
    unittest.main()
