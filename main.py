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
from config import GAME_CONFIGS, PRIMARY_MODES, STAGE_CONFIGS, normalize_config, SUBFLOW_CONFIGS, get_monitor_index
from utils import get_stage_configs, PauseController
from utils.daily_manager import DailyManager
from utils.steam_launcher import SteamGameLauncher
from utils.window import select_game_window

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

def prompt_choice(prompt_text: str, default_val: str) -> str:
    """Prompt user for input in terminal; return default_val when user presses Enter or on empty/interrupt."""
    try:
        val = input(prompt_text).strip()
        return val if val else default_val
    except (EOFError, KeyboardInterrupt):
        return default_val
    except Exception:
        return default_val


def persist_mode_updates(config, updates: dict) -> None:
    """Write CLI changes back to the TOML table that supplied this mode."""
    from config import get_active_profile, update_profile_config

    mode_key = config.get("_config_mode_key", config.get("type", "mix"))
    update_profile_config(get_active_profile(), {"primary_modes": {mode_key: updates}})

def setup_stage_config(config, prompt_prefix="", stage_level=None, sub_stage_type=None):
    stage_configs = get_stage_configs()
    
    # 1. 取得當前 TOML 的預設大關設定 (預設為 6: 冰凍峽谷)
    default_lvl = str(stage_level) if (stage_level is not None and str(stage_level) in stage_configs) else str(config.get("tier4_stage_level", "6"))
    if default_lvl not in stage_configs:
        default_lvl = "6"

    # 若由 CLI 明確指定 (--stage)，直接套用免詢問
    if stage_level is not None and str(stage_level) in stage_configs:
        choice = str(stage_level)
    else:
        default_name = stage_configs[default_lvl]["name"]
        print(f"\n{prompt_prefix}請選擇要打的關卡大關 (當前 Profile TOML 設定: Level {default_lvl} {default_name})：")
        for lvl_k in sorted(stage_configs.keys(), key=lambda x: int(x)):
            name = stage_configs[lvl_k]["name"]
            mark = " - 當前預設" if lvl_k == default_lvl else ""
            print(f" {lvl_k}) {name} (Level {lvl_k}){mark}")
        choice = prompt_choice(f"請輸入關卡數字 [1-6] (直接 Enter 鍵保持為 {default_lvl}): ", default_lvl)

    if choice not in stage_configs:
        print(f"[!] 無效選擇 '{choice}'，已自動使用預設的 [{stage_configs[default_lvl]['name']}]...")
        choice = default_lvl

    # 檢查是否異動大關
    changed_level = (int(choice) != config.get("tier4_stage_level"))
    config["tier4_stage_level"] = int(choice)

    cfg = stage_configs[choice]
    stage_name = cfg["name"]
    sub_stages = cfg["sub_stages"]

    # 2. 小關選擇
    default_sub = sub_stage_type if (sub_stage_type and sub_stage_type in sub_stages) else config.get("tier4_sub_stage", "first")
    if default_sub not in sub_stages:
        default_sub = "first" if "first" in sub_stages else "final"

    if sub_stage_type is not None and sub_stage_type in sub_stages:
        sub_choice_key = sub_stage_type
    elif len(sub_stages) > 1:
        print(f"\n{prompt_prefix}請選擇 [{stage_name}] 要打的小關卡類型 (當前 Profile TOML 設定: {default_sub})：")
        opts = []
        default_opt_num = "1"
        if "first" in sub_stages:
            opts.append(("1", "first", "第一小關 (First Stage)"))
            if default_sub == "first": default_opt_num = "1"
        if "middle" in sub_stages:
            opts.append(("2", "middle", "中間小關 (Middle Stage)"))
            if default_sub == "middle": default_opt_num = "2"
        if "six" in sub_stages:
            opts.append(("3", "six", "第六小關 (Six Stage)"))
            if default_sub == "six": default_opt_num = "3"
        opts.append(("4", "final", "魔王關 (Boss / Final)"))
        if default_sub == "final": default_opt_num = "4"

        for opt_num, opt_key, opt_label in opts:
            mark = " - 當前預設" if opt_key == default_sub else ""
            print(f" {opt_num}) {opt_label}{mark}")

        sub_choice = prompt_choice(f"請輸入數字 (直接 Enter 鍵保持為 {default_opt_num}: {default_sub}): ", default_opt_num)

        matched_key = None
        for opt_num, opt_key, _ in opts:
            if sub_choice == opt_num or sub_choice.lower() == opt_key.lower():
                matched_key = opt_key
                break
        if matched_key is None:
            print(f"[!] 無效選擇 '{sub_choice}'，已自動使用預設的 [{default_sub}]...")
            matched_key = default_sub
        sub_choice_key = matched_key
    else:
        sub_choice_key = "first" if "first" in sub_stages else "final"

    if sub_choice_key not in sub_stages:
        print(f"\n[!] 錯誤：該關卡 [{stage_name}] 未配置小關卡類型 '{sub_choice_key}'，或找不到對應的模板圖片！")
        sys.exit(1)

    changed_sub = (sub_choice_key != config.get("tier4_sub_stage"))
    config["tier4_sub_stage"] = sub_choice_key

    # 若有異動，同步寫回當前 Profile 的 config.toml
    if changed_level or changed_sub:
        persist_mode_updates(config, {
            "tier4_stage_level": int(choice),
            "tier4_sub_stage": sub_choice_key,
        })

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
    original_settings = {
        key: config.get(key)
        for key in (
            "greedy_dungeon", "tier4_dungeon_index", "greedy_allowed_indices",
            "bless_mode", "auto_resume_dungeon_on_cd",
        )
    }
    configured_index = config.get("tier4_dungeon_index", 4)
    default_dungeon_choice = "6" if config.get("greedy_dungeon", False) else str(configured_index + 1)
    if default_dungeon_choice not in {"1", "2", "3", "4", "5", "6"}:
        default_dungeon_choice = "5"

    print("請選擇要探索的地下城：")
    print(f" 1) 黏糊糊的石窟 (Slime_entry)")
    print(f" 2) 幽影地穴 (Ghost_entry)")
    print(f" 3) 森林迷宮 (Forest_entry)")
    print(f" 4) 神秘遺跡 (Ruins_entry)")
    print(f" 5) 冰雪洞窟 (Ice_entry) {'- 當前預設' if default_dungeon_choice == '5' else ''}")
    print(f" 6) 自動貪婪挑選 (Greedy Select) {'- 當前預設' if default_dungeon_choice == '6' else ''}")
    choice = prompt_choice(f"請輸入地下城數字 [1-6] (直接 Enter 鍵保持為 {default_dungeon_choice}): ", default_dungeon_choice)

    dungeon_map = {
        "1": ("dungeons/Slime_entry.png", "黏糊糊的石窟", False),
        "2": ("dungeons/Ghost_entry.png", "幽影地穴", False),
        "3": ("dungeons/Forest_entry.png", "森林迷宮", False),
        "4": ("dungeons/Ruins_entry.png", "神秘遺跡", False),
        "5": ("dungeons/Ice_entry.png", "冰雪洞窟", False),
        "6": (None, "自動貪婪挑選", True)
    }
    if choice not in dungeon_map:
        print(f"[!] 無效選擇 '{choice}'，已自動使用預設的第五關 [冰雪洞窟]...")
        choice = "5"

    entry_btn, dungeon_name, is_greedy = dungeon_map[choice]
    config["name"] = f"地下城 - {dungeon_name}"
    config["greedy_dungeon"] = is_greedy
    if not is_greedy:
        config["tier4_dungeon_index"] = int(choice) - 1
    if is_greedy:
        config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png"]
        
        # 自訂貪婪挑選的關卡篩選
        print("\n你已選擇自動貪婪挑選。請輸入允許打的地下城編號清單（如 135 代表 1、3、5 關；直接 Enter 鍵預設為全部打）：")
        print(" 1) 黏糊糊的石窟 (Slime)")
        print(" 2) 幽影地穴 (Ghost)")
        print(" 3) 森林迷宮 (Forest)")
        print(" 4) 神秘遺跡 (Ruins)")
        print(" 5) 冰雪洞窟 (Ice)")
        configured_allowed = config.get("greedy_allowed_indices", [0, 1, 2, 3, 4])
        default_allowed = "".join(str(index + 1) for index in configured_allowed if index in range(5))
        if not default_allowed:
            default_allowed = "12345"
        allowed_input = prompt_choice(
            f"👉 請輸入 [1-5] (直接 Enter 保留 {default_allowed}): ", default_allowed
        )
        allowed_indices = []
        for char in allowed_input:
            if char in "12345":
                idx = int(char) - 1
                if idx not in allowed_indices:
                    allowed_indices.append(idx)
        if not allowed_indices:
            allowed_indices = [0, 1, 2, 3, 4]
            
        config["greedy_allowed_indices"] = allowed_indices
        allowed_names = [dungeon_map[str(idx+1)][1] for idx in allowed_indices]
        print(f"[*] 貪婪模式允許關卡：{', '.join(allowed_names)}")
    else:
        config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png", entry_btn]

    # 選擇地下城祝福模式
    bless_mode = args.blessmode
    if not bless_mode:
        current_bless = config.get("bless_mode", "combat")
        default_bless_num = {"combat": "1", "life": "2", "exp": "3"}.get(current_bless, "1")
        print(f"\n請選擇地下城祝福模式 (當前 Profile TOML 設定: {current_bless})：")
        print(f" 1) 戰鬥/傷害祝福 (Combat) {'- 當前預設' if current_bless == 'combat' else ''}")
        print(f" 2) 生命祝福 (Life) {'- 當前預設' if current_bless == 'life' else ''}")
        print(f" 3) 經驗祝福 (Exp) {'- 當前預設' if current_bless == 'exp' else ''}")
        bless_choice = prompt_choice(f"請輸入數字 [1-3] (直接 Enter 鍵保持為 {default_bless_num}: {current_bless}): ", default_bless_num)

        bless_map = {
            "1": "combat",
            "2": "life",
            "3": "exp"
        }
        new_bless = bless_map.get(bless_choice, current_bless)
        config["bless_mode"] = new_bless
        print(f"[*] 戰鬥祝福模式已設定為: {config['bless_mode']}")

    # 選擇體力退避期間是否自動返回地下城
    current_resume = config.get("auto_resume_dungeon_on_cd", False)
    default_resume_num = "1" if current_resume else "2"
    print(f"\n當體力耗盡轉入定時領取 (collect_only) 時，若地下城冷卻結束，是否自動返回去刷地下城 (當前 Profile TOML 設定: {'是' if current_resume else '否'})？")
    print(f" 1) 是 (地下城與定時領取來回切換) {'- 當前預設' if current_resume else ''}")
    print(f" 2) 否 (維持定時領取直到滿時間) {'- 當前預設' if not current_resume else ''}")
    auto_resume_choice = prompt_choice(f"請輸入數字 [1-2] (直接 Enter 鍵保持為 {default_resume_num}): ", default_resume_num)

    new_resume = (auto_resume_choice == "1")
    config["auto_resume_dungeon_on_cd"] = new_resume

    changed_settings = {
        key: config[key]
        for key, old_value in original_settings.items()
        if config.get(key) != old_value
    }
    if changed_settings:
        persist_mode_updates(config, changed_settings)

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
    parser.add_argument("--target", type=str, default=None,
                        help="指定控制的遊戲實例 (可傳入編號如 1, 2，別名 native, sandbox，或 HWND 如 0x2707a8)")
    parser.add_argument("--interval", type=float, default=0.5, help="畫面偵測間隔秒數 (預設: 0.5)")
    parser.add_argument("--mode", type=str, default="mix", choices=list(PRIMARY_MODES.keys()), 
                        help="主掛機模式：mix (混合模式，預設)、dungeon (地下城)、stage (普通關卡)、golden_empire (黃金古國領地)、collect_only (純領取)")
    parser.add_argument("--subflow", nargs="+", choices=list(SUBFLOW_CONFIGS.keys()), default=None,
                        help="【Dev 單體測試專用】直接單獨或組合執行城鎮子流程 (如 --subflow blood_altar 或 --subflow jewelry_workshop)")
    parser.add_argument("--backend", action="store_true", help="啟用後台掛機模式 (不搶滑鼠，支援雙螢幕)")
    parser.add_argument("--monitor", "--screen", type=int, default=None,
                        help="指定全螢幕擷取/開遊戲的顯示器編號 (預設: 依據 Profile TOML [global.monitor_index] 設定)")
    parser.add_argument("--blessmode", type=str, default=None, choices=["combat", "life", "exp"],
                        help="地下城祝福模式：combat (戰鬥) 或 life (生命) 或 exp (經驗)")
    # 模組化活動開關參數 (使用 BooleanOptionalAction 自動支援 --xxx 與 --no-xxx)
    parser.add_argument("--boss", dest="enable_lord_boss", action=argparse.BooleanOptionalAction, default=None, help="啟用/停用首領領主討伐 (lord_boss)")
    parser.add_argument("--dungeon", dest="enable_dungeon", action=argparse.BooleanOptionalAction, default=None, help="啟用/停用地下城探索 (dungeon)")
    parser.add_argument("--stage", dest="enable_stage_farming", action=argparse.BooleanOptionalAction, default=None, help="啟用/停用普通關卡打怪 (stage farming)")
    parser.add_argument("--town", dest="enable_town_daily", action=argparse.BooleanOptionalAction, default=None, help="啟用/停用每日城鎮速領 (chest, hero, altar, jewelry)")
    parser.add_argument("--profile", type=str, default=None,
                        help="指定帳號配置名稱 (例如 native, sandbox, acc2)，將自動綁定 user_data/<profile>/ (包含專屬 config.toml 與 daily_status.json)")
    return parser.parse_args()

