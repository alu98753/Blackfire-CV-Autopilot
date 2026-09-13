"""
Unit tests for Destination-Scoped REACH_TOWN Normalization Core.

Verifies:
1. ReachTownNormalizationPolicy: Pure mapping from SceneSnapshot to REACH_TOWN ActionDecision.
2. ReachTownNormalizationController:
   - Responsible ONLY for reaching Town ('到 Town 為止').
   - Invariant: MUST NOT touch subflow completion, red-dot logic, defer intent, or queue pop.
   - Invariant: Normalization failure isolation (retry exhaustion never mutates business intent).
   - Multi-step normalization pipeline (Modal over Building -> Dismiss Overlay -> Exit Building -> Town).
"""

import unittest
from unittest.mock import MagicMock

from states.navigation_intent import (
    ActionId,
    DecisionKind,
    IntentId,
    PostconditionId,
    ReasonCode,
)
from states.navigation_progress import NavigationProgress, NavigationProgressSettings
from states.reach_town_normalization import (
    NormalizationResult,
    ReachTownNormalizationController,
    ReachTownNormalizationPolicy,
)
from utils.scene_snapshot import ElementId, ElementMatch, SceneId, SceneSnapshot


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TestReachTownNormalizationPolicy(unittest.TestCase):
    def setUp(self):
        self.policy = ReachTownNormalizationPolicy()

    def test_overlay_dismissal_takes_precedence_over_all_scenes(self):
        """若有彈窗遮擋，無論當前處於建築內還是大廳，優先輸出 DISMISS_OVERLAY。"""
        elements = {
            ElementId.CLOSE_OVERLAY: ElementMatch(100, 100, 0.95, "common/quit.png"),
            ElementId.EXIT_BUILDING_TO_TOWN: ElementMatch(200, 200, 0.90, "exit.png"),
        }
        scene = SceneSnapshot(frame_id=1, captured_at=1.0, scene=SceneId.TOWN_BUILDING, elements=elements)
        decision = self.policy.resolve(scene)

        self.assertEqual(decision.kind, DecisionKind.CLICK)
        self.assertEqual(decision.action, ActionId.DISMISS_OVERLAY)
        self.assertEqual(decision.expected, PostconditionId.OVERLAY_CLOSED)
        self.assertEqual(decision.element, ElementId.CLOSE_OVERLAY)

    def test_building_egress_decision_resolved(self):
        """處於 TOWN_BUILDING 且見 EXIT_BUILDING_TO_TOWN 時，輸出 EXIT_BUILDING_TO_TOWN 回城。"""
        elements = {
            ElementId.EXIT_BUILDING_TO_TOWN: ElementMatch(50, 500, 0.92, "exit.png"),
        }
        scene = SceneSnapshot(frame_id=2, captured_at=2.0, scene=SceneId.TOWN_BUILDING, elements=elements)
        decision = self.policy.resolve(scene)

        self.assertEqual(decision.kind, DecisionKind.CLICK)
        self.assertEqual(decision.action, ActionId.EXIT_BUILDING_TO_TOWN)
        self.assertEqual(decision.expected, PostconditionId.TOWN)
        self.assertEqual(decision.element, ElementId.EXIT_BUILDING_TO_TOWN)

    def test_lobby_or_stage_select_resolves_goback_town(self):
        """處於 LOBBY / STAGE_SELECT 且見 GOBACK_TOWN 時，輸出 RETURN_TOWN 回城。"""
        for src_scene in (SceneId.LOBBY, SceneId.STAGE_SELECT, SceneId.DUNGEON_SELECT):
            elements = {
                ElementId.GOBACK_TOWN: ElementMatch(30, 40, 0.90, "goback.png"),
            }
            scene = SceneSnapshot(frame_id=3, captured_at=3.0, scene=src_scene, elements=elements)
            decision = self.policy.resolve(scene)

            self.assertEqual(decision.kind, DecisionKind.CLICK)
            self.assertEqual(decision.action, ActionId.RETURN_TOWN)
            self.assertEqual(decision.expected, PostconditionId.TOWN)
            self.assertEqual(decision.element, ElementId.GOBACK_TOWN)

    def test_domain_explore_resolves_exit_domain_to_lobby(self):
        """處於 DOMAIN_EXPLORE 且見 EXIT_TO_LOBBY 時，輸出 EXIT_DOMAIN_TO_LOBBY 至大廳。"""
        elements = {
            ElementId.EXIT_TO_LOBBY: ElementMatch(120, 80, 0.91, "exit_domain.png"),
        }
        scene = SceneSnapshot(frame_id=4, captured_at=4.0, scene=SceneId.DOMAIN_EXPLORE, elements=elements)
        decision = self.policy.resolve(scene)

        self.assertEqual(decision.kind, DecisionKind.CLICK)
        self.assertEqual(decision.action, ActionId.EXIT_DOMAIN_TO_LOBBY)
        self.assertEqual(decision.expected, PostconditionId.LOBBY)

    def test_town_scene_resolves_arrival(self):
        """若物理畫面已是 TOWN，輸出 DELEGATE 標記已到達。"""
        scene = SceneSnapshot(frame_id=5, captured_at=5.0, scene=SceneId.TOWN)
        decision = self.policy.resolve(scene)

        self.assertEqual(decision.kind, DecisionKind.DELEGATE)
        self.assertEqual(decision.expected, PostconditionId.TOWN)

    def test_unknown_scene_resolves_wait(self):
        """未知場景無可用邊界時，輸出 WAIT。"""
        scene = SceneSnapshot(frame_id=6, captured_at=6.0, scene=SceneId.UNKNOWN)
        decision = self.policy.resolve(scene)

        self.assertEqual(decision.kind, DecisionKind.WAIT)


