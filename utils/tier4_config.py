"""Pure assembly of Daily Tier 4 route configurations."""

from copy import deepcopy

from config import (
    DEFAULT_TIER4_DOMAIN,
    TIER4_MODE_DOMAIN,
    TIER4_MODE_NONE,
    TIER4_MODE_STAGE,
)


DOMAIN_ROUTE_KEYS = (
    "name",
    "type",
    "domain",
    "bread_cost",
    "enable_lord_boss",
    "nemesis_action",
    "nemesis_templates",
    "navigation_path",
    "explore_priorities",
    "result_buttons",
    "lobby_start_btn",
    "domain_tab_btn",
    "domain_tab_after_btn",
    "domain_entry_btn",
    "domain_reset_max_attempts",
)


def validate_daily_domain_policy(config: dict) -> None:
    """Validate Daily Tier 4 Domain policy invariants.

    Invariants:
    1. If tier4_mode == 'domain', enable_domain MUST be True (fail-fast if False).
    2. If tier4_mode == 'domain', tier4_domain MUST be explicitly present and non-empty.
    """
    if not isinstance(config, dict):
        return
    if config.get("tier4_mode") == TIER4_MODE_DOMAIN:
        if config.get("enable_domain") is False:
            raise ValueError(
                "Daily policy 衝突：tier4_mode 設定為 'domain'，但 enable_domain 為 false。"
            )
        domain_key = config.get("tier4_domain")
        if not domain_key or not isinstance(domain_key, str) or not domain_key.strip():
            raise ValueError(
                "Daily policy 錯誤：tier4_mode 設定為 'domain' 時，必須明確指定 'tier4_domain'，不可為空或依賴隱式預設值。"
            )


def build_tier4_fallback_config(primary_config: dict, mode_configs: dict) -> dict:
    """Resolve the player's Daily policy into one executable Tier 4 route."""
    fallback = deepcopy(primary_config)
    primary_type = primary_config.get("type")
    # 純地下城模式為獨立活動模式，退守時保持自身配置，不適用 Daily Tier 4 政策轉換
    if primary_type == "dungeon":
        return fallback

    tier4_mode = fallback.get("tier4_mode", TIER4_MODE_STAGE)
    if tier4_mode == TIER4_MODE_NONE:
        fallback["type"] = "collect_only"
        fallback["tier4_mode"] = TIER4_MODE_NONE
        fallback["enable_stage_farming"] = False
        fallback["enable_dungeon"] = primary_config.get("enable_dungeon", True)
        fallback["name"] = "每日懸賞任務 (定時待機 collect_only)"
        return fallback

    if tier4_mode != TIER4_MODE_DOMAIN:
        stage_cfg = mode_configs.get("stage", {})
        fallback["type"] = "stage"
        fallback["tier4_mode"] = TIER4_MODE_STAGE
        fallback["enable_stage_farming"] = True
        fallback["enable_dungeon"] = primary_config.get("enable_dungeon", True)
        fallback["greedy_dungeon"] = False

        # Invariant: type == stage 時，navigation_path 必須為 canonical stage 路由，嚴禁殘留地下城路徑
        canonical_stage_nav = (
            primary_config.get("stage_navigation_path")
            or stage_cfg.get("stage_navigation_path")
            or stage_cfg.get("navigation_path")
        )
        if canonical_stage_nav:
            fallback["navigation_path"] = deepcopy(canonical_stage_nav)

        if "stage_templates" not in fallback and "stage_templates" in stage_cfg:
            fallback["stage_templates"] = deepcopy(stage_cfg["stage_templates"])
        for key in ("stage_name", "stage_entry", "stage_target"):
            if key in stage_cfg and key not in fallback:
                fallback[key] = deepcopy(stage_cfg[key])
        return fallback

    # Phase 1: Enforce Daily Domain policy invariants (fail-fast on contradiction or missing tier4_domain)
    validate_daily_domain_policy(fallback)

    domain_key = fallback["tier4_domain"]
    if domain_key not in mode_configs or mode_configs[domain_key].get("type") != "domain":
        raise ValueError(f"無效的 Daily Tier 4 領地設定: tier4_domain={domain_key!r} 不存在於合法領地目錄中")
    domain_config = mode_configs[domain_key]
    for key in DOMAIN_ROUTE_KEYS:
        if key in domain_config:
            fallback[key] = deepcopy(domain_config[key])

    fallback["name"] = f"每日懸賞任務 (Tier 4 退守: {domain_config['name']})"
    fallback["tier4_mode"] = TIER4_MODE_DOMAIN
    fallback["tier4_domain"] = domain_key
    fallback["enable_domain"] = True
    fallback["enable_stage_farming"] = False
    fallback["enable_dungeon"] = primary_config.get("enable_dungeon", True)
    return fallback
