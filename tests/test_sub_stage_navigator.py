import unittest
from utils.sub_stage_navigator import (
    SubStageDirection,
    SubStageListNavigator,
)


class TestSubStageListNavigator(unittest.TestCase):
    """
    SubStageListNavigator 純領域導航測試（測試先行 TDD）
    驗證自適應雙向方向判定、階層比對、有界重試以及維持 200px (±100px) 拉動手感。
    """

    def test_get_stage_key(self):
        self.assertEqual(SubStageListNavigator.get_stage_key("stages/first_stage.png"), "first")
        self.assertEqual(SubStageListNavigator.get_stage_key("stages/level6_middle.png"), "middle")
        self.assertEqual(SubStageListNavigator.get_stage_key("stages/six_stage.png"), "six")
        self.assertEqual(SubStageListNavigator.get_stage_key("stages/level1_final.png"), "final")
        self.assertEqual(SubStageListNavigator.get_stage_key("stages/level6_final.png"), "final")
        self.assertIsNone(SubStageListNavigator.get_stage_key("stages/stage_label.png"))
        self.assertIsNone(SubStageListNavigator.get_stage_key("common/door.png"))

    def test_get_candidate_sub_stage_templates(self):
        nav_path_lvl6 = ["common/door.png", "stages/level6_ice_cave.png", "stages/first_stage.png"]
        cands6 = SubStageListNavigator.get_candidate_sub_stage_templates(nav_path_lvl6)
        self.assertIn("stages/first_stage.png", cands6)
        self.assertIn("stages/six_stage.png", cands6)
        self.assertIn("stages/level6_middle.png", cands6)
        self.assertIn("stages/level6_final.png", cands6)
        self.assertEqual(len(cands6), 4)

        cands_generic = SubStageListNavigator.get_candidate_sub_stage_templates([])
        self.assertIn("stages/first_stage.png", cands_generic)
        self.assertIn("stages/level1_final.png", cands_generic)
        self.assertIn("stages/level6_final.png", cands_generic)

    def test_evaluate_when_target_already_visible(self):
        visible = ["stages/first_stage.png", "stages/level6_middle.png"]
        target = "stages/first_stage.png"
        direction, attempts = SubStageListNavigator.evaluate(
            visible_templates=visible,
            target_template=target,
            attempts=2,
            max_attempts=5,
        )
        self.assertEqual(direction, SubStageDirection.NONE)
        self.assertEqual(attempts, 0)

    def test_evaluate_target_below_visible_scrolls_down(self):
        # 畫面上看見 first (rank 0)，目標為 final (rank 3) ➔ 目標在下方，需向下拉動清單 (手勢向上拖曳)
        visible = ["stages/first_stage.png"]
        target = "stages/level6_final.png"
        direction, attempts = SubStageListNavigator.evaluate(
            visible_templates=visible,
            target_template=target,
            attempts=0,
            max_attempts=5,
        )
        self.assertEqual(direction, SubStageDirection.SCROLL_DOWN)
        self.assertEqual(attempts, 1)

        # 畫面上看見 middle (rank 1)，目標為 six (rank 2) ➔ 目標在下方
        direction2, attempts2 = SubStageListNavigator.evaluate(
            visible_templates=["stages/level6_middle.png"],
            target_template="stages/six_stage.png",
            attempts=1,
            max_attempts=5,
        )
        self.assertEqual(direction2, SubStageDirection.SCROLL_DOWN)
        self.assertEqual(attempts2, 2)

    def test_evaluate_target_above_visible_scrolls_up(self):
        # 畫面上看見 final (rank 3)，目標為 first (rank 0) ➔ 目標在上方，需向上拉動清單 (手勢向下拖曳)
        visible = ["stages/level6_final.png"]
        target = "stages/first_stage.png"
        direction, attempts = SubStageListNavigator.evaluate(
            visible_templates=visible,
            target_template=target,
            attempts=0,
            max_attempts=5,
        )
        self.assertEqual(direction, SubStageDirection.SCROLL_UP)
        self.assertEqual(attempts, 1)

        # 畫面上看見 six (rank 2)，目標為 middle (rank 1) ➔ 目標在上方
        direction2, attempts2 = SubStageListNavigator.evaluate(
            visible_templates=["stages/six_stage.png"],
            target_template="stages/level6_middle.png",
            attempts=2,
            max_attempts=5,
        )
        self.assertEqual(direction2, SubStageDirection.SCROLL_UP)
        self.assertEqual(attempts2, 3)

    def test_evaluate_no_sub_stage_visible_defaults(self):
        # 視野遺失，但目標是 first ➔ 預設向上拉回頂端
        dir_first, att_first = SubStageListNavigator.evaluate(
            visible_templates=[],
            target_template="stages/first_stage.png",
            attempts=1,
            max_attempts=5,
        )
        self.assertEqual(dir_first, SubStageDirection.SCROLL_UP)
        self.assertEqual(att_first, 2)

        # 視野遺失，但目標是 final ➔ 預設向下拉動
        dir_final, att_final = SubStageListNavigator.evaluate(
            visible_templates=[],
            target_template="stages/level6_final.png",
            attempts=1,
            max_attempts=5,
        )
        self.assertEqual(dir_final, SubStageDirection.SCROLL_DOWN)
        self.assertEqual(att_final, 2)

    def test_evaluate_attempts_exhausted(self):
        # 超過最大重試次數 ➔ 回傳 EXHAUSTED
        direction, attempts = SubStageListNavigator.evaluate(
            visible_templates=["stages/first_stage.png"],
            target_template="stages/level6_final.png",
            attempts=5,
            max_attempts=5,
        )
        self.assertEqual(direction, SubStageDirection.EXHAUSTED)
        self.assertEqual(attempts, 5)

    def test_calculate_drag_coordinates_matches_original_feeling(self):
        rect = {"left": 100, "top": 200, "width": 800, "height": 600}
        center_x = 100 + 400  # 500
        center_y = 200 + 300  # 500

        # SCROLL_DOWN: 手勢向上拖曳 (center_y + 100 ➔ center_y - 100)
        sx, sy, ex, ey = SubStageListNavigator.calculate_drag_coords(
            rect,
            SubStageDirection.SCROLL_DOWN,
            offset_y=100,
        )
        self.assertEqual(sx, center_x)
        self.assertEqual(ex, center_x)
        self.assertEqual(sy, center_y + 100)
        self.assertEqual(ey, center_y - 100)
        self.assertEqual(abs(sy - ey), 200)

        # SCROLL_UP: 手勢向下拖曳 (center_y - 100 ➔ center_y + 100)
        sx, sy, ex, ey = SubStageListNavigator.calculate_drag_coords(
            rect,
            SubStageDirection.SCROLL_UP,
            offset_y=100,
        )
        self.assertEqual(sx, center_x)
        self.assertEqual(ex, center_x)
        self.assertEqual(sy, center_y - 100)
        self.assertEqual(ey, center_y + 100)
        self.assertEqual(abs(sy - ey), 200)

        # NONE / EXHAUSTED: 回傳原地靜止
        sx, sy, ex, ey = SubStageListNavigator.calculate_drag_coords(
            rect,
            SubStageDirection.NONE,
        )
        self.assertEqual((sx, sy, ex, ey), (center_x, center_y, center_x, center_y))


if __name__ == "__main__":
    unittest.main()
