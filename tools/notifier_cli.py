"""Diagnostic CLI tool for testing Discord webhook notification dispatch and reconciliation."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta
from typing import Any

from ports.notification_port import NotificationPort
from runtime.discord_payload_builder import (
    build_alarm_payload,
    build_milestone_payload,
)
from runtime.discord_webhook_adapter import DiscordWebhookAdapter
from runtime.json_notification_history_store import JsonNotificationHistoryStore
from runtime.notifier_factory import resolve_webhook_url


def _safe_print(text: str = "") -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "ascii"
        print(text.encode(encoding, errors="replace").decode(encoding))


def _build_test_targets(
    profile: str | None,
    test_type: str,
    language: str,
) -> list[tuple[str, dict[str, Any]]]:
    """Construct test notification payloads based on requested test_type."""
    from runtime.notification_i18n import (
        format_daily_claim_deadline_alarm,
        format_milestone1,
        format_milestone2,
        format_subflow_status,
        format_supervisor_crash_alarm,
    )

    prof = profile or "test_preview"
    lang = language
    now_dt = datetime.now()
    targets: list[tuple[str, dict[str, Any]]] = []

    if test_type in ["all", "milestone", "milestone1"]:
        accepted_quests = ["[Daily] Clear 20 Skeletons", "[Daily] Clear 15 Spiders"]
        try:
            from utils.daily_manager import DailyManager
            dm = DailyManager(profile=profile)
            bb_quests = dm.status.get("subflows", {}).get("bulletin_board", {}).get("accepted_quests", [])
            if bb_quests:
                accepted_quests = bb_quests
        except Exception:
            pass

        m1_title, m1_desc, m1_fields, m1_footer = format_milestone1(
            profile=prof,
            accepted_quests=accepted_quests,
            subflow_statuses=[
                format_subflow_status("chest", True, language=lang),
                format_subflow_status("hero_draw", True, language=lang),
                format_subflow_status("blood_altar", True, language=lang),
                format_subflow_status("jewelry_workshop", True, language=lang),
                format_subflow_status("bulletin_board", True, language=lang),
            ],
            language=lang,
            now_dt=now_dt,
        )
        payload = build_milestone_payload(
            title=m1_title,
            description=m1_desc,
            fields=m1_fields,
            footer_text=m1_footer,
            language=lang,
        )
        targets.append((f"Milestone 1: {m1_title}", payload))

    if test_type in ["all", "milestone", "milestone2"]:
        m2_title, m2_desc, m2_fields, m2_footer = format_milestone2(
            profile=prof,
            fallback_mode="Tier 4 Loop (mix)",
            language=lang,
            now_dt=now_dt,
            cleared_count=4,
            cleared_quests=["Clear 20 Skeletons", "Clear 15 Spiders", "Dungeon 4", "Dungeon 2"],
        )
        payload = build_milestone_payload(
            title=m2_title,
            description=m2_desc,
            fields=m2_fields,
            footer_text=m2_footer,
            language=lang,
        )
        targets.append((f"Milestone 2: {m2_title}", payload))

    if test_type in ["all", "alarm", "deadline"]:
        d_title, d_reason, d_details, d_desc, d_footer = format_daily_claim_deadline_alarm(
            profile=prof,
            deadline_minutes=30,
            pending_subflows=["bulletin_board"],
            current_state="STATE_NAVIGATING",
            language=lang,
            now_dt=now_dt,
        )
        payload = build_alarm_payload(
            code="DAILY_CLAIM_DEADLINE_EXCEEDED",
            title=d_title,
            reason=d_reason,
            details=d_details,
            description=d_desc,
            footer_text=d_footer,
            language=lang,
        )
        targets.append((f"Alarm: {d_title}", payload))

    if test_type in ["all", "alarm", "supervisor", "crash"]:
        s_title, s_reason, s_details, s_desc, s_footer = format_supervisor_crash_alarm(
            profile=prof,
            restarts=6,
            max_restarts=5,
            window_duration_str="15m",
            window_seconds=900.0,
            language=lang,
            now_dt=now_dt,
        )
        payload = build_alarm_payload(
            code="SUPERVISOR_CRASH_LOOP_EXCEEDED",
            title=s_title,
            reason=s_reason,
            details=s_details,
            description=s_desc,
            footer_text=s_footer,
            language=lang,
        )
        targets.append((f"Alarm: {s_title}", payload))

    return targets


def _run_live_deletion_verification(
    notifier: NotificationPort,
    message_id: str,
    delete_after_seconds: float,
) -> bool:
    """Execute Tier 2 live deletion: pause -> DELETE #1 (204) -> DELETE #2 (404 idempotency)."""
    if not message_id:
        _safe_print("    [WARNING] No external_message_id returned; skipping deletion verification.")
        return False

    if delete_after_seconds > 0:
        _safe_print(f"    Pausing {delete_after_seconds:.0f}s for human visual verification in Discord...")
        total_seconds = int(delete_after_seconds)
        for remaining in range(total_seconds, 0, -1):
            _safe_print(f"    ... Deleting in {remaining}s")
            time.sleep(1.0)
        fractional = delete_after_seconds - total_seconds
        if fractional > 0:
            time.sleep(fractional)

    # DELETE #1: HTTP 204 expected
    del_res1 = notifier.delete_message(message_id)
    d1_status = "removed" if del_res1.status_code in (200, 204) else f"failed: {del_res1.error}"
    _safe_print(f"    DELETE #1: HTTP {del_res1.status_code} -> {d1_status}")

    # DELETE #2: HTTP 404 expected (already absent, treated as converged by domain reconciliation semantics)
    del_res2 = notifier.delete_message(message_id)
    if del_res2.status_code == 404:
        d2_status = "already absent, treated as converged (reconciliation semantics verified)"
    elif del_res2.status_code in (200, 204):
        d2_status = "removed again"
    else:
        d2_status = f"failed: {del_res2.error}"
    _safe_print(f"    DELETE #2: HTTP {del_res2.status_code} -> {d2_status}")

    return bool(del_res1.success and del_res2.success)


