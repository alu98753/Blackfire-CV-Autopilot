"""Runtime event loop with pause and configuration safe-point handling."""

import sys
import time
import logging

from utils import PauseController
from runtime.heartbeat import touch_heartbeat
from runtime.incident_journal import record_unhandled_exception, record_manual_restart
from runtime.supervisor import MANUAL_EXIT_CODE, MANUAL_RESTART_EXIT_CODE
from states.nemesis_intervention import UserResumeDecision


def run_main_loop(state_machine, interval):
    pause_controller = None
    try:
        import pyautogui

        def on_pause_toggle():
            intervention = getattr(state_machine, "nemesis_intervention", None)
            if intervention is not None and intervention.blocks_user_toggle():
                return
            if state_machine.is_paused:
                if intervention is not None:
                    decision = intervention.request_user_resume()
                    if decision in (UserResumeDecision.BLOCKED_TIMEOUT, UserResumeDecision.BLOCKED_INTERVENTION):
                        return
                pause_duration = state_machine.resume(user_initiated=True)
                touch_heartbeat(state_machine, force=True)
                state_machine.prev_mouse_pos = pyautogui.position()
                print(f"\n[RESUMED] state={state_machine.current_state}; paused {pause_duration:.1f}s\n", flush=True)
            else:
                state_machine.pause()
                touch_heartbeat(state_machine, force=True)
                print(f"\n[PAUSED] state={state_machine.current_state}\n", flush=True)

        def on_intervention_acknowledge():
            intervention = getattr(state_machine, "nemesis_intervention", None)
            if intervention is None or not intervention.acknowledge():
                return
            print("\n[Nemesis] 已確認你已回到電腦；自動化仍保持暫停。手動處理完成後請按 Ctrl+Space 恢復。\n", flush=True)
            touch_heartbeat(state_machine, force=True)

        pause_controller = PauseController(
            capturer=getattr(state_machine, "capturer", None),
            on_toggle=on_pause_toggle,
            on_acknowledge=on_intervention_acknowledge,
            is_paused_fn=lambda: getattr(state_machine, "is_paused", False),
            heartbeat_callback=lambda: touch_heartbeat(state_machine),
        )

        while True:
            start_time = time.time()
            if pause_controller.check_manual_exit_triggered():
                print("\n[Manual Exit] Ctrl+Shift+Q received.")
                raise SystemExit(MANUAL_EXIT_CODE)
            if pause_controller.check_manual_restart_triggered():
                print("\n[Manual Restart] Ctrl+Q received.")
                record_manual_restart(state_machine, "manual_restart_hotkey")
                raise SystemExit(MANUAL_RESTART_EXIT_CODE)

            intervention = getattr(state_machine, "nemesis_intervention", None)
            if intervention is not None and intervention.has_pending_timeout_recovery():
                intervention.run_pending_timeout_recovery()
                continue
            if pause_controller.check_toggle_triggered() and not pause_controller._thread:
                on_pause_toggle()
            if state_machine.is_paused:
                touch_heartbeat(state_machine)
                time.sleep(0.05)
                continue
            state_machine.refresh_config_at_safe_point()
            touch_heartbeat(state_machine)
            state_machine.step()
            time.sleep(max(0.001, interval - (time.time() - start_time)))
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:
        logging.exception("[Runtime] Unhandled bot exception; exiting for supervisor recovery.")
        record_unhandled_exception(state_machine, exc)
        raise
    finally:
        if pause_controller is not None:
            pause_controller.stop()
        capturer = getattr(state_machine, "capturer", None)
        if capturer is not None and hasattr(capturer, "close"):
            capturer.close()
