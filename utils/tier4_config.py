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
    "nemesis_action",
    "nemesis_templates",
    "navigation_path",
    "explore_priorities",
    "result_buttons",
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
        fallback["enable_golden_empire"] = False
        fallback["enable_dungeon"] = primary_config.get("enable_dungeon", True)
        fallback["name"] = "每日懸賞任務 (定時待機 collect_only)"
        return fallback

    if tier4_mode != TIER4_MODE_DOMAIN:
        stage_cfg = mode_configs.get("stage", {})
        fallback["type"] = "stage"
        fallback["tier4_mode"] = TIER4_MODE_STAGE
        fallback["enable_stage_farming"] = True
        fallback["enable_golden_empire"] = False
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

    domain_key = fallback.get("tier4_domain", DEFAULT_TIER4_DOMAIN)
    if domain_key not in mode_configs:
        domain_key = DEFAULT_TIER4_DOMAIN
    domain_config = mode_configs[domain_key]
    for key in DOMAIN_ROUTE_KEYS:
        if key in domain_config:
            fallback[key] = deepcopy(domain_config[key])

    fallback["name"] = f"每日懸賞任務 (Tier 4 退守: {domain_config['name']})"
    fallback["tier4_mode"] = TIER4_MODE_DOMAIN
    fallback["tier4_domain"] = domain_key
    fallback["enable_stage_farming"] = False
    fallback["enable_golden_empire"] = True
    fallback["enable_dungeon"] = primary_config.get("enable_dungeon", True)
    return fallback
