"""Persist explicit CLI selections to the active profile."""


def persist_mode_updates(config, updates: dict) -> None:
    """Write changed CLI choices to the TOML mode table that supplied the config."""
    from config import get_active_profile, update_profile_config

    mode_key = config.get("_config_mode_key", config.get("type", "mix"))
    update_profile_config(get_active_profile(), {"primary_modes": {mode_key: updates}})
