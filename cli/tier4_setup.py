"""Interactive Daily Tier 4 route selection."""

from config import (
    TIER4_MODE_DOMAIN,
    TIER4_MODE_NONE,
    TIER4_MODE_OPTIONS,
    TIER4_MODE_STAGE,
    get_tier4_domain_options,
)
from cli.profile_updates import persist_mode_updates
from cli.prompts import prompt_choice
from cli.stage_setup import setup_stage_config


def _select_from_options(title, options, current_key, interactive):
    keys = [key for key, _label in options]
    has_valid_current = current_key in keys
    default_number = str(keys.index(current_key) + 1) if has_valid_current else None
    print(f"\n{title}")
    for number, (key, label) in enumerate(options, start=1):
        marker = " - 當前預設" if has_valid_current and key == current_key else ""
        print(f" {number}) {label}{marker}")
    if not interactive:
        if default_number is not None:
            return keys[int(default_number) - 1]
        raise ValueError(f"非互動模式下缺少必要選項: {title}")

    valid_indexes = {str(index) for index in range(1, len(options) + 1)}
    if default_number is not None:
        choice = prompt_choice(
            f"請輸入數字 [1-{len(options)}] (直接 Enter 保留 {default_number}): ",
            default_number,
        )
        if choice not in valid_indexes:
            print(f"[!] 無效選擇 '{choice}'，已保留目前設定。")
            choice = default_number
        return keys[int(choice) - 1]

    prompt_msg = f"請輸入數字 [1-{len(options)}]: "
    while True:
        try:
            raw = input(prompt_msg).strip()
        except (EOFError, KeyboardInterrupt):
            raise ValueError(f"未進行必要選擇，終止設定: {title}")
        if raw in valid_indexes:
            return keys[int(raw) - 1]
        print(f"[!] 無效選擇 '{raw}'，請明確輸入有效選項 [1-{len(options)}]。")


def setup_daily_tier4_config(config, interactive=True):
    """Select and persist the continuous activity used after Daily work."""
    original = {
        "tier4_mode": config.get("tier4_mode", TIER4_MODE_STAGE),
        "tier4_domain": config.get("tier4_domain"),
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

    if tier4_mode == TIER4_MODE_DOMAIN:
        if config.get("enable_domain") is False:
            raise ValueError("Daily policy 衝突：tier4_mode 設定為 'domain'，但 enable_domain 為 false。")
        domain_options = get_tier4_domain_options()
        if not domain_options:
            raise ValueError("配置錯誤：未在 primary_modes 中宣告任何合法領地！")
        valid_keys = [k for k, _ in domain_options]
        if not interactive:
            domain_key = config.get("tier4_domain")
            if not domain_key or not isinstance(domain_key, str) or not domain_key.strip():
                raise ValueError("配置錯誤：tier4_mode='domain' 時必須明確指定 'tier4_domain'，不可為空或依賴隱式預設值")
            if domain_key not in valid_keys:
                raise ValueError(
                    f"配置錯誤：tier4_domain [{domain_key}] 不存在於合法領地目錄中！可選領地: {valid_keys}"
                )
        else:
            current_domain = config.get("tier4_domain")
            current_key = current_domain if current_domain in valid_keys else None
            domain_key = _select_from_options(
                "請選擇要探索的領地：",
                domain_options,
                current_key,
                interactive,
            )
        config["tier4_domain"] = domain_key
        config["enable_stage_farming"] = False
        updates.update({"tier4_domain": domain_key, "enable_stage_farming": False})
        _persist_changed(config, original, updates)
        domain_label = dict(domain_options)[domain_key]
        config["name"] = f"每日懸賞任務 (Tier 4: {domain_label})"
        return config

    config["enable_stage_farming"] = False
    updates["enable_stage_farming"] = False
    _persist_changed(config, original, updates)
    config["name"] = "每日懸賞任務 (無 Tier 4 長駐 / 純定時待機)"
    return config


def _persist_changed(config, original, updates):
    if any(original.get(key) != value for key, value in updates.items()):
        persist_mode_updates(config, updates)
