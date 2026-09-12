"""Compatibility exports backed by the declarative config/defaults.toml file."""
from __future__ import annotations

from typing import Tuple

import logging
from copy import deepcopy
from pathlib import Path

from utils.config_helper import get_stage_configs
from utils.config_manager import JsonConfigManager, TomlConfigManager, dump_toml_dict


WINDOW_TITLE = "Blackfire Crusade"
STEAM_APP_ID = "1765770"

# 基準設計解析度 (1080p SSOT) 與等比縮放工具函式
BASE_RESOLUTION_WIDTH: float = 1920.0
BASE_RESOLUTION_HEIGHT: float = 1080.0
BASE_RESOLUTION: Tuple[int, int] = (1920, 1080)


def compute_screen_scale(
    screen_or_width=None,
    base_width: float = BASE_RESOLUTION_WIDTH,
    min_scale: float = 0.1,
) -> float:
    """計算畫面寬度相對於設計基準寬度的自適應縮放比例。

    支援傳入影像物件 (具備 .shape 的 ndarray)、數值 (int/float) 或 None。
    若數值非正或物件異常，安全回傳 1.0；下限保護為 min_scale。
    """
    if screen_or_width is None:
        return 1.0
    if isinstance(screen_or_width, (int, float)):
        return max(min_scale, float(screen_or_width) / base_width) if screen_or_width > 0 else 1.0
    if hasattr(screen_or_width, "shape") and len(screen_or_width.shape) >= 2:
        try:
            w = screen_or_width.shape[1]
            return max(min_scale, float(w) / base_width) if w > 0 else 1.0
        except Exception:
            return 1.0
    return 1.0


def compute_screen_scale_y(
    screen_or_height=None,
    base_height: float = BASE_RESOLUTION_HEIGHT,
    min_scale: float = 0.1,
) -> float:
    """計算畫面高度相對於設計基準高度的自適應縮放比例。

    支援傳入影像物件 (具備 .shape 的 ndarray)、數值 (int/float) 或 None。
    若數值非正或物件異常，安全回傳 1.0；下限保護為 min_scale。
    """
    if screen_or_height is None:
        return 1.0
    if isinstance(screen_or_height, (int, float)):
        return max(min_scale, float(screen_or_height) / base_height) if screen_or_height > 0 else 1.0
    if hasattr(screen_or_height, "shape") and len(screen_or_height.shape) >= 2:
        try:
            h = screen_or_height.shape[0]
            return max(min_scale, float(h) / base_height) if h > 0 else 1.0
        except Exception:
            return 1.0
    return 1.0

TIER4_MODE_STAGE = "stage"
TIER4_MODE_DOMAIN = "domain"
TIER4_MODE_NONE = "none"
DEFAULT_TIER4_DOMAIN = "golden_empire"
TIER4_MODE_OPTIONS = (
    (TIER4_MODE_STAGE, "普通關卡 (Stage)"),
    (TIER4_MODE_DOMAIN, "領地探索 (Domain)"),
    (TIER4_MODE_NONE, "停用 (全冷卻時collect only)"),
)
TIER4_DOMAIN_OPTIONS = (
    (DEFAULT_TIER4_DOMAIN, "黃金古國"),
)
TOWN_ANCHOR_BRIGHTNESS_THRESHOLD = 0.35
TOWN_BUILDING_BRIGHTNESS_THRESHOLD = 0.35

# Supervisor 外部監控看門狗預設常數 (SSOT: config/defaults.toml [supervisor])
DEFAULT_SUPERVISOR_WATCHDOG_TIMEOUT: float = 90.0
DEFAULT_SUPERVISOR_RELAUNCH_BUFFER_SECONDS: float = 30.0
DEFAULT_SUPERVISOR_MAX_RESTARTS: int = 5

CONFIG_DIR = Path(__file__).with_name("config")
USER_DATA_DIR = Path(__file__).with_name("user_data")
DEFAULTS_PATH = CONFIG_DIR / "defaults.toml"
LOCAL_CONFIG_PATH = CONFIG_DIR / "local.toml"
_ACTIVE_PROFILE: str = "native"
_PROFILE_MANAGER = None

