"""Small, atomic liveness signal consumed by the external supervisor."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HEARTBEAT_PATH = PROJECT_ROOT / "scratch" / "runtime" / "heartbeat.json"
HEARTBEAT_INTERVAL_SECONDS = 10.0
_last_write_times: dict[Path, float] = {}
_heartbeat_lock = threading.Lock()


def heartbeat_path_for_profile(profile: str) -> Path:
    """Return an isolated heartbeat path for a profile-safe name."""
    normalized = re.sub(r"[^a-z0-9_-]", "_", str(profile).strip().lower()) or "native"
    return DEFAULT_HEARTBEAT_PATH.with_name(f"heartbeat_{normalized}.json")


def touch_heartbeat(machine: Any = None, path: Path | None = None, force: bool = False) -> None:
    machine_path = getattr(machine, "heartbeat_path", None)
    if not isinstance(machine_path, (str, Path)):
        machine_path = None
    path = path or machine_path or DEFAULT_HEARTBEAT_PATH
    path = Path(path)
    now = time.time()

    with _heartbeat_lock:
        if not force and now - _last_write_times.get(path, 0.0) < HEARTBEAT_INTERVAL_SECONDS:
            return

        state = getattr(machine, "current_state", None)
        run_count = getattr(machine, "run_count", None)
        target = getattr(machine, "restart_target", None)
        profile = getattr(machine, "restart_profile", None)
        is_paused = bool(getattr(machine, "is_paused", False))
        payload = {
            "timestamp": now,
            "pid": os.getpid(),
            "state": state if isinstance(state, (str, int, float, bool)) else None,
            "is_paused": is_paused,
            "run_count": run_count if isinstance(run_count, (str, int, float, bool)) else None,
            "target": target if isinstance(target, str) else None,
            "profile": profile if isinstance(profile, str) else None,
        }
        temporary = path.with_name(f"{path.stem}_{os.getpid()}_{threading.get_ident()}_{time.time_ns()}.tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary, path)
            _last_write_times[path] = now
        except (OSError, TypeError):
            # The bot must remain functional even if the diagnostic drive is unavailable.
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            return