class TestReachTownNormalizationController(unittest.TestCase):
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.mouse = MagicMock()
        self.controller = ReachTownNormalizationController(self.mock_machine)
        self.clock = FakeClock()
        self.settings = NavigationProgressSettings(
            action_timeout_seconds=2.0,
            action_max_attempts=3,
            collection_backoff_seconds=180.0,
            collection_recovery_failure_limit=3,
        )
        self.progress = NavigationProgress(self.settings)
        self.rect = {"left": 0, "top": 0}

    def test_is_in_town_boundary_only(self):
        """驗證控制器只判定是否處於 SceneId.TOWN，絕不觸碰子流程紅點或派發邏輯。"""
        town_scene = SceneSnapshot(frame_id=1, captured_at=1.0, scene=SceneId.TOWN)
        result = self.controller.step(town_scene, self.rect, self.progress)

        self.assertEqual(result, NormalizationResult.ARRIVED)
        # 斷言：控制器沒有調用任何業務方法
        self.mock_machine.dispatch_current_town_subflow.assert_not_called()
        self.mock_machine.complete_current_town_subflow.assert_not_called()
        self.mock_machine.pop_and_next_town_subflow.assert_not_called()

    def test_normalization_failure_domain_isolation_does_not_mutate_business_intent(self):
        """
        [Invariant 2 & User Instruction]:
        驗證當 REACH_TOWN 的物理動作重試耗盡 (ProgressStatus.DEFERRED) 時：
        - 控制器標記 FAILED
        - 嚴禁調用 defer_current_town_subflow (不得污染業務 Intent)
        - 嚴禁調用 pop_and_next_town_subflow (不得丟棄佇列)
        - 嚴禁調用 complete_current_town_subflow (不得假裝完成)
        """
        # 設置當前業務 intent
        self.mock_machine.current_town_subflow = "chest"

        # 模擬在店內發起退出建築點擊
        elements = {ElementId.EXIT_BUILDING_TO_TOWN: ElementMatch(50, 500, 0.92, "exit.png")}
        scene1 = SceneSnapshot(frame_id=1, captured_at=self.clock.monotonic(), scene=SceneId.TOWN_BUILDING, elements=elements)

        # 第 1 幀：發起點擊退出
        res1 = self.controller.step(scene1, self.rect, self.progress)
        self.assertEqual(res1, NormalizationResult.IN_PROGRESS)
        self.assertIsNotNone(self.progress.in_flight)
        self.assertEqual(self.progress.in_flight.action_id, ActionId.EXIT_BUILDING_TO_TOWN)

        # 推進時間超過 timeout，模擬多次重試耗盡
        for i in range(self.settings.action_max_attempts):
            self.clock.advance(self.settings.action_timeout_seconds + 0.1)
            scene_retry = SceneSnapshot(
                frame_id=10 + i, captured_at=self.clock.monotonic(), scene=SceneId.TOWN_BUILDING, elements=elements
            )
            res = self.controller.step(scene_retry, self.rect, self.progress)

        # 最終重試耗盡時，應回傳 FAILED
        self.assertEqual(res, NormalizationResult.FAILED)
        self.assertEqual(self.controller.last_failure_reason, "action_retry_exhausted")

        # 核心不變量斷言：
        self.mock_machine.defer_current_town_subflow.assert_not_called()
        self.mock_machine.pop_and_next_town_subflow.assert_not_called()
        self.mock_machine.complete_current_town_subflow.assert_not_called()
        self.assertEqual(self.mock_machine.current_town_subflow, "chest")

    def test_multi_step_normalization_pipeline(self):
        """
        驗證多步場景連續歸一化：
        Step 1: 建築內浮層遮擋 (CLOSE_OVERLAY) -> 點擊關閉 -> IN_PROGRESS
        Step 2: 浮層關閉後見 EXIT_BUILDING_TO_TOWN -> 點擊離場 -> IN_PROGRESS
        Step 3: 抵達城門 (SceneId.TOWN) -> ARRIVED
        """
        # Step 1: 彈窗遮擋
        elem_modal = {ElementId.CLOSE_OVERLAY: ElementMatch(400, 300, 0.95, "common/quit.png")}
        scene_modal = SceneSnapshot(frame_id=1, captured_at=self.clock.monotonic(), scene=SceneId.TOWN_BUILDING, elements=elem_modal)

        res1 = self.controller.step(scene_modal, self.rect, self.progress)
        self.assertEqual(res1, NormalizationResult.IN_PROGRESS)
        self.assertEqual(self.progress.in_flight.action_id, ActionId.DISMISS_OVERLAY)

        # 模擬彈窗關閉，看到建築退出按鈕
        self.clock.advance(0.5)
        elem_building = {ElementId.EXIT_BUILDING_TO_TOWN: ElementMatch(50, 500, 0.90, "exit.png")}
        scene_building = SceneSnapshot(frame_id=2, captured_at=self.clock.monotonic(), scene=SceneId.TOWN_BUILDING, elements=elem_building)

        res2 = self.controller.step(scene_building, self.rect, self.progress)
        self.assertEqual(res2, NormalizationResult.IN_PROGRESS)
        self.assertEqual(self.progress.in_flight.action_id, ActionId.EXIT_BUILDING_TO_TOWN)

        # 模擬點擊退出後，角色抵達城門
        self.clock.advance(0.5)
        scene_town = SceneSnapshot(frame_id=3, captured_at=self.clock.monotonic(), scene=SceneId.TOWN)

        res3 = self.controller.step(scene_town, self.rect, self.progress)
        self.assertEqual(res3, NormalizationResult.ARRIVED)
        self.assertIsNone(self.progress.in_flight)


if __name__ == "__main__":
    unittest.main()