_REQUIRED_DEFAULT_SETTING_PATHS = (
    ("global",),
    ("navigation", "action_timeout_seconds"),
    ("navigation", "action_max_attempts"),
    ("navigation", "collection_backoff_seconds"),
    ("navigation", "collection_recovery_failure_limit"),
    ("navigation", "town_entry_wait_max_observations"),
    ("navigation", "town_no_red_dot_confirm_frames"),
    ("navigation", "stamina_retreat_quit_max_attempts"),
    ("quest", "max_run_limit"),
    ("quest", "target_count"),
    ("quest", "stage_batch_size"),
    ("quest", "dungeon_batch_size"),
    ("bounty_quests", "max_stage"),
    ("bounty_quests", "max_dungeon"),
    ("catalog", "dungeon_names"),
    ("catalog", "dungeon_entry_templates"),
    ("catalog", "stage_templates"),
    ("ocr", "task_banner"),
    ("ocr", "bulletin_board"),
    ("ocr", "merchant_gold"),
    ("defaults", "disassemble_colors"),
    ("defaults", "keep_colors"),
    ("defaults", "activities"),
    ("primary_modes",),
    ("subflow_configs",),
    ("backpack_full", "destroy_goods"),
    ("base_stage_levels",),
    ("supervisor", "watchdog_timeout"),
    ("supervisor", "relaunch_buffer_seconds"),
    ("supervisor", "max_restarts"),
)


def _validate_defaults_snapshot(settings: dict) -> None:
    """Reject syntactically valid but incomplete defaults during an editor save."""
    if settings.get("config_version") != 1:
        raise ValueError("不支援的 config/defaults.toml config_version")

    for path in _REQUIRED_DEFAULT_SETTING_PATHS:
        value = settings
        for key in path:
            if not isinstance(value, dict) or key not in value:
                dotted_path = ".".join(path)
                raise ValueError(f"config/defaults.toml 缺少必要設定: {dotted_path}")
            value = value[key]


_DEFAULTS_MANAGER = TomlConfigManager(
    DEFAULTS_PATH,
    validator=_validate_defaults_snapshot,
)


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
    return _normalize_legacy_override(_PROFILE_MANAGER.snapshot())


def _normalize_legacy_override(override: dict) -> dict:
    """Map the former jewelry goods_settings key before merging with defaults."""
    normalized = deepcopy(override)
    subflows = normalized.get("subflow_configs")
    if not isinstance(subflows, dict):
        return normalized

    workshop = subflows.get("jewelry_workshop")
    if not isinstance(workshop, dict):
        return normalized

    if "sell_goods" not in workshop and "goods_settings" in workshop:
        workshop["sell_goods"] = workshop.pop("goods_settings")
    return normalized


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
BATTLE_MAX_DEFEAT = GLOBAL_SETTINGS.get("battle_max_defeat", 20)
DEFAULT_BAG_MAINTENANCE_ORDER = list(
    GLOBAL_SETTINGS.get("default_bag_maintenance_order", ["blood_sacrifice", "bag_tidy", "jewelry_workshop"])
)


def get_default_bag_maintenance_order() -> list[str]:
    """取得背包維護流水線的預設子流程順序 (重複使用 default_bag_maintenance_order 設定)"""
    return list(GLOBAL_SETTINGS.get("default_bag_maintenance_order", DEFAULT_BAG_MAINTENANCE_ORDER))


QUEST_MAX_RUN_LIMIT = _SETTINGS["quest"]["max_run_limit"]
QUEST_TARGET_COUNT = _SETTINGS["quest"]["target_count"]
QUEST_STAGE_BATCH_SIZE = _SETTINGS["quest"]["stage_batch_size"]
QUEST_DUNGEON_BATCH_SIZE = _SETTINGS["quest"]["dungeon_batch_size"]
BOUNTY_QUESTS_CONFIG = dict(_SETTINGS["bounty_quests"])

DUNGEON_NAMES = _SETTINGS["catalog"]["dungeon_names"]
DUNGEON_ENTRY_TEMPLATES = _SETTINGS["catalog"]["dungeon_entry_templates"]
STAGE_TEMPLATES = _SETTINGS["catalog"]["stage_templates"]


def get_all_dungeon_indices() -> list[int]:
    """Return dynamic list of 1-based dungeon indices derived from defaults TOML catalog."""
    from utils.dungeon_catalog import DungeonCatalog
    return DungeonCatalog.get_all_indices(DUNGEON_NAMES)


