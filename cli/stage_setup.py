"""Interactive stage selection and runtime stage-path construction."""

import os
import sys

from cli.profile_updates import persist_mode_updates
from cli.prompts import prompt_choice
from utils import get_stage_configs


def setup_stage_config(config, prompt_prefix="", stage_level=None, sub_stage_type=None, interactive=True):
    """Build stage navigation; non-interactive restarts select persisted defaults."""
    prompt_choice = globals()["prompt_choice"]
    if not interactive:
        prompt_choice = lambda _prompt, default: default
    stage_configs = get_stage_configs()
    default_lvl = str(stage_level) if (stage_level is not None and str(stage_level) in stage_configs) else str(config.get("tier4_stage_level", "6"))
    if default_lvl not in stage_configs:
        default_lvl = "6"

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

    changed_level = int(choice) != config.get("tier4_stage_level")
    config["tier4_stage_level"] = int(choice)
    cfg = stage_configs[choice]
    stage_name = cfg["name"]
    sub_stages = cfg["sub_stages"]
    default_sub = sub_stage_type if (sub_stage_type and sub_stage_type in sub_stages) else config.get("tier4_sub_stage", "first")
    if default_sub not in sub_stages:
        default_sub = "first" if "first" in sub_stages else "final"

    if sub_stage_type is not None and sub_stage_type in sub_stages:
        sub_choice_key = sub_stage_type
    elif len(sub_stages) > 1:
        print(f"\n{prompt_prefix}請選擇 [{stage_name}] 要打的小關卡類型 (當前 Profile TOML 設定: {default_sub})：")
        opts = []
        default_opt_num = "1"
        for opt_num, opt_key, opt_label in (("1", "first", "第一小關 (First Stage)"), ("2", "middle", "中間小關 (Middle Stage)"), ("3", "six", "第六小關 (Six Stage)")):
            if opt_key in sub_stages:
                opts.append((opt_num, opt_key, opt_label))
                if default_sub == opt_key:
                    default_opt_num = opt_num
        opts.append(("4", "final", "魔王關 (Boss / Final)"))
        if default_sub == "final":
            default_opt_num = "4"
        for opt_num, opt_key, opt_label in opts:
            mark = " - 當前預設" if opt_key == default_sub else ""
            print(f" {opt_num}) {opt_label}{mark}")
        sub_choice = prompt_choice(f"請輸入數字 (直接 Enter 鍵保持為 {default_opt_num}: {default_sub}): ", default_opt_num)
        sub_choice_key = next((key for number, key, _ in opts if sub_choice == number or sub_choice.lower() == key.lower()), default_sub)
        if sub_choice_key == default_sub and sub_choice not in {number for number, _, _ in opts} and sub_choice.lower() != default_sub.lower():
            print(f"[!] 無效選擇 '{sub_choice}'，已自動使用預設的 [{default_sub}]...")
    else:
        sub_choice_key = "first" if "first" in sub_stages else "final"

    if sub_choice_key not in sub_stages:
        print(f"\n[!] 錯誤：該關卡 [{stage_name}] 未配置小關卡類型 '{sub_choice_key}'，或找不到對應的模板圖片！")
        sys.exit(1)
    changed_sub = sub_choice_key != config.get("tier4_sub_stage")
    config["tier4_sub_stage"] = sub_choice_key
    if changed_level or changed_sub:
        persist_mode_updates(config, {"tier4_stage_level": int(choice), "tier4_sub_stage": sub_choice_key})
    fight_entrance = sub_stages[sub_choice_key]
    if not os.path.exists(os.path.join("templates", fight_entrance)):
        print(f"\n[!] 錯誤：找不到該關卡的模板圖片 'templates/{fight_entrance}'，請先使用 crop_tool 進行裁剪！")
        sys.exit(1)
    level_btn = cfg["entry"]
    config["stage_name"] = f"{stage_name} ({sub_choice_key})"
    config["stage_entry"] = level_btn
    config["stage_target"] = fight_entrance
    config["stage_navigation_path"] = ["common/door.png", "common/select_stage.png", level_btn, "stages/stage_label.png", fight_entrance]
    if config.get("type") == "stage":
        config["name"] = f"普通關卡 - {stage_name} ({sub_choice_key})"
        config["navigation_path"] = ["common/door.png", "exit_battle.png", "common/select_stage.png", level_btn, "stages/stage_label.png", fight_entrance]
