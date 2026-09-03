"""Compatibility entry point for the state-machine-owned stamina recovery."""

from config import get_stamina_retreat_settings
from states.stamina_retreat import StaminaRetreatRecovery, StaminaRetreatSettings


def handle_insufficient_stamina(state_machine, screen_img, rect):
    """Advance one observable stamina-recovery step from the supplied frame.

    Kept as a function for legacy callers, but deliberately does not capture,
    sleep, or chain clicks.  The machine owns the plan for its full lifecycle.
    """
    recovery = getattr(state_machine, "stamina_recovery", None)
    if not isinstance(recovery, StaminaRetreatRecovery):
        recovery = StaminaRetreatRecovery(
            StaminaRetreatSettings.from_mapping(get_stamina_retreat_settings())
        )
        state_machine.stamina_recovery = recovery
    return recovery.handle(state_machine, screen_img, rect)
