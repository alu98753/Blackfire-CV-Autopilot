# config.py

GAME_CONFIGS = {
    # ------------------ 普通關卡模式 ------------------
    "stage": {
        "name": "普通關卡",
        "type": "stage",
        # 導航進入路徑 (普通關卡在大廳直接開始，不需尋路)
        "navigation_path": [],
        # 大廳準備按鈕
        "lobby_start_btn": "start.png",
        # 戰鬥結束按鈕 (PK 相似度，挑選最高的點擊)
        "result_buttons": ["retry.png", "continue1.png", "continue2.png", "continue3.png"],
    },
    
    # ------------------ 史萊姆地下城模式 ------------------
    "dungeon_slime": {
        "name": "史萊姆地下城",
        "type": "dungeon",
        # 導航進入路徑：總入口 -> 地下城 -> 史萊姆副本
        "navigation_path": ["door.png", "dungeon.png", "Slime_entry.png"],
        # 進入地下城內每一層戰鬥的入口按鈕
        "dungeon_fight_btn": "dungeon_fight.png",
        # 地下城戰鬥的結算按鈕 (注意：沒有關卡專屬的 continue3.png)
        "dungeon_battle_results": ["continue1.png", "continue2.png"],
        # 地下城探險中 (層與層之間) 畫面所有事件按鈕的優先級 (由高到低比對)
        "explore_priorities": [
            "dungeons_complete.png",       # 1. 地下城通關結束
            "gungeon_godown_confirm.png",   # 2. 確認前進下一層 (注意拼寫：gungeon_godown_confirm.png)
            "gungeon_godown.png",           # 3. 前進下一層 (注意拼寫：gungeon_godown.png)
            "dungeon_fight.png",           # 4. 戰鬥房入口
            "Get_tresure_comfirm.png",     # 5. 獲得寶物確認 (注意拼寫：Get_tresure_comfirm.png)
            "Get_tresure.png",             # 6. 獲得寶物 (注意拼寫：Get_tresure.png)
            "Treasure.png",                # 7. 寶箱房開箱 (注意拼寫：Treasure.png)
            "choice_bless.png",            # 8. 選擇祝福
            "dungeon_bless.png"            # 9. 接受祝福
        ]
    }
}
