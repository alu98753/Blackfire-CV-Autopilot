"""
Script to generate the complete Stages and Dungeons documentation from meta_datas.tres.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import json
from meta_data.tres_parser import TresParser

def generate_doc():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(base_dir, "Game_docs", "Combat", "ALL_STAGES_AND_DUNGEONS.md")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    parser = TresParser()
    data = parser.parse()

    lg = data.get("level_groups", {})
    dg = data.get("dungeons", {})
    dm = data.get("domains", {})
    lords = data.get("lords", {})
    demon_lords = data.get("demon_lords", {})

    # Stage names dictionary
    stage_names_zh = {
        "skyward_plains": ("蒼穹平原 (天空平原)", 1),
        "forsaken_stonefield": ("荒蕪岩地 (遺棄石原)", 2),
        "ancient_woodlands": ("古樹森林 (遠古樹林)", 3),
        "desert_ruins": ("沙漠廢墟 (沙漠遺跡)", 4),
        "dark_swamp": ("幽暗沼澤 (黑暗沼澤)", 5),
        "frozen_gorge": ("冰凍峽谷 (冰霜峽谷)", 6),
        "forgotten_wasteland": ("被遺忘的荒原 (遺忘荒地)", 7),
        "fiery_volcano": ("熾熱火山", 8),
        "domain_dead": ("亡者領域 (死者領域)", 9),
        "gate_hell": ("地獄之門", 10),
    }

    # Dungeon names dictionary
    dungeon_names_zh = {
        "slime_cave": ("黏糊糊的石窟 (史萊姆洞窟)", 1),
        "shadowy_abyss": ("幽影地穴 (幽影深淵)", 2),
        "forest_maze": ("森林迷宮", 3),
        "mysterious_ruins": ("神秘遺跡", 4),
        "dark_prison": ("幽暗監獄 (黑暗監獄)", 5),
        "frozen_caverns": ("冰雪洞窟 (冰霜洞窟)", 6),
        "orc_bunker": ("獸人掩體 (獸人地堡)", 7),
        "dragon_lair": ("巨龍之巢", 8),
        "ancient_tomb": ("遠古陵墓 (遠古墓穴)", 9),
        "abyss_hell": ("深淵地獄", 10),
    }

    # Domain names dictionary
    domain_names_zh = {
        "golden_empire": ("黃金帝國", 1),
        "coldoath_citadel": ("冷誓要塞 (寒誓古堡)", 2),
        "abyssbeast_lair": ("深淵獸巢", 3),
        "sunkentide_ruins": ("沉潮廢墟", 4),
        "disordered_ironworks": ("紊亂鐵工廠", 5),
    }

    # Sorted stages
    stage_keys = [k for k, _ in sorted(stage_names_zh.items(), key=lambda x: x[1][1])]
    dungeon_keys = [k for k, _ in sorted(dungeon_names_zh.items(), key=lambda x: x[1][1])]

    doc = []
    w = doc.append

    w("# 🗺️ Blackfire Crusade 全關卡 (Stages) 與地下城 (Dungeons) 完整名稱與變數圖鑑\n")
    w("> 依據遊戲底層核心資料庫 `meta_data/raw_tres/meta_datas.tres` 精確提取編寫，完整收錄主線普通關卡 (`level_groups`)、地下城 (`dungeons`) 之全部名稱、變數識別碼 (ID)、全域機制變數與關聯戰鬥系統。\n")
    w("---\n")

    # 1. 快速導航與全景對應
    w("## 🧭 一、關卡 (Stage) 與地下城 (Dungeon) 1 對 1 階梯對應表\n")
    w("在《Blackfire Crusade》的數值架構中，主線關卡與地下城呈**嚴格的等級階梯推進與前置解鎖關係**：每通關一個主線章節，即可解鎖對應等級區間的地下城。\n\n")
    
    w("| 階級序號 | 主線關卡名稱 (Stage) | 關卡變數 ID | 怪物等級區間 | 推薦戰力 | 解鎖地下城名稱 (Dungeon) | 地下城變數 ID | 地下城等級 | 刷新冷卻 (CD) |\n")
    w("| :---: | :--- | :--- | :---: | :---: | :--- | :--- | :---: | :---: |\n")

    for i in range(10):
        sk = stage_keys[i]
        dk = dungeon_keys[i]
        s_data = lg.get(sk, {})
        d_data = dg.get(dk, {})

        s_zh, s_idx = stage_names_zh[sk]
        d_zh, d_idx = dungeon_names_zh[dk]

        req_p = s_data.get("required_power", "-")
        req_p_str = f"{int(req_p):,}" if isinstance(req_p, (int, float)) else "無限制"
        s_lvl_min = int(s_data["levels"][0]["enemy_level"])
        s_lvl_max = int(s_data["levels"][-1]["enemy_level"])
        s_lvl_str = f"Lv. {s_lvl_min} ~ {s_lvl_max}"

        d_lvl = d_data.get("level", [0, 0])
        d_lvl_str = f"Lv. {int(d_lvl[0])} ~ {int(d_lvl[1])}"

        cd_ms = d_data.get("refresh_time", 0.0)
        cd_min = int(cd_ms / 60000.0)
        cd_str = "即時刷新 (0分)" if cd_min == 0 else f"{cd_min} 分鐘"

        w(f"| **第 {i+1} 階** | **{s_zh}** | `{sk}` | {s_lvl_str} | {req_p_str} | **{d_zh}** | `{dk}` | {d_lvl_str} | {cd_str} |\n")

    w("\n```mermaid\n")
    w("graph TD\n")
    w("    subgraph Stages[\"🏰 主線關卡章節鏈 (Stages)\"]\n")
    w("        S1[\"第1章 蒼穹平原<br>skyward_plains (Lv.0~9)\"] --> S2[\"第2章 荒蕪岩地<br>forsaken_stonefield (Lv.10~19)\"]\n")
    w("        S2 --> S3[\"第3章 古樹森林<br>ancient_woodlands (Lv.20~29)\"]\n")
    w("        S3 --> S4[\"第4章 沙漠廢墟<br>desert_ruins (Lv.30~39)\"]\n")
    w("        S4 --> S5[\"第5章 幽暗沼澤<br>dark_swamp (Lv.40~49)\"]\n")
    w("        S5 --> S6[\"第6章 冰凍峽谷<br>frozen_gorge (Lv.50~59)\"]\n")
    w("        S6 --> S7[\"第7章 被遺忘的荒原<br>forgotten_wasteland (Lv.60~69)\"]\n")
    w("        S7 --> S8[\"第8章 熾熱火山<br>fiery_volcano (Lv.70~79)\"]\n")
    w("        S8 --> S9[\"第9章 亡者領域<br>domain_dead (Lv.80~89)\"]\n")
    w("        S9 --> S10[\"第10章 地獄之門<br>gate_hell (Lv.90~99)\"]\n")
    w("    end\n")
    w("    subgraph Dungeons[\"🕳️ 對應解鎖地下城 (Dungeons)\"]\n")
    w("        D1[\"史萊姆洞窟 (slime_cave)<br>CD: 0分\"]\n")
    w("        D2[\"幽影地穴 (shadowy_abyss)<br>CD: 5分\"]\n")
    w("        D3[\"森林迷宮 (forest_maze)<br>CD: 15分\"]\n")
    w("        D4[\"神秘遺跡 (mysterious_ruins)<br>CD: 20分\"]\n")
    w("        D5[\"幽暗監獄 (dark_prison)<br>CD: 25分\"]\n")
    w("        D6[\"冰雪洞窟 (frozen_caverns)<br>CD: 30分\"]\n")
    w("        D7[\"獸人掩體 (orc_bunker)<br>CD: 35分\"]\n")
    w("        D8[\"巨龍之巢 (dragon_lair)<br>CD: 40分\"]\n")
    w("        D9[\"遠古陵墓 (ancient_tomb)<br>CD: 45分\"]\n")
    w("        D10[\"深淵地獄 (abyss_hell)<br>CD: 50分\"]\n")
    w("    end\n")
    w("    S1 -.->|通關解鎖| D1\n")
    w("    S2 -.->|通關解鎖| D2\n")
    w("    S3 -.->|通關解鎖| D3\n")
    w("    S4 -.->|通關解鎖| D4\n")
    w("    S5 -.->|通關解鎖| D5\n")
    w("    S6 -.->|通關解鎖| D6\n")
    w("    S7 -.->|通關解鎖| D7\n")
    w("    S8 -.->|通關解鎖| D8\n")
    w("    S9 -.->|通關解鎖| D9\n")
    w("    S10 -.->|通關解鎖| D10\n")
    w("```\n\n")

    w("---\n\n")

    # 2. 全域配置變數解析
    w("## ⚙️ 二、底層全域機制變數清單 (Global Variables)\n\n")
    w("在 `meta_datas.tres` 中，關卡與地下城模組均定義了控制機制運算的全域常數：\n\n")

    w("### 1. 主線關卡模組全域變數 (`level_groups`)\n\n")
    w("| 變數名稱 (Variable Key) | 資料型態 | 數值 / 設定值 | 機制作用說明 |\n")
    w("| :--- | :---: | :--- | :--- |\n")
    w("| `battle_coins` | `List[float]` | `[1.0, 2.0]` | 每場普通戰鬥勝利掉落的戰鬥幣 (Battle Coin) 隨機區間 |\n")
    w("| `gold_coins` | `List[float]` | `[5.0, 10.0]` | 每場普通戰鬥勝利掉落的金幣 (Gold Coin) 隨機區間 |\n")
    w("| `food_per_level` | `Dict[str, float]` | `{'normal': 1.0, 'boss': 2.0}` | 關卡體力/麵包消耗：普通子關卡每次消耗 1 點食物，Boss 關卡消耗 2 點食物 |\n")
    w("| `raid_default_price` | `float` | `10.0` | 關卡快速掃蕩 (Raid) 基準消耗/定價 |\n")
    w("| `raid_boss_offset` | `float` | `2.0` | 掃蕩包含 Boss 之關卡時的額外費用加成 |\n")
    w("| `raid_level_offset` | `float` | `0.0` | 關卡等級掃蕩費用增量偏移 |\n")
    w("| `star_rounds` | `List[float]` | `[30.0, 15.0]` | 關卡評星回合門檻：30 回合內通關評 2 星，15 回合內通關評 3 星滿星 |\n\n")

    w("### 2. 地下城模組全域變數 (`dungeons`)\n\n")
    w("| 變數名稱 (Variable Key) | 資料型態 | 數值 / 設定值 | 機制作用說明 |\n")
    w("| :--- | :---: | :--- | :--- |\n")
    w("| `battle_coins` | `List[float]` | `[1.0, 5.0]` | 地下城每場戰鬥勝利掉落的戰鬥幣隨機區間 (1~5 枚) |\n")
    w("| `dungeon_coins` | `List[float]` | `[5.0, 10.0]` | 通關結算時額外給予的地下城代幣隨機區間 |\n")
    w("| `blessings` | `Dict[str, Dict]` | `dam_blessing`, `exp_blessing`, `hp_blessing` | 地下城祭壇三大祝福：傷害+25% (`0.25`)、經驗+25% (`0.25`)、生命+25% (`0.25`) |\n")
    w("| `blessing_prices` | `List[float]` | `[0.0, 20.0, 30.0]` | 祭壇選取祝福的費用曲線：第 1 次免費 (0 幣)，第 2 次 20 幣，第 3 次 30 幣 |\n")
    w("| `skill_card_prices` | `List[float]` | `[0.0, 10.0, 20.0]` | 技能卡牌房購買/抽取技能的費用曲線：第 1 次免費，第 2 次 10 幣，第 3 次 20 幣 |\n")
    w("| `enemy_increase_attr` | `Dict[str, float]` | `{'dam_bouns': 25.0, 'hp_bouns': 50.0}` | 地下城深層 (第 4~5 層) 怪物屬性成長增益：傷害+25%，生命+50% |\n")
    w("| `skip_battle_price_offset` | `float` | `3.0` | 跳過已通關戰鬥房間時的額外代幣費用偏移 |\n")
    w("| `star_max` | `float` | `5.0` | 地下城挑戰最高評價星級 (5 星) |\n")
    w("| `star_unlock` | `float` | `3.0` | 解鎖快速跳過/自動戰鬥特權所需的最低星級 (3 星) |\n\n")

    w("---\n\n")

    # 3. 主線關卡詳細拆解
    w("## 🏰 三、主線普通關卡全 10 大章節詳解 (`level_groups`)\n\n")
    w("每個主線章節固定包含 **10 個子關卡 (Sub-levels, 如 1-1 ~ 1-10)**，並在第 5 關與第 10 關設有小 Boss 與章節大魔王守關。\n\n")

    for i, sk in enumerate(stage_keys, 1):
        s_data = lg.get(sk, {})
        s_zh, _ = stage_names_zh[sk]
        pre = s_data.get("pre_level_group", "none")
        if pre == "none":
            pre_str = "無 (初始第 1 章，直接開放)"
        else:
            pre_zh = stage_names_zh.get(pre, (pre, 0))[0] if pre in stage_names_zh else pre
            pre_str = f"`{pre}` ({pre_zh})"

        star_unlock = s_data.get("star_to_unlock", 0.0)
        req_p = s_data.get("required_power", "無限制")
        raid_p = s_data.get("raid_prices", [0, 0])
        rewards = s_data.get("rewards", [])
        quests = s_data.get("quests", [])
        q_items = s_data.get("quest_items", [])
        levels = s_data.get("levels", [])

        rew_str = ", ".join([f"{int(r.get('count', 0))} {r.get('id')}" for r in rewards]) if rewards else "無"
        quests_str = ", ".join([f"`{q}`" for q in quests]) if quests else "無特定任務"
        q_items_str = ", ".join([f"`{it}`" for it in q_items]) if q_items else "無特殊掉落"

        w(f"### {i}. 【第 {i} 章】{s_zh} (`{sk}`)\n\n")
        w(f"- **變數識別碼 (ID)**：`{sk}`\n")
        w(f"- **前置關卡 (`pre_level_group`)**：{pre_str}\n")
        w(f"- **解鎖所需累計星數 (`star_to_unlock`)**：⭐ **{int(star_unlock)} 星**\n")
        w(f"- **推薦戰力門檻 (`required_power`)**：🛡️ **{int(req_p) if isinstance(req_p, (int, float)) else req_p}**\n")
        w(f"- **掃蕩體力價格 (`raid_prices`)**：普通關 **{int(raid_p[0])}** / 魔王關 **{int(raid_p[1])}** 食物\n")
        w(f"- **滿星章節寶箱 (`rewards`)**：🎁 **{rew_str}**\n")
        w(f"- **關卡掉落任務道具 (`quest_items`)**：{q_items_str}\n")
        w(f"- **關聯懸賞任務 (`quests`)**：{quests_str}\n\n")

        w("#### 📋 10 大子關卡敵方陣容與等級明細表\n\n")
        w("| 子關卡編號 | 敵方等級 (`enemy_level`) | 守關 Boss (`bosses`) | 出沒怪物清單 (`enemies`) |\n")
        w("| :---: | :---: | :--- | :--- |\n")

        for idx, lvl in enumerate(levels, 1):
            elvl = int(lvl.get("enemy_level", 0))
            bosses = lvl.get("bosses", [])
            enemies = lvl.get("enemies", [])

            boss_str = "、".join([f"🔥 **`{b}`**" for b in bosses]) if bosses else "—"
            enemy_str = ", ".join([f"`{e}`" for e in enemies]) if enemies else "無常規怪 (純 Boss 戰)"

            w(f"| **{i}-{idx}** | Lv. {elvl} | {boss_str} | {enemy_str} |\n")

        w("\n---\n\n")

    # 4. 地下城詳細拆解
    w("## 🕳️ 四、10 大地下城全景剖析 (`dungeons`)\n\n")
    w("地下城固定包含 **5 層 (Floors)**，是遊戲中產出金幣、經驗藥水、精華材料、高階飾品圖紙、命運幣與英雄幣的核心場所。\n\n")

    for i, dk in enumerate(dungeon_keys, 1):
        d_data = dg.get(dk, {})
        d_zh, _ = dungeon_names_zh[dk]
        pre = d_data.get("pre_level_group", "無")
        pre_zh = stage_names_zh.get(pre, (pre, 0))[0] if pre in stage_names_zh else pre
        floor = int(d_data.get("floor", 5))
        level_range = d_data.get("level", [0, 0])
        cd_ms = d_data.get("refresh_time", 0.0)
        cd_min = int(cd_ms / 60000.0)
        cd_str = "即時刷新 (0分)" if cd_min == 0 else f"{cd_min} 分鐘 ({int(cd_ms):,} ms)"
        exp_pts = int(d_data.get("expedition_points", 0))
        spec_rooms = d_data.get("special_rooms", [])
        rewards = d_data.get("rewards", [])
        chest = d_data.get("chest_dic", {})
        enemies = d_data.get("enemies", [])
        boss_groups = d_data.get("boss_groups", [])
        quests = d_data.get("quests", [])
        q_items = d_data.get("quest_items", [])

        rew_str = ", ".join([f"{int(r.get('count', 0))} {r.get('id')}" for r in rewards]) if rewards else "無"
        spec_str = ", ".join([f"`{s}`" for s in spec_rooms]) if spec_rooms else "無"
        chest_coins = chest.get("coins", [0, 0])
        chest_items = chest.get("items", [])
        chest_str = f"金幣 `{int(chest_coins[0])}~{int(chest_coins[1])}` 枚；道具池：{', '.join([f'`{it}`' for it in chest_items])}"
        quests_str = ", ".join([f"`{q}`" for q in quests]) if quests else "無特定任務"
        q_items_str = ", ".join([f"`{it}`" for it in q_items]) if q_items else "無特殊掉落"

        w(f"### {i}. 【地下城 No. {i}】{d_zh} (`{dk}`)\n\n")
        w(f"- **變數識別碼 (ID)**：`{dk}`\n")
        w(f"- **前置解鎖主線 (`pre_level_group`)**：`{pre}` ({pre_zh})\n")
        w(f"- **總層數 (`floor`)**：🏛️ **{floor} 層**\n")
        w(f"- **怪物與 Boss 等級 (`level`)**：📊 **Lv. {int(level_range[0])} ~ {int(level_range[1])}**\n")
        w(f"- **通關刷新計時 (`refresh_time`)**：⏳ **{cd_str}**\n")
        w(f"- **遠征活躍點數 (`expedition_points`)**：🎯 **+{exp_pts} 點**\n")
        w(f"- **特殊房間配置 (`special_rooms`)**：{spec_str}\n")
        w(f"- **首次通關獎勵 (`rewards`)**：🎁 **{rew_str}**\n")
        w(f"- **任務關聯 (`quests`)**：{quests_str}\n")
        w(f"- **專屬任務道具 (`quest_items`)**：{q_items_str}\n")
        w(f"- **結算寶箱獎勵庫 (`chest_dic`)**：{chest_str}\n\n")

        w("#### 👾 出沒敵方與首領陣容配置\n\n")
        w(f"* **常規出沒怪物 (`enemies`)**：{', '.join([f'`{e}`' for e in enemies])}\n")
        w("* **Boss 戰隨機陣容池 (`boss_groups`)**：\n")
        for bg in boss_groups:
            bg_id = bg.get("id")
            bg_enemies = bg.get("enemies", [])
            w(f"  - 🔴 首領組合 `{bg_id}`：登場敵方包含 {', '.join([f'`{be}`' for be in bg_enemies])}\n")

        w("\n---\n\n")

    # 5. 延伸戰鬥系統對照
    w("## 🌍 五、關卡與地下城關聯系統延伸 (Related Combat Modes)\n\n")
    w("除常規主線關卡與地下城外，遊戲中兩者深度驅動了以下高階戰鬥系統：\n\n")

    w("### 1. 五大冒險領地 (`domains`)\n\n")
    w("| 領地序號 | 冒險領地名稱 | 變數 ID | 挑戰等級區間 | 解鎖前置主線關卡 / 任務 | 核心首領與隱藏英雄 |\n")
    w("| :---: | :--- | :--- | :---: | :--- | :--- |\n")
    w("| **Domain 1** | **黃金帝國** | `golden_empire` | Lv. 49 ~ 69 | 通關 Stage 6 `frozen_gorge` (`blood_altar_golden_empire`) | 秘銀巫婆、黃金屠拉克、阿爾塔林、金牆守衛 |\n")
    w("| **Domain 2** | **冷誓要塞** | `coldoath_citadel` | Lv. 69 ~ 89 | 通關 Stage 7 `forgotten_wasteland` (`blood_altar_coldoath_citadel`) | 🌟 **寒噬女巫 · 艾卡希雅** (`hero_mage_ecasia`)、霜龍阿祖洛斯 |\n")
    w("| **Domain 3** | **深淵獸巢** | `abyssbeast_lair` | Lv. 79 ~ 99 | 通關 Stage 8 `fiery_volcano` (`blood_altar_abyssbeast_lair`) | 🌟 **深淵暗影 · 維爾贊** (`hero_rogue_vilzaan`)、淵行者戈爾瓦斯 |\n")
    w("| **Domain 4** | **沉潮廢墟** | `sunkentide_ruins` | Lv. 89 ~ 109 | 通關 Stage 9 `domain_dead` (`blood_altar_sunkentide_ruins`) | 🌟 **破浪狂弓 · 奧拉夫** (`hero_archer_olaf`)、深淵噬海獸 |\n")
    w("| **Domain 5** | **紊亂鐵工廠** | `disordered_ironworks` | Lv. 99 ~ 119 | 通關 Stage 10 `gate_hell` (`blood_altar_disordered_ironworks`) | 🌟 **機甲技師 · 格利格** (`hero_knight_glig`)、鐵顎機甲 |\n\n")

    w("### 2. 首領領主討伐 (`lords`)\n\n")
    w("7 大領主討伐全部**嚴格綁定對應前置地下城**的通關狀態：\n\n")
    w("| 領主 ID | 中文名稱 | 等級 | 刷新 CD | 綁定前置地下城變數 (`required_dungeon_id`) |\n")
    w("| :--- | :--- | :---: | :---: | :--- |\n")
    w("| `spider_broodmother` | 育母蜘蛛麗拉西亞 | Lv. 19 | 1 小時 | `shadowy_abyss` (幽影地穴) |\n")
    w("| `wraith_issarion` | 古代惡靈伊瑟倫 | Lv. 39 | 2 小時 | `mysterious_ruins` (神秘遺跡) |\n")
    w("| `ghoul_snow` | 雪山食屍王瓦爾瑪 | Lv. 59 | 3 小時 | `frozen_caverns` (冰雪洞窟) |\n")
    w("| `orc_gul` | 獸人督軍古爾 | Lv. 69 | 3 小時 | `orc_bunker` (獸人掩體) |\n")
    w("| `dragon_krono` | 炎鱗幼龍克羅諾 | Lv. 79 | 3 小時 | `dragon_lair` (巨龍之巢) |\n")
    w("| `sludge_fiend_olg` | 污泥魔物奧爾格 | Lv. 89 | 3 小時 | `ancient_tomb` (遠古陵墓) |\n")
    w("| `demon_samael` | 熔火惡魔薩麥爾 | Lv. 99 | 3 小時 | `abyss_hell` (深淵地獄) |\n\n")

    w("---\n\n")

    # 6. 完整資料庫欄位與變數字典
    w("## 📖 六、資料庫欄位與變數字典 (Full Field Reference)\n\n")
    w("本表收錄於 `meta_datas.tres` 中 `level_groups` 與 `dungeons` 出現的全部底層欄位變數：\n\n")

    w("### `level_groups` 關卡物件欄位字典\n\n")
    w("| 欄位變數名稱 | 資料型態 (Type) | 必填/選填 | 意義與系統用途 |\n")
    w("| :--- | :---: | :---: | :--- |\n")
    w("| `levels` | `List[Dict]` | 必填 | 包含 10 個子關卡陣列，每個元素具備 `enemies`, `bosses`, `enemy_level` |\n")
    w("| `pre_level_group` | `str` | 必填 | 前置章節 ID，首章為 `'none'` |\n")
    w("| `star_to_unlock` | `float` | 必填 (除首章) | 解鎖該章節需達成的全遊戲累計獲得星數 |\n")
    w("| `required_power` | `float` | 選填 | 關卡建議/限制最低綜合戰鬥力 (第 6~10 章啟用) |\n")
    w("| `raid_prices` | `List[float]` | 必填 | 快速掃蕩所需食物消耗 `[普通關, Boss關]` |\n")
    w("| `rewards` | `List[Dict]` | 必填 | 達成該章節 30 星滿星時發放之一次性寶箱 (含 `gem`, `hero_coin`) |\n")
    w("| `quests` | `List[str]` | 選填 | 本關卡包含的常規擊殺懸賞任務清單 |\n")
    w("| `quest_items` | `List[str]` | 選填 | 本關卡掉落的任務特殊道具/憑證變數 ID |\n\n")

    w("### `dungeons` 地下城物件欄位字典\n\n")
    w("| 欄位變數名稱 | 資料型態 (Type) | 必填/選填 | 意義與系統用途 |\n")
    w("| :--- | :---: | :---: | :--- |\n")
    w("| `floor` | `float` | 必填 | 地下城探索總層數，固定為 `5.0` |\n")
    w("| `level` | `List[float]` | 必填 | 敵方等級範圍 `[最低等級, 最高等級]` |\n")
    w("| `pre_level_group` | `str` | 必填 | 前置解鎖之主線關卡變數 ID |\n")
    w("| `refresh_time` | `float` | 必填 | 通關後的冷卻計時 (毫秒 ms) |\n")
    w("| `expedition_points` | `float` | 必填 | 遠征活躍點數獎勵 (1.0 ~ 3.0) |\n")
    w("| `enemies` | `List[str]` | 必填 | 地下城常規遭遇的小怪名單 |\n")
    w("| `boss_groups` | `List[Dict]` | 必填 | 深層隨機 Boss 戰鬥群組 (含 `id` 與陣容 `enemies`) |\n")
    w("| `chest_dic` | `Dict` | 必填 | 結算寶箱金幣範圍 `coins: [min, max]` 與掉落池 `items: List[str]` |\n")
    w("| `rewards` | `List[Dict]` | 必填 | 首次通關寶箱給予之鑽石 (`gem`) 與英雄幣 (`hero_coin`) |\n")
    w("| `special_rooms` | `List[str]` | 必填 | 特殊功能房間類型 (如 `skill_card` 技能卡房) |\n")
    w("| `quests` | `List[str]` | 選填 | 地下城相關之懸賞擊殺任務 |\n")
    w("| `quest_items` | `List[str]` | 選填 | 地下城產出之特定任務道具變數 ID |\n\n")

    w("### 🎮 專案程式碼設定映射 (Project Config Mapping)\n\n")
    w("在專案核心程式碼中，上述關卡與地下城名稱亦由下列設定模組統一定義並進行常數對應：\n")
    w("- `config/defaults.toml`：\n")
    w("  - `[catalog] dungeon_names`：`[\"黏糊糊的石窟\", \"幽影地穴\", \"森林迷宮\", \"神秘遺跡\", \"幽暗監獄\", \"冰雪洞窟\"]` (前 6 大高頻掛機地下城)\n")
    w("  - `[base_stage_levels]`：Stage 1~6 之中文名稱 (`蒼穹平原` ~ `冰凍峽谷`) 與進入點範本圖片範疇\n")
    w("- `utils/dungeon_catalog.py`：地下城 1-based 索引檢索與冷卻木牌評估核心服務\n")
    w("- `utils/quest_mapper.py`：懸賞任務標的派發與關卡/地下城狀態轉換路由\n")

    full_content = "".join(doc)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_content)

    print(f"Successfully generated doc at: {output_path}")
    print(f"Total lines: {len(full_content.splitlines())}, Total bytes: {len(full_content.encode('utf-8'))}")

if __name__ == "__main__":
    generate_doc()
