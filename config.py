from utils.config_helper import get_stage_configs

# ==================== 全域冷卻時間與模板清單設定 ====================
GLOBAL_SETTINGS = {
    # 非純領取模式下（推圖、刷副本）的資源檢測與領取冷卻時間（秒）
    "default_diamond_cd": 7200.0,  # 預設 2 小時領一次鑽石
    "default_bread_cd": 1800.0,    # 預設 30 分鐘領一次體力
    "default_bless_mode": "combat",  # 預設為戰鬥/傷害祝福
    "default_town_subflow_order": ["blood_altar", "jewelry_workshop"],  # 預設背包清理後連動的城鎮建築順序
    "dry_run_bag_clean": False,  # 安全測試開關：設為 True 時，背包清理不真實點擊分解裝備，保護裝備並續行測試城鎮流水線
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

GAME_CONFIGS = {
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
            "dungeons/gungeon_godown.png"
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
        # 退守普通關卡配置 (預設為第 6 關第一小關)
        "stage_name": "冰雪洞窟 (first)",
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
    
    # ------------------ 背包整理模式 ------------------
    "bag_clean": {
        "name": "背包整理",
        "type": "bag_clean",
        "navigation_path": [],
        "lobby_start_btn": "stages/start.png",
    },
    
    # ------------------ 定時領取麵包與鑽石模式 ------------------
    "collect_only": {
        "name": "定時領取麵包與鑽石",
        "type": "collect_only",
        "navigation_path": [],
        "diamond_cd": 300.0, # 預設 2 小時 (7200秒) 可改為 60.0 進行 1 分鐘測試
        "bread_cd": 300.0,   # 預設 2 小時 (7200秒) 可改為 60.0 進行 1 分鐘測試
        "stamina_retreat_duration": 7.0, # 體力不足退避後，在 collect_only 模式下執行的時間 (小時)
    },

    # ------------------ 血之祭壇獻祭模式 ------------------
    "blood_altar": {
        "name": "血之祭壇獻祭",
        "type": "blood_altar",
        "building_btn": "town_building/Blood_Altar/Blood_Altar.png",
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
                "Warcraft_Fang": False,
                "lizard_skin": True,
                "scrap": True,
            },
            "green": {
                "The_cloth_wrapped_around_the_dead": True,
                "Giant_Beast_Gold_Tooth": True,
            },
            "blue": {},
            "purple": {},
        },
        "goods_dir": "town_building/Jewelry_workshop/goods",
        "navigation_path": [],
        "lobby_start_btn": "stages/start.png",
    }
}

BASE_STAGE_LEVELS = {
    "1": {"name": "蒼穹平原", "entry": "stages/level1_sky_plains.png"},
    "2": {"name": "荒蕪岩地", "entry": "stages/level2_barren_rocks.png"},
    "3": {"name": "古樹森林", "entry": "stages/level3_ancient_forest.png"},
    "4": {"name": "沙漠廢墟", "entry": "stages/level4_desert_ruins.png"},
    "5": {"name": "幽暗沼澤", "entry": "stages/level5_gloomy_swamp.png"},
    "6": {"name": "冰雪洞窟", "entry": "stages/level6_ice_cave.png"},
}

from utils.config_helper import get_stage_configs

# 預設維持匯入時動態讀取 STAGE_CONFIGS
STAGE_CONFIGS = get_stage_configs(BASE_STAGE_LEVELS)
