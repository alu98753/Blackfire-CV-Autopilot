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
from utils import get_stage_configs

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

def setup_stage_config(config, prompt_prefix=""):
    stage_configs = get_stage_configs()
    print(f"\n{prompt_prefix}請選擇要打的關卡大關：")
    print(" 1) 蒼穹平原 (Level 1)")
    print(" 2) 荒蕪岩地 (Level 2)")
    print(" 3) 古樹森林 (Level 3)")
    print(" 4) 沙漠廢墟 (Level 4)")
    print(" 5) 幽暗沼澤 (Level 5)")
    print(" 6) 冰雪洞窟 (Level 6) - 預設")
    try:
        choice = input("請輸入關卡數字 [1-6] (直接 Enter 鍵預設為 6): ").strip()
        if not choice:
            choice = "6"
    except KeyboardInterrupt:
        print("\n[!] 取消啟動。")
        sys.exit(0)
    except Exception:
        choice = "6"

    if choice not in stage_configs:
        print(f"[!] 無效選擇 '{choice}'，已自動使用預設的第六關 [冰雪洞窟]...")
        choice = "6"

    cfg = stage_configs[choice]
    stage_name = cfg["name"]
    
    # 判斷是否有多個子關卡
    sub_stages = cfg["sub_stages"]
    sub_choice_key = "first" if "first" in sub_stages else "final"  # 預設打第一小關 First Stage
    
    if len(sub_stages) > 1:
        print(f"\n{prompt_prefix}請選擇 [{stage_name}] 要打的小關卡類型：")
        opts = []
        if "first" in sub_stages:
            print(" 1) 第一小關 (First Stage) - 預設")
            opts.append(("1", "first"))
        if "middle" in sub_stages:
            print(" 2) 中間小關 (Middle Stage)")
            opts.append(("2", "middle"))
        if "six" in sub_stages:
            print(" 3) 第六小關 (Six Stage)")
            opts.append(("3", "six"))
        print(" 4) 魔王關 (Boss / Final)")
        opts.append(("4", "final"))
        
        try:
            sub_choice = input("請輸入數字 (直接 Enter 鍵預設為 1): ").strip()
            if not sub_choice:
                sub_choice = "1"
        except KeyboardInterrupt:
            print("\n[!] 取消啟動。")
            sys.exit(0)
        except Exception:
            sub_choice = "1"
            
        matched_key = None
        for opt_num, opt_key in opts:
            if sub_choice == opt_num:
                matched_key = opt_key
                break
        if matched_key is None:
            print(f"[!] 無效選擇 '{sub_choice}'，已自動使用預設的 [第一小關]...")
            matched_key = "first" if "first" in sub_stages else "final"
        sub_choice_key = matched_key

    if sub_choice_key not in sub_stages:
        print(f"\n[!] 錯誤：該關卡 [{stage_name}] 未配置小關卡類型 '{sub_choice_key}'，或找不到對應的模板圖片！")
        sys.exit(1)
        
    fight_entrance = sub_stages[sub_choice_key]
    if not os.path.exists(os.path.join("templates", fight_entrance)):
        print(f"\n[!] 錯誤：找不到該關卡的模板圖片 'templates/{fight_entrance}'，請先使用 crop_tool 進行裁剪！")
        sys.exit(1)

    level_btn = cfg["entry"]
    config["stage_name"] = f"{stage_name} ({sub_choice_key})"
    config["stage_entry"] = level_btn
    config["stage_target"] = fight_entrance
    config["stage_navigation_path"] = [
        "common/door.png",
        "common/select_stage.png",
        level_btn,
        "stages/stage_label.png",
        fight_entrance
    ]
    if config.get("type") == "stage":
        config["name"] = f"普通關卡 - {stage_name} ({sub_choice_key})"
        config["navigation_path"] = [
            "common/door.png",
            "exit_battle.png",
            "common/select_stage.png",
            level_btn,
            "stages/stage_label.png",
            fight_entrance
        ]

