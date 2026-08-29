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

    def test_collect_only_wakes_ready_quest_through_navigation_once(self):
        """A ready daily quest must leave idle mode via the shared navigation boundary."""
        machine = self._tier4_machine()
        task = self.mapper.parse_quest("史萊姆王的毀滅")
        scheduler = QuestScheduler()
        scheduler.add_task(task)
        machine.attach_quest_scheduler(scheduler)
        machine.current_state = machine.STATE_COLLECT_ONLY
        machine.matcher.match.return_value = (None, 0.0)
        screen_img = MagicMock()
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        machine.handlers[machine.STATE_COLLECT_ONLY].handle(screen_img, rect)

        self.assertEqual(machine.current_state, machine.STATE_NAVIGATING)
        self.assertFalse(machine.pending_daily_quest_preemption)
        self.assertFalse(machine.config.get("is_tier4_fallback", False))
        self.assertTrue(machine.config["enable_dungeon"])


    def test_advancing_when_all_quests_completed_restores_tier4_fallback(self):
        """Completing all daily quests must immediately restore Tier 4 fallback config."""
        machine = self._tier4_machine()
        task = self.mapper.parse_quest("清除蜥蜴")
        scheduler = QuestScheduler()
        scheduler.add_task(task)
        machine.attach_quest_scheduler(scheduler)

        # 模擬已切換到該任務的專屬關卡配置 (例如沙漠廢墟 middle)
        quest_cfg = task.to_config_dict(base_config=self.primary_config)
        machine.set_config(quest_cfg)
        self.assertFalse(machine.config.get("is_tier4_fallback", False))
        self.assertIn("沙漠廢墟", machine.config.get("name", ""))

        # 標記任務完成
        task.completed_count = task.target_count
        self.assertTrue(scheduler.is_all_completed())

        # 推進任務目標
        res = machine.check_and_advance_quest_target()
        self.assertIsNone(res)
        self.assertIsNone(machine.quest_scheduler)
        self.assertTrue(machine.config.get("is_tier4_fallback", False))
        self.assertEqual(machine.config.get("name"), self.primary_config["name"])

    def test_advancing_when_all_tasks_cooling_switches_to_tier4_fallback(self):
        """When all remaining quests are on cooldown, machine must fall back to Tier 4."""
        machine = self._tier4_machine()
        dungeon_task = self.mapper.parse_quest("史萊姆王的毀滅")
        scheduler = QuestScheduler()
        scheduler.add_task(dungeon_task)
        machine.attach_quest_scheduler(scheduler)

        # 模擬已套用地下城任務配置
        quest_cfg = dungeon_task.to_config_dict(base_config=self.primary_config)
        machine.set_config(quest_cfg)
        self.assertFalse(machine.config.get("is_tier4_fallback", False))

        # 設定該地下城正在冷卻中
        machine.dungeon_cooldowns[dungeon_task.dungeon_index] = 9999999999.0

        # 推進任務目標
        res = machine.check_and_advance_quest_target()
        self.assertIsNone(res)
        self.assertTrue(machine.config.get("is_tier4_fallback", False))
        self.assertEqual(machine.config.get("name"), self.primary_config["name"])


if __name__ == "__main__":
    unittest.main()
