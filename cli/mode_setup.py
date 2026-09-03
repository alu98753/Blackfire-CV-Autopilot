"""Interactive mode and equipment configuration assembly."""

import sys

from config import GAME_CONFIGS
from cli.dungeon_setup import setup_dungeon_config
from cli.profile_updates import persist_mode_updates
from cli.prompts import prompt_choice
from cli.stage_setup import setup_stage_config
from cli.tier4_setup import setup_daily_tier4_config

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
    if getattr(args, "enable_demon_lords", None) is not None:
        config["enable_demon_lords"] = args.enable_demon_lords

    # A restarted process must never wait for stdin.  The profile already holds
    # the user's last choices; rebuild only the derived navigation paths.
    if getattr(args, "resume", False) is True:
        if args.mode == "stage":
            setup_stage_config(config, interactive=False)
            config["enable_stage_farming"] = True
        elif args.mode in ["dungeon", "mix"]:
            setup_dungeon_config(config, args, interactive=False)
            if config.get("enable_stage_farming", False):
                setup_stage_config(config, interactive=False)
        elif args.mode == "daily":
            setup_dungeon_config(config, args, interactive=False)
            setup_daily_tier4_config(config, interactive=False)
            config["lobby_start_btn"] = "stages/start.png"
            config["result_buttons"] = ["stages/retry.png", "common/continue.png", "common/continue_gray.png"]
        return config

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
        print("\n[*] 【每日懸賞任務模式】週期活動會優先執行，Tier 4 僅在等待期間長駐：")
        print(f"    地下城：{'啟用' if config.get('enable_dungeon', True) else '停用（Profile TOML / CLI）'}")
        print(f"    Lord：{'啟用' if config.get('enable_lord_boss', True) else '停用（Profile TOML / CLI）'}")
        setup_daily_tier4_config(config)
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
