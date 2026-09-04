"""Process-external watchdog for restarting an unresponsive bot process."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Sequence

from runtime.heartbeat import DEFAULT_HEARTBEAT_PATH
from runtime.incident_journal import (
    CRASH,
    HEARTBEAT_TIMEOUT,
    SCHEDULED_MAINTENANCE,
    explicit_profile_from_command,
    new_session_id,
    read_child_termination,
    write_incident,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
MANUAL_EXIT_CODE = 75
DEFAULT_DAILY_RESTART_HOUR = 8


def heartbeat_age_seconds(path: Path, now: float | None = None) -> float:
    now = time.time() if now is None else now
    try:
        return max(0.0, now - path.stat().st_mtime)
    except OSError:
        return float("inf")


def heartbeat_is_current(path: Path, started_at: float) -> bool:
    """True only when the heartbeat was written by the current child process."""
    try:
        return path.stat().st_mtime >= started_at
    except OSError:
        return False


def read_heartbeat(path: Path) -> dict[str, object]:
    """Read restart metadata without allowing a corrupt diagnostic file to stop recovery."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def heartbeat_incident_context(heartbeat: dict[str, object], child_pid: int | None, heartbeat_current: bool, session_id: str) -> dict[str, object]:
    """Use heartbeat context only when it belongs to this exact child launch."""
    if not heartbeat_current or heartbeat.get("pid") != child_pid or heartbeat.get("session_id") != session_id:
        return {"session_id": session_id, "state": None, "run_count": 0}
    return {
        "session_id": session_id,
        "state": heartbeat.get("state") if isinstance(heartbeat.get("state"), str) else None,
        "run_count": heartbeat.get("run_count") if isinstance(heartbeat.get("run_count"), (int, float)) else 0,
    }


def prepare_child_command(command: Sequence[str], session_id: str) -> list[str]:
    prepared: list[str] = []
    skip_next = False
    for token in command:
        if skip_next:
            skip_next = False
            continue
        if token == "--incident-session-id":
            skip_next = True
            continue
        prepared.append(token)
    return [*prepared, "--incident-session-id", session_id]


def prepare_resume_command(
    command: Sequence[str],
    heartbeat: dict[str, object],
    restart_game: bool = False,
) -> list[str]:
    """Preserve first-run CLI options and restore the selected instance on restart."""
    resumed = [tok for tok in command if tok != "--restart-game"]
    options = set(resumed)
    for option, field in (("--target", "target"), ("--profile", "profile")):
        value = heartbeat.get(field)
        if option not in options and isinstance(value, str) and value.strip():
            resumed.extend((option, value.strip()))
    if "--resume" not in options:
        resumed.append("--resume")
    if restart_game:
        resumed.append("--restart-game")
    return resumed


def is_manual_exit(exit_code: int | None) -> bool:
    """Only the dedicated in-app hotkey may stop the supervisor cleanly."""
    return exit_code == MANUAL_EXIT_CODE


def fallback_child_exit_reason(
    exit_code: int | None,
    handoff: dict[str, object] | None,
    *,
    scheduled_restart: bool,
    termination_reason: str | None,
) -> str | None:
    """Classify an exit that the child did not already explain via its handoff."""
    if scheduled_restart or termination_reason is not None or handoff is not None:
        return None
    return "unexpected_clean_exit" if exit_code == 0 else "child_exit_without_handoff"


def daily_restart_state_path(heartbeat_path: Path) -> Path:
    """Keep each supervised profile's maintenance history separate."""
    return heartbeat_path.with_name(f"{heartbeat_path.stem}_supervisor_state.json")


