# ==================== 全域冷卻時間設定 ====================
GLOBAL_SETTINGS = {
    # 非純領取模式下（推圖、刷副本）的資源檢測與領取冷卻時間（秒）
    "default_diamond_cd": 7200.0,  # 預設 2 小時領一次鑽石
    "default_bread_cd": 1800.0,    # 預設 30 分鐘領一次體力
}

GAME_CONFIGS = {
    # ------------------ 普通關卡模式 ------------------
    "stage": {
        "name": "普通關卡",
        "type": "stage",
        # 導航進入路徑：離開戰鬥 -> 選擇關卡 -> 點選第二關 -> 分關入口 -> 魔王關入口
        "navigation_path": [
            "common/door.png",
            "exit_battle.png",
            "common/select_stage.png",
            "stages/level2_barren_rocks.png",
            "stages/stage_label.png",
            "stages/level2_final.png"
        ],
        # 大廳準備按鈕
        "lobby_start_btn": "stages/start.png",
        # 戰鬥結束按鈕 (PK 相似度，挑選最高的點擊)
        "result_buttons": ["stages/retry.png", "common/continue.png", "common/continue_gray.png"],
    },
    
    # ------------------ 史萊姆地下城模式 ------------------
    "dungeon_slime": {
        "name": "史萊姆地下城",
        "type": "dungeon",
        # 導航進入路徑：總入口 -> 地下城 -> 史萊姆副本
        "navigation_path": ["common/door.png", "dungeons/dungeon.png", "dungeons/Slime_entry.png"],
        # 進入地下城內每一層戰鬥的入口按鈕
        "dungeon_fight_btn": "dungeons/dungeon_fight.png",
        # 地下城戰鬥的結算按鈕 (注意：沒有關卡專屬的 continue3.png)
        "dungeon_battle_results": ["common/continue.png", "common/continue_gray.png"],
        # 地下城探險中 (層與層之間) 畫面所有事件按鈕的優先級 (由高到低比對)
        # 注意：choice_bless.png 必須在 quit.png 之前，確保先點選取祝福，才點擊退出關閉事件！
        "explore_priorities": [
            # === 第一階段：彈窗與對話框處理 (高優先級，必須先解決，否則會卡在畫面上) ===
            "dungeons/dungeons_complete.png",       # 1. 地下城通關結束
            "common/confirm.png",                   # 2. 通用確認彈窗 (如：下樓確認、獲得寶物確認等)
            "common/continue.png",                  # 結算繼續按鈕 (金色)
            "common/continue_gray.png",             # 結算繼續按鈕 (灰色)
            "dungeons/gungeon_godown_confirm.png",   # 3. 下樓特定確認彈窗
            "common/ok.png",                        # 5. 通用 OK 按鈕 (如：選完祝福後的確認等)
            "dungeons/dungeon_fight.png",           # 9. 戰鬥房入口 (優先級調高，避免在入口彈窗誤點 quit 關閉)
            "common/quit.png",                      # 10. 結束/關閉事件彈窗 (例如選擇祝福後的退出按鈕)

            # === 第二階段：地圖格與背景動作 (低優先級，沒有彈窗時才處理) ===
            "dungeons/Treasure.png",                # 11. 寶箱房開箱 (優先於下樓)
            "dungeons/skill_event.png",             # 12. 技能事件卡片/選項 (優先於下樓)
            "dungeons/dungeon_bless.png",           # 13. 接受祝福 (優先於下樓)
            "dungeons/gungeon_godown.png"           # 14. 前進下一層 (下樓放到最後，確保本層事件做完後才下樓)
        ]
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