def resolve_profile_name(args, target_title: str = "") -> str:
    """
    依據 CLI 參數 (--profile, --target) 或視窗標題解析對應的 Profile 名稱 ('native', 'sandbox' 或自訂名稱)。
    - 若傳入 --profile ➔ <profile>
    - 若 --target 為 sandbox 或視窗標題包含 [#] ➔ sandbox
    - 其餘預設 ➔ native
    """
    if getattr(args, "profile", None):
        return args.profile.strip().lower()
    
    target_str = str(getattr(args, "target", "") or "").strip().lower()
    if target_str in ["sandbox", "sandboxed", "box", "sb", "2"] or "[#]" in target_title:
        return "sandbox"
    
    return "native"

# 相容別名
def resolve_status_filename(args, target_title: str = "") -> str:
    profile = resolve_profile_name(args, target_title)
    return f"{profile}/daily_status.json"

def setup_mode_config(args):
    # 若指定了 --subflow，為純城鎮子流程測試，完全不跳出地下城與關卡選單提示！
    if args.subflow:
        target_key = args.subflow[0]
        config = GAME_CONFIGS[target_key].copy()
        config["backend_mode"] = args.backend
        print(f"🛠️ [Dev 測試模式] 直接發起城鎮子流程: {args.subflow} (免選關卡，直通城鎮)")
        return config

    target_key = args.mode
    config = GAME_CONFIGS[target_key].copy()
    # `daily` uses type="mix" at runtime, so retain its TOML table identity.
    config["_config_mode_key"] = target_key
    config["backend_mode"] = args.backend

    # 覆蓋 CLI 明確傳入之活動開關
    if args.enable_lord_boss is not None:
        config["enable_lord_boss"] = args.enable_lord_boss
    if args.enable_dungeon is not None:
        config["enable_dungeon"] = args.enable_dungeon
    if args.enable_stage_farming is not None:
        config["enable_stage_farming"] = args.enable_stage_farming
    if args.enable_town_daily is not None:
        config["enable_town_daily"] = args.enable_town_daily

    if args.mode == "stage":
        setup_stage_config(config)
        config["enable_stage_farming"] = True
    elif args.mode in ["dungeon", "mix"]:
        setup_dungeon_config(config, args)
        if args.enable_stage_farming is None:
            current_farm = config.get("enable_stage_farming", False)
            default_farm_num = "1" if current_farm else "2"
            print("\n當地下城冷卻時，是否要前往普通關卡刷怪？")
            print(f" 1) 是 (前往普通關卡刷怪){' - 目前 TOML 預設' if current_farm else ''}")
            print(f" 2) 否 (回到城鎮待機，零浪費體力){' - 目前 TOML 預設' if not current_farm else ''}")
            stage_farm_choice = prompt_choice(
                f"請輸入數字 [1-2] (直接 Enter 保留 {default_farm_num}): ", default_farm_num
            )
            new_farm = (stage_farm_choice == "1")
            if new_farm != current_farm:
                persist_mode_updates(config, {"enable_stage_farming": new_farm})
            config["enable_stage_farming"] = new_farm
        
        if config.get("enable_stage_farming", False):
            setup_stage_config(config, prompt_prefix="[當地下城冷卻時] ")
            print(f"[*] 當地下城冷卻時Fallback至普通關卡目標：{config.get('stage_name', '')} ({config.get('stage_target', '')})")
        else:
            print("[*] 已設定：當地下城冷卻時回到城鎮待機 (COLLECT_ONLY)，不打小怪。")
    elif args.mode == "collect_only":
        if args.enable_lord_boss is None:
            current_boss = config.get("enable_lord_boss", False)
            default_boss_num = "1" if current_boss else "2"
            print("\n在待機領取期間，若 Boss (首領討伐) 冷卻結束，是否要自動去打 Boss？")
            print(f" 1) 是 (打 Boss + 定時領取){' - 目前 TOML 預設' if current_boss else ''}")
            print(f" 2) 否 (純定時領取待機){' - 目前 TOML 預設' if not current_boss else ''}")
            boss_choice = prompt_choice(
                f"請輸入數字 [1-2] (直接 Enter 保留 {default_boss_num}): ", default_boss_num
            )
            new_boss = (boss_choice == "1")
            if new_boss != current_boss:
                persist_mode_updates(config, {"enable_lord_boss": new_boss})
            config["enable_lord_boss"] = new_boss
            if config["enable_lord_boss"]:
                print("[*] 已啟用：定時待機期間，Boss 冷卻結束將自動前往討伐！")
    elif args.mode == "daily":
        print("\n[*] 【每日懸賞任務模式】設定 Tier 4 退守目標 (當懸賞全清且無 Boss 可打時)：")
        
        # Backend controls game input only; it must never suppress configuration choices.
        setup_dungeon_config(config, args)

        # 2. 是否前往普通關卡刷怪
        current_farm = config.get("enable_stage_farming", True)
        default_farm_num = "1" if current_farm else "2"
        if args.enable_stage_farming is not None:
            config["enable_stage_farming"] = args.enable_stage_farming
        else:
            print(f"\n當所有懸賞任務與地下城皆完成/冷卻時，是否要前往普通關卡刷怪 (當前 Profile TOML 設定: {'是' if current_farm else '否'})？")
            print(f" 1) 是 (前往普通關卡刷怪) {'- 當前預設' if current_farm else ''}")
            print(f" 2) 否 (回到城鎮待機，零浪費體力) {'- 當前預設' if not current_farm else ''}")
            try:
                stage_farm_choice = input(f"請輸入數字 [1-2] (直接 Enter 鍵保持為 {default_farm_num}): ").strip()
                if not stage_farm_choice:
                    stage_farm_choice = default_farm_num
            except KeyboardInterrupt:
                print("\n[!] 取消啟動。")
                sys.exit(0)
            except Exception:
                stage_farm_choice = default_farm_num
            new_farm = (stage_farm_choice == "1")
            if new_farm != config.get("enable_stage_farming"):
                config["enable_stage_farming"] = new_farm
                persist_mode_updates(config, {"enable_stage_farming": new_farm})
            else:
                config["enable_stage_farming"] = new_farm

        if config.get("enable_stage_farming", True):
            setup_stage_config(config, prompt_prefix="[Tier 4 退守關卡] ")
            config["name"] = f"每日懸賞任務 (Tier 4 退守: {config.get('stage_name', '')})"
            print(f"[*] 懸賞任務模式啟動：完成所有懸賞任務後，將自動退守執行【{config.get('stage_name', '')}】。")
        else:
            config["name"] = "每日懸賞任務 (Tier 4 退守: 城鎮待機)"
            print("[*] 懸賞任務模式啟動：完成所有懸賞任務後，將回到城鎮待機 (COLLECT_ONLY)，不打小怪。")
        config["lobby_start_btn"] = "stages/start.png"
        config["result_buttons"] = ["stages/retry.png", "common/continue.png", "common/continue_gray.png"]

    elif args.mode == "golden_empire" or config.get("type") == "domain":
        domain_name = config.get("name", "黃金古國")
        print(f"\n🏛️ [領地模式] 啟動【{domain_name}】自動探索 (每次消耗 3 麵包，含挖寶與戰鬥處理)...")

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
    if config.get("type") in ["collect_only", "blood_altar", "jewelry_workshop", "chest", "lord_boss", "hero_draw"]:
        return

    original_keep_colors = list(config.get("keep_colors", []))
    original_disassemble_colors = list(config.get("disassemble_colors", []))

    keep_choices_map = {
        "1": ["green", "blue", "purple", "orange_yellow", "red"],
        "2": ["blue", "purple", "orange_yellow", "red"],
        "3": ["purple", "orange_yellow", "red"],
        "4": ["orange_yellow", "red"]
    }
    default_keep_choice = next(
        (key for key, colors in keep_choices_map.items() if colors == original_keep_colors), "3"
    )
    print("\n請選擇要【保留/領取】的最低裝備品質（該品質及以上皆會被保留，背包滿時優先拿取）：")
    for key, label in (("1", "綠色 (優秀)"), ("2", "藍色 (精良)"), ("3", "紫色 (史詩)"), ("4", "橘黃色 (傳奇)")):
        print(f" {key}) {label}{' - 目前 TOML 預設' if key == default_keep_choice else ''}")
    keep_choice = prompt_choice(
        f"請輸入數字 [1-4] (直接 Enter 保留 {default_keep_choice}): ", default_keep_choice
    )
    if keep_choice not in keep_choices_map:
        print(f"[!] 無效選擇 '{keep_choice}'，已保留目前 TOML 設定。")
        keep_choice = default_keep_choice

    config["keep_colors"] = keep_choices_map[keep_choice]

    disassemble_choices_map = {
        "1": ["gray_or_empty"],
        "2": ["gray_or_empty", "green"],
        "3": ["gray_or_empty", "green", "blue"],
        "4": ["gray_or_empty", "green", "blue", "purple"],
        "5": ["gray_or_empty", "green", "blue", "purple", "orange_yellow"]
    }
    default_disassemble_choice = next(
        (key for key, colors in disassemble_choices_map.items() if colors == original_disassemble_colors), "4"
    )
    print("\n請選擇可【大量分解】的最高裝備品質（該品質及以下在大廳時會被自動大量分解）：")
    for key, label in (("1", "灰色 (普通)"), ("2", "綠色 (優秀)"), ("3", "藍色 (精良)"), ("4", "紫色 (史詩)"), ("5", "橘黃色 (傳奇)")):
        print(f" {key}) {label}{' - 目前 TOML 預設' if key == default_disassemble_choice else ''}")
    disassemble_choice = prompt_choice(
        f"請輸入數字 [1-5] (直接 Enter 保留 {default_disassemble_choice}): ", default_disassemble_choice
    )
    if disassemble_choice not in disassemble_choices_map:
        print(f"[!] 無效選擇 '{disassemble_choice}'，已保留目前 TOML 設定。")
        disassemble_choice = default_disassemble_choice

    config["disassemble_colors"] = disassemble_choices_map[disassemble_choice]
    updates = {}
    if config["keep_colors"] != original_keep_colors:
        updates["keep_colors"] = config["keep_colors"]
    if config["disassemble_colors"] != original_disassemble_colors:
        updates["disassemble_colors"] = config["disassemble_colors"]
    if updates:
        from config import get_active_profile, update_profile_config
        update_profile_config(get_active_profile(), {"defaults": updates})

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