def _verify_reconcile_test_invariants(
    coordinator: Any,
    notifier: NotificationPort,
    message_id: str,
    today_tag: str,
    fake_0705: datetime,
) -> bool:
    """Verify desired-state cleanup, daily completion latch, and message absence."""
    _safe_print("[*] Step 5: Verifying Desired-State & Invariants...")
    history = coordinator.history_store.load_history()
    remaining_expired = [
        m for m in history.get("dispatched_messages", [])
        if str(m.get("date", "")) < today_tag
    ]
    assert_dispatched_empty = (len(remaining_expired) == 0)
    assert_latched = (history.get("last_reconciled_date") == today_tag)
    second_reconciled = coordinator.reconcile_expired_messages(now_dt=fake_0705, force=False)
    assert_latch_effective = (second_reconciled == 0)
    verify_del = notifier.delete_message(message_id)
    assert_message_gone = (verify_del.status_code == 404)

    _safe_print(f"    - Temporary expired messages cleared: {'PASS' if assert_dispatched_empty else 'FAIL'}")
    _safe_print(f"    - Daily completion latch set (last_reconciled_date == {today_tag}): {'PASS' if assert_latched else 'FAIL'}")
    _safe_print(f"    - Daily completion latch zero-recheck invariant: {'PASS' if assert_latch_effective else 'FAIL'}")
    _safe_print(f"    - Discord message confirmed absent (HTTP 404): {'PASS' if assert_message_gone else 'FAIL'}")

    all_passed = assert_dispatched_empty and assert_latched and assert_latch_effective and assert_message_gone
    status_msg = "ALL INVARIANTS SATISFIED (PASS)" if all_passed else "VERIFICATION FAILED"
    _safe_print("=" * 65)
    _safe_print(f"[*] Live Reconciliation Verification: {status_msg}")
    _safe_print("=" * 65 + "\n")
    return all_passed


