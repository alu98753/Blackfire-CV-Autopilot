"""Process-external watchdog for restarting an unresponsive bot process."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Sequence

from runtime.heartbeat import DEFAULT_HEARTBEAT_PATH


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
MANUAL_EXIT_CODE = 75


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


def prepare_resume_command(command: Sequence[str], heartbeat: dict[str, object]) -> list[str]:
    """Preserve first-run CLI options and restore the selected instance on restart."""
    resumed = list(command)
    options = set(resumed)
    for option, field in (("--target", "target"), ("--profile", "profile")):
        value = heartbeat.get(field)
        if option not in options and isinstance(value, str) and value.strip():
            resumed.extend((option, value.strip()))
    if "--resume" not in options:
        resumed.append("--resume")
    return resumed


def is_manual_exit(exit_code: int | None) -> bool:
    """Only the dedicated in-app hotkey may stop the supervisor cleanly."""
    return exit_code == MANUAL_EXIT_CODE


def supervise(command: Sequence[str], heartbeat_path: Path, timeout_seconds: float = 180.0) -> int:
    if not command:
        raise ValueError("A bot command is required after '--'.")

    restart_count = 0
    launch_command = list(command)
    while True:
        started_at = time.time()
        try:
            heartbeat_path.unlink(missing_ok=True)
        except OSError:
            pass
        logging.info("[Supervisor] Starting bot process: %s", " ".join(launch_command))
        child = subprocess.Popen(launch_command)
        try:
            while child.poll() is None:
                # A previous run's heartbeat must never be allowed to kill a
                # freshly created process, even if deleting it was unavailable.
                current_heartbeat = heartbeat_is_current(heartbeat_path, started_at)
                age = heartbeat_age_seconds(heartbeat_path) if current_heartbeat else time.time() - started_at
                # The first launch legitimately pauses for the user's CLI choices.
                # Restarted launches include --resume and use the normal liveness limit.
                allowed_age = max(timeout_seconds, 600.0) if restart_count == 0 and "--resume" not in launch_command else timeout_seconds
                if age > allowed_age:
                    logging.error("[Supervisor] Heartbeat stale for %.1fs; terminating bot for recovery.", age)
                    child.terminate()
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=10)
                    break
                time.sleep(5.0)
        except KeyboardInterrupt:
            # Ctrl+C is treated as child recovery, not supervisor shutdown.
            # The user can use Ctrl+Shift+Q inside the bot for a deliberate exit.
            logging.warning("[Supervisor] Ctrl+C received; restarting bot with saved settings.")
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=10)

        exit_code = child.poll()
        if is_manual_exit(exit_code):
            logging.info("[Supervisor] Manual exit hotkey received; stopping supervisor.")
            return 0
        launch_command = prepare_resume_command(launch_command, read_heartbeat(heartbeat_path))
        restart_count += 1
        delay = min(60.0, 2.0 ** min(restart_count, 5))
        logging.warning("[Supervisor] Bot exited (%s); restart #%d in %.0fs.", exit_code, restart_count, delay)
        time.sleep(delay)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the game bot under a liveness supervisor.")
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT_PATH)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    return supervise(command, args.heartbeat, timeout_seconds=args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
