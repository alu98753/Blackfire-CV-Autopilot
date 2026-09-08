import unittest
from unittest.mock import MagicMock, patch
import time

from states.handlers.battle import BattleHandler
from utils.dungeon_catalog import DungeonCatalog


class TestDungeonNemesisBehavior(unittest.TestCase):
    """
    測試地下城與通用強敵遭遇 (Nemesis Encounter) 處置行為：
    - 戰鬥中遭遇冰雪洞窟 BOSS 寒冰元素王 (ice_boss_calvia_body.png)
    - 放棄選單支援 defeat_giveup.png
    - 地下城主動放棄後自動排入 15 分鐘冷卻期並重置 is_in_dungeon
    - 領域強敵相容性驗證
    """

    def setUp(self):
        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        self.mock_machine = MagicMock()
        self.mock_machine.STATE_BATTLE = "BATTLE"
        self.mock_machine.STATE_NAVIGATING = "NAVIGATING"
        self.mock_machine.STATE_COLLECT_ONLY = "COLLECT_ONLY"
        self.mock_machine.STATE_DUNGEON_EXPLORING = "EXPLORING"
        self.mock_machine.dungeon_detection_features.return_value = []
        self.mock_machine.battle_elapsed_seconds.return_value = 1.0
        self.mock_machine.is_in_collect_only_mode.return_value = False
        self.mock_machine.config = {}
        self.mock_machine.primary_config = {}
        self.mock_machine.dungeon_cooldowns = DungeonCatalog.build_default_cooldowns()

    def test_dungeon_nemesis_giveup_sets_cooldown_and_navigates(self):
        """
        Given: 地下城戰鬥中 (current_dungeon_index = 6 冰雪洞窟, is_in_dungeon = True)
               遭遇強敵 ice_boss_calvia_body.png，選單彈出 defeat_giveup.png 按鈕
        When: 執行 BattleHandler.handle()
        Then: 依序點擊 setting ➔ defeat_giveup ➔ confirm ➔ 冰雪洞窟排入冷卻 ➔ 轉移至 NAVIGATING
        """
        battle_handler = BattleHandler(self.mock_machine)
        mock_img = MagicMock()

        self.mock_machine.config = {
            "nemesis_action": "flee",
            "nemesis_templates": ["dungeons/exception/ice_boss_calvia_body.png"],
            "cooldown_map": {6: 900.0},
        }
        self.mock_machine.current_dungeon_index = 6
        self.mock_machine.is_in_dungeon = True
        self.mock_machine.defeat_count = 0
        self.mock_machine.last_auto_click_time = 0.0

        clicked_templates = []

        def fake_match(img, template, threshold=0.75, *args, **kwargs):
            if template == "dungeons/exception/ice_boss_calvia_body.png":
                return ((500, 300), 0.85)
            if template == "battle/setting.png":
                return ((1800, 50), 0.90)
            if template == "defeat_giveup.png":
                return ((960, 600), 0.90)
            if template in ["common/confirm.png", "common/ok.png"]:
                return ((960, 700), 0.90)
            return (None, 0.0)

        def fake_click(x, y):
            clicked_templates.append((x, y))

        self.mock_machine.matcher.match.side_effect = fake_match
        self.mock_machine.mouse.click.side_effect = fake_click

        now = time.time()
        with patch("os.path.exists", return_value=True):
            battle_handler.handle(mock_img, self.rect)

        # 斷言點擊次數為 3 (setting, defeat_giveup, confirm)
        self.assertEqual(len(clicked_templates), 3)

        # 斷言冰雪洞窟 (index 6) 被寫入約 900 秒冷卻
        cd_target = self.mock_machine.dungeon_cooldowns.get(6, 0.0)
        self.assertGreaterEqual(cd_target, now + 890.0)

        # 斷言地下城旗標重置與狀態切換
        self.assertFalse(self.mock_machine.is_in_dungeon)
        self.assertIsNone(self.mock_machine.current_dungeon_index)
        self.assertEqual(self.mock_machine.defeat_count, 0)
        self.mock_machine.transition_to.assert_called_with("NAVIGATING")

    def test_dungeon_nemesis_reads_from_primary_config(self):
        """
        Given: 當前 config 為空，但 primary_config 定義了 nemesis 設定
        When: 執行 BattleHandler.handle()
        Then: 能順利自 primary_config 繼承並執行放棄流程
        """
        battle_handler = BattleHandler(self.mock_machine)
        mock_img = MagicMock()

        self.mock_machine.config = {}
        self.mock_machine.primary_config = {
            "nemesis_action": "flee",
            "nemesis_templates": ["dungeons/exception/ice_boss_calvia_body.png"],
        }
        self.mock_machine.current_dungeon_index = 6
        self.mock_machine.is_in_dungeon = True

        def fake_match(img, template, threshold=0.75, *args, **kwargs):
            if template == "dungeons/exception/ice_boss_calvia_body.png":
                return ((500, 300), 0.85)
            if template in ["battle/setting.png", "defeat_giveup.png", "common/confirm.png"]:
                return ((900, 500), 0.90)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            battle_handler.handle(mock_img, self.rect)

        self.mock_machine.transition_to.assert_called_with("NAVIGATING")
        self.assertFalse(self.mock_machine.is_in_dungeon)

    def test_dungeon_nemesis_collect_only_fallback(self):
        """
        Given: 處於 is_in_collect_only_mode = True
        When: 地下城放棄強敵
        Then: 狀態應轉移至 STATE_COLLECT_ONLY
        """
        battle_handler = BattleHandler(self.mock_machine)
        mock_img = MagicMock()

        self.mock_machine.is_in_collect_only_mode.return_value = True
        self.mock_machine.config = {
            "nemesis_action": "flee",
            "nemesis_templates": ["dungeons/exception/ice_boss_calvia_body.png"],
        }
        self.mock_machine.current_dungeon_index = 6
        self.mock_machine.is_in_dungeon = True

        def fake_match(img, template, threshold=0.75, *args, **kwargs):
            if template == "dungeons/exception/ice_boss_calvia_body.png":
                return ((500, 300), 0.85)
            if template in ["battle/setting.png", "defeat_giveup.png", "common/confirm.png"]:
                return ((900, 500), 0.90)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            battle_handler.handle(mock_img, self.rect)

        self.mock_machine.transition_to.assert_called_with("COLLECT_ONLY")

    def test_golden_empire_regression_remains_intact(self):
        """
        Given: 黃金古國領域探索戰鬥 (無地下城 index)
        When: 遭遇領域強敵 golden_king.png
        Then: 依然點擊 giveup_battle.png，不產生地下城冷卻，轉移回 NAVIGATING
        """
        battle_handler = BattleHandler(self.mock_machine)
        mock_img = MagicMock()

        self.mock_machine.config = {
            "nemesis_action": "flee",
            "nemesis_templates": ["domains/golden_empire/exception/golden_king.png"],
        }
        self.mock_machine.current_dungeon_index = None
        self.mock_machine.is_in_dungeon = False

        clicked = []

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
        self.mock_machine.mouse.click.side_effect = lambda x, y: clicked.append((x, y))

        with patch("os.path.exists", return_value=True):
            battle_handler.handle(mock_img, self.rect)

        self.assertEqual(len(clicked), 3)
        self.mock_machine.transition_to.assert_called_with("NAVIGATING")


if __name__ == "__main__":
    unittest.main()
