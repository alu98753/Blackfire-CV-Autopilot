"""Notification Internationalization (i18n) Module.

Supports:
- "zh-TW" (Traditional Chinese, default)
- "en" (English)

Raises ValueError early upon invalid language codes (Fail-Fast at startup/config loading).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

SUPPORTED_LANGUAGES = ("zh-TW", "en")
DEFAULT_LANGUAGE = "zh-TW"

LANGUAGE_ALIASES: dict[str, str] = {
    "zh-tw": "zh-TW",
    "zh_tw": "zh-TW",
    "zh": "zh-TW",
    "en": "en",
    "en-us": "en",
    "en_us": "en",
}

SUBFLOW_NAMES: dict[str, dict[str, str]] = {
    "zh-TW": {
        "chest": "寶箱 (chest)",
        "hero_draw": "英雄召喚 (hero_draw)",
        "blood_altar": "血之祭壇 (blood_altar)",
        "jewelry_workshop": "珠寶工坊 (jewelry_workshop)",
        "bulletin_board": "懸賞告示牌 (bulletin_board)",
    },
    "en": {
        "chest": "Chest",
        "hero_draw": "Hero Draw",
        "blood_altar": "Blood Altar",
        "jewelry_workshop": "Jewelry Workshop",
        "bulletin_board": "Bulletin Board",
    },
}

MESSAGES: dict[str, dict[str, Any]] = {
    "zh-TW": {
        "footer_healthy": "黑火遠征 • 自動掛機運行正常",
        "footer_alarm": "黑火遠征 • 需要人工介入處理",
        "common_alarm_desc": "自動恢復機制已耗盡，需要手動介入處理。",
        "field_timestamp": "時間戳記",
        "field_profile": "角色檔案",
        "field_alarm_code": "警報代碼",
        "field_reason": "原因",
        "milestone1": {
            "title": "每日城鎮速領完成",
            "description": "所有城鎮每日速領子流程已推進完畢；告示牌懸賞任務已順利接取。",
            "field_quests_accepted": "已接取懸賞",
            "field_town_subflows": "城鎮子流程",
        },
        "milestone2": {
            "title": "每日懸賞全數清空",
            "description": "所有已接取的每日懸賞任務皆已完成。掛機程序切換至常規常駐退守模式。",
            "field_status": "狀態",
            "status_completed": "所有懸賞任務已完成",
            "field_next_target": "後續目標",
            "field_cleared_count": "完成任務數",
            "field_cleared_quests": "已核銷懸賞",
        },
        "deadline_alarm": {
            "title": "每日速領超時卡死警報",
            "reason_template": "每日 08:05 重置後超過 {minutes} 分鐘仍未完成城鎮速領階段。",
            "field_pending_subflows": "未完成子流程",
            "field_current_state": "當前狀態機狀態",
        },
        "supervisor_alarm": {
            "title": "Supervisor 崩潰循環超限警報",
            "reason_template": "Supervisor 在滑動觀察窗口 ({window_seconds}秒) 內重啟次數超過上限 ({max_restarts}次)。",
            "field_restarts": "窗口內重啟次數",
            "field_window_duration": "滑動窗口時長",
        },
    },
    "en": {
        "footer_healthy": "Blackfire Crusade • Automation Healthy",
        "footer_alarm": "Blackfire Crusade • Operator Action Required",
        "common_alarm_desc": "Automatic recovery exhausted. Manual intervention required.",
        "field_timestamp": "Timestamp",
        "field_profile": "Profile",
        "field_alarm_code": "Alarm Code",
        "field_reason": "Reason",
        "milestone1": {
            "title": "Daily Claim Phase Completed",
            "description": "All town daily claim subflows completed; bulletin board bounty quests accepted.",
            "field_quests_accepted": "Quests Accepted",
            "field_town_subflows": "Town Subflows",
        },
        "milestone2": {
            "title": "Bounty Quests Cleared",
            "description": "All accepted bounty quests completed. Bot transitioning to steady-state mode.",
            "field_status": "Status",
            "status_completed": "All accepted quests completed",
            "field_next_target": "Next Target",
            "field_cleared_count": "Cleared Quests Count",
            "field_cleared_quests": "Cleared Quests",
        },
        "deadline_alarm": {
            "title": "Daily Claim Deadline Exceeded",
            "reason_template": "Daily claim phase not completed within {minutes} minutes after 08:05 reset.",
            "field_pending_subflows": "Pending Subflows",
            "field_current_state": "Current State",
        },
        "supervisor_alarm": {
            "title": "Supervisor Crash Loop Exceeded",
            "reason_template": "Supervisor exceeded {max_restarts} restarts within sliding window ({window_seconds}s).",
            "field_restarts": "Restarts in Window",
            "field_window_duration": "Window Duration",
        },
    },
}


def normalize_language(lang: str | None) -> str:
    """Normalize and strictly validate language code.

    Raises:
        ValueError: If lang is invalid or unsupported (Fail-Fast at startup).
    """
    if lang is None:
        return DEFAULT_LANGUAGE
    if not isinstance(lang, str):
        raise ValueError(f"通知語言設定必須為字串，收到: {type(lang).__name__} ({lang!r})")

    clean = lang.strip().lower()
    if clean in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[clean]

    supported_list = ", ".join(f"'{s}'" for s in SUPPORTED_LANGUAGES)
    aliases_list = ", ".join(f"'{a}'" for a in LANGUAGE_ALIASES.keys())
    raise ValueError(
        f"不支援的通知語言設定: '{lang}'。目前支援的語言: [{supported_list}] (或別名: [{aliases_list}])"
    )


def format_subflow_status(subflow_key: str, completed: bool, language: str = DEFAULT_LANGUAGE) -> str:
    """Format single town subflow status with localized name."""
    lang = normalize_language(language)
    names = SUBFLOW_NAMES.get(lang, SUBFLOW_NAMES[DEFAULT_LANGUAGE])
    display_name = names.get(subflow_key, subflow_key)
    mark = "✓" if completed else "✗"
    return f"{display_name}({mark})"


def format_milestone1(
    profile: str,
    accepted_quests: list[str],
    subflow_statuses: list[str],
    language: str = DEFAULT_LANGUAGE,
    now_dt: datetime | None = None,
) -> tuple[str, str, dict[str, Any], str]:
    """Return (title, description, fields, footer_text) for Milestone 1."""
    lang = normalize_language(language)
    msg = MESSAGES[lang]
    m1 = msg["milestone1"]
    now_str = (now_dt or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

    fields = {
        msg["field_timestamp"]: now_str,
        msg["field_profile"]: profile,
        m1["field_quests_accepted"]: accepted_quests,
        m1["field_town_subflows"]: ", ".join(subflow_statuses),
    }
    return m1["title"], m1["description"], fields, msg["footer_healthy"]


def format_milestone2(
    profile: str,
    fallback_mode: str,
    language: str = DEFAULT_LANGUAGE,
    now_dt: datetime | None = None,
    cleared_count: int | None = None,
    cleared_quests: list[str] | None = None,
) -> tuple[str, str, dict[str, Any], str]:
    """Return (title, description, fields, footer_text) for Milestone 2."""
    lang = normalize_language(language)
    msg = MESSAGES[lang]
    m2 = msg["milestone2"]
    now_str = (now_dt or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

    fields: dict[str, Any] = {
        msg["field_timestamp"]: now_str,
        msg["field_profile"]: profile,
    }
    if cleared_count is not None:
        fields[m2["field_cleared_count"]] = str(cleared_count)
    if cleared_quests is not None:
        fields[m2["field_cleared_quests"]] = cleared_quests
    if cleared_count is None and cleared_quests is None:
        fields[m2["field_status"]] = m2["status_completed"]

    fields[m2["field_next_target"]] = fallback_mode
    return m2["title"], m2["description"], fields, msg["footer_healthy"]


def format_daily_claim_deadline_alarm(
    profile: str,
    deadline_minutes: int,
    pending_subflows: list[str],
    current_state: str,
    language: str = DEFAULT_LANGUAGE,
    now_dt: datetime | None = None,
) -> tuple[str, str, dict[str, Any], str, str]:
    """Return (title, reason, details, alarm_description, footer_text) for Daily Claim Deadline Alarm."""
    lang = normalize_language(language)
    msg = MESSAGES[lang]
    da = msg["deadline_alarm"]
    now_str = (now_dt or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    reason = da["reason_template"].format(minutes=deadline_minutes)

    details = {
        msg["field_timestamp"]: now_str,
        msg["field_profile"]: profile,
        da["field_pending_subflows"]: ", ".join(pending_subflows) or "None",
        da["field_current_state"]: current_state,
    }
    return da["title"], reason, details, msg["common_alarm_desc"], msg["footer_alarm"]


def format_supervisor_crash_alarm(
    profile: str,
    restarts: int,
    max_restarts: int,
    window_duration_str: str,
    window_seconds: float,
    language: str = DEFAULT_LANGUAGE,
    now_dt: datetime | None = None,
) -> tuple[str, str, dict[str, Any], str, str]:
    """Return (title, reason, details, alarm_description, footer_text) for Supervisor Crash Loop Alarm."""
    lang = normalize_language(language)
    msg = MESSAGES[lang]
    sa = msg["supervisor_alarm"]
    now_str = (now_dt or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    reason = sa["reason_template"].format(max_restarts=max_restarts, window_seconds=int(window_seconds))

    details = {
        msg["field_timestamp"]: now_str,
        msg["field_profile"]: profile,
        sa["field_restarts"]: f"{restarts} / {max_restarts}",
        sa["field_window_duration"]: window_duration_str,
    }
    return sa["title"], reason, details, msg["common_alarm_desc"], msg["footer_alarm"]