TASK_BANNER_OCR_OFFSET = _SETTINGS["ocr"]["task_banner"]
BULLETIN_BOARD_OCR_OFFSET = _SETTINGS["ocr"]["bulletin_board"]
MERCHANT_GOLD_OCR_ROI = _SETTINGS["ocr"]["merchant_gold"]

PRIMARY_MODES = _restore_mode_key_types(_SETTINGS["primary_modes"])
SUBFLOW_CONFIGS = _SETTINGS["subflow_configs"]
BACKPACK_FULL_SETTINGS = _SETTINGS["backpack_full"]
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
    is_sub_stage = any(k in template_name for k in ["final", "first", "middle", "six", "boss_skull", "skull"])
    if is_sub_stage:
        return float(SUB_STAGE_THRESHOLD)
    return float(DEFAULT_THRESHOLD)


def get_monitor_index() -> int:
    """Return configured target monitor index (1-indexed) from global settings."""
    return int(GLOBAL_SETTINGS.get("monitor_index", 1))


def get_battle_max_duration_seconds() -> float:
    """Return the TOML-configured hard cap for one continuous battle."""
    return float(GLOBAL_SETTINGS.get("battle_max_duration_sec", 900.0))


def get_battle_stall_settings() -> dict:
    """Return TOML-configured battle stall detection limits, retry count, and ROI ratios."""
    return {
        "timeout_seconds": float(GLOBAL_SETTINGS.get("battle_stall_timeout_sec", 30.0)),
        "max_retries": int(GLOBAL_SETTINGS.get("battle_stall_max_retries", 2)),
        "roi_top_ratio": float(GLOBAL_SETTINGS.get("battle_hp_roi_top_ratio", 0.64)),
        "roi_bottom_ratio": float(GLOBAL_SETTINGS.get("battle_hp_roi_bottom_ratio", 0.69)),
    }


def get_log_level() -> str:
    """Return the active profile's configured log level, falling back to global TOML defaults."""
    level = GLOBAL_SETTINGS.get("log_level", "INFO")
    if isinstance(level, str) and level.strip():
        return level.strip().upper()
    return "INFO"


