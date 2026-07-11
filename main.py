# 已關閉 DPI 識別度，使腳本以 DPI-unaware 模式運行，相容高 DPI 螢幕下的遊戲後台截圖與無黑邊對齊
# import ctypes
# try:
#     ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
# except Exception:
#     try:
#         ctypes.windll.user32.SetProcessDPIAware()
#     except Exception:
#         pass

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

def main():
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
            
    parser = argparse.ArgumentParser(description="Blackfire Crusade 副本與地下城自動掛機腳本")
    parser.add_argument("--title", type=str, default="Blackfire Crusade", help="遊戲視窗標題")
    parser.add_argument("--interval", type=float, default=0.05, help="畫面偵測間隔秒數 (預設: 0.05)")
    parser.add_argument("--mode", type=str, default="stage", choices=list(GAME_CONFIGS.keys()), 
                        help="掛機模式：stage (普通關卡) 或 dungeon_slime (史萊姆地下城)")
    parser.add_argument("--backend", action="store_true", help="啟用後台掛機模式 (不搶滑鼠，支援雙螢幕)")
    args = parser.parse_args()

    # 取得當前模式的配置
    config = GAME_CONFIGS[args.mode].copy()  # 使用 copy 避免影響原始 GAME_CONFIGS 字典
    config["backend_mode"] = args.backend

    if args.mode == "stage":
        print("請選擇要打的關卡 Boss：")
        print(" 1) 蒼穹平原 (Level 1)")
        print(" 2) 荒蕪岩地 (Level 2) - 預設")
        print(" 3) 古樹森林 (Level 3)")
        print(" 4) 沙漠廢墟 (Level 4)")
        print(" 5) 幽暗沼澤 (Level 5)")
        try:
            choice = input("請輸入關卡數字 [1-5] (直接 Enter 鍵預設為 5): ").strip()
            if not choice:
                choice = "5"
        except KeyboardInterrupt:
            print("\n[!] 取消啟動。")
            sys.exit(0)
        except Exception:
            choice = "5"

        stage_map = {
            "1": ("stages/level1_sky_plains.png", "stages/level1_final.png", "蒼穹平原"),
            "2": ("stages/level2_barren_rocks.png", "stages/level2_final.png", "荒蕪岩地"),
            "3": ("stages/level3_ancient_forest.png", "stages/level3_final.png", "古樹森林"),
            "4": ("stages/level4_desert_ruins.png", "stages/level4_final.png", "沙漠廢墟"),
            "5": ("stages/level5_gloomy_swamp.png", "stages/level5_final.png", "幽暗沼澤")
        }
        if choice not in stage_map:
            print(f"[!] 無效選擇 '{choice}'，已自動使用預設的第五關 [幽暗沼澤]...")
            choice = "5"

        level_btn, boss_btn, stage_name = stage_map[choice]
        config["name"] = f"普通關卡 - {stage_name}"
        config["navigation_path"] = [
            "common/door.png",
            "exit_battle.png",
            "common/select_stage.png",
            level_btn,
            "stages/stage_label.png",
            boss_btn
        ]

    elif args.mode == "dungeon_slime":
        print("請選擇要探索的地下城：")
        print(" 1) 黏糊糊的石窟 (Slime_entry)")
        print(" 2) 幽影地穴 (Ghost_entry)")
        print(" 3) 森林迷宮 (Forest_entry)")
        print(" 4) 神秘遺跡 (Ruins_entry)")
        print(" 5) 自動貪婪挑選 (Greedy Select) - 預設")
        try:
            choice = input("請輸入地下城數字 [1-5] (直接 Enter 鍵預設為 5): ").strip()
            if not choice:
                choice = "5"
        except KeyboardInterrupt:
            print("\n[!] 取消啟動。")
            sys.exit(0)
        except Exception:
            choice = "5"

        dungeon_map = {
            "1": ("dungeons/Slime_entry.png", "黏糊糊的石窟", False),
            "2": ("dungeons/Ghost_entry.png", "幽影地穴", False),
            "3": ("dungeons/Forest_entry.png", "森林迷宮", False),
            "4": ("dungeons/Ruins_entry.png", "神秘遺跡", False),
            "5": (None, "自動貪婪挑選", True)
        }
        if choice not in dungeon_map:
            print(f"[!] 無效選擇 '{choice}'，已自動使用預設的第五關 [自動貪婪挑選]...")
            choice = "5"

        entry_btn, dungeon_name, is_greedy = dungeon_map[choice]
        config["name"] = f"地下城 - {dungeon_name}"
        config["greedy_dungeon"] = is_greedy
        if is_greedy:
            config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png"]
        else:
            config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png", entry_btn]

    if args.mode == "collect_only":
        config["keep_colors"] = []
        config["disassemble_colors"] = []
    else:
        # 1. 選擇要保留/領取的最低裝備品質
        print("\n請選擇要【保留/領取】的最低裝備品質（該品質及以上皆會被保留，背包滿時優先拿取）：")
        print(" 1) 綠色 (優秀)")
        print(" 2) 藍色 (精良) - 預設")
        print(" 3) 紫色 (史詩)")
        print(" 4) 橘黃色 (傳奇)")
        try:
            keep_choice = input("請輸入數字 [1-4] (直接 Enter 鍵預設為 2): ").strip()
            if not keep_choice:
                keep_choice = "2"
        except KeyboardInterrupt:
            print("\n[!] 取消啟動。")
            sys.exit(0)
        except Exception:
            keep_choice = "2"

        keep_choices_map = {
            "1": ["green", "blue", "purple", "orange_yellow", "red"],
            "2": ["blue", "purple", "orange_yellow", "red"],
            "3": ["purple", "orange_yellow", "red"],
            "4": ["orange_yellow", "red"]
        }
        if keep_choice not in keep_choices_map:
            print(f"[!] 無效選擇 '{keep_choice}'，已自動使用預設的 [2: 藍色及以上]...")
            keep_choice = "2"

        config["keep_colors"] = keep_choices_map[keep_choice]

        # 2. 選擇可大量分解的最高裝備品質
        print("\n請選擇可【大量分解】的最高裝備品質（該品質及以下在大廳時會被自動大量分解）：")
        print(" 1) 灰色 (普通)")
        print(" 2) 綠色 (優秀)")
        print(" 3) 藍色 (精良) - 預設")
        print(" 4) 紫色 (史詩)")
        print(" 5) 橘黃色 (傳奇)")
        try:
            disassemble_choice = input("請輸入數字 [1-5] (直接 Enter 鍵預設為 3): ").strip()
            if not disassemble_choice:
                disassemble_choice = "3"
        except KeyboardInterrupt:
            print("\n[!] 取消啟動。")
            sys.exit(0)
        except Exception:
            disassemble_choice = "3"

        disassemble_choices_map = {
            "1": ["gray_or_empty"],
            "2": ["gray_or_empty", "green"],
            "3": ["gray_or_empty", "green", "blue"],
            "4": ["gray_or_empty", "green", "blue", "purple"],
            "5": ["gray_or_empty", "green", "blue", "purple", "orange_yellow"]
        }
        if disassemble_choice not in disassemble_choices_map:
            print(f"[!] 無效選擇 '{disassemble_choice}'，已自動使用預設的 [3: 藍色及以下]...")
            disassemble_choice = "3"

        config["disassemble_colors"] = disassemble_choices_map[disassemble_choice]

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
        "common/confirm.png",
        "common/ok.png",
        "common/quit.png"
    ]
    enable_bread = True
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
    else:
        print("[*] 自動領體力功能: 停用 (缺少部分體力相關模板，已自動忽略)")
    print("=" * 60)

    # 初始化模組
    capturer = ScreenCapturer(window_title=args.title, backend_mode=args.backend)
    matcher = TemplateMatcher(templates_dir="templates", template_scale=0.8)
    mouse = MouseController(human_like=True, backend_mode=args.backend)
    
    # 初始化狀態機 (傳入模式配置)
    state_machine = GameStateMachine(capturer=capturer, matcher=matcher, mouse=mouse)
    state_machine.backend_mode = args.backend
    # 建立滑鼠控制器與狀態機的關聯以支援防搶滑鼠保護
    mouse.state_machine = state_machine
    # 將當前配置與體力啟用狀態設定至狀態機中
    state_machine.config = config
    if config["type"] == "bag_clean":
        state_machine.enable_bread = False
        state_machine.need_diamond_collection = False
        state_machine.need_bread_collection = False
    else:
        state_machine.enable_bread = enable_bread

    print("[+] 初始化成功！請確認您的遊戲視窗非最小化，且維持在畫面上。")
    print("[+] 按 [Ctrl + C] 可以隨時終止本程式。")
    print("[*] 將在 3 秒後開始偵測...")
    time.sleep(3)

    try:
        import pyautogui  # 導入 pyautogui 用於滑鼠座標位置監控
        
        # 初始記錄一次滑鼠座標
        state_machine.prev_mouse_pos = pyautogui.position()
        
        while True:
            start_time = time.time()
            
            # 1. 偵測使用者手動介入操作 (滑鼠移動檢測)
            cur_pos = pyautogui.position()
            
            if state_machine.prev_mouse_pos is not None:
                dx = abs(cur_pos[0] - state_machine.prev_mouse_pos[0])
                dy = abs(cur_pos[1] - state_machine.prev_mouse_pos[1])
                
                # 若滑鼠偏移大於 5 像素且腳本在 1.2 秒內無動作，視為手動介入
                if dx > 5 or dy > 5:
                    is_inside = True
                    if getattr(state_machine, "backend_mode", False):
                        rect = state_machine.capturer.get_window_rect()
                        if rect:
                            mx, my = cur_pos
                            is_inside = (rect["left"] <= mx <= rect["left"] + rect["width"] and 
                                         rect["top"] <= my <= rect["top"] + rect["height"])
                        else:
                            is_inside = False

                    if is_inside:
                        last_action_diff = time.time() - state_machine.mouse.last_action_time
                        if last_action_diff > 1.2:
                            if not state_machine.user_operating:
                                logging.warning(f"⚠️ 偵測到使用者手動操作 (滑鼠移動至 {cur_pos})，自動暫停掛機，鎖定目前狀態: [{state_machine.current_state}]。")
                                state_machine.user_operating = True
                            state_machine.last_user_operation_time = time.time()
            
            # 更新滑鼠座標快照
            state_machine.prev_mouse_pos = cur_pos
            
            # 2. 處理手動操作暫停期
            if state_machine.user_operating:
                # 使用者停止操作 3.0 秒後恢復自動掛機
                if time.time() - state_machine.last_user_operation_time > 3.0:
                    logging.info(f"🟢 偵測到使用者已停止手動操作達 3 秒，恢復自動掛機。鎖定狀態: [{state_machine.current_state}]。")
                    state_machine.user_operating = False
                    state_machine.prev_mouse_pos = pyautogui.position() # 防止瞬間重新觸發
                else:
                    # 暫停單步決策，等待 0.05 秒重新檢查
                    time.sleep(0.05)
                    continue
                    
            # 3. 執行自動掛機單步決策
            state_machine.step()
            
            # 計算該步所花費時間，若低於設定的偵測間隔，則補足間隔時間
            elapsed = time.time() - start_time
            sleep_time = max(0.001, args.interval - elapsed)
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
