import os
import logging
from utils.config_helper import get_stage_configs


# ==================== 全域冷卻時間與模板清單設定 ====================
GLOBAL_SETTINGS = {
    # 非純領取模式下（推圖、刷副本）的資源檢測與領取冷卻時間（秒）
    "default_diamond_cd": 7200.0,  # 預設 2 小時領一次鑽石
    "default_bread_cd": 1800.0,    # 預設 30 分鐘領一次體力
    "default_bless_mode": "combat",  # 預設為戰鬥/傷害祝福
    "default_town_subflow_order": ["blood_altar", "jewelry_workshop"],  # 預設背包清理後連動的城鎮建築順序
    "dry_run_bag_clean": False,  # 安全測試開關：設為 True 時，背包清理不真實點擊分解裝備，保護裝備並續行測試城鎮流水線
    # 背包已滿彈窗中向下滾動搜尋與向上復原的最多滾動次數 (預設為 5 次)
    "default_backpack_full_max_scroll": 5,
}

DUNGEON_NAMES = ["黏糊糊的石窟", "幽影地穴", "森林迷宮", "神秘遺跡", "冰雪洞窟"]
DUNGEON_ENTRY_TEMPLATES = [
    "dungeons/Slime_entry.png",
    "dungeons/Ghost_entry.png",
    "dungeons/Forest_entry.png",
    "dungeons/Ruins_entry.png",
    "dungeons/Ice_entry.png"
]
STAGE_TEMPLATES = [
    "stages/level1_sky_plains.png",
    "stages/level2_Barren_Rocky_Ground.png",
    "stages/level2_barren_rocks.png",
    "stages/level3_ancient_forest.png",
    "stages/level4_desert_ruins.png",
    "stages/level5_gloomy_swamp.png"
]

# ==================== 1. 主掛機大局模式 (PRIMARY MODES - 5 個) ====================

