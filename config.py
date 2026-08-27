"""Compatibility exports backed by the declarative config/defaults.toml file."""

from __future__ import annotations

import logging
from pathlib import Path

from utils.config_helper import get_stage_configs
from utils.config_manager import JsonConfigManager, TomlConfigManager


WINDOW_TITLE = "Blackfire Crusade"
CONFIG_DIR = Path(__file__).with_name("config")
DEFAULTS_PATH = CONFIG_DIR / "defaults.toml"
_DEFAULTS_MANAGER = TomlConfigManager(DEFAULTS_PATH)


def get_defaults_config() -> dict:
    """Return a safe snapshot of the declarative defaults configuration."""
    return _DEFAULTS_MANAGER.snapshot()


def _load_legacy_exports() -> dict:
    settings = get_defaults_config()
    if settings.get("config_version") != 1:
        raise ValueError("不支援的 config/defaults.toml config_version")
    return settings


_SETTINGS = _load_legacy_exports()


def _restore_mode_key_types(modes: dict) -> dict:
    """TOML table keys are strings; runtime dungeon indices are integers."""
    for mode in modes.values():
        cooldown_map = mode.get("cooldown_map")
        if isinstance(cooldown_map, dict):
            mode["cooldown_map"] = {
                int(index) if str(index).isdigit() else index: cooldown
                for index, cooldown in cooldown_map.items()
            }
    return modes

# Existing imports remain valid while configuration data now lives in TOML.
GLOBAL_SETTINGS = _SETTINGS["global"]
QUEST_MAX_RUN_LIMIT = _SETTINGS["quest"]["max_run_limit"]
QUEST_TARGET_COUNT = _SETTINGS["quest"]["target_count"]
QUEST_STAGE_BATCH_SIZE = _SETTINGS["quest"]["stage_batch_size"]
QUEST_DUNGEON_BATCH_SIZE = _SETTINGS["quest"]["dungeon_batch_size"]

DUNGEON_NAMES = _SETTINGS["catalog"]["dungeon_names"]
DUNGEON_ENTRY_TEMPLATES = _SETTINGS["catalog"]["dungeon_entry_templates"]
STAGE_TEMPLATES = _SETTINGS["catalog"]["stage_templates"]

TASK_BANNER_OCR_OFFSET = _SETTINGS["ocr"]["task_banner"]
BULLETIN_BOARD_OCR_OFFSET = _SETTINGS["ocr"]["bulletin_board"]

PRIMARY_MODES = _restore_mode_key_types(_SETTINGS["primary_modes"])
SUBFLOW_CONFIGS = _SETTINGS["subflow_configs"]
BASE_STAGE_LEVELS = _SETTINGS["base_stage_levels"]

DEFAULT_DISASSEMBLE_COLORS = _SETTINGS["defaults"]["disassemble_colors"]
DEFAULT_KEEP_COLORS = _SETTINGS["defaults"]["keep_colors"]
DEFAULT_ACTIVITIES = _SETTINGS["defaults"]["activities"]


def normalize_config(config):
    """Populate the mode-independent equipment and activity defaults."""
    if not isinstance(config, dict):
        return config

    cfg = config.copy()
    if not cfg.get("disassemble_colors"):
        cfg["disassemble_colors"] = list(DEFAULT_DISASSEMBLE_COLORS)
    if not cfg.get("keep_colors"):
        cfg["keep_colors"] = list(DEFAULT_KEEP_COLORS)

    mode_type = cfg.get("type")
    for activity_key, default_value in DEFAULT_ACTIVITIES.items():
        if activity_key in cfg:
            continue
        if activity_key == "enable_stage_farming":
            cfg[activity_key] = mode_type in ["stage", "mix", "daily"]
        elif activity_key == "enable_dungeon":
            cfg[activity_key] = False if mode_type in ["stage", "collect_only"] else default_value
        elif activity_key == "enable_lord_boss":
            cfg[activity_key] = False if mode_type == "collect_only" else default_value
        elif activity_key == "enable_town_daily":
            cfg[activity_key] = False if mode_type == "collect_only" else default_value
        elif activity_key == "enable_quests":
            cfg[activity_key] = mode_type == "daily"
        else:
            cfg[activity_key] = default_value
    return cfg


RAW_GAME_CONFIGS = {**PRIMARY_MODES, **SUBFLOW_CONFIGS}
GAME_CONFIGS = {key: normalize_config(value) for key, value in RAW_GAME_CONFIGS.items()}
STAGE_CONFIGS = {
    key: normalize_config(value)
    for key, value in get_stage_configs(BASE_STAGE_LEVELS).items()
}


_EXCEPTION_CONFIG_MANAGER = None


def get_exception_features_config():
    """Return the latest valid exception-feature configuration snapshot."""
    global _EXCEPTION_CONFIG_MANAGER
    default_config = {
        "critical_templates": ["exceptions/Raid_Box.png"],
        "auto_discover_exceptions_dir": "templates/exceptions",
        "mismatch_scan_interval_sec": 30.0,
        "non_battle_stuck_timeout_sec": 30.0,
        "battle_stuck_timeout_sec": 90.0,
    }
    if _EXCEPTION_CONFIG_MANAGER is None:
        _EXCEPTION_CONFIG_MANAGER = JsonConfigManager(
            CONFIG_DIR / "exception_features.json", default=default_config
        )

    was_reloaded = _EXCEPTION_CONFIG_MANAGER.reload_if_changed()
    if was_reloaded:
        logging.info("🔄 [HotReload] 已動態套用 config/exception_features.json")
    elif _EXCEPTION_CONFIG_MANAGER.last_error is not None:
        logging.warning(
            "⚠️ [HotReload] exception_features.json 無法套用，保留上一份有效設定：%s",
            _EXCEPTION_CONFIG_MANAGER.last_error,
        )
    return _EXCEPTION_CONFIG_MANAGER.snapshot()


def get_critical_exception_templates():
    """Return configured and auto-discovered critical exception templates."""
    config = get_exception_features_config()
    templates = set(config.get("critical_templates", []))
    for feature in config.get("subflow_feature_mapping", {}).values():
        if isinstance(feature, dict) and "trigger_template" in feature:
            templates.add(feature["trigger_template"])

    exceptions_dir = config.get("auto_discover_exceptions_dir", "templates/exceptions")
    resolved_dir = Path(exceptions_dir)
    if resolved_dir.is_dir():
        templates.update(
            f"exceptions/{path.name}"
            for path in resolved_dir.iterdir()
            if path.suffix.lower() in {".png", ".jpg", ".jpeg"}
        )
    return list(templates)


def get_subflow_feature_mapping():
    return get_exception_features_config().get("subflow_feature_mapping", {})
