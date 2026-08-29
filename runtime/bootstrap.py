"""Runtime dependency construction and template preflight checks."""

import logging
import os
import sys
import time

from actions.mouse import MouseController
from capture.screen import ScreenCapturer
from config import get_monitor_index, normalize_config
from states.state_machine import GameStateMachine
from utils.daily_manager import DailyManager
from vision.matcher import TemplateMatcher
from cli.profiles import resolve_profile_name

def check_mode_templates(config):
    """
    依據選定的模式配置，動態檢查必要的模板圖片是否存在。
    """
    missing = []
    
    # 1. 檢查尋路導航的按鈕
    for btn in config.get("navigation_path", []):
        path = os.path.join("templates", btn)
        if not os.path.exists(path):
            missing.append(btn)
            
    # 2. 檢查類型專屬按鈕
    if config["type"] == "stage":
        # 關卡需要大廳開始按鈕與再戰按鈕
        lobby_btn = config["lobby_start_btn"]
        if not os.path.exists(os.path.join("templates", lobby_btn)):
            missing.append(lobby_btn)
            
        retry_btn = "stages/retry.png"
        if not os.path.exists(os.path.join("templates", retry_btn)):
            missing.append(retry_btn)
            
    elif config["type"] == "dungeon":
        # 地下城需要戰鬥入口按鈕與結束按鈕
        fight_btn = config["dungeon_fight_btn"]
        if not os.path.exists(os.path.join("templates", fight_btn)):
            missing.append(fight_btn)
            
        complete_btn = "dungeons/dungeons_complete.png"
        if not os.path.exists(os.path.join("templates", complete_btn)):
            missing.append(complete_btn)
            
        # 檢查基本通用的戰鬥結算
        for btn in config["dungeon_battle_results"]:
            if not os.path.exists(os.path.join("templates", btn)):
                missing.append(btn)
                
    elif config["type"] == "domain":
        # 領地模式檢查探索優先級按鈕與結算按鈕
        for btn in config.get("explore_priorities", []):
            if not os.path.exists(os.path.join("templates", btn)):
                missing.append(btn)
        for btn in config.get("result_buttons", []):
            if not os.path.exists(os.path.join("templates", btn)):
                missing.append(btn)

    elif config["type"] == "bag_clean":
        # 背包整理需要相關按鈕
        bag_files = [
            "common/bag.png",
            "common/Backpack_Disassembly.png",
            "common/select_all.png",
            "common/Disassembly.png",
            "common/confirm.png",
            "common/tidy.png",
            "common/quit.png"
        ]
        for btn in bag_files:
            if not os.path.exists(os.path.join("templates", btn)):
                missing.append(btn)
                
    return missing


