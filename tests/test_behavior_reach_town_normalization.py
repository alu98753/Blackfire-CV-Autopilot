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

    def test_town_with_overlay_must_dismiss_overlay_before_arrived(self):
        """
        [Blocker 1 Fix Verification]:
        當畫面雖然是 SceneId.TOWN，但同時存在 ElementId.CLOSE_OVERLAY 時：
        - 物理遮擋動作優先於目的地滿足判定！
        - 第 1 步：必須輸出 DISMISS_OVERLAY，回傳 IN_PROGRESS，絕不得提前回傳 ARRIVED。
        - 第 2 步：待浮層關閉且重新 observe 為乾淨 Town 後，才回傳 ARRIVED。
        """
        elem_with_overlay = {
            ElementId.CLOSE_OVERLAY: ElementMatch(500, 300, 0.95, "common/quit.png"),
        }
        scene_town_blocked = SceneSnapshot(
            frame_id=1,
            captured_at=self.clock.monotonic(),
            scene=SceneId.TOWN,
            elements=elem_with_overlay,
        )

        # 第 1 幀：必須點擊關閉浮層，回傳 IN_PROGRESS，絕不可直接 ARRIVED
        res1 = self.controller.step(scene_town_blocked, self.rect, self.progress)
        self.assertEqual(res1, NormalizationResult.IN_PROGRESS)
        self.assertNotEqual(res1, NormalizationResult.ARRIVED)
        self.assertIsNotNone(self.progress.in_flight)
        self.assertEqual(self.progress.in_flight.action_id, ActionId.DISMISS_OVERLAY)

        # 模擬浮層關閉，下一幀是乾淨無遮擋的 TOWN
        self.clock.advance(0.5)
        scene_clean_town = SceneSnapshot(
            frame_id=2,
            captured_at=self.clock.monotonic(),
            scene=SceneId.TOWN,
            elements={},
        )
        res2 = self.controller.step(scene_clean_town, self.rect, self.progress)
        self.assertEqual(res2, NormalizationResult.ARRIVED)
        self.assertIsNone(self.progress.in_flight)

    def test_normalization_failure_retains_failed_state_until_recovery_or_arrival(self):
        """
        [Blocker 2 Fix Verification]:
        驗證當 REACH_TOWN 重試耗盡回傳 FAILED 後：
        - 若未經 recovery/reset 且畫面仍處於未抵達場景，後續呼叫保持 FAILED，不重啟盲目點擊。
        - 經 reset_failure() 後方可再次發起正規化。
        """
        elements = {ElementId.EXIT_BUILDING_TO_TOWN: ElementMatch(50, 500, 0.92, "exit.png")}
        scene = SceneSnapshot(frame_id=1, captured_at=self.clock.monotonic(), scene=SceneId.TOWN_BUILDING, elements=elements)

        # 發起並耗盡重試
        self.controller.step(scene, self.rect, self.progress)
        for i in range(self.settings.action_max_attempts):
            self.clock.advance(self.settings.action_timeout_seconds + 0.1)
            scene_retry = SceneSnapshot(frame_id=10 + i, captured_at=self.clock.monotonic(), scene=SceneId.TOWN_BUILDING, elements=elements)
            res = self.controller.step(scene_retry, self.rect, self.progress)

        self.assertEqual(res, NormalizationResult.FAILED)

        # 同樣場景下一幀再調用 step：依然維持 FAILED，不重複發起點擊
        self.clock.advance(0.5)
        scene_next = SceneSnapshot(frame_id=20, captured_at=self.clock.monotonic(), scene=SceneId.TOWN_BUILDING, elements=elements)
        res_next = self.controller.step(scene_next, self.rect, self.progress)
        self.assertEqual(res_next, NormalizationResult.FAILED)

        # 經重置後
        self.controller.reset_failure()
        res_after_reset = self.controller.step(scene_next, self.rect, self.progress)
        self.assertEqual(res_after_reset, NormalizationResult.IN_PROGRESS)

    def test_town_with_clear_anchor_establishes_readiness_immediately(self):
        """
        [Invariant 6 / Scenario 9 Verification]:
        當畫面為 SceneId.TOWN 且包含 ElementId.TOWN_CLEAR_ANCHOR 且無 blocker 時：
        立即滿足 Town Interaction Readiness，回傳 NormalizationResult.ARRIVED。
        """
        elements = {
            ElementId.DOOR: ElementMatch(100, 200, 0.9, "common/door.png"),
            ElementId.TOWN_CLEAR_ANCHOR: ElementMatch(500, 400, 0.92, "town_building/arena_of_glory/arena_of_glory.png"),
        }
        scene = SceneSnapshot(frame_id=1, captured_at=self.clock.monotonic(), scene=SceneId.TOWN, elements=elements)
        result = self.controller.step(scene, self.rect, self.progress)
        self.assertEqual(result, NormalizationResult.ARRIVED)

    def test_town_without_clear_anchor_when_required_bounds_unknown_then_fails_isolated(self):
        """
        [Implementation Guard / Scenario 8 & Invariant 2 Verification]:
        當 require_clear_anchor=True 時：
        - 畫面雖為 SceneId.TOWN 但無 TOWN_CLEAR_ANCHOR：Readiness 為 UNKNOWN。
        - 進行有界重新觀察（bounded re-observation），前 2 幀回傳 WAITING。
        - 第 3 幀次數耗盡，升級為 FAILED (readiness_unknown_exhausted)。
        - 嚴格守護 Invariant 2：絕不 defer、pop 或 complete 業務 Intent！
        """
        controller = ReachTownNormalizationController(
            self.mock_machine,
            max_readiness_unknown_frames=3,
            require_clear_anchor=True,
        )
        self.mock_machine.current_town_subflow = "chest"
        elements = {ElementId.DOOR: ElementMatch(100, 200, 0.9, "common/door.png")}

        # 第 1 幀：UNKNOWN -> WAITING
        scene1 = SceneSnapshot(frame_id=1, captured_at=1.0, scene=SceneId.TOWN, elements=elements)
        res1 = controller.step(scene1, self.rect, self.progress)
        self.assertEqual(res1, NormalizationResult.WAITING)

        # 第 2 幀：UNKNOWN -> WAITING
        scene2 = SceneSnapshot(frame_id=2, captured_at=1.5, scene=SceneId.TOWN, elements=elements)
        res2 = controller.step(scene2, self.rect, self.progress)
        self.assertEqual(res2, NormalizationResult.WAITING)

        # 第 3 幀：UNKNOWN 次數耗盡 -> FAILED
        scene3 = SceneSnapshot(frame_id=3, captured_at=2.0, scene=SceneId.TOWN, elements=elements)
        res3 = controller.step(scene3, self.rect, self.progress)
        self.assertEqual(res3, NormalizationResult.FAILED)
        self.assertEqual(controller.last_failure_reason, "readiness_unknown_exhausted")

        # 斷言：失敗領域嚴格隔離，絕不觸碰業務 Intent
        self.mock_machine.defer_current_town_subflow.assert_not_called()
        self.mock_machine.pop_and_next_town_subflow.assert_not_called()
        self.mock_machine.complete_current_town_subflow.assert_not_called()
        self.assertEqual(self.mock_machine.current_town_subflow, "chest")

    def test_town_clear_anchor_appears_during_reobservation_resolves_to_arrived(self):
        """驗證若在有界重新觀察期間 TOWN_CLEAR_ANCHOR 出現，順利收斂為 ARRIVED。"""
        controller = ReachTownNormalizationController(
            self.mock_machine,
            max_readiness_unknown_frames=3,
            require_clear_anchor=True,
        )
        elem_no_anchor = {ElementId.DOOR: ElementMatch(100, 200, 0.9, "common/door.png")}
        scene1 = SceneSnapshot(frame_id=1, captured_at=1.0, scene=SceneId.TOWN, elements=elem_no_anchor)
        self.assertEqual(controller.step(scene1, self.rect, self.progress), NormalizationResult.WAITING)

        # 第 2 幀 clear anchor 成功辨識
        elem_with_anchor = {
            ElementId.DOOR: ElementMatch(100, 200, 0.9, "common/door.png"),
            ElementId.TOWN_CLEAR_ANCHOR: ElementMatch(500, 400, 0.92, "arena.png"),
        }
        scene2 = SceneSnapshot(frame_id=2, captured_at=1.5, scene=SceneId.TOWN, elements=elem_with_anchor)
        self.assertEqual(controller.step(scene2, self.rect, self.progress), NormalizationResult.ARRIVED)

    def test_production_failure_latch_auto_resets_when_scene_changes(self):
        """
        [Production Reset Lifecycle Verification]:
        驗證當在 TOWN_BUILDING 發生重試耗盡 latch 為 FAILED 後，
        若物理場景發生變化（例如 recovery 帶角色回到 LOBBY）：
        控制器自動感知場景遷移並自我重置 failure latch，恢復正常導航！
        """
        elem_building = {ElementId.EXIT_BUILDING_TO_TOWN: ElementMatch(50, 500, 0.92, "exit.png")}
        scene_building = SceneSnapshot(frame_id=1, captured_at=self.clock.monotonic(), scene=SceneId.TOWN_BUILDING, elements=elem_building)

        # 耗盡重試進入 FAILED
        self.controller.step(scene_building, self.rect, self.progress)
        for i in range(self.settings.action_max_attempts):
            self.clock.advance(self.settings.action_timeout_seconds + 0.1)
            scene_retry = SceneSnapshot(frame_id=10 + i, captured_at=self.clock.monotonic(), scene=SceneId.TOWN_BUILDING, elements=elem_building)
            self.controller.step(scene_retry, self.rect, self.progress)
        self.assertEqual(self.controller.last_failure_reason, "action_retry_exhausted")

        # 場景變更至 LOBBY（例如 recovery 退出或外部轉場）
        elem_lobby = {ElementId.GOBACK_TOWN: ElementMatch(30, 40, 0.90, "goback_town.png")}
        scene_lobby = SceneSnapshot(frame_id=20, captured_at=self.clock.monotonic(), scene=SceneId.LOBBY, elements=elem_lobby)

        # 自動解鎖 latch 並發起 RETURN_TOWN 點擊
        res = self.controller.step(scene_lobby, self.rect, self.progress)
        self.assertEqual(res, NormalizationResult.IN_PROGRESS)
        self.assertIsNone(self.controller.last_failure_reason)
        self.assertEqual(self.progress.in_flight.action_id, ActionId.RETURN_TOWN)


if __name__ == "__main__":
    unittest.main()
