"""Compatibility exports backed by the declarative config/defaults.toml file."""

from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path

from utils.config_helper import get_stage_configs
from utils.config_manager import JsonConfigManager, TomlConfigManager


WINDOW_TITLE = "Blackfire Crusade"
STEAM_APP_ID = "1765770"
CONFIG_DIR = Path(__file__).with_name("config")
USER_DATA_DIR = Path(__file__).with_name("user_data")
DEFAULTS_PATH = CONFIG_DIR / "defaults.toml"
LOCAL_CONFIG_PATH = CONFIG_DIR / "local.toml"
_DEFAULTS_MANAGER = TomlConfigManager(DEFAULTS_PATH)
_ACTIVE_PROFILE: str = "native"
_PROFILE_MANAGER = None


def get_active_profile() -> str:
    """Return currently active profile name (e.g. 'native', 'sandbox')."""
    return _ACTIVE_PROFILE


def get_profile_config_path(profile: str | None = None) -> Path:
    """Return the profile-specific config override path (user_data/<profile>/config.toml)."""
    p = (profile or _ACTIVE_PROFILE).strip().lower()
    return USER_DATA_DIR / p / "config.toml"


def get_defaults_config() -> dict:
    """Return defaults merged with the optional profile/local runtime override file."""
    return _deep_merge(_DEFAULTS_MANAGER.snapshot(), _get_override_config())


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge tables recursively; lists and scalar values replace whole values."""
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _get_override_config() -> dict:
    """Load user_data/<profile>/config.toml (or fallback config/local.toml) transactionally when it exists."""
    global _PROFILE_MANAGER
    profile_path = get_profile_config_path()
    target_path = profile_path if profile_path.exists() else LOCAL_CONFIG_PATH
    if not target_path.exists():
        _PROFILE_MANAGER = None
        return {}
    if _PROFILE_MANAGER is None or _PROFILE_MANAGER.path != target_path:
        _PROFILE_MANAGER = TomlConfigManager(target_path, default={})
    return _PROFILE_MANAGER.snapshot()


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

VISION_SETTINGS = _SETTINGS.get("vision", {})
DEFAULT_THRESHOLD = VISION_SETTINGS.get("default_threshold", 0.80)
SUB_STAGE_THRESHOLD = VISION_SETTINGS.get("sub_stage_threshold", 0.93)
EXIT_BATTLE_THRESHOLD = VISION_SETTINGS.get("exit_battle_threshold", 0.88)
ENTRY_THRESHOLD = VISION_SETTINGS.get("entry_threshold", 0.60)
TEMPLATE_THRESHOLDS = dict(VISION_SETTINGS.get("template_thresholds", {}))


def get_template_threshold(template_name: str, default: float | None = None) -> float:
    """Return specific template threshold from TOML if defined, else default or SUB_STAGE_THRESHOLD for sub-stages."""
    if template_name in TEMPLATE_THRESHOLDS:
        return float(TEMPLATE_THRESHOLDS[template_name])
    if default is not None:
        return float(default)
    is_sub_stage = any(k in template_name for k in ["final", "first", "middle", "six"])
    if is_sub_stage:
        return float(SUB_STAGE_THRESHOLD)
    return float(DEFAULT_THRESHOLD)


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
            cfg[activity_key] = False if mode_type in ["stage", "collect_only", "domain"] else default_value
        elif activity_key == "enable_lord_boss":
            cfg[activity_key] = False if mode_type in ["collect_only", "domain"] else default_value
        elif activity_key == "enable_town_daily":
            cfg[activity_key] = False if mode_type == "collect_only" else default_value
        elif activity_key == "enable_quests":
            cfg[activity_key] = mode_type == "daily"
        elif activity_key == "enable_golden_empire":
            cfg[activity_key] = (mode_type == "domain" and cfg.get("domain") == "golden_empire")
        else:
            cfg[activity_key] = default_value
    return cfg


RAW_GAME_CONFIGS = {**PRIMARY_MODES, **SUBFLOW_CONFIGS}
GAME_CONFIGS = {key: normalize_config(value) for key, value in RAW_GAME_CONFIGS.items()}
STAGE_CONFIGS = {
    key: normalize_config(value)
    for key, value in get_stage_configs(BASE_STAGE_LEVELS).items()
}


def _replace_mapping(target: dict, source: dict) -> None:
    """Update exports in place so existing imports keep seeing new settings."""
    target.clear()
    target.update(source)


def _reapply_all_settings(settings: dict) -> None:
    """Update all global config exports in place with the latest settings dictionary."""
    global _SETTINGS, VISION_SETTINGS, DEFAULT_THRESHOLD, SUB_STAGE_THRESHOLD, EXIT_BATTLE_THRESHOLD, ENTRY_THRESHOLD, TEMPLATE_THRESHOLDS
    _SETTINGS = settings
    _replace_mapping(GLOBAL_SETTINGS, settings["global"])
    _replace_mapping(PRIMARY_MODES, _restore_mode_key_types(settings["primary_modes"]))
    _replace_mapping(SUBFLOW_CONFIGS, settings["subflow_configs"])
    _replace_mapping(BASE_STAGE_LEVELS, settings["base_stage_levels"])
    
    # Vision settings
    VISION_SETTINGS = settings.get("vision", {})
    DEFAULT_THRESHOLD = VISION_SETTINGS.get("default_threshold", 0.80)
    SUB_STAGE_THRESHOLD = VISION_SETTINGS.get("sub_stage_threshold", 0.93)
    EXIT_BATTLE_THRESHOLD = VISION_SETTINGS.get("exit_battle_threshold", 0.88)
    ENTRY_THRESHOLD = VISION_SETTINGS.get("entry_threshold", 0.60)
    _replace_mapping(TEMPLATE_THRESHOLDS, VISION_SETTINGS.get("template_thresholds", {}))

    raw_configs = {**PRIMARY_MODES, **SUBFLOW_CONFIGS}
    _replace_mapping(GAME_CONFIGS, {key: normalize_config(value) for key, value in raw_configs.items()})
    _replace_mapping(STAGE_CONFIGS, {
        key: normalize_config(value)
        for key, value in get_stage_configs(BASE_STAGE_LEVELS).items()
    })


def set_active_profile(profile: str) -> None:
    """
    切換當前生效的角色 Profile (如 'native', 'sandbox', 'acc2')。
    自動重新計算 defaults.toml 與 user_data/<profile>/config.toml 的階層覆蓋，並即時更新全域設定導出。
    """
    global _ACTIVE_PROFILE, _PROFILE_MANAGER
    _ACTIVE_PROFILE = profile.strip().lower()
    _PROFILE_MANAGER = None
    settings = get_defaults_config()
    if settings.get("config_version") == 1:
        _reapply_all_settings(settings)
        profile_path = get_profile_config_path(_ACTIVE_PROFILE)
        if profile_path.exists():
            logging.info(f"⚙️ [ProfileConfig] 成功套用角色專屬覆蓋配置: user_data/{_ACTIVE_PROFILE}/config.toml")


def refresh_runtime_config() -> bool:
    """Publish TOML changes only when a full valid snapshot is available."""
    global _SETTINGS, _PROFILE_MANAGER
    defaults_changed = _DEFAULTS_MANAGER.reload_if_changed()
    override_changed = False
    
    profile_path = get_profile_config_path()
    target_path = profile_path if profile_path.exists() else LOCAL_CONFIG_PATH
    
    if target_path.exists():
        if _PROFILE_MANAGER is None or _PROFILE_MANAGER.path != target_path:
            _get_override_config()
            override_changed = True
        else:
            override_changed = _PROFILE_MANAGER.reload_if_changed()
    elif _PROFILE_MANAGER is not None:
        _PROFILE_MANAGER = None
        override_changed = True
        
    if not (defaults_changed or override_changed):
        return False

    settings = get_defaults_config()
    if settings.get("config_version") != 1:
        logging.error("[HotReload] ignored unsupported TOML config_version")
        return False
    _reapply_all_settings(settings)
    target_desc = f"user_data/{_ACTIVE_PROFILE}/config.toml" if target_path == profile_path else "config/local.toml"
    logging.info(f"[HotReload] applied config/defaults.toml and {target_desc}")
    return True


def get_runtime_game_config(key: str) -> dict:
    """Return a copy of the newest complete configuration for one mode."""
    refresh_runtime_config()
    return deepcopy(GAME_CONFIGS[key])


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
