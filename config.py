# ==================== 全域冷卻時間與模板清單設定 ====================
GLOBAL_SETTINGS = {
    # 非純領取模式下（推圖、刷副本）的資源檢測與領取冷卻時間（秒）
    "default_diamond_cd": 7200.0,  # 預設 2 小時領一次鑽石
    "default_bread_cd": 1800.0,    # 預設 30 分鐘領一次體力
    "default_bless_mode": "combat",  # 預設為戰鬥/傷害祝福
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
        "stamina_retreat_duration": 4.0, # 體力不足退避後，在 collect_only 模式下執行的時間 (小時)
    }
}

STAGE_CONFIGS = {
    "1": {
        "name": "蒼穹平原",
        "entry": "stages/level1_sky_plains.png",
        "sub_stages": {
            "final": "stages/level1_final.png"
        }
    },
    "2": {
        "name": "荒蕪岩地",
        "entry": "stages/level2_barren_rocks.png",
        "sub_stages": {
            "final": "stages/level2_final.png"
        }
    },
    "3": {
        "name": "古樹森林",
        "entry": "stages/level3_ancient_forest.png",
        "sub_stages": {
            "final": "stages/level3_final.png"
        }
    },
    "4": {
        "name": "沙漠廢墟",
        "entry": "stages/level4_desert_ruins.png",
        "sub_stages": {
            "final": "stages/level4_final.png"
        }
    },
    "5": {
        "name": "幽暗沼澤",
        "entry": "stages/level5_gloomy_swamp.png",
        "sub_stages": {
            "final": "stages/level5_final.png"
        }
    },
    "6": {
        "name": "冰雪洞窟",
        "entry": "stages/level6_ice_cave.png",
        "sub_stages": {
            "first": "stages/first_stage.png",
            "middle": "stages/level6_middle.png",
            "six": "stages/six_stage.png",
            "final": "stages/level6_final.png"
        }
    }
}
