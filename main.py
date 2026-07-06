import time
import sys
import os
import argparse
import logging
from capture.screen import ScreenCapturer
from vision.matcher import TemplateMatcher
from actions.mouse import MouseController
from states.state_machine import GameStateMachine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def check_templates_exist():
    # 最基本的兩個必要模板：開始戰鬥與再戰
    required = ["start.png", "retry.png"]
    missing = []
    for r in required:
        path = os.path.join("templates", r)
        if not os.path.exists(path):
            missing.append(r)
    return missing

def main():
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
    parser = argparse.ArgumentParser(description="Blackfire Crusade 自動刷副本腳本")
    parser.add_argument("--title", type=str, default="Blackfire Crusade", help="遊戲視窗標題")
    parser.add_argument("--interval", type=float, default=0.5, help="畫面偵測間隔秒數 (預設: 0.5)")
    args = parser.parse_args()

    print("=" * 60)
    print(" 🚀 Blackfire Crusade 自動刷副本輔助腳本啟動 🚀")
    print("=" * 60)
    print(f"[*] 目標視窗標題: {args.title}")
    print(f"[*] 畫面偵測間隔: {args.interval} 秒")
    print("=" * 60)

    # 檢查 templates 資料夾與圖片是否存在
    os.makedirs("templates", exist_ok=True)
    missing = check_templates_exist()
    if missing:
        print("[!] 偵測到以下必要的模板圖片缺失：")
        for m in missing:
            print(f"    - templates/{m}")
        print("\n[!] 請先執行以下命令使用裁剪工具建立模板圖片：")
        print("    python crop_tool.py")
        print("    依序裁剪儲存為 start.png、retry.png、ok.png。")
        print("=" * 60)
        sys.exit(1)

    # 初始化模組
    capturer = ScreenCapturer(window_title=args.title)
    matcher = TemplateMatcher(templates_dir="templates")
    mouse = MouseController(human_like=True)
    
    # 初始化狀態機
    state_machine = GameStateMachine(capturer=capturer, matcher=matcher, mouse=mouse)

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
