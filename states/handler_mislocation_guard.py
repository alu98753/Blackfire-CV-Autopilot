"""
Pure evidence-based mislocation guard for committed town subflow handlers.

Evaluates own-specific evidence vs generic building-context evidence to decide:
- RETAIN: Own-specific evidence verified; keep physical handler ownership.
- WAIT: Transient evidence absence or confirmation in progress; wait boundedly.
- RELINQUISH: Generic building evidence confirmed with own-specific evidence absent;
  yield physical ownership back to shared REACH_TOWN normalization.
"""

from enum import Enum


class MislocationDecision(str, Enum):
    RETAIN = "retain"
    WAIT = "wait"
    RELINQUISH = "relinquish"


class MislocationGuard:
    """
    Pure evidence-based policy for handling mislocation in committed handlers.
    Strictly isolated from state machine or I/O side effects.
    """

    def __init__(self, threshold: int = 2):
        self.threshold = threshold
        self.consecutive_count: int = 0

    def reset(self):
        self.consecutive_count = 0

    def evaluate(
        self,
        own_evidence: bool,
        generic_building_evidence: bool,
    ) -> MislocationDecision:
        """
        Evaluate frame observations against ownership contracts:
        1. own_evidence is True -> retain ownership (counter reset to 0).
        2. generic_building_evidence is True + own_evidence is False ->
           suspected mislocation; increment counter.
           If counter reaches threshold -> RELINQUISH.
           Else -> WAIT.
        3. Neither evidence is True -> counter reset to 0, WAIT for transient transition.
        """
        if own_evidence:
            self.consecutive_count = 0
            return MislocationDecision.RETAIN

        if generic_building_evidence:
            self.consecutive_count += 1
            if self.consecutive_count >= self.threshold:
                return MislocationDecision.RELINQUISH
            return MislocationDecision.WAIT

        self.consecutive_count = 0
        return MislocationDecision.WAIT