def run_main_loop(state_machine, interval):
    try:
        import pyautogui
        def on_pause_toggle():
            if state_machine.is_paused:
                pause_duration = state_machine.resume()
                state_machine.prev_mouse_pos = pyautogui.position()
                print("\n" + "=" * 60)
                print(f" ▶️ [RESUMED] 腳本已恢復掛機 (已補償內部防卡死計時器: {pause_duration:.1f} 秒)")
                print(f" 👉 繼續執行狀態: [{state_machine.current_state}]")
                print("=" * 60 + "\n", flush=True)
            else:
                state_machine.pause()
                print("\n" + "=" * 60)
                print(f" ⏸️ [PAUSED] 腳本已手動暫停 (目前狀態: [{state_machine.current_state}])")
                print(f" 👉 在終端機或遊戲視窗 按 [Ctrl + Space] 隨時暫停/繼續 即可恢復自動掛機...")
                print("=" * 60 + "\n", flush=True)

        pause_controller = PauseController(
            capturer=getattr(state_machine, "capturer", None),
            on_toggle=on_pause_toggle
        )
        
        while True:
            start_time = time.time()
            
            # 1. 檢測熱鍵事件標記 (若為非執行緒模式之備用輪詢)
            if pause_controller.check_toggle_triggered() and not pause_controller._thread:
                on_pause_toggle()

            # 2. 若處於手動暫停狀態，進入輕量休眠迴圈，跳過 step()
            if state_machine.is_paused:
                time.sleep(0.05)
                continue

            state_machine.refresh_config_at_safe_point()
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

    # 1. 優先偵測並選擇遊戲視窗實例 (最優先確認目標實例，支援雙開/沙盒自動列舉與目標指定)
    target_hwnd, target_title = select_game_window(target=args.target, auto_prompt=True)
    if target_title:
        args.title = target_title

    # 套用 Profile 專屬配置覆蓋 (如 user_data/sandbox/config.toml)
    profile_name = resolve_profile_name(args, target_title)
    from config import set_active_profile
    set_active_profile(profile_name)

    # 2. 處理模式設定選單 (避免遊戲開啟後停留在 CLI 輸入視窗造成阻塞)
    config = setup_mode_config(args)
    setup_equipment_config(config)

    # 3. 檢查遊戲是否開啟，發起直連啟動並傳送至指定螢幕與最大化全螢幕
    active_monitor = args.monitor if args.monitor is not None else get_monitor_index()
    launcher = SteamGameLauncher(game_title=args.title, backend_mode=args.backend, monitor_index=active_monitor, hwnd=target_hwnd)
    if not launcher.ensure_game_ready():
        print("[!] 遊戲啟動準備失敗，終止腳本。")
        sys.exit(1)

    # 4. 初始化主狀態機並立即運行 (無縫接續執行 LoginFlow 登入與 Click Until 流程)
    state_machine = init_state_machine_system(args, config, target_hwnd=target_hwnd)
    run_main_loop(state_machine, args.interval)

if __name__ == "__main__":
    main()