def _run_live_reconcile_verification(
    webhook_url: str,
    profile: str | None,
    language: str,
    delete_after_seconds: float = 0.0,
) -> bool:
    """Execute Tier 3 Live Reconciliation Test with isolated temporary history and injected clock."""
    from runtime.notification_i18n import format_milestone1
    from states.daily_pipeline_notifier import DailyPipelineNotifier
    from states.daily_reconciliation import (
        DailyReconciliationService,
        resolve_business_dt,
    )

    _safe_print("\n" + "=" * 65)
    _safe_print("[TIER 3 LIVE RECONCILIATION TEST] Isolated E2E Verification")
    _safe_print("=" * 65)

    now_dt = resolve_business_dt()
    today_tag = now_dt.strftime("%Y-%m-%d")
    yesterday_tag = (now_dt.date() - timedelta(days=1)).strftime("%Y-%m-%d")
    fake_0705 = now_dt.replace(hour=7, minute=5, second=0, microsecond=0)
    notifier = DiscordWebhookAdapter(webhook_url=webhook_url, language=language, profile=profile)

    with tempfile.TemporaryDirectory(prefix="blackfire_live_reconcile_") as temp_dir:
        temp_history_file = os.path.join(temp_dir, "notification_history.json")
        _safe_print(f"[*] Isolated temporary history: {temp_history_file}")
        _safe_print("    (Strict Invariant: Production history is NEVER touched)")

        temp_store = JsonNotificationHistoryStore(history_file_path=temp_history_file)
        reconcile_service = DailyReconciliationService(
            notification_port=notifier,
            history_store=temp_store,
        )
        coord = DailyPipelineNotifier(
            notification_port=notifier,
            history_store=temp_store,
            reconciliation_service=reconcile_service,
            profile=profile or "test_preview",
            language=language,
        )

        m_title, m_desc, m_fields, m_footer = format_milestone1(
            profile=profile or "live_test",
            accepted_quests=["[Live-Test] Reconcile Verification Quest"],
            subflow_statuses=[],
            language=language,
            now_dt=now_dt,
        )
        post_res = notifier.notify_milestone(
            title=f"[Reconcile Test] {m_title}",
            description=m_desc,
            fields=m_fields,
            footer_text=m_footer,
            sync=True,
        )
        if not post_res.success or not post_res.external_message_id:
            _safe_print(f"[ERROR] Failed to dispatch test message to Discord: {post_res.error}")
            return False

        msg_id = post_res.external_message_id
        _safe_print(f"[*] Step 1: Live message dispatched! ID: {msg_id}")
        _safe_print(f"[*] Step 2: Seeding message into temp history with date = {yesterday_tag}...")
        history = temp_store.load_history()
        history.setdefault("dispatched_messages", []).append({
            "id": msg_id,
            "date": yesterday_tag,
            "tag": "live_test_reconcile",
            "last_attempt_time": 0.0,
            "retry_after": 0.0,
        })
        temp_store.save_history(history)

        wait_sec = delete_after_seconds if delete_after_seconds > 0 else 5.0
        _safe_print(f"[*] Step 3: Pausing {wait_sec:.0f}s for human visual verification in Discord...")
        for rem in range(int(wait_sec), 0, -1):
            _safe_print(f"    ... Reconciling in {rem}s")
            time.sleep(1.0)
        if wait_sec > int(wait_sec):
            time.sleep(wait_sec - int(wait_sec))

        _safe_print(f"[*] Step 4: Reconciling with simulated business time 07:05 Asia/Taipei...")
        reconciled = coord.reconcile_expired_messages(now_dt=fake_0705, force=True)
        _safe_print(f"    Reconcile processed: {reconciled} message(s).")

        return _verify_reconcile_test_invariants(coord, notifier, msg_id, today_tag, fake_0705)