def setup_dungeon_config(config, args):
    print("請選擇要探索的地下城：")
    print(" 1) 黏糊糊的石窟 (Slime_entry)")
    print(" 2) 幽影地穴 (Ghost_entry)")
    print(" 3) 森林迷宮 (Forest_entry)")
    print(" 4) 神秘遺跡 (Ruins_entry)")
    print(" 5) 冰雪洞窟 (Ice_entry)")
    print(" 6) 自動貪婪挑選 (Greedy Select) - 預設")
    try:
        choice = input("請輸入地下城數字 [1-6] (直接 Enter 鍵預設為 6): ").strip()
        if not choice:
            choice = "6"
    except KeyboardInterrupt:
        print("\n[!] 取消啟動。")
        sys.exit(0)
    except Exception:
        choice = "6"

    dungeon_map = {
        "1": ("dungeons/Slime_entry.png", "黏糊糊的石窟", False),
        "2": ("dungeons/Ghost_entry.png", "幽影地穴", False),
        "3": ("dungeons/Forest_entry.png", "森林迷宮", False),
        "4": ("dungeons/Ruins_entry.png", "神秘遺跡", False),
        "5": ("dungeons/Ice_entry.png", "冰雪洞窟", False),
        "6": (None, "自動貪婪挑選", True)
    }
    if choice not in dungeon_map:
        print(f"[!] 無效選擇 '{choice}'，已自動使用預設的第六關 [自動貪婪挑選]...")
        choice = "6"

    entry_btn, dungeon_name, is_greedy = dungeon_map[choice]
    config["name"] = f"地下城 - {dungeon_name}"
    config["greedy_dungeon"] = is_greedy
    if is_greedy:
        config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png"]
        
        # 自訂貪婪挑選的關卡篩選
        print("\n你已選擇自動貪婪挑選。請輸入允許打的地下城編號清單（如 135 代表 1、3、5 關；直接 Enter 鍵預設為全部打）：")
        print(" 1) 黏糊糊的石窟 (Slime)")
        print(" 2) 幽影地穴 (Ghost)")
        print(" 3) 森林迷宮 (Forest)")
        print(" 4) 神秘遺跡 (Ruins)")
        print(" 5) 冰雪洞窟 (Ice)")
        try:
            allowed_input = input("👉 請輸入 [1-5] (直接 Enter 預設全部打): ").strip()
            if not allowed_input:
                allowed_indices = [0, 1, 2, 3, 4]
            else:
                allowed_indices = []
                for char in allowed_input:
                    if char in "12345":
                        idx = int(char) - 1
                        if idx not in allowed_indices:
                            allowed_indices.append(idx)
                if not allowed_indices:
                    allowed_indices = [0, 1, 2, 3, 4]
        except KeyboardInterrupt:
            print("\n[!] 取消啟動。")
            sys.exit(0)
        except Exception:
            allowed_indices = [0, 1, 2, 3, 4]
            
        config["greedy_allowed_indices"] = allowed_indices
        allowed_names = [dungeon_map[str(idx+1)][1] for idx in allowed_indices]
        print(f"[*] 貪婪模式允許關卡：{', '.join(allowed_names)}")
    else:
        config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png", entry_btn]

    # 選擇地下城祝福模式
    bless_mode = args.blessmode
    if not bless_mode:
        print("\n請選擇地下城祝福模式：")
        print(" 1) 戰鬥/傷害祝福 (Combat) - 預設")
        print(" 2) 生命祝福 (Life)")
        print(" 3) 經驗祝福 (Exp)")
        try:
            bless_choice = input("請輸入數字 [1-3] (直接 Enter 鍵預設為 1): ").strip()
            if not bless_choice:
                bless_choice = "1"
        except KeyboardInterrupt:
            print("\n[!] 取消啟動。")
            sys.exit(0)
        except Exception:
            bless_choice = "1"

        bless_map = {
            "1": "combat",
            "2": "life",
            "3": "exp"
        }
        if bless_choice not in bless_map:
            print(f"[!] 無效選擇 '{bless_choice}'，已自動使用預設的 [1: 戰鬥/傷害祝福]...")
            config["bless_mode"] = "combat"
        else:
            config["bless_mode"] = bless_map[bless_choice]
        print(f"[*] 戰鬥祝福模式已設定為: {config['bless_mode']}")

    # 選擇體力退避期間是否自動返回地下城
    print("\n當體力耗盡轉入定時領取 (collect_only) 時，若地下城冷卻結束，是否自動返回去刷地下城？")
    print(" 1) 是 (地下城與定時領取來回切換) - 預設")
    print(" 2) 否 (維持定時領取直到滿時間)")
    try:
        auto_resume_choice = input("請輸入數字 [1-2] (直接 Enter 鍵預設為 1): ").strip()
        if not auto_resume_choice:
            auto_resume_choice = "1"
    except KeyboardInterrupt:
        print("\n[!] 取消啟動。")
        sys.exit(0)
    except Exception:
        auto_resume_choice = "1"

    config["auto_resume_dungeon_on_cd"] = (auto_resume_choice == "1")
    if config["auto_resume_dungeon_on_cd"]:
        print("[*] 已啟用：體力退避期間若地下城冷卻結束，將自動切回刷地下城。")
    else:
        print("[*] 未啟用：體力退避期間維持純定時領取，直到滿時間。")

def setup_utf8_encoding():
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