def init_state_machine_system(args, config, target_hwnd=None):
    print("=" * 60)
    print(" 🚀 Blackfire Crusade 自動掛機輔助腳本啟動 🚀")
    print("=" * 60)
    active_monitor = args.monitor if args.monitor is not None else get_monitor_index()
    print(f"[*] 目標視窗標題: {args.title} (HWND: {hex(target_hwnd) if target_hwnd else '自動查找'})")
    print(f"[*] 目標顯示器編號: Monitor {active_monitor} (由 {'CLI 參數' if args.monitor is not None else 'Profile TOML'} 指定)")
    print(f"[*] 畫面偵測間隔: {args.interval} 秒")
    print(f"[*] 當前掛機模式: {config['name']} ({args.mode})")
    print("=" * 60)

    # 檢查 templates 資料夾與圖片是否存在
    os.makedirs("templates", exist_ok=True)
    missing = check_mode_templates(config)
    if missing:
        print(f"[!] 偵測到當前模式 '{config['name']}' 的必要模板圖片缺失：")
        for m in missing:
            print(f"    - templates/{m}")
        print("\n[!] 請先執行以下命令使用裁剪工具建立對應的模板圖片：")
        print("    python scripts/crop_tool.py")
        print("=" * 60)
        sys.exit(1)

    # 檢查是否啟用自動領體力
    bread_files = [
        "common/door.png",
        "common/bread.png",
        "common/confirm.png",
        "common/ok.png",
        "common/quit.png"
    ]
    enable_bread = config.get("auto_bread", True)
    if enable_bread:
        for bf in bread_files:
            if not os.path.exists(os.path.join("templates", bf)):
                enable_bread = False
                break

    if enable_bread:
        # 額外檢查收集按鈕，collect.png 或 bread_collection.png 必須至少存在一個
        has_collect = os.path.exists(os.path.join("templates", "common/collect.png")) or \
                      os.path.exists(os.path.join("templates", "common/bread_collection.png"))
        if not has_collect:
            enable_bread = False

    if enable_bread:
        cd_msg = "每 2 小時" if args.mode == "collect_only" else "每 30 分鐘"
        print(f"[*] 自動領體力功能: 啟用 (啟動時與{cd_msg}執行一次)")
    elif not config.get("auto_bread", True):
        print("[*] 自動領體力功能: 停用 (配置設定 auto_bread = false)")
    else:
        print("[*] 自動領體力功能: 停用 (缺少部分體力相關模板，已自動忽略)")
    print("=" * 60)

    # 初始化模組
    capturer = ScreenCapturer(window_title=args.title, backend_mode=args.backend, hwnd=target_hwnd, monitor_index=active_monitor)
    matcher = TemplateMatcher(templates_dir="templates", template_scale=1.0, auto_scale=True)
    mouse = MouseController(human_like=True, backend_mode=args.backend, window_title=args.title,
                            capturer=capturer, hwnd=target_hwnd)

    # 初始化狀態機
    state_machine = GameStateMachine(capturer=capturer, matcher=matcher, mouse=mouse)
    state_machine.backend_mode = args.backend
    state_machine.window_title = args.title
    state_machine.target_hwnd = target_hwnd
    state_machine.is_sandbox = ("[#]" in args.title)
    config = normalize_config(config)
    # Callback 接線：解耦 MouseController 與 GameStateMachine (Issue #11)
    # 動作成功後通知 SM 重置卡死計數（告知而非詢問，單向依賴）
    mouse._on_action_success = lambda: setattr(state_machine, 'consecutive_stuck_count', 0)
    # 查詢 SM 暫停狀態，由上層提供查詢函式（依賴倒置）
    mouse._is_paused_fn = lambda: getattr(state_machine, 'is_paused', False)
    # 注入 threading.Event 門閥供底層動作進行原地定格 (Freeze-in-Place)
    mouse._resume_event = state_machine.resume_event
    capturer._resume_event = state_machine.resume_event
    state_machine.config = config
    state_machine.primary_config = config.copy()
    state_machine.enable_runtime_config_refresh(
        args.subflow[0] if getattr(args, "subflow", None) else args.mode,
        config,
    )
    profile_name = resolve_profile_name(args, getattr(args, "title", ""))
    daily_manager = DailyManager(profile=profile_name)
    logging.info(f"📂 [DailyManager] 成功綁定角色狀態檔: user_data/{profile_name}/daily_status.json")
    state_machine.daily_manager = daily_manager

    # 若使用 --subflow 發起 Dev 階段獨立測試
    if hasattr(args, "subflow") and args.subflow:
        state_machine.is_dev_subflow_run = True
        state_machine.start_subflow_queue(args.subflow)

    # 每日任務主模式：載入 accepted_quests、掛載 QuestScheduler 並啟動 Daily Master Pipeline 全域流水線
    if getattr(args, "mode", None) == "daily":
        quest_scheduler = daily_manager.load_quest_scheduler()
        state_machine.attach_quest_scheduler(quest_scheduler)
        state_machine.evaluate_and_schedule_daily_pipeline()




    state_machine.bread_collection_available = enable_bread
    if config["type"] in ["bag_clean", "blood_altar"] or not config.get("auto_bread", True):
        state_machine.enable_bread = False
        state_machine.need_bread_collection = False
    else:
        state_machine.enable_bread = enable_bread

    if not config.get("auto_diamond", True):
        state_machine.need_diamond_collection = False

    print("[+] 初始化成功！請確認您的遊戲視窗非最小化，且維持在畫面上。")
    print("[+] 快捷鍵提示：在終端機或遊戲視窗按 [Ctrl + Space] 隨時暫停/繼續；按 [Ctrl + C] 終止程式。")
    print("[*] 將在 3 秒後開始偵測...")
    time.sleep(3)
    return state_machine