def send_test_notifications(
    webhook_url: str | None = None,
    profile: str | None = None,
    test_type: str = "all",
    live: bool = False,
    delete_after_seconds: float = 0.0,
    test_reconcile: bool = False,
) -> bool:
    """Execute test notification with strict Dry-Run vs Live isolation and optional deletion/reconciliation."""
    url = (webhook_url or "").strip() or resolve_webhook_url(profile=profile)
    from config import get_notification_language
    lang = get_notification_language(profile)

    if not live:
        if delete_after_seconds > 0:
            _safe_print("\n[ERROR] '--delete-after' requires '--live'. Deletion cannot be tested in dry-run mode.\n")
            return False
        if test_reconcile:
            _safe_print("\n[ERROR] '--test-reconcile' requires '--live'. Reconciliation cannot be tested in dry-run mode.\n")
            return False

    if live and not url:
        _safe_print("\n[ERROR] DISCORD_WEBHOOK_URL is required for live send.")
        _safe_print("   Please set DISCORD_WEBHOOK_URL in environment or configure it in TOML.\n")
        return False

    if live and test_reconcile:
        return _run_live_reconcile_verification(
            webhook_url=url,
            profile=profile,
            language=lang,
            delete_after_seconds=delete_after_seconds,
        )

    targets = _build_test_targets(profile=profile, test_type=test_type, language=lang)

    if not live:
        _safe_print("\n" + "=" * 65)
        _safe_print("[DRY-RUN PREVIEW] Discord Webhook Notification Payload (No Network Sent)")
        _safe_print("Hint: Pass '--live' to perform actual HTTP POST to Discord.")
        _safe_print(f"Webhook URL Status: {'Configured (' + url[:30] + '...)' if url else 'NOT CONFIGURED'}")
        _safe_print("=" * 65)
        for label, payload in targets:
            _safe_print(f"\n--- [{label}] ---")
            _safe_print(json.dumps(payload, ensure_ascii=False, indent=2))
        _safe_print("=" * 65 + "\n")
        return True

    # --- LIVE SENDING MODE ---
    _safe_print("\n" + "=" * 65)
    _safe_print(f"[LIVE SEND] Dispatching {len(targets)} notification(s) to Discord...")
    _safe_print(f"Webhook URL: {url[:35]}...")
    _safe_print("=" * 65)

    notifier = DiscordWebhookAdapter(webhook_url=url, language=lang, profile=profile)
    all_success = True
    for label, payload in targets:
        _safe_print(f"[*] Posting [{label}]...")
        res = notifier._post_payload(payload)
        status_text = "SUCCESS" if res.success else "FAILED"
        msg_id_info = f" (id: {res.external_message_id})" if res.external_message_id else ""
        _safe_print(f"    Delivery: {status_text}{msg_id_info}")
        if not res.success:
            all_success = False
            continue

        if delete_after_seconds > 0 and res.external_message_id:
            del_ok = _run_live_deletion_verification(
                notifier=notifier,
                message_id=res.external_message_id,
                delete_after_seconds=delete_after_seconds,
            )
            if not del_ok:
                all_success = False

    _safe_print("=" * 65 + "\n")
    return all_success


def main() -> int:
    parser = argparse.ArgumentParser(description="Discord Webhook Notification Diagnostic Tool.")
    parser.add_argument("--url", type=str, default=None, help="Explicit Discord Webhook URL for one-off testing")
    parser.add_argument("--profile", type=str, default=None, help="Profile name to resolve webhook config")
    parser.add_argument(
        "--type",
        choices=["all", "milestone", "milestone1", "milestone2", "alarm", "deadline", "supervisor", "crash"],
        default="all",
        help="Notification type to test (default: all)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Perform real HTTP POST to Discord (default: Dry-Run preview only)",
    )
    parser.add_argument(
        "--delete-after",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="Seconds to wait before deleting dispatched live message (requires --live)",
    )
    parser.add_argument(
        "--test-reconcile",
        action="store_true",
        default=False,
        help="Execute end-to-end reconciliation test with isolated temporary history and injected clock (requires --live)",
    )
    args = parser.parse_args()

    ok = send_test_notifications(
        webhook_url=args.url,
        profile=args.profile,
        test_type=args.type,
        live=args.live,
        delete_after_seconds=args.delete_after,
        test_reconcile=args.test_reconcile,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