PRIMARY_MODES = {
    # ------------------ 普通關卡模式 ------------------
    "stage": {
        "name": "普通關卡",
        "type": "stage",
        "dungeon_names": DUNGEON_NAMES,
        "dungeon_entries": DUNGEON_ENTRY_TEMPLATES,
        "stage_templates": STAGE_TEMPLATES,
        # 導航進入路徑：離開戰鬥 -> 選擇關卡 -> 點選第六關 -> 分關入口 -> 第一小關
        "navigation_path": [
            "common/door.png",
            "exit_battle.png",
            "common/select_stage.png",
            "stages/level6_ice_cave.png",
            "stages/stage_label.png",
            "stages/first_stage.png"
        ],
        # 大廳準備按鈕
        "lobby_start_btn": "stages/start.png",
        # 戰鬥結束按鈕 (PK 相似度，挑選最高的點擊)
        "result_buttons": ["stages/retry.png", "common/continue.png", "common/continue_gray.png"],
        # 普通關卡最大戰敗次數限制
        "stage_max_defeat": 2,
    },
    
    # ------------------ 地下城模式 ------------------
    "dungeon": {
        "name": "地下城",
        "type": "dungeon",
        "dungeon_names": DUNGEON_NAMES,
        "dungeon_entries": DUNGEON_ENTRY_TEMPLATES,
        "stage_templates": STAGE_TEMPLATES,
        "bless_mode": "combat",  # 預設為戰鬥/傷害祝福
        "cooldown_map": {0: 0.0, 1: 300.0, 2: 900.0, 3: 1200.0, 4: 1800.0},
        "greedy_dungeon": True,
        "greedy_allowed_indices": [0, 1, 2, 3, 4],  # 預設允許全部地下城 [0, 1, 2, 3, 4]
        "auto_resume_dungeon_on_cd": False,  # 體力退避期間若地下城冷卻結束，是否自動切回刷地下城
        # 導航進入路徑：總入口 -> 地下城 -> 史萊姆副本
        "navigation_path": ["common/door.png", "dungeons/dungeon.png", "dungeons/Slime_entry.png"],
        # 進入地下城內每一層戰鬥的入口按鈕
        "dungeon_fight_btn": "dungeons/dungeon_fight.png",
        # 地下城戰鬥的結算按鈕 (注意：沒有關卡專屬的 continue3.png)
        "dungeon_battle_results": ["common/continue.png", "common/continue_gray.png"],
        # 地下城探險中 (層與層之間) 畫面所有事件按鈕的優先級 (由高到低比對)
        "explore_priorities": [
            "dungeons/dungeons_complete.png",
            "common/confirm.png",
            "common/continue.png",
            "common/continue_gray.png",
            "dungeons/gungeon_godown_confirm.png",
            "common/ok.png",
            "dungeons/dungeon_fight.png",
            "common/quit.png",
            "dungeons/Treasure.png",
            "dungeons/skill_event.png",
            "dungeons/dungeon_bless.png",
            "dungeons/gungeon_godown.png",
            "dungeons/leave.png"
        ]
    },

    # ------------------ 混合模式 (地下城 + 普通關卡動態切換) ------------------
    "mix": {
        "name": "混合模式",
        "type": "mix",
        "dungeon_names": DUNGEON_NAMES,
        "dungeon_entries": DUNGEON_ENTRY_TEMPLATES,
        "stage_templates": STAGE_TEMPLATES,
        "bless_mode": "combat",  # 預設為戰鬥/傷害祝福
        "cooldown_map": {0: 0.0, 1: 300.0, 2: 900.0, 3: 1200.0, 4: 1800.0},
        "greedy_dungeon": True,
        "greedy_allowed_indices": [0, 1, 2, 3, 4],  # 預設允許全部地下城 [0, 1, 2, 3, 4]
        "auto_resume_dungeon_on_cd": False,  # 體力退避期間若地下城冷卻結束，是否自動切回刷地下城
        "navigation_path": ["common/door.png", "dungeons/dungeon.png", "dungeons/Ice_entry.png"],

        "dungeon_fight_btn": "dungeons/dungeon_fight.png",
        "dungeon_battle_results": ["common/continue.png", "common/continue_gray.png"],
        "explore_priorities": [
            "dungeons/dungeons_complete.png",
            "common/confirm.png",
            "common/continue.png",
            "common/continue_gray.png",
            "dungeons/gungeon_godown_confirm.png",
            "common/ok.png",
            "dungeons/dungeon_fight.png",
            "common/quit.png",
            "dungeons/Treasure.png",
            "dungeons/skill_event.png",
            "dungeons/dungeon_bless.png",
            "dungeons/gungeon_godown.png",
            "dungeons/leave.png"
        ],
        # 退守普通關卡配置 (預設為第 6 關第一小關)
        "stage_name": "冰凍峽谷 (first)",

        "stage_entry": "stages/level6_ice_cave.png",
        "stage_target": "stages/first_stage.png",
        "stage_max_defeat": 2,
        "stage_navigation_path": [
            "common/door.png",
            "common/select_stage.png",
            "stages/level6_ice_cave.png",
            "stages/stage_label.png",
            "stages/first_stage.png"
        ],
        "lobby_start_btn": "stages/start.png",
        "result_buttons": ["stages/retry.png", "common/continue.png", "common/continue_gray.png"],
    },
    
    # ------------------ 定時領取麵包與鑽石模式 ------------------
    "collect_only": {
        "name": "定時領取麵包與鑽石",
        "type": "collect_only",
        "navigation_path": [],
        "diamond_cd": 300.0,
        "bread_cd": 300.0,
        "stamina_retreat_duration": 7,
    },
    # 7hr collect only+dungeon = 203 energy ,可以打 dungeon+stagesix_first  x 小時, 上面數字可以 打一休一共12小時 8.08988764

    # ------------------ 每日懸賞任務動態調度模式 ------------------
    "daily": {
        "name": "每日懸賞任務",

        "type": "mix",
        "dungeon_names": DUNGEON_NAMES,
        "dungeon_entries": DUNGEON_ENTRY_TEMPLATES,
        "stage_templates": STAGE_TEMPLATES,
        "bless_mode": "combat",
        "cooldown_map": {0: 0.0, 1: 300.0, 2: 900.0, 3: 1200.0, 4: 1800.0},
        "greedy_dungeon": True,
        "greedy_allowed_indices": [0, 1, 2, 3, 4],
        "auto_resume_dungeon_on_cd": False,
        "navigation_path": ["common/door.png", "dungeons/dungeon.png", "dungeons/Slime_entry.png"],
        "dungeon_fight_btn": "dungeons/dungeon_fight.png",
        "dungeon_battle_results": ["common/continue.png", "common/continue_gray.png"],
        "explore_priorities": [
            "dungeons/dungeons_complete.png",
            "common/confirm.png",
            "common/continue.png",
            "common/continue_gray.png",
            "dungeons/gungeon_godown_confirm.png",
            "common/ok.png",
            "dungeons/dungeon_fight.png",
            "common/quit.png",
            "dungeons/Treasure.png",
            "dungeons/skill_event.png",
            "dungeons/dungeon_bless.png",
            "dungeons/gungeon_godown.png"
        ],
        "lobby_start_btn": "stages/start.png",
        "result_buttons": ["stages/retry.png", "common/continue.png", "common/continue_gray.png"],
    }
}

