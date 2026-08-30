"""Fail-safe, profile-isolated runtime incident records."""

from __future__ import annotations

import json
import logging
import os
import re
import time
import traceback
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from config import USER_DATA_DIR


CRASH = "CRASH"
HEARTBEAT_TIMEOUT = "HEARTBEAT_TIMEOUT"
SCHEDULED_MAINTENANCE = "SCHEDULED_MAINTENANCE"
IN_GAME_RECOVERY = "IN_GAME_RECOVERY"
VALID_CATEGORIES = {CRASH, HEARTBEAT_TIMEOUT, SCHEDULED_MAINTENANCE, IN_GAME_RECOVERY}
PROFILE_PATTERN = re.compile(r"[a-z0-9_-]+")
SENSITIVE_KEY_PATTERN = re.compile(r"token|password|passwd|secret|api[_-]?key|authorization|account", re.IGNORECASE)
SENSITIVE_VALUE_PATTERN = re.compile(r"(?i)\b(token|password|passwd|secret|api[ _-]?key|authorization)\b\\?['\"]?\s*([:=])\s*\\?['\"]?([^\\\s,;'\"}\]]+)")
BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[^\s,;]+")


def normalize_profile(profile: str | None) -> str:
    value = str(profile or "native").strip().lower()
    value = value or "native"
    if not PROFILE_PATTERN.fullmatch(value):
        raise ValueError("Profile names may contain only lowercase letters, digits, '_' and '-'.")
    return value


def runtime_data_dir(profile: str | None) -> Path:
    return Path(USER_DATA_DIR) / normalize_profile(profile) / "runtime"


def incident_path(profile: str | None, now: datetime | None = None) -> Path:
    now = now or datetime.now().astimezone()
    return runtime_data_dir(profile) / "incidents" / f"{now.date().isoformat()}.jsonl"


def handoff_path(profile: str | None) -> Path:
    return runtime_data_dir(profile) / "latest_child_termination.json"


def new_session_id() -> str:
    return str(uuid.uuid4())


def explicit_profile_from_command(command: Sequence[str]) -> str | None:
    """Return exactly one nonblank declared profile, otherwise ``None``."""
    values: list[str] = []
    for index, token in enumerate(command):
        if token == "--profile":
            if index + 1 >= len(command):
                return None
            values.append(str(command[index + 1]).strip())
    if len(values) != 1 or not values[0]:
        return None
    if values[0].startswith("--"):
        return None
    return normalize_profile(values[0])


def _redact(value: Any, key: str | None = None) -> Any:
    if key and SENSITIVE_KEY_PATTERN.search(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(item_key): _redact(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        redacted = SENSITIVE_VALUE_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", value)
        return BEARER_PATTERN.sub("Bearer [REDACTED]", redacted)
    return value


def _safe_scalar(value: Any) -> str | int | float | bool | None:
    return value if isinstance(value, (str, int, float, bool)) or value is None else str(value)


def _machine_context(machine: Any) -> dict[str, object]:
    return {
        "session_id": getattr(machine, "incident_session_id", None),
        "pid": os.getpid(),
        "state": _safe_scalar(getattr(machine, "current_state", None)),
        "run_count": _safe_scalar(getattr(machine, "run_count", 0)) or 0,
    }


def write_incident(
    profile: str | None,
    category: str,
    reason_code: str,
    *,
    session_id: str | None = None,
    pid: int | None = None,
    state: str | None = None,
    run_count: int | float | None = 0,
    details: Mapping[str, Any] | None = None,
) -> dict[str, object] | None:
    """Append one compact event. Diagnostic write failures are always non-fatal."""
    if category not in VALID_CATEGORIES:
        logging.warning("[IncidentJournal] Rejected unknown category: %s", category)
        return None
    try:
        now = datetime.now().astimezone()
        payload: dict[str, object] = {
            "schema_version": 1,
            "event_id": str(uuid.uuid4()),
            "occurred_at": now.isoformat(timespec="milliseconds"),
            "category": category,
            "reason_code": str(reason_code),
            "profile": normalize_profile(profile),
            "session_id": session_id,
            "pid": int(pid if pid is not None else os.getpid()),
            "state": _safe_scalar(state),
            "run_count": _safe_scalar(run_count) if run_count is not None else 0,
            "details": _redact(dict(details or {})),
        }
        encoded = (json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str) + "\n").encode("utf-8")
        path = incident_path(profile, now)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND)
        try:
            os.write(descriptor, encoded)
        finally:
            os.close(descriptor)
        return payload
    except Exception as exc:
        logging.warning("[IncidentJournal] Could not append incident: %s", exc)
        return None


def clear_child_termination(profile: str | None) -> bool:
    try:
        handoff_path(profile).unlink(missing_ok=True)
        return True
    except Exception as exc:
        logging.warning("[IncidentJournal] Could not clear child handoff: %s", exc)
        return False


def write_child_termination(profile: str | None, event: Mapping[str, Any]) -> bool:
    """Atomically publish a child termination event for its supervisor."""
    try:
        path = handoff_path(profile)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f"{path.stem}_{os.getpid()}_{time.time_ns()}.tmp")
        temporary.write_text(json.dumps(dict(event), ensure_ascii=False, default=str), encoding="utf-8")
        os.replace(temporary, path)
        return True
    except Exception as exc:
        logging.warning("[IncidentJournal] Could not publish child handoff: %s", exc)
        return False


def read_child_termination(profile: str | None, expected_pid: int | None = None) -> dict[str, object] | None:
    try:
        payload = json.loads(handoff_path(profile).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None
        if expected_pid is not None and payload.get("pid") != expected_pid:
            return None
        return payload
    except Exception:
        return None


def record_unhandled_exception(machine: Any, exc: BaseException) -> dict[str, object] | None:
    """Persist Python crash evidence before the caller re-raises it."""
    profile = getattr(machine, "restart_profile", None)
    context = _machine_context(machine)
    event = write_incident(
        profile,
        CRASH,
        "unhandled_python_exception",
        **context,
        details={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        },
    )
    if event is not None:
        write_child_termination(profile, event)
    return event


def record_recovery(machine: Any, reason_code: str, details: Mapping[str, Any] | None = None) -> dict[str, object] | None:
    profile = getattr(machine, "restart_profile", None)
    return write_incident(profile, IN_GAME_RECOVERY, reason_code, **_machine_context(machine), details=details)


def summarize_incidents(profile: str | None, top_limit: int = 10) -> dict[str, object]:
    """Return the spec's four-category summary plus top reason codes per category."""
    counts = {category: 0 for category in VALID_CATEGORIES}
    reasons = {category: Counter() for category in VALID_CATEGORIES}
    try:
        directory = runtime_data_dir(profile) / "incidents"
        for path in sorted(directory.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    logging.warning("[IncidentJournal] Skipping corrupt event in %s", path)
                    continue
                if not isinstance(payload, dict):
                    continue
                category = payload.get("category")
                reason_code = payload.get("reason_code")
                if category in VALID_CATEGORIES and isinstance(reason_code, str):
                    counts[category] += 1
                    reasons[category][reason_code] += 1
    except Exception as exc:
        logging.warning("[IncidentJournal] Could not summarize incidents: %s", exc)
    return {
        "profile": normalize_profile(profile),
        "category_counts": counts,
        "top_reasons": {
            category: [
                {"reason_code": reason_code, "count": count}
                for reason_code, count in counter.most_common(max(0, top_limit))
            ]
            for category, counter in reasons.items()
        },
    }