def parse_arguments():
    parser = argparse.ArgumentParser(description="Blackfire Crusade 副本與地下城自動掛機腳本")
    parser.add_argument("--title", type=str, default="Blackfire Crusade", help="遊戲視窗標題")
    parser.add_argument("--interval", type=float, default=0.5, help="畫面偵測間隔秒數 (預設: 0.5)")
    parser.add_argument("--mode", type=str, default="mix", choices=list(GAME_CONFIGS.keys()), 
                        help="掛機模式：mix (混合模式，預設)、dungeon (地下城) 或 stage (普通關卡)")
    parser.add_argument("--backend", action="store_true", help="啟用後台掛機模式 (不搶滑鼠，支援雙螢幕)")
    parser.add_argument("--blessmode", type=str, default=None, choices=["combat", "life", "exp"],
                        help="地下城祝福模式：combat (戰鬥) 或 life (生命) 或 exp (經驗)")
    return parser.parse_args()

def setup_mode_config(args):
    config = GAME_CONFIGS[args.mode].copy()
    config["backend_mode"] = args.backend

    if args.mode == "stage":
        setup_stage_config(config)
    elif args.mode == "dungeon":
        setup_dungeon_config(config, args)
    elif args.mode == "mix":
        setup_dungeon_config(config, args)
        setup_stage_config(config, prompt_prefix="[當地下城冷卻時] ")
        print(f"[*] 當地下城冷卻時Fallback至普通關卡目標：{config['stage_name']} ({config['stage_target']})")
    elif args.mode == "blood_altar":
        print("\n請選擇要獻祭/消耗的血水品質（設定為『否/保留』者將不進行點選獻祭）：")
        print(" 1) 灰、綠、藍獻祭 (紫色保留不賣/不獻祭) - 預設")
        print(" 2) 全部獻祭 (包含紫色)")
        try:
            sac_choice = input("請輸入數字 [1-2] (直接 Enter 鍵預設為 1): ").strip()
            if not sac_choice:
                sac_choice = "1"
        except KeyboardInterrupt:
            print("\n[!] 取消啟動。")
            sys.exit(0)
        except Exception:
            sac_choice = "1"
            
        if sac_choice == "2":
            config["sacrifice_settings"] = {"gray": True, "green": True, "blue": True, "purple": True}
            print("[*] 血水獻祭設定：灰 (✔), 綠 (✔), 藍 (✔), 紫 (✔)")
        else:
            config["sacrifice_settings"] = {"gray": True, "green": True, "blue": True, "purple": False}
            print("[*] 血水獻祭設定：灰 (✔), 綠 (✔), 藍 (✔), 紫 (✖ 保留不獻祭)")
    elif args.mode == "jewelry_workshop":
        print("\n[*] 已選擇 [珠寶加工廠出售] 模式：將自動進入珠寶加工廠並出售所有材料與商品。")
    
    return config

def setup_equipment_config(config):
    if config["type"] in ["collect_only", "blood_altar", "jewelry_workshop"]:
        config["keep_colors"] = []
        config["disassemble_colors"] = []
        return

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

def init_state_machine_system(args, config):
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
    
    # 初始化狀態機
    state_machine = GameStateMachine(capturer=capturer, matcher=matcher, mouse=mouse)
    state_machine.backend_mode = args.backend
    # 建立滑鼠控制器與狀態機的關聯以支援防搶滑鼠保護
    mouse.state_machine = state_machine
    state_machine.config = config

    if config["type"] in ["bag_clean", "blood_altar"]:
        state_machine.enable_bread = False
        state_machine.need_diamond_collection = False
        state_machine.need_bread_collection = False
    else:
        state_machine.enable_bread = enable_bread

    print("[+] 初始化成功！請確認您的遊戲視窗非最小化，且維持在畫面上。")
    print("[+] 按 [Ctrl + C] 可以隨時終止本程式。")
    print("[*] 將在 3 秒後開始偵測...")
    time.sleep(3)
    return state_machine

def run_main_loop(state_machine, interval):
    try:
        import pyautogui
        state_machine.prev_mouse_pos = pyautogui.position()
        
        while True:
            start_time = time.time()
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
            
            state_machine.prev_mouse_pos = cur_pos
            
            if state_machine.user_operating:
                if time.time() - state_machine.last_user_operation_time > 3.0:
                    logging.info(f"🟢 偵測到使用者已停止手動操作達 3 秒，恢復自動掛機。鎖定狀態: [{state_machine.current_state}]。")
                    state_machine.user_operating = False
                    state_machine.prev_mouse_pos = pyautogui.position() # 防止瞬間重新觸發
                else:
                    time.sleep(0.05)
                    continue
                    
            state_machine.step()
            
            elapsed = time.time() - start_time
            sleep_time = max(0.001, interval - elapsed)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print(" 🛑 程式已由使用者中斷。")
        print(f" 📊 統計資訊：")
        print(f"    - 總共啟動戰鬥場次: {state_machine.run_count} 次")
        print("=" * 60)
        sys.exit(0)

def main():
    setup_utf8_encoding()
    args = parse_arguments()
    config = setup_mode_config(args)
    setup_equipment_config(config)
    state_machine = init_state_machine_system(args, config)
    run_main_loop(state_machine, args.interval)

if __name__ == "__main__":
    main()