# ------------------ 懸賞完成彈窗 (task_complete.png) OCR 裁切框自訂配置 ------------------
# 相對於卷軸圖示 (task.png) 中心的偏移與框大小 (使用者可自由微調)
TASK_BANNER_OCR_OFFSET = {
    "offset_x": 100,    # X 軸水平右移像素 (正數為往右)
    "offset_y": -50,    # Y 軸垂直上移像素 (負數為向上)
    "box_width": 400,   # 裁切框寬度 (像素)
    "box_height": 60,   # 裁切框高度 (像素)
}

# ------------------ 懸賞告示牌清單 (bulletin_board) OCR 裁切框自訂配置 ------------------
# 相對於卷軸圖示 (task.png) 右上角的偏移與框大小 (使用者可自由微調)
BULLETIN_BOARD_OCR_OFFSET = {
    "offset_x": 5,      # X 軸水平右移像素
    "offset_y": -10,     # Y 軸垂直上移像素 (負數為向上)
    "box_width": 360,   # 裁切框寬度 (像素)
    "box_height": 57,   # 裁切框高度 (像素)
}





# ==================== 2. 城鎮子流程獨立配置 (SUBFLOW CONFIGS - 專供 Dev 測試與 08:05 佇列) ====================
# ------------------ 以下為 08:05 每日任務城鎮子流程 (Daily Subflows) ------------------
SUBFLOW_CONFIGS = {
    # ------------------ 背包整理模式 ------------------
    "bag_clean": {
        "enabled": True,
        "name": "背包整理",
        "type": "bag_clean",
        "disassemble_colors": ["gray_or_empty", "green", "blue", "purple"],
        "navigation_path": [],
        "lobby_start_btn": "stages/start.png",
    },

    # ------------------ 血之祭壇獻祭模式 ------------------
    "blood_altar": {
        "enabled": True,
        "name": "血之祭壇獻祭",
        "type": "blood_altar",
        "building_btn": "town_building/Blood_Altar/Blood_Altar.png",
        "receive_entry_btn": "town_building/Blood_Altar/receive_entry.png",
        "receive_daily_btn": "town_building/Blood_Altar/receive_daily.png",
        "sacrifice_btn": "town_building/Blood_Altar/Sacrifice.png",
        "alter_btn": "town_building/Blood_Altar/alter.png",
        "exit_building_btn": "town_building/exitfromhouse_and_to_town.png",
        "sacrifice_settings": {
            "gray": True,
            "green": True,
            "blue": True,
            "purple": False,  # 預設不獻祭/賣紫色血水 (保留)
        },
        "blood_templates": {
            "gray": "town_building/Blood_Altar/gray_blood.png",
            "green": "town_building/Blood_Altar/green_blood.png",
            "blue": "town_building/Blood_Altar/blue_blood.png",
            "purple": "town_building/Blood_Altar/purple_blood.png",
        },
        "navigation_path": [],
        "lobby_start_btn": "stages/start.png",
    },

    # ------------------ 珠寶加工廠出售模式 ------------------
    "jewelry_workshop": {
        "enabled": True,
        "name": "珠寶加工廠出售",
        "type": "jewelry_workshop",
        "building_btn": "town_building/Jewelry_workshop/Jewelry_workshop.png",
        "sell_out_btn": "town_building/sell_out.png",
        "sell_btn": "town_building/sell.png",
        "sell_max_btn": "town_building/sell_max.png",
        "exit_building_btn": "town_building/exitfromhouse_and_to_town.png",
        "goods_settings": {
            "gray": {
                "Sandworm_scales": True,
                "Spider_silk": True,
                "Spider_venom_glands": True,
                "Warcraft_Fang": True,
                "lizard_skin": True,
                "scrap": True,
                "Frog_Skin": True,
                "Purple_Spore": True,
                "Slime_Mucus": True,
                "Bat_wings": True,
                "Wolf_skin": True,
            },
            "green": {
                "The_cloth_wrapped_around_the_dead": True,
                "Giant_Beast_Gold_Tooth": True,
                "Toad_Venom": True,
                "Dead_Soul_Core": True,
                "Wild_boar_tusk": True,
                "Scorpion_Shell": True,
                "Venom_Fang": True,
            },
            "blue": {},
            "purple": {},
        },
        "goods_dir": "town_building/Jewelry_workshop/goods",
        "navigation_path": [],
        "lobby_start_btn": "stages/start.png",
    },

    # ------------------ 首領領主討伐模式 ------------------
    "lord_boss": {
        "enabled": True,
        "name": "首領領主討伐",
        "type": "lord_boss",
        "entry_btn": "load/Lord_entry.png",
        "entry_after_btn": "load/Lord_entry_after.png",
        "bosses": {
            "lord_spider": {
                "name": "育母蜘蛛麗拉西亞",
                "template": "load/lord_spider.png",
                "cooldown_seconds": 3600.0,
            },
            "lord_spectre": {
                "name": "古代惡靈伊瑟倫",
                "template": "load/lord_spectre.png",
                "cooldown_seconds": 7200.0,
            }
        },
        "start_btn": "stages/start.png",
        "result_buttons": ["common/continue.png", "common/continue1.png", "common/continue2.png", "common/continue_gray.png"],
        "navigation_path": [],
    },

    # ------------------ 神秘寶箱模式 (開寶箱) ------------------
    "chest": {
        "enabled": True,
        "name": "神秘寶箱",
        "type": "chest",
        "building_btn": "town_building/mysterious_treasure/mysterious_treasure.png",
        "free_btn": "free.png",
        "navigation_path": [],
        "lobby_start_btn": "stages/start.png",
    },

    # ------------------ 抽英雄模式 (酒館招募) ------------------
    "hero_draw": {
        "enabled": True,  # 抽英雄子流程開關
        "name": "抽英雄",
        "type": "hero_draw",
        "building_btn": "town_building/Tavern/Tavern.png",
        "recruitment_btn": "town_building/Tavern/free_recruitment.png",
        "navigation_path": [],
        "lobby_start_btn": "stages/start.png",
    },

    # ------------------ 懸賞告示牌模式 (領任務) ------------------
    "bulletin_board": {
        "enabled": True,
        "name": "懸賞告示牌",
        "type": "bulletin_board",
        "building_btn": "town_building/bulletin_board/bulletin_board.png",
        "reset_btn": "town_building/bulletin_board/reset.png",
        "accept_btn": "town_building/bulletin_board/accept_task.png",
        "task_after_btn": "town_building/bulletin_board/task_after.png",
        "task_already_full_btn": "town_building/bulletin_board/task_already_full.png",
        "navigation_path": [],
        "lobby_start_btn": "stages/start.png",
    },
}

