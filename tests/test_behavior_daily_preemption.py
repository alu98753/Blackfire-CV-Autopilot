import unittest
from unittest.mock import MagicMock

from states.state_machine import GameStateMachine
from utils.quest_mapper import QuestMapper
from utils.quest_scheduler import QuestScheduler


class TestDailyQuestPreemptionBehavior(unittest.TestCase):
    def setUp(self):
        self.mapper = QuestMapper()
        self.primary_config = {
            "name": "Tier 4 baseline",
            "type": "mix",
            "enable_dungeon": False,
            "enable_stage_farming": True,
        }

    def _tier4_machine(self):
        machine = GameStateMachine(MagicMock(), MagicMock(), MagicMock(), preload_ocr=False)
        machine.primary_config = self.primary_config.copy()
        machine.apply_tier4_fallback_config()
        return machine

    def test_scheduler_reports_earliest_pending_quest_ready_time(self):
        scheduler = QuestScheduler()
        first = self.mapper.parse_quest("史萊姆王的毀滅")
        second = self.mapper.parse_quest("破除森林的枷鎖")
        scheduler.add_task(first)
        scheduler.add_task(second)

        now = 10_000.0
        cooldowns = {
            first.dungeon_index: now + 90.0,
            second.dungeon_index: now + 30.0,
        }

        self.assertEqual(
            scheduler.get_next_ready_at(dungeon_cooldowns=cooldowns, now_ts=now),
            now + 30.0,
        )

    def test_preemption_is_armed_without_reconfiguring_tier4(self):
        machine = self._tier4_machine()
        scheduler = MagicMock()
        scheduler.get_next_action_node.return_value = (None, "all cooling")
        scheduler.get_next_ready_at.return_value = 1_100.0
        machine.quest_scheduler = scheduler
        before = machine.config.copy()

        self.assertFalse(machine.arm_daily_quest_preemption(now_ts=1_000.0))
        self.assertEqual(machine.next_daily_quest_ready_at, 1_100.0)
        self.assertFalse(machine.pending_daily_quest_preemption)
        self.assertEqual(machine.config, before)

    def test_reapplying_active_tier4_refreshes_deadline_without_reconfiguring(self):
        machine = self._tier4_machine()
        scheduler = MagicMock()
        scheduler.get_next_action_node.return_value = (None, "all cooling")
        scheduler.get_next_ready_at.return_value = 1_200.0
        machine.quest_scheduler = scheduler
        before = machine.config.copy()

        self.assertFalse(machine.apply_tier4_fallback_config())
        self.assertEqual(machine.next_daily_quest_ready_at, 1_200.0)
        self.assertEqual(machine.config, before)

    def test_deadline_latches_preemption_without_changing_config_mid_battle(self):
        machine = self._tier4_machine()
        scheduler = MagicMock()
        ready_task = MagicMock()
        scheduler.get_next_action_node.return_value = (ready_task, "ready")
        machine.quest_scheduler = scheduler
        machine.next_daily_quest_ready_at = 1_100.0
        machine.current_state = machine.STATE_BATTLE
        before = machine.config.copy()

        self.assertFalse(machine.poll_daily_quest_preemption(now_ts=1_099.0))
        self.assertTrue(machine.poll_daily_quest_preemption(now_ts=1_100.0))
        self.assertTrue(machine.pending_daily_quest_preemption)
        self.assertEqual(machine.config, before)

    def test_navigation_consumes_latched_preemption_once(self):
        machine = self._tier4_machine()
        machine.pending_daily_quest_preemption = True
        machine.check_and_advance_quest_target = MagicMock(return_value=MagicMock())

        self.assertTrue(machine.consume_daily_quest_preemption_for_navigation())
        machine.check_and_advance_quest_target.assert_called_once_with()
        self.assertFalse(machine.pending_daily_quest_preemption)


if __name__ == "__main__":
    unittest.main()
