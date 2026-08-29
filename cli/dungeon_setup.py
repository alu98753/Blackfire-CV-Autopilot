"""Interactive dungeon selection and its persisted policy updates."""

from cli.profile_updates import persist_mode_updates
from cli.prompts import prompt_choice

def setup_dungeon_config(config, args):
    original_settings = {
        key: config.get(key)
        for key in (
            "greedy_dungeon", "tier4_dungeon_index", "greedy_allowed_indices",
            "bless_mode", "auto_resume_dungeon_on_cd",
        )
    }
    configured_index = config.get("tier4_dungeon_index", 5)
    default_dungeon_choice = "7" if config.get("greedy_dungeon", False) else str(configured_index + 1)
    if default_dungeon_choice not in {"1", "2", "3", "4", "5", "6", "7"}:
        default_dungeon_choice = "5"

    print("請選擇要探索的地下城：")
    print(f" 1) 黏糊糊的石窟 (Slime_entry)")
    print(f" 2) 幽影地穴 (Ghost_entry)")
    print(f" 3) 森林迷宮 (Forest_entry)")
    print(f" 4) 神秘遺跡 (Ruins_entry)")
    print(f" 5) 幽暗監獄 (dark_prison) {'- 當前預設' if default_dungeon_choice == '5' else ''}")
    print(f" 6) 冰雪洞窟 (Ice_entry) {'- 當前預設' if default_dungeon_choice == '6' else ''}")
    print(f" 7) 自動貪婪挑選 (Greedy Select) {'- 當前預設' if default_dungeon_choice == '7' else ''}")
    choice = prompt_choice(f"請輸入地下城數字 [1-7] (直接 Enter 鍵保持為 {default_dungeon_choice}): ", default_dungeon_choice)

    dungeon_map = {
        "1": ("dungeons/Slime_entry.png", "黏糊糊的石窟", False),
        "2": ("dungeons/Ghost_entry.png", "幽影地穴", False),
        "3": ("dungeons/Forest_entry.png", "森林迷宮", False),
        "4": ("dungeons/Ruins_entry.png", "神秘遺跡", False),
        "5": ("dungeons/dark_prison.png", "幽暗監獄", False),
        "6": ("dungeons/Ice_entry.png", "冰雪洞窟", False),
        "7": (None, "自動貪婪挑選", True)
    }
    if choice not in dungeon_map:
        print(f"[!] 無效選擇 '{choice}'，已自動使用預設的第五關 [幽暗監獄]...")
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
        print(" 5) 幽暗監獄 (Prison)")
        print(" 6) 冰雪洞窟 (Ice)")
        configured_allowed = config.get("greedy_allowed_indices", [0, 1, 2, 3, 4, 5])
        default_allowed = "".join(str(index + 1) for index in configured_allowed if index in range(6))
        if not default_allowed:
            default_allowed = "123456"
        allowed_input = prompt_choice(
            f"👉 請輸入 [1-6] (直接 Enter 保留 {default_allowed}): ", default_allowed
        )
        allowed_indices = []
        for char in allowed_input:
            if char in "123456":
                idx = int(char) - 1
                if idx not in allowed_indices:
                    allowed_indices.append(idx)
        if not allowed_indices:
            allowed_indices = [0, 1, 2, 3, 4, 5]
            
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
