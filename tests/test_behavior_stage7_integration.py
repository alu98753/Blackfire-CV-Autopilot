"""
Unit & Behavioral integration test for Stage 7 (Forgotten Wasteland) support.
"""

import unittest
from config import BASE_STAGE_LEVELS, STAGE_TEMPLATES
from utils.config_helper import get_stage_configs
from utils.quest_mapper import TaskNode
from utils.sub_stage_navigator import SubStageListNavigator


class TestStage7Integration(unittest.TestCase):
    def test_base_stage_levels_contains_stage_7(self):
        """驗證 config/defaults.toml 正確導出 Stage 7 基本資訊。"""
        self.assertIn("7", BASE_STAGE_LEVELS)
        self.assertEqual(BASE_STAGE_LEVELS["7"]["name"], "遺忘荒地")
        self.assertEqual(BASE_STAGE_LEVELS["7"]["entry"], "stages/level7_forgotten_wasteland.png")

    def test_get_stage_configs_resolves_stage_7(self):
        """驗證動態關卡組裝服務 get_stage_configs() 能精準包含第 7 關與其通用小關卡。"""
        stage_configs = get_stage_configs()
        self.assertIn("7", stage_configs)
        cfg7 = stage_configs["7"]
        self.assertEqual(cfg7["name"], "遺忘荒地")
        self.assertEqual(cfg7["entry"], "stages/level7_forgotten_wasteland.png")
        
        # 驗證通用小關卡 first, middle, six, final 全數正確掛載
        self.assertIn("first", cfg7["sub_stages"])
        self.assertEqual(cfg7["sub_stages"]["first"], "stages/first_stage.png")
        self.assertIn("middle", cfg7["sub_stages"])
        self.assertEqual(cfg7["sub_stages"]["middle"], "stages/boss_skull.png")
        self.assertIn("six", cfg7["sub_stages"])
        self.assertEqual(cfg7["sub_stages"]["six"], "stages/six_stage.png")
        self.assertIn("final", cfg7["sub_stages"])
        self.assertEqual(cfg7["sub_stages"]["final"], "stages/boss_skull.png")

    def test_task_node_routes_stage_7(self):
        """驗證懸賞任務節點派發至第 7 關時能正確產出對應配置與導航路徑。"""
        node = TaskNode(
            quest_title="討伐荒原半獸人",
            mode_type="stage",
            target_count=5,
            stage_level=7,
            sub_stage="first",
        )
        cfg = node.to_config_dict()
        self.assertEqual(cfg["stage_level"], 7)
        self.assertEqual(cfg["stage_entry"], "stages/level7_forgotten_wasteland.png")
        self.assertIn("遺忘荒地", cfg["name"])
        self.assertIn("stages/level7_forgotten_wasteland.png", cfg["stage_navigation_path"])
        self.assertIn("stages/first_stage.png", cfg["stage_navigation_path"])

    def test_stage_templates_contains_stage_7(self):
        """驗證大廳與場景偵測的備援 stage_templates 包含第 7 關。"""
        self.assertIn("stages/level7_forgotten_wasteland.png", STAGE_TEMPLATES)

    def test_sub_stage_navigator_candidates_for_stage_7(self):
        """驗證導航器在遇到包含 level7 的 nav_path 時能自動包含 level7 相關候選。"""
        nav_path_lvl7 = [
            "common/door.png",
            "stages/level7_forgotten_wasteland.png",
            "stages/first_stage.png",
        ]
        cands = SubStageListNavigator.get_candidate_sub_stage_templates(nav_path_lvl7)
        self.assertIn("stages/first_stage.png", cands)
        self.assertIn("stages/six_stage.png", cands)
        self.assertIn("stages/boss_skull.png", cands)
        self.assertEqual(len(cands), 3)


if __name__ == "__main__":
    unittest.main()
