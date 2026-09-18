"""Pure assembly of Daily Tier 4 route configurations."""

from copy import deepcopy

from config import (
    TIER4_MODE_DOMAIN,
    TIER4_MODE_NONE,
    TIER4_MODE_STAGE,
)


DAILY_SCHEDULING_CONTEXT_KEYS = (
    "enable_dungeon",
    "dungeon_names",
    "dungeon_entries",
    "cooldown_map",
    "greedy_dungeon",
    "greedy_allowed_indices",
    "auto_resume_dungeon_on_cd",
    "enable_town_daily",
    "enable_demon_lords",
    "keep_colors",
    "disassemble_colors",
    "subflow_configs",
)


def build_domain_execution_route(daily_policy: dict, selected_domain_config: dict) -> dict:
    """Assemble a Domain Tier 4 execution route with selected Domain config as the execution base.

    Contract & Architectural Invariants (Phase 2):
    1. Domain Execution SSOT: The execution route is rooted in deepcopy(selected_domain_config).
       All Domain execution-owned fields (navigation_path, tab buttons, lobby buttons,
       bread_cost, explore_priorities, result_buttons, domain_reset_max_attempts,
       and domain-specific enable_lord_boss) strictly derive from selected_domain_config.
       Daily execution-like fields CANNOT override Domain execution fields.
    2. Policy Separation: 'enable_domain' belongs strictly to Daily scheduler policy and
       is never injected into the Domain execution config.
    3. Daily Scheduling Context: Only minimal scheduling and player equipment attributes
       required while Daily is resident in Domain are attached.
    4. Runtime Tags: Sets tier4_mode='domain', tier4_domain, and is_tier4_fallback=True.
    """
    route = deepcopy(selected_domain_config)

    # 1. 嚴禁 enable_domain 存在於 Domain execution config (Section 5)
    route.pop("enable_domain", None)

    # 2. 附加 Daily 在領地長駐期間所需的必要排程上下文與 Tier4 運行標籤
    # 嚴格區分：tier4_domain 為 primary mode selection key，domain 為 strategy/domain identity，嚴禁互相 fallback
    mode_selection_key = daily_policy["tier4_domain"]
    domain_identity = selected_domain_config["domain"]
    domain_name = selected_domain_config.get("name", mode_selection_key)
    route["name"] = f"每日懸賞任務 (Tier 4 退守: {domain_name})"
    route["type"] = "domain"
    route["tier4_mode"] = TIER4_MODE_DOMAIN
    route["tier4_domain"] = mode_selection_key
    route["domain"] = domain_identity
    route["is_tier4_fallback"] = True
    route["enable_stage_farming"] = False

    # 3. 附加 minimal Daily scheduling policy context
    for key in DAILY_SCHEDULING_CONTEXT_KEYS:
        if key in daily_policy:
            route[key] = deepcopy(daily_policy[key])
    if "enable_dungeon" not in route:
        route["enable_dungeon"] = daily_policy.get("enable_dungeon", True)

    return route


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

    # Phase 2: Enforce Daily Domain policy invariants and assemble route from selected Domain base
    validate_daily_domain_policy(primary_config)

    domain_key = primary_config["tier4_domain"]
    if domain_key not in mode_configs or mode_configs[domain_key].get("type") != "domain":
        raise ValueError(f"無效的 Daily Tier 4 領地設定: tier4_domain={domain_key!r} 不存在於合法領地目錄中")

    raw_domain = mode_configs[domain_key]
    from config import normalize_domain_execution_config
    domain_config = normalize_domain_execution_config(raw_domain)
    return build_domain_execution_route(primary_config, domain_config)