def read_last_scheduled_restart_date(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        value = payload.get("last_scheduled_restart_date") if isinstance(payload, dict) else None
        return value if isinstance(value, str) else None
    except (OSError, ValueError, TypeError):
        return None


def record_scheduled_restart(path: Path, now: datetime) -> bool:
    """Record before stopping the child, so a failed restart is never rescheduled today."""
    payload = {"last_scheduled_restart_date": now.date().isoformat()}
    temporary = path.with_name(f"{path.stem}_{time.time_ns()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(payload), encoding="utf-8")
        temporary.replace(path)
        return True
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def daily_restart_is_due(now: datetime, last_restart_date: str | None, restart_hour: int) -> bool:
    return now.hour >= restart_hour and last_restart_date != now.date().isoformat()


def daily_restart_is_eligible(supervisor_started_at: datetime, now: datetime, restart_hour: int) -> bool:
    """Do not restart a bot that was itself freshly launched after today's schedule."""
    return not (
        supervisor_started_at.date() == now.date()
        and supervisor_started_at.hour >= restart_hour
    )


def _stop_child(child: subprocess.Popen, timeout_seconds: float = 10.0) -> None:
    """End only the supervisor-owned child, escalating when graceful termination stalls."""
    if child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=timeout_seconds)


def supervise(
    command: Sequence[str],
    heartbeat_path: Path,
    timeout_seconds: float = 180.0,
    daily_restart_hour: int | None = DEFAULT_DAILY_RESTART_HOUR,
) -> int:
    if not command:
        raise ValueError("A bot command is required after '--'.")

    profile = explicit_profile_from_command(command)
    if profile is None:
        raise ValueError("A supervised bot command must include an explicit '--profile <name>'.")

    restart_count = 0
    launch_command = list(command)
    maintenance_state_path = daily_restart_state_path(heartbeat_path)
    supervisor_started_at = datetime.now()
    while True:
        started_at = time.time()
        session_id = new_session_id()
        child_command = prepare_child_command(launch_command, session_id)
        termination_reason: str | None = None
        try:
            heartbeat_path.unlink(missing_ok=True)
        except OSError:
            pass
        logging.info("[Supervisor] Starting bot process: %s", " ".join(child_command))
        child = subprocess.Popen(child_command)
        scheduled_restart = False
        try:
            while child.poll() is None:
                if daily_restart_hour is not None:
                    local_now = datetime.now()
                    last_restart_date = read_last_scheduled_restart_date(maintenance_state_path)
                    if (
                        daily_restart_is_eligible(supervisor_started_at, local_now, daily_restart_hour)
                        and daily_restart_is_due(local_now, last_restart_date, daily_restart_hour)
                    ):
                        # Persist first: watchdog recovery after a failed child restart must not
                        # produce a second maintenance restart on the same calendar day.
                        if record_scheduled_restart(maintenance_state_path, local_now):
                            scheduled_restart = True
                            termination_reason = "daily_scheduled_restart"
                            last_heartbeat = read_heartbeat(heartbeat_path)
                            write_incident(
                                profile,
                                SCHEDULED_MAINTENANCE,
                                termination_reason,
                                pid=getattr(child, "pid", None),
                                **heartbeat_incident_context(last_heartbeat, getattr(child, "pid", None), heartbeat_is_current(heartbeat_path, started_at), session_id),
                                details={"scheduled_hour": daily_restart_hour, "last_scheduled_restart_date": local_now.date().isoformat()},
                            )
                            logging.warning(
                                "[Supervisor] Daily maintenance restart scheduled at %s; restarting bot with saved settings.",
                                local_now.strftime("%Y-%m-%d %H:%M:%S"),
                            )
                            _stop_child(child)
                            break
                        logging.error(
                            "[Supervisor] Daily restart state could not be persisted; postponing maintenance restart."
                        )
                # A previous run's heartbeat must never be allowed to kill a
                # freshly created process, even if deleting it was unavailable.
                current_heartbeat = heartbeat_is_current(heartbeat_path, started_at)
                age = heartbeat_age_seconds(heartbeat_path) if current_heartbeat else time.time() - started_at
                # The first launch legitimately pauses for the user's CLI choices.
                # Restarted launches include --resume and use the normal liveness limit.
                allowed_age = max(timeout_seconds, 600.0) if restart_count == 0 and "--resume" not in launch_command else timeout_seconds
                if age > allowed_age:
                    termination_reason = "heartbeat_stale"
                    last_heartbeat = read_heartbeat(heartbeat_path)
                    write_incident(
                        profile,
                        HEARTBEAT_TIMEOUT,
                        termination_reason,
                        pid=getattr(child, "pid", None),
                        **heartbeat_incident_context(last_heartbeat, getattr(child, "pid", None), current_heartbeat, session_id),
                        details={
                            "heartbeat_age_seconds": age,
                            "timeout_seconds": allowed_age,
                            "last_heartbeat": last_heartbeat.get("timestamp"),
                        },
                    )
                    logging.error("[Supervisor] Heartbeat stale for %.1fs; terminating bot for recovery.", age)
                    _stop_child(child)
                    break
                time.sleep(5.0)
        except KeyboardInterrupt:
            # Ctrl+C is treated as child recovery, not supervisor shutdown.
            # The user can use Ctrl+Shift+Q inside the bot for a deliberate exit.
            logging.warning("[Supervisor] Ctrl+C received; restarting bot with saved settings.")
            termination_reason = "interrupt_recovery_requested"
            last_heartbeat = read_heartbeat(heartbeat_path)
            write_incident(
                profile,
                SCHEDULED_MAINTENANCE,
                termination_reason,
                pid=getattr(child, "pid", None),
                **heartbeat_incident_context(last_heartbeat, getattr(child, "pid", None), heartbeat_is_current(heartbeat_path, started_at), session_id),
                details={"restart_number": restart_count + 1},
            )
            _stop_child(child)

        exit_code = child.poll()
        if is_manual_exit(exit_code):
            last_heartbeat = read_heartbeat(heartbeat_path)
            write_incident(
                profile,
                SCHEDULED_MAINTENANCE,
                "manual_exit_hotkey",
                pid=getattr(child, "pid", None),
                **heartbeat_incident_context(last_heartbeat, getattr(child, "pid", None), heartbeat_is_current(heartbeat_path, started_at), session_id),
                details={"exit_code": exit_code},
            )
            logging.info("[Supervisor] Manual exit hotkey received; stopping supervisor.")
            return 0
        child_pid = getattr(child, "pid", None)
        expected_pid = child_pid if isinstance(child_pid, int) else None
        handoff = read_child_termination(profile, expected_pid)
        fallback_reason = fallback_child_exit_reason(
            exit_code,
            handoff,
            scheduled_restart=scheduled_restart,
            termination_reason=termination_reason,
        )
        if fallback_reason is not None:
            last_heartbeat = read_heartbeat(heartbeat_path)
            write_incident(
                profile,
                CRASH,
                fallback_reason,
                pid=expected_pid,
                **heartbeat_incident_context(last_heartbeat, expected_pid, heartbeat_is_current(heartbeat_path, started_at), session_id),
                details={
                    "exit_code": exit_code,
                    "started_at": started_at,
                    "last_heartbeat": last_heartbeat.get("timestamp"),
                },
            )
        need_restart_game = scheduled_restart or (termination_reason == "heartbeat_stale")
        launch_command = prepare_resume_command(
            launch_command,
            read_heartbeat(heartbeat_path),
            restart_game=need_restart_game,
        )
        restart_count = 0 if scheduled_restart else restart_count + 1
        delay = min(60.0, 2.0 ** min(restart_count, 5))
        if scheduled_restart:
            logging.warning("[Supervisor] Daily maintenance restart prepared; restarting in %.0fs.", delay)
        else:
            logging.warning("[Supervisor] Bot exited (%s); restart #%d in %.0fs.", exit_code, restart_count, delay)
        time.sleep(delay)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the game bot under a liveness supervisor.")
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT_PATH)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument(
        "--daily-restart-hour",
        type=int,
        default=DEFAULT_DAILY_RESTART_HOUR,
        choices=range(24),
        metavar="HOUR",
        help="Restart the bot once daily at or after this local hour (default: 8).",
    )
    parser.add_argument(
        "--disable-daily-restart",
        action="store_true",
        help="Disable the daily scheduled maintenance restart.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    daily_restart_hour = None if args.disable_daily_restart else args.daily_restart_hour
    return supervise(command, args.heartbeat, timeout_seconds=args.timeout, daily_restart_hour=daily_restart_hour)


if __name__ == "__main__":
    raise SystemExit(main())
