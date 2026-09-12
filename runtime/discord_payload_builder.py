"""Builders for constructing structured Discord embed payloads."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping

from ports.notification_port import DISCORD_COLOR_ALARM, DISCORD_COLOR_MILESTONE


def build_milestone_payload(
    title: str,
    description: str,
    fields: Mapping[str, Any] | None = None,
    footer_text: str | None = None,
    language: str = "zh-TW",
) -> dict[str, Any]:
    """Construct a Discord Webhook JSON payload for milestone notifications."""
    from runtime.notification_i18n import MESSAGES
    msg = MESSAGES.get(language, MESSAGES["zh-TW"])

    embed_fields: list[dict[str, Any]] = []
    if fields:
        for k, v in fields.items():
            val_str = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
            embed_fields.append({"name": str(k), "value": val_str, "inline": False})

    return {
        "embeds": [
            {
                "title": f"✅ {title}",
                "description": description,
                "color": DISCORD_COLOR_MILESTONE,
                "fields": embed_fields,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "footer": {"text": footer_text or msg["footer_healthy"]},
            }
        ]
    }


def build_alarm_payload(
    code: str,
    title: str,
    reason: str,
    details: Mapping[str, Any] | None = None,
    description: str | None = None,
    footer_text: str | None = None,
    language: str = "zh-TW",
) -> dict[str, Any]:
    """Construct a Discord Webhook JSON payload for alarm notifications."""
    from runtime.notification_i18n import MESSAGES
    msg = MESSAGES.get(language, MESSAGES["zh-TW"])

    merged_details = dict(details or {})
    code_key = msg["field_alarm_code"]
    reason_key = msg["field_reason"]
    if code_key not in merged_details and "Alarm Code" not in merged_details:
        merged_details[code_key] = code
    if reason_key not in merged_details and "Reason" not in merged_details:
        merged_details[reason_key] = reason

    embed_fields: list[dict[str, Any]] = []
    for k, v in merged_details.items():
        val_str = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
        embed_fields.append({"name": str(k), "value": val_str, "inline": False})

    return {
        "embeds": [
            {
                "title": f"🚨 {title}",
                "description": description or msg["common_alarm_desc"],
                "color": DISCORD_COLOR_ALARM,
                "fields": embed_fields,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "footer": {"text": footer_text or msg["footer_alarm"]},
            }
        ]
    }
