"""Pure assembly of Daily Tier 4 route configurations."""

from copy import deepcopy

from config import (
    DEFAULT_TIER4_DOMAIN,
    TIER4_MODE_DOMAIN,
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
    tier4_mode = fallback.get("tier4_mode", TIER4_MODE_STAGE)
    if tier4_mode != TIER4_MODE_DOMAIN:
        fallback["tier4_mode"] = TIER4_MODE_STAGE
        fallback["enable_stage_farming"] = True
        fallback["enable_golden_empire"] = False
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
    return fallback