def apply_log_level(level_name: str | None = None) -> str:
    """Apply the specified (or profile configured) log level to the root logger and its handlers."""
    target_level_str = (level_name or get_log_level()).strip().upper()
    numeric_level = getattr(logging, target_level_str, logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    for handler in root_logger.handlers:
        handler.setLevel(numeric_level)
    return target_level_str


def get_log_retention_days() -> int:
    """Return configured daily log retention days from profile or global settings."""
    try:
        return int(GLOBAL_SETTINGS.get("log_retention_days", 7))
    except (ValueError, TypeError):
        return 7


def get_navigation_progress_settings() -> dict:
    """Return required TOML-only action timeout and collection backoff settings."""
    settings = get_defaults_config()["navigation"]
    return {
        "action_timeout_seconds": float(settings["action_timeout_seconds"]),
        "action_max_attempts": int(settings["action_max_attempts"]),
        "collection_backoff_seconds": float(
            settings["collection_backoff_seconds"]
        ),
        "collection_recovery_failure_limit": int(
            settings["collection_recovery_failure_limit"]
        ),
        "town_entry_wait_max_observations": int(
            settings["town_entry_wait_max_observations"]
        ),
    }


def get_stamina_retreat_settings() -> dict:
    """Return TOML-only limits for the bounded stamina retreat recovery."""
    settings = get_defaults_config()["navigation"]
    return {
        "dismiss_max_attempts": int(settings["action_max_attempts"]),
        "quit_max_attempts": int(settings["stamina_retreat_quit_max_attempts"]),
        "return_town_max_attempts": int(settings["action_max_attempts"]),
    }


def get_bounty_quest_config(profile: str | None = None) -> dict:
    """Return [bounty_quests] settings for the active or specified profile."""
    base = dict(_DEFAULTS_MANAGER.snapshot().get("bounty_quests", {}))
    p = (profile or get_active_profile()).strip().lower()
    target_path = get_profile_config_path(p)
    if not target_path.exists():
        return base

    try:
        import tomllib
        with target_path.open("rb") as f:
            data = tomllib.load(f)
        override = data.get("bounty_quests")
        if isinstance(override, dict):
            base.update(override)
    except Exception as e:
        logging.warning("讀取 Profile [%s] bounty_quests 設定失敗: %s", p, e)

    return base


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
        elif activity_key == "lord_boss_targets":
            cfg[activity_key] = list(default_value)
        elif activity_key == "enable_town_daily":
            cfg[activity_key] = mode_type in ["daily", "mix"]
        elif activity_key == "enable_demon_lords":
            cfg[activity_key] = mode_type in ["daily", "mix"]
        elif activity_key == "enable_quests":
            cfg[activity_key] = mode_type == "daily"
        elif activity_key == "enable_golden_empire":
            cfg[activity_key] = (mode_type == "domain" and cfg.get("domain") == "golden_empire")
        else:
            cfg[activity_key] = default_value

    if cfg.get("greedy_dungeon", False):
        if cfg.get("greedy_allowed_indices") is None:
            from utils.dungeon_catalog import DungeonCatalog
            d_names = cfg.get("dungeon_names", DUNGEON_NAMES)
            cfg["greedy_allowed_indices"] = DungeonCatalog.get_all_indices(custom_names=d_names)

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
    global _SETTINGS, DEFAULT_DISASSEMBLE_COLORS, DEFAULT_KEEP_COLORS, DEFAULT_ACTIVITIES
    global VISION_SETTINGS, DEFAULT_THRESHOLD, SUB_STAGE_THRESHOLD, EXIT_BATTLE_THRESHOLD, ENTRY_THRESHOLD, TEMPLATE_THRESHOLDS
    _SETTINGS = settings
    _replace_mapping(GLOBAL_SETTINGS, settings["global"])
    _replace_mapping(PRIMARY_MODES, _restore_mode_key_types(settings["primary_modes"]))
    _replace_mapping(SUBFLOW_CONFIGS, settings["subflow_configs"])
    _replace_mapping(BACKPACK_FULL_SETTINGS, settings["backpack_full"])
    _replace_mapping(BASE_STAGE_LEVELS, settings["base_stage_levels"])
    _replace_mapping(BOUNTY_QUESTS_CONFIG, settings.get("bounty_quests", {}))
    DEFAULT_DISASSEMBLE_COLORS = settings["defaults"]["disassemble_colors"]
    DEFAULT_KEEP_COLORS = settings["defaults"]["keep_colors"]
    DEFAULT_ACTIVITIES = settings["defaults"]["activities"]
    
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


def get_supervisor_settings(profile: str | None = None) -> dict[str, float | int]:
    """Return supervisor watchdog and crash-loop settings from profile or global defaults TOML."""
    if profile:
        set_active_profile(profile)
    settings = get_defaults_config().get("supervisor", {})
    return {
        "watchdog_timeout": float(settings.get("watchdog_timeout", DEFAULT_SUPERVISOR_WATCHDOG_TIMEOUT)),
        "relaunch_buffer_seconds": float(settings.get("relaunch_buffer_seconds", DEFAULT_SUPERVISOR_RELAUNCH_BUFFER_SECONDS)),
        "max_restarts": int(settings.get("max_restarts", DEFAULT_SUPERVISOR_MAX_RESTARTS)),
    }


def update_profile_config(profile: str | None = None, updates: dict | None = None) -> Path:
    """
    將使用者在終端機選單中修改的設定，增量合併並寫入 user_data/<profile>/config.toml。
    更新後立即重新整理配置快照並完成熱加載。
    """
    p = (profile or _ACTIVE_PROFILE).strip().lower()
    target_path = get_profile_config_path(p)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    current_data: dict = {}
    if target_path.exists():
        try:
            import tomllib
            with target_path.open("rb") as f:
                current_data = tomllib.load(f)
        except Exception as e:
            logging.warning(f"讀取既有 Profile config 失敗 ({e})，將重新構建。")
            current_data = {}

    if updates:
        merged = _deep_merge(current_data, updates)
    else:
        merged = current_data

    toml_str = dump_toml_dict(merged)
    target_path.write_text(toml_str, encoding="utf-8")

    refresh_runtime_config()
    logging.info(f"💾 [ConfigSync] 已成功同步設定至 user_data/{p}/config.toml")
    return target_path


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
