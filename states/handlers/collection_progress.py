"""Shared collection completion and bounded recovery operations."""

from states.navigation_progress import CollectionOutcome


def complete_collection(machine, intent_id, cooldown_detected):
    outcome = (
        CollectionOutcome.COOLDOWN
        if cooldown_detected
        else CollectionOutcome.SUCCESS
    )
    machine.navigation_progress.complete(intent_id, outcome)


def defer_collection(machine, intent_id):
    machine.navigation_progress.defer(intent_id, machine.clock.monotonic())
    recovery_intent = machine.navigation_progress.take_recovery_intent()
    if recovery_intent is None:
        return False
    machine.request_relaunch(
        f"collection_recovery_limit_{recovery_intent.value}"
    )
    return True
