"""
Unit & Behavioral integration test for Stage 8 (Fiery Volcano) support.
"""

import unittest
from config import BASE_STAGE_LEVELS, STAGE_TEMPLATES
from utils.config_helper import get_stage_configs
from utils.quest_mapper import TaskNode, QuestMapper
from utils.sub_stage_navigator import SubStageListNavigator


class TestStage8Integration(unittest.TestCase):
    def test_base_stage_levels_contains_stage_8(self):
        """驗證 config/defaults.toml 正確導出 Stage 8 基本資訊。"""
        self.assertIn("8", BASE_STAGE_LEVELS)
        self.assertEqual(BASE_STAGE_LEVELS["8"]["name"], "熾熱火山")
        self.assertEqual(BASE_STAGE_LEVELS["8"]["entry"], "stages/level8_fiery_volcano.png")

    def test_get_stage_configs_resolves_stage_8(self):
        """驗證動態關卡組裝服務 get_stage_configs() 能精準包含第 8 關與其通用小關卡。"""
        stage_configs = get_stage_configs()
        self.assertIn("8", stage_configs)
        cfg8 = stage_configs["8"]
        self.assertEqual(cfg8["name"], "熾熱火山")
        self.assertEqual(cfg8["entry"], "stages/level8_fiery_volcano.png")
        
        # 驗證通用小關卡 first, middle, six, final 全數正確掛載
        self.assertIn("first", cfg8["sub_stages"])
        self.assertEqual(cfg8["sub_stages"]["first"], "stages/first_stage.png")
        self.assertIn("middle", cfg8["sub_stages"])
        self.assertEqual(cfg8["sub_stages"]["middle"], "stages/boss_skull.png")
        self.assertIn("six", cfg8["sub_stages"])
        self.assertEqual(cfg8["sub_stages"]["six"], "stages/six_stage.png")
        self.assertIn("final", cfg8["sub_stages"])
        self.assertEqual(cfg8["sub_stages"]["final"], "stages/boss_skull.png")

    def test_task_node_routes_stage_8(self):
        """驗證懸賞任務節點派發至第 8 關時能正確產出對應配置與導航路徑。"""
        node = TaskNode(
            quest_title="討伐熔岩火怪",
            mode_type="stage",
            target_count=5,
            stage_level=8,
            sub_stage="first",
        )
        cfg = node.to_config_dict()
        self.assertEqual(cfg["stage_level"], 8)
        self.assertEqual(cfg["stage_entry"], "stages/level8_fiery_volcano.png")
        self.assertIn("熾熱火山", cfg["name"])
        self.assertIn("stages/level8_fiery_volcano.png", cfg["stage_navigation_path"])
        self.assertIn("stages/first_stage.png", cfg["stage_navigation_path"])

    def test_defeat_fire_elemental_mapped_to_stage8_six(self):
        """驗證『擊敗火元素』懸賞任務被精準映射至 Stage 8 的 sub_stage 'six'。"""
        mapper = QuestMapper()
        node = mapper.parse_quest("擊敗火元素")
        self.assertIsNotNone(node)
        self.assertEqual(node.mode_type, "stage")
        self.assertEqual(node.stage_level, 8)
        self.assertEqual(node.sub_stage, "six")
        self.assertEqual(node.counting_policy, TaskNode.POLICY_DETERMINISTIC)
        cfg = node.to_config_dict()
        self.assertEqual(cfg["stage_entry"], "stages/level8_fiery_volcano.png")
        self.assertIn("stages/level8_fiery_volcano.png", cfg["stage_navigation_path"])
        self.assertIn("stages/six_stage.png", cfg["stage_navigation_path"])

    def test_stage_templates_contains_stage_8(self):
        """驗證大廳與場景偵測的備援 stage_templates 包含第 8 關。"""
        self.assertIn("stages/level8_fiery_volcano.png", STAGE_TEMPLATES)

    def test_sub_stage_navigator_candidates_for_stage_8(self):
        """驗證導航器在遇到包含 level8 的 nav_path 時能自動包含 level8 相關候選。"""
        nav_path_lvl8 = [
            "common/door.png",
            "stages/level8_fiery_volcano.png",
            "stages/first_stage.png",
        ]
        cands = SubStageListNavigator.get_candidate_sub_stage_templates(nav_path_lvl8)
        self.assertIn("stages/first_stage.png", cands)
        self.assertIn("stages/six_stage.png", cands)
        self.assertIn("stages/boss_skull.png", cands)
        self.assertEqual(len(cands), 3)


if __name__ == "__main__":
    unittest.main()
