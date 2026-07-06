# config.py

GAME_CONFIGS = {
    # ------------------ 普通關卡模式 ------------------
    "stage": {
        "name": "普通關卡",
        "type": "stage",
        # 導航進入路徑 (普通關卡在大廳直接開始，不需尋路)
        "navigation_path": [],
        # 大廳準備按鈕
        "lobby_start_btn": "stages/start.png",
        # 戰鬥結束按鈕 (PK 相似度，挑選最高的點擊)
        "result_buttons": ["stages/retry.png", "common/continue1.png", "common/continue2.png", "stages/continue3.png"],
    },
    
    # ------------------ 史萊姆地下城模式 ------------------
    "dungeon_slime": {
        "name": "史萊姆地下城",
        "type": "dungeon",
        # 導航進入路徑：總入口 -> 地下城 -> 史萊姆副本
        "navigation_path": ["dungeons/door.png", "dungeons/dungeon.png", "dungeons/Slime_entry.png"],
        # 進入地下城內每一層戰鬥的入口按鈕
        "dungeon_fight_btn": "dungeons/dungeon_fight.png",
        # 地下城戰鬥的結算按鈕 (注意：沒有關卡專屬的 continue3.png)
        "dungeon_battle_results": ["common/continue1.png", "common/continue2.png"],
        # 地下城探險中 (層與層之間) 畫面所有事件按鈕的優先級 (由高到低比對)
        # 注意：choice_bless.png 必須在 quit.png 之前，確保先點選取祝福，才點擊退出關閉事件！
        "explore_priorities": [
            # === 第一階段：彈窗與對話框處理 (高優先級，必須先解決，否則會卡在畫面上) ===
            "dungeons/dungeons_complete.png",       # 1. 地下城通關結束
            "common/confirm.png",                   # 2. 通用確認彈窗 (如：下樓確認、獲得寶物確認等)
            "common/ok.png",                        # 3. 通用 OK 按鈕 (如：選完祝福後的確認等)
            "dungeons/Get_tresure.png",             # 4. 獲得寶物
            "dungeons/choice_bless.png",            # 5. 選擇祝福 (準備進入戰鬥或接受祝福後的彈窗選項)
            "dungeons/dungeon_fight.png",           # 6. 戰鬥房入口 (優先級調高，避免在入口彈窗誤點 quit 關閉)
            "dungeons/quit.png",                    # 7. 結束/關閉事件彈窗 (例如選擇祝福後的退出按鈕)

            # === 第二階段：地圖格與背景動作 (低優先級，沒有彈窗時才處理) ===
            "dungeons/gungeon_godown.png",           # 8. 前進下一層
            "dungeons/Treasure.png",                # 9. 寶箱房開箱
            "dungeons/dungeon_bless.png"            # 10. 接受祝福
        ]
    }
}