# ==================== 中央配置規範化 (Centralized Config Normalization) ====================
DEFAULT_DISASSEMBLE_COLORS = ["gray_or_empty", "green", "blue"]
DEFAULT_KEEP_COLORS = ["purple", "orange_yellow", "red"]

def normalize_config(config):
    """
    中央配置規範化器 (Centralized Config Normalizer)
    確保在任何模式 (daily, mix, dungeon, stage, subflow 等) 與啟動管道下，
    config 字典都 100% 擁有精準的 disassemble_colors 與 keep_colors 狀態。
    """
    if not isinstance(config, dict):
        return config

    cfg = config.copy()

    # 特定只做領取/戰鬥不分解裝備的非刷關子流程，保持 disassemble_colors 生效
    if "disassemble_colors" not in cfg or cfg["disassemble_colors"] is None or len(cfg["disassemble_colors"]) == 0:
        cfg["disassemble_colors"] = list(DEFAULT_DISASSEMBLE_COLORS)

    if "keep_colors" not in cfg or cfg["keep_colors"] is None or len(cfg["keep_colors"]) == 0:
        cfg["keep_colors"] = list(DEFAULT_KEEP_COLORS)

    return cfg

# ==================== 3. 統一匯出 (GAME_CONFIGS 向後完全相容) ====================
RAW_GAME_CONFIGS = {**PRIMARY_MODES, **SUBFLOW_CONFIGS}
GAME_CONFIGS = {k: normalize_config(v) for k, v in RAW_GAME_CONFIGS.items()}

