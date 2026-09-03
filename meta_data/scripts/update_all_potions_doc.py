"""
Update All Potions Documentation Generator.

Parses meta_data/raw_tres/meta_datas.tres to generate:
1. meta_data/Game_docs/Potion/ALL_POTIONS.md
2. meta_data/dicts/potion_i18n.json

Usage:
    python meta_data/scripts/update_all_potions_doc.py
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from meta_data.tres_parser import TresParser

# Standard translations mapping for all potions, chrisms, and elixirs
POTION_TRANSLATIONS = {
    # === Tier 0 ===
    'hp_potion_1': '初級生命藥水',
    'antidote_potion': '解毒藥水',
    'clarity_potion': '清醒藥水',
    'exp_potion_1': '一階經驗藥水',

    # === Tier 1 ===
    'hp_potion_2': '中級生命藥水',
    'armor_potion': '護甲藥水',
    'plague_potion': '抗瘟疫藥水',
    'exp_potion_2': '二階經驗藥水',

    # === Tier 2 ===
    'hp_potion_3': '高級生命藥水',
    'ap_potion': '行動點藥水',
    'energy_potion': '能量藥水 (SP藥水)',
    'frostshield_potion': '霜盾藥水',
    'frog_eye_potion': '蛙眼閃避藥水',
    'exp_potion_3': '三階經驗藥水',

    # === Tier 3 ===
    'hp_potion_4': '特級生命藥水',
    'hp_potion_abyssal': '深淵生命藥水 (禁忌之水)',
    'hp_potion_expedition': '遠征生命藥水',
    'rage_howl_potion': '狂怒嚎叫藥水',
    'resurrection_potion': '復活神藥',
    'exp_potion_4': '四階經驗藥水',

    # === Tier 4 ===
    'hp_potion_5': '頂級生命藥水',
    'hp_potion_urde': '厄德的眼淚',
    'ap_potion_2': '二階行動點藥水',
    'aqueous_aegis_potion': '水流庇護衝擊藥水',
    'radiant_war_potion': '光輝戰陣藥水',
    'snowbane_potion': '破雪耐火藥水',
    'chrism_thousand_souls': '千魂聖油 (永久魔藥)',
    'exp_potion_5': '五階經驗藥水',

    # === Tier 5 ===
    'abyssal_potion': '深淵狂化藥水',
    'deepone_ichor_potion': '深海者膿血詛咒藥劑',
    'chrism_frostoath': '霜誓聖油 (永久魔藥)',
    'chrism_abyss_broodlord': '深淵巢主聖油 (永久魔藥)',
    'exp_potion_6': '六階經驗藥水',

    # === Tier 6 ===
    'chrism_abyss_elemental': '深淵元素創世聖油 (永久魔藥)',

    # === Tavern Elixirs ===
    'beverage_courage_elixir': '勇氣秘藥 (臨時)',
    'beverage_dead_elixir': '亡者秘藥 (臨時)',
    'beverage_life_elixir': '生命秘藥 (臨時)',
    'beverage_lightness_elixir': '輕盈秘藥 (臨時)',
    'beverage_immortality': '不朽秘藥 (永久)',
    'beverage_phantom': '幻影秘藥 (永久)',
    'beverage_ragestrike': '狂暴秘藥 (永久)',
    'beverage_warrior_draught': '戰士秘藥 (永久)',

    # === Potion Designs ===
    'design_frog_eye_potion': '圖紙：蛙眼閃避藥水',
    'design_rage_howl_potion': '圖紙：狂怒嚎叫藥水',
    'design_aqueous_aegis_potion': '圖紙：水流庇護藥水',
    'design_hp_potion_abyssal': '圖紙：深淵生命藥水',
    'design_radiant_war_potion': '圖紙：光輝戰陣藥水',
    'design_snowbane_potion': '圖紙：破雪耐火藥水',
    'design_abyssal_potion': '圖紙：深淵狂化藥水',
    'design_chrism_frostoath': '圖紙：霜誓聖油',
    'design_chrism_abyss_elemental': '圖紙：深淵元素創世聖油',
}

# Material name mapping for crafting recipes
MATERIAL_NAMES = {
    'bone_powder_basic': '基礎骨粉',
    'bone_powder_enhanced': '強化骨粉',
    'bone_powder_advanced': '高級骨粉',
    'bone_powder_epic': '史詩骨粉',
    'bone_powder_legendary': '傳說骨粉',
    'bone_powder_mystic': '神秘骨粉',
    'monster_blood_1': '魔物血液 (1級)',
    'monster_blood_2': '魔物血液 (2級)',
    'monster_blood_3': '魔物血液 (3級)',
    'monster_blood_4': '魔物血液 (4級)',
    'monster_blood_5': '魔物血液 (5級)',
    'monster_blood_abysscrawler': '深淵爬行者魔血',
    'monster_blood_orc': '獸人之血',
    'spider_venom_gland': '蜘蛛毒腺',
    'purple_spores': '紫色孢子',
    'stoneskin_fruit': '堅石果實',
    'toad_venom': '蟾蜍毒液',
    'vitality_fruit': '活力果實',
    'energy_fruit': '能量果實',
    'frog_eye_crystal': '蛙眼晶石',
    'chillspawn_hatch_fluid': '寒卵孵化液',
    'root_immortality': '不朽之根',
    'suffocating_coral': '窒息珊瑚',
    'deepsea_bubble': '深海氣泡',
    'gilded_blood_tear': '鍍金血淚',
    'snowbane_alkahest': '破雪萬能溶劑',
    'abyssal_tendril_specimen': '深淵觸鬚標本',
    'abyssal_slime': '深淵黏液',
    'bloodstained_letter': '染血信箋',
    'frostbreath_page': '霜息殘頁',
    'essence_4': '四階精華',
    'essence_5': '五階精華',
    'essence_6': '六階精華',
}

TIER_INFO = {
    0: ("0 星 / 白色普通藥劑 (Common)", "⚪ 白色 (0.0 / None)", "初級回血、解毒、清醒與基礎經驗"),
    1: ("1 星 / 綠色優秀藥劑 (Uncommon)", "🟢 綠色 (1.0)", "中級回血、護甲加固、抗瘟疫與進階經驗"),
    2: ("2 星 / 藍色稀有藥劑 (Rare)", "🔵 藍色 (2.0)", "高級回血、行動點(AP)、大招充能(SP)、霜盾結界與全場閃避"),
    3: ("3 星 / 紫色史詩藥劑 (Epic)", "🟣 紫色 (3.0)", "特級回血、遠征雙抗狂怒、禁忌深淵回血、起死回生復活神藥、暴擊傷害雙爆發"),
    4: ("4 星 / 橘黃傳說藥劑 (Legendary)", "🟠 橘/黃色 (4.0)", "頂級回血、AP+2超載、樹人聖泉、水流千傷、光輝戰陣、燃燒免疫與千魂永久魔藥"),
    5: ("5 星 / 橙色神話藥劑 (Mythic)", "🔶 橙色 (5.0)", "深淵種子狂暴藥、深海者敵方全體詛咒毒瓶、霜誓與巢主永久屬性聖油"),
    6: ("6 星 / 紅色遠古創世魔藥 (Ancient)", "🔴 紅色 (6.0)", "深淵元素創世聖油（全6大元素抗性永久+1%終極神藥）")
}


def format_craft(craft_list):
    if not craft_list:
        return "關卡 / 任務 / 首領掉落"
    parts = []
    for ci in craft_list:
        cid = ci.get('id', '')
        cname = MATERIAL_NAMES.get(cid, cid)
        count = int(ci.get('count', 1))
        parts.append(f"{cname} x{count}")
    return "<br>".join(parts)


def format_effects(it):
    parts = []
    if 'hp' in it:
        parts.append(f"❤️ **立即恢復 {int(it['hp'])} 點生命**")
    if 'ap' in it:
        parts.append(f"⚡ **回復 {int(it['ap'])} 點行動點 (AP)**")
    if 'energy' in it:
        parts.append(f"🔥 **回復 {int(it['energy'])} 點能量值 (SP)**")
    if 'armor' in it:
        parts.append(f"🛡️ **物理護甲 +{int(it['armor'])}**")
    if 'armor_m' in it:
        parts.append(f"🔮 **魔法護甲 +{int(it['armor_m'])}**")
    if 'damage' in it:
        parts.append(f"💥 **造成 {int(it['damage'])} 點傷害**")
    if 'exp' in it:
        parts.append(f"📈 **獲得 {int(it['exp'])} 點英雄經驗**")
    if it.get('resurrection'):
        parts.append("✨ **立即復活陣亡隊友 (起死回生)**")
    if it.get('remove_poison'):
        parts.append("🟢 **驅散中毒狀態**")
    if it.get('remove_hallucination'):
        parts.append("🌀 **驅散幻覺混亂狀態**")
    if it.get('remove_plague'):
        parts.append("🟣 **驅散瘟疫腐化狀態**")
    if it.get('remove_fire'):
        parts.append("🔥 **驅散燃燒灼燒狀態**")

    # buffs
    buffs = it.get('buffs', {})
    if 'battle_fury' in buffs:
        parts.append("⚔️ 戰意激盪：傷害提升 +5% (3回合)")
    if 'protection' in buffs:
        parts.append("🛡️ 聖光庇護：受到傷害減免 -5% (3回合)")
    if 'frost_barrier' in buffs:
        parts.append("❄️ 冰霜結界：冰霜抗性 +75%，魔法抗性 +20% (3回合)")
    if 'buff_dodge' in buffs:
        parts.append("💨 閃避增幅：閃避率 +5% (9回合/整場)")
    if 'critical_strike' in buffs:
        parts.append("🎯 致命打擊：暴擊率 +5% (9回合/整場)")
    if 'damage_surge' in buffs:
        r = int(buffs['damage_surge'].get('round', 3))
        parts.append(f"💥 傷害爆發：全傷害 +5% ({r}回合)")
    if 'burn_immunity' in buffs:
        parts.append("🛡️ 燃燒免疫：免疫灼燒 + 額外傷害提升 +25% (9回合)")
    if 'abyss_seed' in buffs:
        parts.append("🌱 深淵種子：暴擊+1%、傷害+1%、免傷+1% (9回合)")
    if 'darkness' in buffs:
        parts.append("👁️ 致盲失明：敵方命中率 -5% (9回合)")
    if 'vulnerability' in buffs:
        parts.append("🩸 易傷詛咒：敵方受傷加深 +5% (9回合)")
    if 'weakness' in buffs:
        parts.append("🥀 虛弱無力：敵方輸出傷害降低 -5% (9回合)")
    if 'trauma' in buffs:
        parts.append("⚠️ 創傷副作用：受傷加深 +5% (3回合)")

    # random buffs
    if 'random_buffs' in it:
        chance = int(it.get('random_buff_chance', 1.0) * 100)
        parts.append(f"🎲 附加負面詛咒 (機率 {chance}%，3~7回合)")

    # permanent attr
    attr = it.get('attr', {})
    if attr:
        attr_parts = []
        for ak, av in attr.items():
            sign = "+" if av > 0 else ""
            unit = "%" if "con" in ak or "res" in ak or "dodge" in ak or "crit" in ak else ""
            attr_parts.append(f"{ak} {sign}{av}{unit}")
        parts.append(f"💎 **永久屬性提升**：{', '.join(attr_parts)}")

    return "<br>".join(parts) if parts else "特殊效果"


def main():
    parser = TresParser()
    data = parser.parse()
    items = data.get('items', {})
    alchemy = data.get('alchemy_hut', {})

    # Save translation dictionary
    dict_dir = os.path.join(BASE_DIR, 'meta_data', 'dicts')
    os.makedirs(dict_dir, exist_ok=True)
    dict_path = os.path.join(dict_dir, 'potion_i18n.json')
    with open(dict_path, 'w', encoding='utf-8') as f:
        json.dump(POTION_TRANSLATIONS, f, ensure_ascii=False, indent=2)
    print(f"[OK] Dictionary saved: {dict_path}")

    # Separate potions by quality tier (0 to 6)
    # Include pure potions and chrism items that are crafted/classified as potions (exclude design drawings)
    potion_candidates = {}
    for k, v in items.items():
        if k.startswith('design_'):
            continue
        cats = v.get('categories', [])
        if 'potion' in cats or 'chrism' in k:
            potion_candidates[k] = v

    tier_map = {0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: []}
    for k, v in potion_candidates.items():
        r = v.get('rarity')
        tier = int(r) if r is not None else 0
        tier_map[tier].append((k, v))

    out = []
    out.append("# 🧪《黑火遠征》全藥水魔藥資料圖鑑手冊 (按品質排序 0~6 星)\n\n")
    out.append("> **依據底層資料庫**：[meta_datas.tres](../../raw_tres/meta_datas.tres) 與 [alchemy_hut](../../raw_tres/meta_datas.tres) 模組  \n")
    out.append("> **涵蓋範圍**：全遊戲 **30 種常規與特殊戰鬥藥水**、**4 種永久屬性聖油魔藥 (`chrism`)**、**8 種冒險者酒館秘藥 (`beverage_*`)** 與 **9 種藥水配方圖紙**。\n")
    out.append("> **排序規則**：嚴格按品質稀有度（Tier 0 ⚪ 白色 ➔ Tier 6 🔴 紅色）依序排列，完整收錄底層變數名稱 (`id`)、繁中名稱、藥效機制、冷卻回合、目標範圍、煉金配方與圖紙要求。\n\n")
    out.append("---\n\n")

    out.append("## 📊 一、全星級藥水規格總覽表\n\n")
    out.append("| 品質階數 | 代表框色 / 數值 (`rarity`) | 藥水種數 | 代表性藥水項目 | 核心功能特色 |\n")
    out.append("| :---: | :---: | :---: | :--- | :--- |\n")
    out.append("| **Tier 0** | ⚪ 白色 (`0.0` / None) | **4 種** | 初級生命藥水、解毒藥水、清醒藥水、1階經驗藥水 | 基礎生命恢復、異常狀態驅散 (毒/幻覺) |\n")
    out.append("| **Tier 1** | 🟢 綠色 (`1.0`) | **4 種** | 中級生命藥水、護甲藥水、抗瘟疫藥水、2階經驗藥水 | 隊伍護甲強化 (+100 Armor)、瘟疫驅散 |\n")
    out.append("| **Tier 2** | 🔵 藍色 (`2.0`) | **6 種** | 高級生命藥水、行動點藥水(AP)、能量藥水(SP)、霜盾藥水、蛙眼藥水、3階經驗藥水 | 核心戰術藥水：補能量立刻放大招、補AP、全隊閃避 |\n")
    out.append("| **Tier 3** | 🟣 紫色 (`3.0`) | **6 種** | 特級生命藥水、深淵生命藥水、遠征生命藥水、狂怒嚎叫藥水、復活神藥、4階經驗藥水 | 起死回生復活亡者、超量回血、暴擊與傷害雙爆發 |\n")
    out.append("| **Tier 4** | 🟠 橘黃 (`4.0`) | **8 種** | 頂級生命藥水、烏爾德聖泉、AP+2、水流衝擊、光輝戰陣、破雪耐火、千魂聖油、5階經驗 | 攻防一體戰陣 (+200雙防)、燃燒免疫、千魂永久生命魔藥 |\n")
    out.append("| **Tier 5** | 🔶 橙色 (`5.0`) | **5 種** | 深淵狂化藥水、深海者膿血詛咒藥劑、霜誓聖油、深淵巢主聖油、6階經驗藥水 | 敵方全體詛咒毒瓶、深淵種子疊加、永久冰霜/傷害聖油 |\n")
    out.append("| **Tier 6** | 🔴 紅色 (`6.0`) | **1 種** | 深淵元素創世聖油 | 終極創世神藥：英雄全6大元素抗性永久 +1% |\n")
    out.append("| **合計** | - | **34 種核心魔藥** | + 8種酒館秘藥 + 9種圖紙 = **全遊戲 51 種藥水相關項目** | 涵蓋戰鬥消耗、戰略爆發與永久數值養成 |\n\n")
    out.append("---\n\n")

    out.append("## 🧪 二、按品質排序之全藥水詳細資料手冊 (Tier 0 ~ Tier 6)\n\n")

    for tier in range(7):
        title, color_badge, desc = TIER_INFO[tier]
        r_items = tier_map[tier]
        out.append(f"### {tier}. 【Tier {tier}】{title}\n\n")
        out.append(f"> 標籤：`rarity: {float(tier)}` | 框色：**{color_badge}** | 收錄 **{len(r_items)}** 種藥劑  \n")
        out.append(f"> 階級特色：{desc}\n\n")
        out.append("| 序號 | 中文名稱 | 底層變數 (`id`) | 類型 / 目標 | 藥效詳細數值與附加效果 | CD / 消耗 | 煉金配方原料 (`craft_items`) | 圖紙要求 |\n")
        out.append("| :---: | :--- | :--- | :--- | :--- | :---: | :--- | :---: |\n")

        for idx, (item_id, it) in enumerate(sorted(r_items, key=lambda x: x[0]), start=1):
            cname = POTION_TRANSLATIONS.get(item_id, item_id)
            cats = it.get('categories', [])
            cat_tag = "聖油(永久)" if 'chrism' in item_id else ("經驗藥水" if 'exp_potion' in cats else ("生命藥水" if 'hp_potion' in cats else "戰術/增益"))
            t_data = it.get('target_data', {})
            target_scope = t_data.get('target', '')
            if t_data.get('party') == 'ally':
                party = "友方陣亡目標" if target_scope == 'dead' else "友方全體"
            elif t_data.get('party') == 'enemy':
                party = "敵方全體"
            else:
                party = "自身/單體"
            type_target = f"`{cat_tag}`<br>{party}" if 'target_data' in it else f"`{cat_tag}`"

            effects = format_effects(it)
            cd = f"{int(it['cool_round'])} 回合" if 'cool_round' in it else "-"
            craft = format_craft(it.get('craft_items'))
            req_draw = "📜 **需圖紙**" if it.get('require_drawing') else "無須圖紙"

            out.append(f"| {idx} | **{cname}** | `{item_id}` | {type_target} | {effects} | {cd} | {craft} | {req_draw} |\n")
        out.append("\n---\n\n")

    # Append Tavern Beverages
    out.append("## 🍻 三、冒險者酒館秘藥系列 (`beverage_*_elixir`，共 8 種)\n\n")
    out.append("在遊戲城鎮的冒險者酒館（`tavern`）中，冒險者可購買特製的秘藥飲品。分為**戰鬥前飲用的臨時藥劑**與**飲用後永久提升數值的永久魔藥**：\n\n")

    out.append("### 1. ⚔️ 戰前臨時秘藥 (Combat Elixirs，戰鬥開始時生效)\n\n")
    out.append("| 變數名稱 (`id`) | 中文名稱 | 品質 | 效果說明 | 獲取方式 |\n")
    out.append("| :--- | :--- | :---: | :--- | :--- |\n")
    out.append("| `beverage_courage_elixir` | **勇氣秘藥** | ⚪ 白色 | 進入戰鬥後附加戰意激發效果，提升開場攻防面板 | 冒險者酒館購買 / 每日任務交付 |\n")
    out.append("| `beverage_dead_elixir` | **亡者秘藥** | ⚪ 白色 | 進入戰鬥後附加冥府抗性，降低受到的暗影/亡靈傷害 | 冒險者酒館購買 / 酒館老闆任務 |\n")
    out.append("| `beverage_life_elixir` | **生命秘藥** | ⚪ 白色 | 進入戰鬥後開場獲得生命護盾，提供額外生命緩衝 | 冒險者酒館購買 |\n")
    out.append("| `beverage_lightness_elixir` | **輕盈秘藥** | ⚪ 白色 | 進入戰鬥後提升前兩回合先攻權與行動速度 | 冒險者酒館購買 |\n\n")

    out.append("### 2. 💎 永久數值秘藥 (Permanent Stat Elixirs，角色永久提升)\n\n")
    out.append("| 變數名稱 (`id`) | 中文名稱 | 品質星級 | 永久提升屬性 | 獲取來源 |\n")
    out.append("| :--- | :--- | :---: | :--- | :--- |\n")
    out.append("| `beverage_immortality` | **不朽秘藥** | 🟠 4.0 傳說 | **生命值上限 +5.0 點 (`hp: +5.0`)** | 頂級聲望任務 / 命運轉盤神話獎勵 |\n")
    out.append("| `beverage_phantom` | **幻影秘藥** | 🟠 4.0 傳說 | **閃避率 +1.0% (`dodge: +1.0%`)** | 刺客工會隱藏委託 / 轉盤獎勵 |\n")
    out.append("| `beverage_ragestrike` | **狂暴秘藥** | 🟠 4.0 傳說 | **暴擊率 +1.0% (`crit: +1.0%`)** | 狂戰士挑戰賽獎勵 / 轉盤獎勵 |\n")
    out.append("| `beverage_warrior_draught` | **戰士秘藥** | 🟠 4.0 傳說 | **基礎攻擊力 +1.0 點 (`damage: +1.0`)** | 競技場霸主榮譽兌換 / 轉盤獎勵 |\n\n")

    out.append("---\n\n")

    # Append Potion Designs
    out.append("## 📜 四、全 9 大藥水配方圖紙總表 (`potion_design`)\n\n")
    out.append("部分 2~6 星高級藥水與創世聖油必須在背包中先使用學習對應的**配方圖紙（Design Drawing）**後，方可在煉金小屋（`alchemy_hut`）進行調製：\n\n")
    out.append("| 品質星級 | 圖紙變數名稱 (`id`) | 中文名稱 | 解鎖調製的目標藥水 | 主要獲取掉落來源 |\n")
    out.append("| :---: | :--- | :--- | :--- | :--- |\n")
    designs = [
        (2.0, 'design_frog_eye_potion', '圖紙：蛙眼閃避藥水', '`frog_eye_potion` (蛙眼藥水)', '第 3 章【迷霧沼澤】青蛙祭司/首領掉落'),
        (3.0, 'design_rage_howl_potion', '圖紙：狂怒嚎叫藥水', '`rage_howl_potion` (狂怒嚎叫藥水)', '第 4 章【沙漠廢墟】獸人軍閥掉落'),
        (4.0, 'design_aqueous_aegis_potion', '圖紙：水流庇護藥水', '`aqueous_aegis_potion` (水流庇護衝擊)', '第 6 章【沉沒神廟】深海巨怪掉落'),
        (4.0, 'design_hp_potion_abyssal', '圖紙：深淵生命藥水', '`hp_potion_abyssal` (深淵生命藥水)', '第 5 章【冰霜峽谷】深淵爬行者掉落'),
        (4.0, 'design_radiant_war_potion', '圖紙：光輝戰陣藥水', '`radiant_war_potion` (光輝戰陣藥水)', '第 7 章【黃金帝國】黃金教派主教掉落'),
        (4.0, 'design_snowbane_potion', '圖紙：破雪耐火藥水', '`snowbane_potion` (破雪耐火藥水)', '第 5 章【冰霜峽谷】雪山鍊金術士掉落'),
        (5.0, 'design_abyssal_potion', '圖紙：深淵狂化藥水', '`abyssal_potion` (深淵狂化藥水)', '地下城【深淵魔境】終極首領掉落'),
        (5.0, 'design_chrism_frostoath', '圖紙：霜誓聖油', '`chrism_frostoath` (霜誓聖油)', '首領討伐【極地霜龍】專屬掉落'),
        (6.0, 'design_chrism_abyss_elemental', '圖紙：深淵元素創世聖油', '`chrism_abyss_elemental` (深淵元素聖油)', '終極世界首領 / 創世寶箱掉落')
    ]
    for r, did, dname, target, src in designs:
        color = TIER_INFO[int(r)][1]
        out.append(f"| **Tier {int(r)}** ({color}) | `{did}` | **{dname}** | {target} | {src} |\n")

    out.append("\n---\n\n")

    # Append Combat Strategy
    out.append("## 💡 五、自動化掛機與高難關卡藥水攜帶實戰建議\n\n")
    out.append("1. **日常掛機自動循環**：\n")
    out.append("   - 優先配置 **`hp_potion_3` (高級生命藥水)** 或 **`hp_potion_4`** 作為自動喝藥槽，性價比最高且材料量產容易。\n")
    out.append("   - 關卡若具備高頻灼燒或中毒，自動化腳本預載 **`antidote_potion` (解毒)** 或 **`snowbane_potion` (破雪耐火)** 能有效防止滅團。\n")
    out.append("2. **衝榜與高難首領突破 (Boss Burst)**：\n")
    out.append("   - **首回合大招流**：開場直接喝 **`energy_potion` (SP +3)**，全體主C首回合立即釋放耗能量大招，秒殺前排小怪！\n")
    out.append("   - **極限雙爆發**：主C喝 **`radiant_war_potion` (+200雙防 & +5%傷害)** 配合 **`rage_howl_potion` (+5%暴擊 & +5%傷害)**，傷害最大化。\n")
    out.append("   - **保底救場**：坦克倒地後，備用槽使用 **`resurrection_potion` (復活神藥)** 瞬間起死回生。\n\n")

    out.append("---\n\n")
    out.append("## 📑 相關文件索引\n\n")
    out.append("- 原始數據來源：[meta_datas.tres](../../raw_tres/meta_datas.tres)\n")
    out.append("- 全材料手冊：[ALL_MATERIALS.md](../Meterial/ALL_MATERIALS.md)\n")
    out.append("- 戰鬥狀態與BUFF總覽：[BUFF_AND_STATUS_EFFECTS_GUIDE.md](../Combat/BUFF_AND_STATUS_EFFECTS_GUIDE.md)\n")

    final_md = "".join(out)
    target_dir = os.path.join(BASE_DIR, 'meta_data', 'Game_docs', 'Potion')
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, 'ALL_POTIONS.md')
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(final_md)

    print(f"[OK] Potion documentation generated: {target_path} ({len(final_md)} bytes)")


if __name__ == "__main__":
    main()
