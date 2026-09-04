# 已關閉 DPI 識別度，使腳本以 DPI-unaware 模式運行，相容高 DPI 螢幕下的遊戲後台截圖與無黑邊對齊
# import ctypes
# try:
#     ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
# except Exception:
#     try:
#         ctypes.windll.user32.SetProcessDPIAware()
#     except Exception:
#         pass

import sys
import logging
from config import get_monitor_index
from utils.game_process import is_window_hung
from utils.steam_launcher import SteamGameLauncher
from utils.window import select_game_window
from cli.arguments import parse_arguments
from cli.mode_setup import setup_equipment_config, setup_mode_config
from cli.profiles import resolve_profile_name
from runtime.bootstrap import init_state_machine_system
from runtime.heartbeat import heartbeat_path_for_profile, touch_heartbeat
from runtime.incident_journal import clear_child_termination, new_session_id, normalize_profile
from runtime.loop import run_main_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def setup_utf8_encoding():
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

def main():
    setup_utf8_encoding()
    args = parse_arguments()

    # 1. 優先偵測並選擇遊戲視窗實例 (最優先確認目標實例，支援雙開/沙盒自動列舉與目標指定)
    is_resume = getattr(args, "resume", False) is True
    target_hwnd, target_title = select_game_window(target=args.target, auto_prompt=not is_resume)
    if target_title:
        args.title = target_title

    # 套用 Profile 專屬配置覆蓋 (如 user_data/sandbox/config.toml)
    profile_name = normalize_profile(resolve_profile_name(args, target_title))
    from config import set_active_profile
    set_active_profile(profile_name)
    clear_child_termination(profile_name)

    # 2. 處理模式設定選單 (避免遊戲開啟後停留在 CLI 輸入視窗造成阻塞)
    config = setup_mode_config(args)
    if not is_resume:
        setup_equipment_config(config)

    # 3. 檢查遊戲是否開啟，發起直連啟動並傳送至指定螢幕與最大化全螢幕
    active_monitor = args.monitor if args.monitor is not None else get_monitor_index()
    launcher = SteamGameLauncher(game_title=args.title, backend_mode=args.backend, monitor_index=active_monitor, hwnd=target_hwnd)

    force_relaunch = getattr(args, "restart_game", False) is True
    if not force_relaunch and target_hwnd and is_window_hung(target_hwnd):
        logging.warning("⚠️ 偵測到遊戲視窗處於未回應 (Hung) 狀態，自動升級為重啟遊戲流程！")
        force_relaunch = True

    if not launcher.ensure_game_ready(force_relaunch=force_relaunch):
        print("[!] 遊戲啟動準備失敗，終止腳本。")
        sys.exit(1)

    # 4. 初始化主狀態機並立即運行 (無縫接續執行 LoginFlow 登入與 Click Until 流程)
    state_machine = init_state_machine_system(args, config, target_hwnd=target_hwnd)
    state_machine.restart_target = args.target or ("sandbox" if "[#]" in args.title else "native")
    state_machine.restart_profile = profile_name
    state_machine.incident_session_id = getattr(args, "incident_session_id", None) or new_session_id()
    state_machine.heartbeat_path = heartbeat_path_for_profile(profile_name)
    touch_heartbeat(state_machine)
    run_main_loop(state_machine, args.interval)

if __name__ == "__main__":
    main()