BASE_STAGE_LEVELS = {
    "1": {"name": "蒼穹平原", "entry": "stages/level1_sky_plains.png"},
    "2": {"name": "荒蕪岩地", "entry": "stages/level2_barren_rocks.png"},
    "3": {"name": "古樹森林", "entry": "stages/level3_ancient_forest.png"},
    "4": {"name": "沙漠廢墟", "entry": "stages/level4_desert_ruins.png"},
    "5": {"name": "幽暗沼澤", "entry": "stages/level5_gloomy_swamp.png"},
    "6": {"name": "冰凍峽谷", "entry": "stages/level6_ice_cave.png"},

}

from utils.config_helper import get_stage_configs

# 預設維護匯入時動態讀取 STAGE_CONFIGS 並自動進行 normalize_config
STAGE_CONFIGS = {k: normalize_config(v) for k, v in get_stage_configs(BASE_STAGE_LEVELS).items()}

_EXCEPTION_CONFIG_CACHE = None
_EXCEPTION_CONFIG_MTIME = 0.0

def get_exception_features_config():
    """
    動態載入並熱重載 (Hot Reload) config/exception_features.json 設定檔。
    若檔案修改時間 mtime 發生變化自動重新載入。
    """
    global _EXCEPTION_CONFIG_CACHE, _EXCEPTION_CONFIG_MTIME
    json_path = os.path.join("config", "exception_features.json")
    
    default_config = {
        "critical_templates": ["exceptions/Raid_Box.png"],
        "auto_discover_exceptions_dir": "templates/exceptions",
        "mismatch_scan_interval_sec": 30.0,
        "non_battle_stuck_timeout_sec": 30.0,
        "battle_stuck_timeout_sec": 90.0
    }

    if not os.path.exists(json_path):
        return default_config

    try:
        cur_mtime = os.path.getmtime(json_path)
        if _EXCEPTION_CONFIG_CACHE is None or cur_mtime > _EXCEPTION_CONFIG_MTIME:
            with open(json_path, "r", encoding="utf-8") as f:
                import json
                _EXCEPTION_CONFIG_CACHE = json.load(f)
                _EXCEPTION_CONFIG_MTIME = cur_mtime
                logging.info(f"🔄 [HotReload] 已動態加載/更新 config/exception_features.json (mtime: {cur_mtime})")
    except Exception as e:
        logging.warning(f"⚠️ [HotReload] 讀取 exception_features.json 失敗: {e}，回退使用預設設定")
        return default_config

    return _EXCEPTION_CONFIG_CACHE or default_config

def get_critical_exception_templates():
    """
    取得關鍵例外圖示清單。
    支援：
    1. json 內 subflow_feature_mapping 設定之 trigger_template
    2. 自動掃描 templates/exceptions/ 目錄下所有動態新增之 png 圖檔 (Dynamic Auto-Discovery)
    """
    cfg = get_exception_features_config()
    templates = set(cfg.get("critical_templates", []))
    
    mapping = cfg.get("subflow_feature_mapping", {})
    for _, info in mapping.items():
        if isinstance(info, dict) and "trigger_template" in info:
            templates.add(info["trigger_template"])

    exc_dir = cfg.get("auto_discover_exceptions_dir", "templates/exceptions")
    if os.path.exists(exc_dir) and os.path.isdir(exc_dir):
        for fname in os.listdir(exc_dir):
            if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                rel_path = f"exceptions/{fname}"
                templates.add(rel_path)

    return list(templates)

def get_subflow_feature_mapping():
    """
    取得 subflow_name -> trigger_template 映射對照字典。
    """
    cfg = get_exception_features_config()
    return cfg.get("subflow_feature_mapping", {})


