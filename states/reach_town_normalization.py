"""
Destination-Scoped REACH_TOWN Normalization Core.

Provides pure normalization policy and multi-frame controller strictly bounded
to normalizing physical world state to SceneId.TOWN.

ARCHITECTURAL INVARIANTS:
1. Destination-scoped:
   REACH_TOWN applies to consumers that require TOWN, not to every producer that
   finishes in the game world.
2. Failure domain isolation:
   Physical normalization failures (action timeout retry exhaustion or unidentifiable scenes)
   MUST NOT mutate, complete, defer, consume, or replace the business intent.
3. Strict responsibility boundary (Single Responsibility Principle):
   ReachTownNormalizationController is responsible ONLY for 'reaching Town' (到 Town 為止).
   It MUST NOT touch:
   - town subflow completion
   - red-dot business decisions
   - defer business intent
   - queue pop
"""

import logging
from enum import Enum

from states.navigation_intent import (
    ActionDecision,
    ActionId,
    DecisionKind,
    IntentId,
    PostconditionId,
    ReasonCode,
)
from states.navigation_progress import NavigationProgress, ProgressStatus
from states.navigation_table import NavigationGoal, NavigationTable
from utils.scene_snapshot import ElementId, SceneId, SceneSnapshot


class NormalizationResult(str, Enum):
    """Observable outcome of one normalization step."""

    ARRIVED = "arrived"          # Physical world verified as SceneId.TOWN
    IN_PROGRESS = "in_progress"  # Physical action issued (e.g. click exit / dismiss overlay)
    WAITING = "waiting"          # Waiting for in-flight postcondition or transition
    FAILED = "failed"            # Action retry exhausted or unresolvable scene (failure isolated)


class ReachTownNormalizationPolicy:
    """Pure decision policy mapping SceneSnapshot to a REACH_TOWN ActionDecision."""

    def __init__(self, navigation_table: NavigationTable | None = None):
        self.navigation_table = navigation_table or NavigationTable()

    def resolve(self, scene: SceneSnapshot) -> ActionDecision:
        """
        Pure deterministic resolution of next physical normalization action.
        Independent of any specific business intent or subflow key.
        """
        # 1. Overlay dismissal takes precedence across all non-Town surfaces
        if scene.has(ElementId.CLOSE_OVERLAY):
            return ActionDecision.click(
                ReasonCode.TOWN_SUBFLOW_CLOSE_OVERLAY,
                ActionId.DISMISS_OVERLAY,
                PostconditionId.OVERLAY_CLOSED,
                ElementId.CLOSE_OVERLAY,
            )

        # 2. Query declared REACH_TOWN edges from navigation graph (e.g. building egress, return town)
        edge = self.navigation_table.next_goal_edge(scene, NavigationGoal.REACH_TOWN)
        if edge is not None:
            return ActionDecision.click(
                edge.reason,
                edge.action,
                edge.postcondition,
                edge.required_element,
            )

        # 3. If physically verified as TOWN, arrival is established
        if scene.scene == SceneId.TOWN:
            return ActionDecision.delegate(
                ReasonCode.TOWN_SUBFLOW_READY,
                ActionId.RETURN_TOWN,
                PostconditionId.TOWN,
            )

        # 4. Unknown scenes, loading frames, or intermediate states wait without action
        return ActionDecision.wait()


class ReachTownNormalizationController:
    """
    Manages the multi-frame lifecycle of normalizing physical state to SceneId.TOWN.

    BOUNDARIES:
    - Responsible ONLY for reaching Town ('到 Town 為止').
    - Isolated from business intent scheduling and queue manipulation.
    """

    def __init__(
        self,
        machine,
        policy: ReachTownNormalizationPolicy | None = None,
    ):
        self.machine = machine
        self.policy = policy or ReachTownNormalizationPolicy()
        self.last_failure_reason: str | None = None

    def reset_failure(self):
        """Reset failure escalation memory after recovery."""
        self.last_failure_reason = None

    @staticmethod
    def is_in_town(scene: SceneSnapshot) -> bool:
        """Return True only when snapshot physically proves SceneId.TOWN."""
        return scene.scene == SceneId.TOWN

    def step(
        self,
        scene: SceneSnapshot,
        rect: dict,
        progress: NavigationProgress | None = None,
        intent_id: IntentId = IntentId.TOWN_SUBFLOW,
    ) -> NormalizationResult:
        """
        Execute one normalization frame towards SceneId.TOWN.

        Returns NormalizationResult indicating current physical normalization status.
        """
        # 1. Track in-flight action progress if one is actively committed
        if isinstance(progress, NavigationProgress) and progress.in_flight:
            status = progress.observe(scene, scene.captured_at)
            if status == ProgressStatus.WAITING:
                return NormalizationResult.WAITING
            if status == ProgressStatus.DEFERRED:
                # Normalization action retry exhausted!
                # STRICT INVARIANT: Must NOT defer, pop, or complete business intent.
                self.last_failure_reason = "action_retry_exhausted"
                logging.warning(
                    "⚠️ [ReachTownNormalizationController] REACH_TOWN normalization action retry "
                    "exhausted; failure domain isolated, NOT mutating business intent."
                )
                return NormalizationResult.FAILED
            # If status == PROGRESSED or TIMED_OUT, proceed to verify state and resolve next decision

        # 2. If previously exhausted and not recovered/arrived, retain FAILED state
        if self.last_failure_reason is not None and not self.is_in_town(scene):
            return NormalizationResult.FAILED

        # 3. Resolve next action from pure policy FIRST.
        # Critical Invariant: Blocking physical actions (e.g. CLOSE_OVERLAY) take precedence
        # over destination satisfaction (Town + overlay MUST dismiss overlay first!).
        decision = self.policy.resolve(scene)

        # 3.1 Execute physical action (overlay dismissal, building egress, or lobby return)
        if decision.kind == DecisionKind.CLICK and decision.element:
            match = scene.elements.get(decision.element)
            if match is None:
                return NormalizationResult.WAITING

            self.machine.mouse.click(
                rect["left"] + match.client_x,
                rect["top"] + match.client_y,
            )
            if isinstance(progress, NavigationProgress):
                progress.begin(
                    intent_id,
                    decision.action,
                    decision.expected,
                    scene.frame_id,
                    scene.captured_at,
                )
            logging.info(
                "[ReachTownNormalizationController] scene=%s action=%s reason=%s expected=%s",
                scene.scene.value,
                decision.action.value if decision.action else None,
                decision.reason.value,
                decision.expected.value if decision.expected else None,
            )
            return NormalizationResult.IN_PROGRESS

        # 3.2 Physical destination verified (SceneId.TOWN without blocking overlay)
        if self.is_in_town(scene):
            self.last_failure_reason = None
            return NormalizationResult.ARRIVED

        # 3.3 Transient or unresolvable frame waiting
        if decision.kind == DecisionKind.WAIT:
            return NormalizationResult.WAITING

        return NormalizationResult.WAITING
