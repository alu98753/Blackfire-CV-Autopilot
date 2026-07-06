import time
import sys
import os
import argparse
import logging
from capture.screen import ScreenCapturer
from vision.matcher import TemplateMatcher
from actions.mouse import MouseController
from states.state_machine import GameStateMachine
from config import GAME_CONFIGS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

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
                
    return missing

def main():
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
            
    parser = argparse.ArgumentParser(description="Blackfire Crusade 副本與地下城自動掛機腳本")
    parser.add_argument("--title", type=str, default="Blackfire Crusade", help="遊戲視窗標題")
    parser.add_argument("--interval", type=float, default=0.5, help="畫面偵測間隔秒數 (預設: 0.5)")
    parser.add_argument("--mode", type=str, default="stage", choices=list(GAME_CONFIGS.keys()), 
                        help="掛機模式：stage (普通關卡) 或 dungeon_slime (史萊姆地下城)")
    args = parser.parse_args()

    # 取得當前模式的配置
    config = GAME_CONFIGS[args.mode]

    print("=" * 60)
    print(" 🚀 Blackfire Crusade 自動掛機輔助腳本啟動 🚀")
    print("=" * 60)
    print(f"[*] 目標視窗標題: {args.title}")
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
        print("    python crop_tool.py")
        print("=" * 60)
        sys.exit(1)

    # 檢查是否啟用自動領體力
    bread_files = [
        "common/door.png",
        "common/bread.png",
        "common/bread_collection.png",
        "common/confirm.png",
        "common/ok.png",
        "common/quit_bread.png"
    ]
    enable_bread = True
    for bf in bread_files:
        if not os.path.exists(os.path.join("templates", bf)):
            enable_bread = False
            break

    if enable_bread:
        print("[*] 自動領體力功能: 啟用 (啟動時與每 30 分鐘執行一次)")
    else:
        print("[*] 自動領體力功能: 停用 (缺少部分體力相關模板，已自動忽略)")
    print("=" * 60)

    # 初始化模組
    capturer = ScreenCapturer(window_title=args.title)
    matcher = TemplateMatcher(templates_dir="templates")
    mouse = MouseController(human_like=True)
    
    # 初始化狀態機 (傳入模式配置)
    state_machine = GameStateMachine(capturer=capturer, matcher=matcher, mouse=mouse)
    # 將當前配置與體力啟用狀態設定至狀態機中
    state_machine.config = config
    state_machine.enable_bread = enable_bread

    print("[+] 初始化成功！請確認您的遊戲視窗非最小化，且維持在畫面上。")
    print("[+] 按 [Ctrl + C] 可以隨時終止本程式。")
    print("[*] 將在 3 秒後開始偵測...")
    time.sleep(3)

    try:
        while True:
            start_time = time.time()
            
            # 執行單步決策
            state_machine.step()
            
            # 計算該步所花費時間，若低於設定的偵測間隔，則補足間隔時間
            elapsed = time.time() - start_time
            sleep_time = max(0.1, args.interval - elapsed)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print(" 🛑 程式已由使用者中斷。")
        print(f" 📊 統計資訊：")
        print(f"    - 總共啟動戰鬥場次: {state_machine.run_count} 次")
        print("=" * 60)
        sys.exit(0)

if __name__ == "__main__":
    main()
