"""Interactive Daily Tier 4 route selection."""

from config import (
    DEFAULT_TIER4_DOMAIN,
    TIER4_DOMAIN_OPTIONS,
    TIER4_MODE_DOMAIN,
    TIER4_MODE_OPTIONS,
    TIER4_MODE_STAGE,
)
from cli.profile_updates import persist_mode_updates
from cli.prompts import prompt_choice
from cli.stage_setup import setup_stage_config


def _select_from_options(title, options, current_key, interactive):
    keys = [key for key, _label in options]
    default_number = str(keys.index(current_key) + 1) if current_key in keys else "1"
    print(f"\n{title}")
    for number, (key, label) in enumerate(options, start=1):
        marker = " - 當前預設" if key == current_key else ""
        print(f" {number}) {label}{marker}")
    if not interactive:
        return keys[int(default_number) - 1]
    choice = prompt_choice(
        f"請輸入數字 [1-{len(options)}] (直接 Enter 保留 {default_number}): ",
        default_number,
    )
    if choice not in {str(index) for index in range(1, len(options) + 1)}:
        print(f"[!] 無效選擇 '{choice}'，已保留目前設定。")
        choice = default_number
    return keys[int(choice) - 1]


def setup_daily_tier4_config(config, interactive=True):
    """Select and persist the continuous activity used after Daily work."""
    original = {
        "tier4_mode": config.get("tier4_mode", TIER4_MODE_STAGE),
        "tier4_domain": config.get("tier4_domain", DEFAULT_TIER4_DOMAIN),
        "enable_stage_farming": config.get("enable_stage_farming", True),
    }
    current_mode = config.get("tier4_mode", TIER4_MODE_STAGE)
    tier4_mode = _select_from_options(
        "請選擇 Tier 4 長駐打法：", TIER4_MODE_OPTIONS, current_mode, interactive
    )
    updates = {"tier4_mode": tier4_mode}
    config["tier4_mode"] = tier4_mode

    if tier4_mode == TIER4_MODE_STAGE:
        config["enable_stage_farming"] = True
        updates["enable_stage_farming"] = True
        _persist_changed(config, original, updates)
        setup_stage_config(
            config, prompt_prefix="[Tier 4 長駐關卡] ", interactive=interactive
        )
        config["name"] = f"每日懸賞任務 (Tier 4: {config.get('stage_name', '')})"
        return config

    current_domain = config.get("tier4_domain", DEFAULT_TIER4_DOMAIN)
    domain_key = _select_from_options(
        "請選擇要探索的領地：",
        TIER4_DOMAIN_OPTIONS,
        current_domain,
        interactive,
    )
    config["tier4_domain"] = domain_key
    config["enable_stage_farming"] = False
    updates.update({"tier4_domain": domain_key, "enable_stage_farming": False})
    _persist_changed(config, original, updates)
    domain_label = dict(TIER4_DOMAIN_OPTIONS)[domain_key]
    config["name"] = f"每日懸賞任務 (Tier 4: {domain_label})"
    return config


def _persist_changed(config, original, updates):
    if any(original.get(key) != value for key, value in updates.items()):
        persist_mode_updates(config, updates)
