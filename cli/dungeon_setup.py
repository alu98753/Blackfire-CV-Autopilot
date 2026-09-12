"""Interactive dungeon selection and its persisted policy updates."""

from config import DUNGEON_NAMES, DUNGEON_ENTRY_TEMPLATES
from cli.profile_updates import persist_mode_updates
from cli.prompts import prompt_choice
from utils.dungeon_catalog import DungeonCatalog

def setup_dungeon_config(config, args, interactive=True, allow_disable=False):
    """Build runtime paths; supervisor restarts reuse persisted policy values."""
    allow_disable = allow_disable or config.get("_config_mode_key") == "daily"
    prompt_choice = globals()["prompt_choice"]
    if not interactive:
        prompt_choice = lambda _prompt, default: default
    original_settings = {
        key: config.get(key)
        for key in (
            "enable_dungeon", "greedy_dungeon", "tier4_dungeon_index", "greedy_allowed_indices",
            "bless_mode", "auto_resume_dungeon_on_cd",
        )
    }
    num_dungeons = len(DUNGEON_NAMES)
    greedy_choice_str = str(num_dungeons + 1)
    disable_choice_str = str(num_dungeons + 2)

    is_dungeon_enabled = config.get("enable_dungeon", True)
    fallback_index = min(6, num_dungeons) if num_dungeons > 0 else 1
    configured_index = config.get("tier4_dungeon_index", fallback_index)
    if allow_disable and not is_dungeon_enabled:
        default_dungeon_choice = disable_choice_str
    elif config.get("greedy_dungeon", False):
        default_dungeon_choice = greedy_choice_str
    else:
        default_dungeon_choice = str(configured_index)

    valid_choices = {str(i) for i in range(1, num_dungeons + 1)}
    valid_choices.add(greedy_choice_str)
    if allow_disable:
        valid_choices.add(disable_choice_str)

    if default_dungeon_choice not in valid_choices:
        default_dungeon_choice = str(fallback_index)

    print("請選擇要探索的地下城：")
    for idx in range(1, num_dungeons + 1):
        name = DUNGEON_NAMES[idx - 1]
        tmpl = DUNGEON_ENTRY_TEMPLATES[idx - 1] if idx - 1 < len(DUNGEON_ENTRY_TEMPLATES) else ""
        tmpl_short = tmpl.split("/")[-1].replace(".png", "") if tmpl else ""
        is_default = f" - 當前預設" if default_dungeon_choice == str(idx) else ""
        print(f" {idx}) {name} ({tmpl_short}){is_default}")

    is_default_greedy = f" - 當前預設" if default_dungeon_choice == greedy_choice_str else ""
    print(f" {greedy_choice_str}) 自動貪婪挑選 (Greedy Select){is_default_greedy}")
    if allow_disable:
        is_default_disable = f" - 當前預設" if default_dungeon_choice == disable_choice_str else ""
        print(f" {disable_choice_str}) 不打地下城 (停用){is_default_disable}")

    prompt_range = f"[1-{disable_choice_str}]" if allow_disable else f"[1-{greedy_choice_str}]"
    choice = prompt_choice(f"請輸入地下城數字 {prompt_range} (直接 Enter 鍵保持為 {default_dungeon_choice}): ", default_dungeon_choice)

    if allow_disable and choice == disable_choice_str:
        config["enable_dungeon"] = False
        if original_settings.get("enable_dungeon", True) is not False:
            persist_mode_updates(config, {"enable_dungeon": False})
        print("[*] 已設定：停用地下城，每日任務期間將跳過地下城挑戰。")
        return config

    if allow_disable:
        config["enable_dungeon"] = True

    dungeon_map = {}
    for idx in range(1, num_dungeons + 1):
        tmpl = DUNGEON_ENTRY_TEMPLATES[idx - 1] if idx - 1 < len(DUNGEON_ENTRY_TEMPLATES) else ""
        dungeon_map[str(idx)] = (tmpl, DUNGEON_NAMES[idx - 1], False)
    dungeon_map[greedy_choice_str] = (None, "自動貪婪挑選", True)

    if choice not in dungeon_map:
        fallback_str = str(fallback_index)
        print(f"[!] 無效選擇 '{choice}'，已自動使用預設的關卡 [{DUNGEON_NAMES[fallback_index - 1]}]...")
        choice = fallback_str

    entry_btn, dungeon_name, is_greedy = dungeon_map[choice]
    config["name"] = f"地下城 - {dungeon_name}"
    config["greedy_dungeon"] = is_greedy
    if not is_greedy:
        config["tier4_dungeon_index"] = int(choice)
    if is_greedy:
        config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png"]
        
        # 自訂貪婪挑選的關卡篩選
        all_indices = DungeonCatalog.get_all_indices(DUNGEON_NAMES)
        print("\n你已選擇自動貪婪挑選。請輸入允許打的地下城編號清單（如 135 代表 1、3、5 關；直接 Enter 鍵預設為全部打）：")
        for idx in range(1, num_dungeons + 1):
            name = DUNGEON_NAMES[idx - 1]
            tmpl = DUNGEON_ENTRY_TEMPLATES[idx - 1] if idx - 1 < len(DUNGEON_ENTRY_TEMPLATES) else ""
            tmpl_short = tmpl.split("/")[-1].replace(".png", "") if tmpl else ""
            print(f" {idx}) {name} ({tmpl_short})")

        configured_allowed = config.get("greedy_allowed_indices", all_indices)
        default_allowed = "".join(str(index) for index in configured_allowed if 1 <= index <= num_dungeons)
        if not default_allowed:
            default_allowed = "".join(str(index) for index in all_indices)
        allowed_input = prompt_choice(
            f"👉 請輸入 [1-{num_dungeons}] (直接 Enter 保留 {default_allowed}): ", default_allowed
        )
        allowed_indices = []
        for char in allowed_input:
            if char.isdigit():
                idx = int(char)
                if 1 <= idx <= num_dungeons and idx not in allowed_indices:
                    allowed_indices.append(idx)
        if not allowed_indices:
            allowed_indices = list(all_indices)
            
        config["greedy_allowed_indices"] = allowed_indices
        allowed_names = [dungeon_map[str(idx)][1] for idx in allowed_indices]
        print(f"[*] 貪婪模式允許關卡：{', '.join(allowed_names)}")
    else:
        config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png", entry_btn]

    # 選擇地下城祝福模式
    bless_mode = args.blessmode
    if bless_mode:
        config["bless_mode"] = bless_mode
    else:
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

    return config
