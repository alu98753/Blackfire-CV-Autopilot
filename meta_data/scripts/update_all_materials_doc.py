"""
Update All Materials Documentation Generator.

Parses meta_data/raw_tres/meta_datas.tres to generate:
1. meta_data/Game_docs/Meterial/ALL_MATERIALS.md
2. meta_data/dicts/material_i18n.json

Usage:
    python meta_data/scripts/update_all_materials_doc.py
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from meta_data.tres_parser import TresParser

# Standard translations mapping for all materials
TRANSLATIONS = {
    # === Tier 0 ===
    'bat_wing': '蝙蝠翅膀',
    'beast_fang': '野獸獠牙',
    'boar_hide': '野豬皮',
    'bone_powder_basic': '基礎骨粉',
    'equipment_scraps': '裝備碎屑',
    'fabric_rough': '粗製布匹',
    'frog_skin': '蛙皮',
    'hard_shell_fragment': '硬殼碎片',
    'hardened_rock_shard': '硬化岩石碎片',
    'ingot_rough': '粗鐵錠',
    'leather_light': '輕皮革',
    'monster_blood_1': '魔物血液 (1級)',
    'purple_spores': '紫色孢子',
    'rough_linen': '粗亞麻',
    'sandworm_scale': '沙蟲鱗片',
    'slime_mucus': '史萊姆黏液',
    'spider_thread': '蜘蛛絲',
    'spider_venom_gland': '蜘蛛毒腺',
    'tough_lizard_hide': '堅韌蜥蜴皮',
    'wolf_pelt': '狼皮',

    # === Tier 1 ===
    'boar_tusk': '野豬獠牙',
    'bone_powder_enhanced': '強化骨粉',
    'dark_slime_mucus': '暗黑史萊姆黏液',
    'fabric_quality': '優質布匹',
    'frost_spider_silk': '霜蛛絲',
    'giant_teeth': '巨人牙齒',
    'gold_fragment_small': '微小黃金碎屑',
    'golden_slime_mucus': '黃金史萊姆黏液',
    'ingot_quality': '優質鋼錠',
    'leather_medium': '中皮革',
    'leopard_hide': '花豹皮',
    'monster_blood_2': '魔物血液 (2級)',
    'petrified_scale': '石化鱗片',
    'resilient_vine': '韌性藤蔓',
    'sand_ore': '沙礦石',
    'scorpion_carapace': '巨蠍甲殼',
    'stoneskin_fruit': '堅石果實 (石皮果)',
    'toad_venom': '蟾蜍毒液',
    'venomfang_panther': '毒牙獵豹獠牙',
    'wraith_cloth': '怨魂碎布',
    'wraith_core': '怨魂核心',

    # === Tier 2 ===
    'bear_bone_fragment': '巨熊碎骨',
    'behemoth_bone': '巨獸之骨',
    'bone_powder_advanced': '高級骨粉',
    'chillspawn_hatch_fluid': '寒卵孵化液',
    'cursed_bone_fragment': '詛咒骨片',
    'demon_horn': '惡魔之角',
    'energy_fruit': '能量果實',
    'evil_soul_shards': '邪靈碎屑',
    'fabric_finely_woven': '精編布匹',
    'frog_eye_crystal': '蛙眼晶石',
    'giant_hide': '巨人毛皮',
    'ice_crystal_shard': '冰晶碎片',
    'ice_fur': '冰原毛皮',
    'ingot_refined': '精煉鋼錠',
    'iron_ore': '鐵礦石',
    'leather_heavy': '重皮革 (厚重皮革)',
    'leather_orc_fragment': '獸人碎皮',
    'monster_blood_3': '魔物血液 (3級)',
    'netherbone_teel': '冥界鐵骨',
    'rune_shard': '符文碎塊',
    'shackled_fragment': '枷鎖碎片',
    'snake_hide': '蛇皮',
    'swamp_cloth': '沼澤織布',
    'thick_bear_hide': '厚熊皮',
    'vitality_fruit': '活力果實',

    # === Tier 3 ===
    'abyssal_slime': '深淵黏液',
    'behemoth_hide': '巨獸毛皮',
    'bloodstained_letter': '染血信箋',
    'bone_powder_epic': '史詩骨粉',
    'broken_gravestone': '殘破墓碑',
    'deepsea_bubble': '深海氣泡',
    'dragonbone': '巨龍之骨 (龍骨)',
    'fabric_iceweave': '冰織布匹',
    'flame_essence': '烈焰精華素材',
    'frost_ore': '冰霜礦石',
    'ghoul_fang': '食屍鬼尖牙',
    'golden_carapace': '黃金甲殼',
    'hell_chain': '地獄之鏈',
    'ingot_demonite': '惡魔金屬錠',
    'ingot_frezon': '冰霜鋼錠 (寒霜鑄塊)',
    'leather_behemoth': '巨獸皮革',
    'monster_blood_4': '魔物血液 (4級)',
    'monster_blood_abysscrawler': '深淵爬行者魔血',
    'monster_blood_orc': '獸人之血',
    'oathlock_chainlink': '誓約鎖環',
    'orc_fang': '獸人獠牙',
    'otherworldly_fruit': '異界果實',
    'plaguehide': '瘟疫之皮',
    'root_immortality': '不朽之根',
    'worn_gear': '磨損齒輪',

    # === Tier 4 ===
    'abyssal_growth_husk': '深淵增生外殼',
    'bone_powder_legendary': '傳說骨粉',
    'dragonscale_fragment': '龍鱗碎片',
    'essence_hatred': '仇恨精華',
    'everfrozen_basalt': '永凍玄武岩',
    'fallen_heart': '墮落之心',
    'flame_ruby': '烈焰紅寶石',
    'frostbitten_feather': '霜凍之羽',
    'frostbreath_page': '霜息殘頁',
    'gilded_blood_tear': '鍍金血淚',
    'gold_fragments': '黃金碎塊',
    'ingot_gold': '黃金鑄塊',
    'ingot_hellfire': '地獄火鋼錠',
    'ingot_molten': '熔岩鋼錠 (熔火鑄塊)',
    'ingot_oathbound': '誓約鋼錠',
    'lava_ore': '熔岩礦石',
    'leather_orc': '獸人皮革',
    'micro_battery': '微型電池',
    'monster_blood_5': '魔物血液 (5級)',
    'monster_blood_pact': '契約魔血',
    'phasing_scales': '相位鱗片',
    'snowbane_alkahest': '破雪萬能溶劑',
    'soul_crystal': '靈魂水晶',
    'suffocating_coral': '窒息珊瑚',
    'totem_pelt_pendant': '圖騰毛皮吊墜',
    'void_eye': '虛空之眼',
    'voidwoven_cloth': '虛空編織布',
    'wolf_karlther_teeth': '巨狼卡爾瑟之齒',

    # === Tier 5 ===
    'abyssal_tendril_specimen': '深淵觸鬚標本',
    'bloodforged_fragment': '血鍛碎片',
    'bloodvein_hookblade': '血脈鉤刃',
    'bone_powder_mystic': '神秘骨粉 (神話骨粉)',
    'cursedforged_shard': '詛咒鍛造碎片',
    'dimensional_shard': '維度碎片',
    'dragonbreath_core': '龍息核心',
    'frostoath_foundation': '霜誓基石',
    'frostoath_gravemark': '霜誓墓痕',
    'frostoath_headstone': '霜誓墓碑',
    'graystone_carapace': '灰石甲殼',
    'hellbloom': '地獄花',
    'hellhound_tooth': '地獄犬獠牙',
    'ice_heart_fragment': '冰核碎片',
    'infernal_plate_shard': '地獄板甲碎片',
    'inscribed_stone_tablet': '銘刻石板',
    'leather_dragonscale': '龍鱗皮革',
    'martyr_cranium': '殉道者顱骨',
    'overloaded_capacitor_bank': '過載電容組',
    'pale_amethyst': '蒼白紫晶',
    'putrid_heart': '腐臭之心',
    'warlord_bio_vertebra': '軍閥生體脊椎',
    'warped_wombheart': '畸變母巢核心 (畸變胎心)',

    # === Tier 6 ===
    'absolute_zero_heart': '絕對零度之心',
    'broken_soulseal_relic': '殘破魂印聖物',
    'soulforge_hammer': '魂鍛之錘',
    'soulforge_tongs': '魂鍛火鉗',

    # === Essences ===
    'essence_1': '一階精華 (初級精華)',
    'essence_2': '二階精華 (優秀精華)',
    'essence_3': '三階精華 (稀有精華)',
    'essence_4': '四階精華 (史詩精華)',
    'essence_5': '五階精華 (傳說精華)',
    'essence_6': '六階精華 (遠古精華)',

    # === Weapon Shards ===
    'weapon_shard_0': '0 階粗製武器強化石',
    'weapon_shard_1': '1 階優秀武器強化石',
    'weapon_shard_2': '2 階稀有武器強化石',
    'weapon_shard_3': '3 階史詩武器強化石',
    'weapon_shard_4': '4 階傳奇武器強化石',
    'weapon_shard_5': '5 階神話武器強化石',
    'weapon_shard_6': '6 階遠古武器強化石',

    # === Armor Shards ===
    'armor_shard_0': '0 階粗製防具強化石',
    'armor_shard_1': '1 階優秀防具強化石',
    'armor_shard_2': '2 階稀有防具強化石',
    'armor_shard_3': '3 階史詩防具強化石',
    'armor_shard_4': '4 階傳奇防具強化石',
    'armor_shard_5': '5 階神話防具強化石',
    'armor_shard_6': '6 階遠古防具強化石',

    # === Charm Shards ===
    'charm_shard_0': '0 階粗製飾品強化石',
    'charm_shard_1': '1 階優秀飾品強化石',
    'charm_shard_2': '2 階稀有飾品強化石',
    'charm_shard_3': '3 階史詩飾品強化石',
    'charm_shard_4': '4 階傳奇飾品強化石',
    'charm_shard_5': '5 階神話飾品強化石',
    'charm_shard_6': '6 階遠古飾品強化石',

    # === Crystals ===
    'enhancement_crystal_1': '1 階裝備強化水晶',
    'enhancement_crystal_2': '2 階裝備強化水晶',
    'enhancement_crystal_3': '3 階裝備強化水晶',
    'enhancement_crystal_4': '4 階裝備強化水晶',
    'enhancement_crystal_5': '5 階裝備強化水晶',
    'enhancement_crystal_6': '6 階裝備強化水晶',
    'enhancement_crystal_7': '7 階裝備強化水晶',

    # === Royal Cores ===
    'royal_core_slime': '史萊姆皇家核心',
    'royal_core_spider': '蜘蛛皇家核心',
    'royal_core_treant': '樹人皇家核心',

    # === Sin Cores ===
    'sin_core_abysslord': '深淵領主之罪核',
    'sin_core_chaosking': '混沌之王之罪核',
    'sin_core_doomqueen': '毀滅女王之罪核',
    'sin_core_everhunger': '永恆飢渴之罪核',
    'sin_core_firecoreking': '熾炎火核王之罪核',
    'sin_core_frostgiant': '霜巨人王之罪核',
    'sin_core_seaemperor': '深海帝皇之罪核',
    'sin_core_voidwalker': '虛空行者之罪核',
    'sin_core_wastelord': '荒原霸主之罪核',

    # === Dragon Hearts ===
    'dragon_heart_darkness': '暗影巨龍之心',
    'dragon_heart_flame': '烈焰巨龍之心',
    'dragon_heart_frost': '冰霜巨龍之心',
    'dragon_heart_venom': '劇毒巨龍之心',

    # === Special & Broken ===
    'frostoath_emblem': '霜誓徽記',
    'dragonblood_gem': '龍血寶石',
    'warlord_last_word': '軍閥遺言',
    'unnamed_hero_afterglow': '無名英雄之餘暉',
    'blueprint_fragment': '遠古藍圖殘卷',
    'broken_accessory_init_module_left': '殘破飾品初始左模組',
    'broken_accessory_init_module_right': '殘破飾品初始右模組',
    'broken_axe_darok': '達羅克的殘破戰斧',
    'broken_relic_salvation_lantern': '殘破救贖之燈聖物',
    'broken_spear_depth_executioner': '深淵處刑者的殘破之槍',
    'broken_sword_demon_azrim': '惡魔阿茲里姆的殘破魔劍',
}

TIER_INFO = {
    0: ("0 星 / 白色普通素材 (Common)", "⚪ 白色 (0.0)", "基础粗料、生皮、原生原礦、基礎骨粉"),
    1: ("1 星 / 綠色優秀素材 (Uncommon)", "🟢 綠色 (1.0)", "強化骨粉、優質鋼錠、初級加工素材、毒素與纖維"),
    2: ("2 星 / 藍色稀有素材 (Rare)", "🔵 藍色 (2.0)", "高級骨粉、精煉金屬錠、重皮革、礦石與巨獸部位"),
    3: ("3 星 / 紫色史詩素材 (Epic)", "🟣 紫色 (3.0)", "史詩骨粉、惡魔金屬錠、冰霜鋼錠、巨獸皮革、龍骨"),
    4: ("4 星 / 橘黃傳說素材 (Legendary)", "🟠 橘/黃色 (4.0)", "傳說骨粉、熔岩鋼錠、黃金鑄塊、獸人皮革、墮落之心"),
    5: ("5 星 / 橙色神話素材 (Mythic)", "🔶 橙色 (5.0)", "神秘骨粉、龍鱗皮革、霜誓建材、龍息核心、地獄花"),
    6: ("6 星 / 紅色遠古/創世素材 (Ancient / Genesis)", "🔴 紅色 (6.0)", "絕對零度之心、魂鍛神器、殘破魂印聖物")
}


def format_proc(proc_dict):
    if not proc_dict:
        return "-"
    parts = []
    for k, v in sorted(proc_dict.items()):
        name = TRANSLATIONS.get(k, k)
        parts.append(f"{name} x{int(v) if v.is_integer() else v}")
    return "<br>".join(parts)


def format_sources(sources_set):
    if not sources_set:
        return "任務 / 商店 / 特殊掉落"
    src_list = sorted(list(sources_set))
    if len(src_list) <= 3:
        return ", ".join(src_list)
    return ", ".join(src_list[:3]) + f" 等 ({len(src_list)}處)"


def format_uses(uses_set):
    if not uses_set:
        return "-"
    u_list = sorted(list(uses_set))
    named_list = []
    for u in u_list:
        if u in TRANSLATIONS:
            named_list.append(f"【{TRANSLATIONS[u]}】")
        else:
            named_list.append(f"`{u}`")
    if len(named_list) <= 3:
        return ", ".join(named_list)
    return ", ".join(named_list[:3]) + f" 等 ({len(named_list)}項)"


def main():
    parser = TresParser()
    data = parser.parse()
    items = data.get('items', {})
    characters = data.get('characters', {})
    level_groups = data.get('level_groups', {})
    dungeons = data.get('dungeons', {})

    # Save translation dictionary
    dict_dir = os.path.join(BASE_DIR, 'meta_data', 'dicts')
    os.makedirs(dict_dir, exist_ok=True)
    dict_path = os.path.join(dict_dir, 'material_i18n.json')
    with open(dict_path, 'w', encoding='utf-8') as f:
        json.dump(TRANSLATIONS, f, ensure_ascii=False, indent=2)
    print(f"[OK] Dictionary saved: {dict_path}")

    # Build sources
    drop_sources = {}
    for cid, cdata in characters.items():
        if not isinstance(cdata, dict):
            continue
        for key in ['droppable_items', 'drops', 'race_items']:
            items_list = cdata.get(key, [])
            if isinstance(items_list, list):
                for it in items_list:
                    iid = it.get('id') if isinstance(it, dict) else it
                    if iid:
                        if iid not in drop_sources:
                            drop_sources[iid] = set()
                        drop_sources[iid].add(f"`{cid}`")

    for did, ddata in dungeons.items():
        if not isinstance(ddata, dict):
            continue
        chest = ddata.get('chest_dic', {})
        if isinstance(chest, dict):
            for ci in chest.get('items', []):
                if ci not in drop_sources:
                    drop_sources[ci] = set()
                drop_sources[ci].add(f"地下城:`{did}`")

    for gid, gdata in level_groups.items():
        if not isinstance(gdata, dict):
            continue
        for lvl in gdata.get('levels', []):
            if isinstance(lvl, dict):
                for d in lvl.get('droppable_items', []):
                    did = d.get('id') if isinstance(d, dict) else d
                    if did:
                        if did not in drop_sources:
                            drop_sources[did] = set()
                        drop_sources[did].add(f"主線:`{gid}`")

    # Build usage
    used_in = {}
    for iid, idata in items.items():
        if not isinstance(idata, dict):
            continue
        ci = idata.get('craft_items')
        if isinstance(ci, list):
            for c in ci:
                if isinstance(c, dict) and 'id' in c:
                    mid = c['id']
                    if mid not in used_in:
                        used_in[mid] = set()
                    used_in[mid].add(iid)
        pi = idata.get('processing_items')
        if isinstance(pi, dict):
            for mid in pi.keys():
                if mid not in used_in:
                    used_in[mid] = set()
                used_in[mid].add(iid)

    crafting = {k: v for k, v in items.items() if 'crafting' in v.get('categories', [])}

    out = []
    out.append("# 💎《黑火遠征》全素材與材料資料手冊 (0~6 星等級全收錄)\n")
    out.append("> **依據底層資料庫**：[meta_datas.tres](../../raw_tres/meta_datas.tres)  \n")
    out.append("> **涵蓋範圍**：遊戲中全部 **146 種工藝製作材料 (`crafting`)**、**21 種部位強化石 (`enhancement_stone`)**、**7 種強化水晶 (`enhancement_crystal`)**、**6 種精華素材 (`essence`)** 與 **16 大遠古首領核心/龍心**。\n")
    out.append("> **版本規範**：全材料依星級（Tier 0 ~ Tier 6）嚴格分級，收錄底層變數名稱 (`id`)、繁體中文官方名稱、分類標籤、加工精煉配方、主要怪物產出來源及代表性打造去向。\n\n")
    out.append("---\n\n")

    out.append("## 📊 一、全星級素材規格總覽表\n\n")
    out.append("| 星級階數 | 代表框色 / 數值 (`rarity`) | 基礎工藝材料種數 | 強化石 / 水晶 / 精華 | 代表性素材群 |\n")
    out.append("| :---: | :---: | :---: | :---: | :--- |\n")
    out.append("| **Tier 0** | ⚪ 白色 (`0.0` 或無) | **20 種** | 武器/防具/飾品強化石 x3 | 硬化岩石碎片、粗鐵錠、輕皮革、基礎骨粉、粗亞麻 |\n")
    out.append("| **Tier 1** | 🟢 綠色 (`1.0`) | **21 種** | 強化石 x3、1階水晶、1階精華 | 優質鋼錠、中皮革、強化骨粉、沙礦石、堅石果實 |\n")
    out.append("| **Tier 2** | 🔵 藍色 (`2.0`) | **25 種** | 強化石 x3、2階水晶、2階精華 | 精煉鋼錠、重皮革、高級骨粉、鐵礦石、惡魔之角 |\n")
    out.append("| **Tier 3** | 🟣 紫色 (`3.0`) | **25 種** | 強化石 x3、3階水晶、3階精華 | 惡魔金屬錠、冰霜鋼錠、巨獸皮革、史詩骨粉、龍骨 |\n")
    out.append("| **Tier 4** | 🟠 橘黃 (`4.0`) | **28 種** | 強化石 x3、4階水晶、4階精華 | 熔岩鋼錠、黃金鑄塊、獸人皮革、傳說骨粉、墮落之心 |\n")
    out.append("| **Tier 5** | 🔶 橙色 (`5.0`) | **23 種** | 強化石 x3、5階水晶、5階精華、3大皇家核心、4大龍心 | 龍鱗皮革、神秘骨粉、龍息核心、霜誓基石、地獄花 |\n")
    out.append("| **Tier 6** | 🔴 紅色 (`6.0`) | **4 種** | 強化石 x3、6~7階水晶、6階精華、9大罪核、6大破損聖物 | 絕對零度之心、殘破魂印聖物、魂鍛之錘、魂鍛火鉗 |\n")
    out.append("| **合計** | - | **146 種** | **62 種特殊升級與核心素材** | **全遊戲共計 208 種材料** |\n\n")
    out.append("---\n\n")

    out.append("## 🔨 二、全 0~6 星基礎與進階工藝材料總表 (`crafting`，共 146 種)\n\n")

    for tier in range(7):
        title, color_badge, desc = TIER_INFO[tier]
        r_items = [k for k, v in crafting.items() if (v.get('rarity') == float(tier) or (tier == 0 and v.get('rarity') is None))]
        out.append(f"### {tier}. 【Tier {tier}】{title}\n\n")
        out.append(f"> 標籤：`rarity: {float(tier)}` | 框色：**{color_badge}** | 總計 **{len(r_items)}** 種材料  \n")
        out.append(f"> 特點說明：{desc}\n\n")
        out.append("| 序號 | 中文名稱 | 底層變數名稱 (`id`) | 分類 / 標籤 | 加工精煉配方 (`processing_items`) | 主要獲取來源 (怪物/地下城) | 代表打造用途 (`used_in`) |\n")
        out.append("| :---: | :--- | :--- | :--- | :--- | :--- | :--- |\n")

        for idx, item_id in enumerate(sorted(r_items), start=1):
            v = crafting[item_id]
            cname = TRANSLATIONS.get(item_id, item_id)
            sort_id = v.get('sort_id')
            category_tag = f"`{sort_id}`" if sort_id else "原生採集/掉落"
            proc = format_proc(v.get('processing_items'))
            src = format_sources(drop_sources.get(item_id, set()))
            uses = format_uses(used_in.get(item_id, set()))
            out.append(f"| {idx} | **{cname}** | `{item_id}` | {category_tag} | {proc} | {src} | {uses} |\n")
        out.append("\n---\n\n")

    out.append("## 💎 三、裝備強化石、強化水晶與精華素材體系 (0~6 階)\n\n")
    out.append("在《黑火遠征》中，裝備強化升級與突破需要消耗專屬的強化石、水晶與精華素材。此類素材嚴格依階級對應裝備強化等級：\n\n")

    out.append("### 1. ⚔️ 部位強化石 (Enhancement Stones / Shards，共 21 種)\n\n")
    out.append("| 星級階數 | 武器強化石 (`weapon_shard`) | 防具強化石 (`armor_shard`) | 飾品強化石 (`charm_shard`) | 分解裝備來源 (100% 部位與階級對應) |\n")
    out.append("| :---: | :--- | :--- | :--- | :--- |\n")
    for t in range(7):
        w = f"**{TRANSLATIONS[f'weapon_shard_{t}']}** (`weapon_shard_{t}`)"
        a = f"**{TRANSLATIONS[f'armor_shard_{t}']}** (`armor_shard_{t}`)"
        c = f"**{TRANSLATIONS[f'charm_shard_{t}']}** (`charm_shard_{t}`)"
        tier_desc = f"分解 {t} 階 (星級 {t}.0) 對應部位裝備產出 (4 合 1 可精煉升級)"
        out.append(f"| **Tier {t}** | {w} | {a} | {c} | {tier_desc} |\n")
    out.append("\n")

    out.append("### 2. 🔮 裝備強化水晶 (Enhancement Crystals，共 7 種)\n\n")
    out.append("| 水晶階級 | 變數名稱 (`id`) | 中文名稱 | 對應裝備強化區間 | 備註 |\n")
    out.append("| :---: | :--- | :--- | :---: | :--- |\n")
    for t in range(1, 8):
        cid = f"enhancement_crystal_{t}"
        cname = TRANSLATIONS[cid]
        out.append(f"| **{t} 階** | `{cid}` | **{cname}** | 裝備 +{t} ~ +{min(t+2, 10)} 強化 | 雜貨鋪購買、轉盤抽獎、寶箱或高級地下城獎勵 |\n")
    out.append("\n")

    out.append("### 3. 🧪 六大階級精華素材 (Essences，共 6 種)\n\n")
    out.append("| 精華階級 | 變數名稱 (`id`) | 中文名稱 | 品質星級 | 主要用途與打造領域 |\n")
    out.append("| :---: | :--- | :--- | :---: | :--- |\n")
    for t in range(1, 7):
        eid = f"essence_{t}"
        ename = TRANSLATIONS[eid]
        out.append(f"| **{t} 階** | `{eid}` | **{ename}** | Tier {t} ({t}.0) | 全 {t} 階裝備、武器、副手及藥劑之核心精華黏合劑 |\n")
    out.append("\n---\n\n")

    out.append("## 👑 四、首領核心、巨龍之心與遠古神話素材 (5~6 星)\n\n")

    out.append("### 1. 🏰 3 大皇家核心 (`royal_core`，Tier 5 神話橙)\n\n")
    out.append("| 變數名稱 (`id`) | 中文名稱 | 品質星級 | 主要掉落首領 | 核心用途 |\n")
    out.append("| :--- | :--- | :---: | :--- | :--- |\n")
    out.append("| `royal_core_slime` | **史萊姆皇家核心** | 5.0 (橙) | 皇家史萊姆國王 / 巨型史萊姆首領 | 打造頂級生命/防禦神話飾品 |\n")
    out.append("| `royal_core_spider` | **蜘蛛皇家核心** | 5.0 (橙) | 蜘蛛母皇 (育母蜘蛛首領) | 打造頂級神話毒素/敏捷飾品與長弓 |\n")
    out.append("| `royal_core_treant` | **樹人皇家核心** | 5.0 (橙) | 遠古守護樹人首領 (烏爾德) | 打造頂級神話生命恢復裝備 |\n\n")

    out.append("### 2. 🐉 4 大屬性巨龍之心 (`dragon_heart`，Tier 5 神話橙)\n\n")
    out.append("| 變數名稱 (`id`) | 中文名稱 | 屬性標籤 | 主要掉落巨龍 | 背包直接分解收益 |\n")
    out.append("| :--- | :--- | :---: | :--- | :--- |\n")
    out.append("| `dragon_heart_darkness` | **暗影巨龍之心** | 暗影 (`darkness`) | 冥淵暗龍首領 | 🎒 可直接分解：保底產出 10 顆強化石 (含 5 顆 4~5 階) |\n")
    out.append("| `dragon_heart_flame` | **烈焰巨龍之心** | 火焰 (`fire`) | 熾炎火龍首領 | 🎒 可直接分解：保底產出 10 顆強化石 (含 5 顆 4~5 階) |\n")
    out.append("| `dragon_heart_frost` | **冰霜巨龍之心** | 冰霜 (`ice`) | 極凍霜龍首領 | 🎒 可直接分解：保底產出 10 顆強化石 (含 5 顆 4~5 階) |\n")
    out.append("| `dragon_heart_venom` | **劇毒巨龍之心** | 毒素 (`poison`) | 沼澤毒龍首領 | 🎒 可直接分解：保底產出 10 顆強化石 (含 5 顆 4~5 階) |\n\n")

    out.append("### 3. ☠️ 9 大罪業王核 (`sin_core`，Tier 6 遠古紅)\n\n")
    out.append("| 變數名稱 (`id`) | 中文名稱 | 品質星級 | 對應大罪 / 領域首領 | 核心特性與分解價值 |\n")
    out.append("| :--- | :--- | :---: | :--- | :--- |\n")
    sin_bosses = [
        ('sin_core_abysslord', '深淵領主之罪核', '深淵魔境 / 深淵之王'),
        ('sin_core_chaosking', '混沌之王之罪核', '混沌邊界 / 混沌之主'),
        ('sin_core_doomqueen', '毀滅女王之罪核', '終焉之座 / 毀滅女王'),
        ('sin_core_everhunger', '永恆飢渴之罪核', '暴食之淵 / 吞噬魔神'),
        ('sin_core_firecoreking', '熾炎火核王之罪核', '熔岩地心 / 火核之王'),
        ('sin_core_frostgiant', '霜巨人王之罪核', '極寒永凍峰 / 冰霜之王'),
        ('sin_core_seaemperor', '深海帝皇之罪核', '沉沒神殿 / 深海帝皇'),
        ('sin_core_voidwalker', '虛空行者之罪核', '無盡虛空 / 虛空漫遊者'),
        ('sin_core_wastelord', '荒原霸主之罪核', '遺忘荒原 / 荒原霸王')
    ]
    for sid, sname, sboss in sin_bosses:
        out.append(f"| `{sid}` | **{sname}** | 6.0 (紅) | {sboss} | 打造頂級遠古創世神裝；分解獲 10 顆高階強化石 |\n")
    out.append("\n")

    out.append("### 4. 🧩 6 大破損聖物部件與特殊遠古素材\n\n")
    out.append("| 變數名稱 (`id`) | 中文名稱 | 品質星級 | 來源與作用說明 |\n")
    out.append("| :--- | :--- | :---: | :--- |\n")
    broken_items = [
        ('broken_accessory_init_module_left', '殘破飾品初始左模組', '6.0 (紅)', '地下城終極試煉掉落，重組遠古首飾必備模組'),
        ('broken_accessory_init_module_right', '殘破飾品初始右模組', '6.0 (紅)', '地下城終極試煉掉落，重組遠古首飾必備模組'),
        ('broken_axe_darok', '達羅克的殘破戰斧', '6.0 (紅)', '狂戰士達羅克專屬傳承神器復原素材'),
        ('broken_relic_salvation_lantern', '殘破救贖之燈聖物', '6.0 (紅)', '大主教救贖聖燈修復核心素材'),
        ('broken_spear_depth_executioner', '深淵處刑者的殘破之槍', '6.0 (紅)', '深淵處刑者神話長槍修復素材'),
        ('broken_sword_demon_azrim', '惡魔阿茲里姆的殘破魔劍', '6.0 (紅)', '惡魔魔王阿茲里姆滅世魔刃修復素材'),
        ('frostoath_emblem', '霜誓徽記', '6.0 (紅)', '霜誓大教堂終極信物，直接分解獲大量高階強化石'),
        ('dragonblood_gem', '龍血寶石', '6.0 (紅)', '巨龍先祖真血結晶，遠古裝備極限打孔與鑲嵌'),
        ('warlord_last_word', '軍閥遺言', '6.0 (紅)', '鋼鐵軍閥之最後信物，分解保底獲高階強化石')
    ]
    for bid, bname, btier, bdesc in broken_items:
        out.append(f"| `{bid}` | **{bname}** | {btier} | {bdesc} |\n")
    out.append("\n---\n\n")

    out.append("## 🔄 五、四大核心加工鏈合成機制總覽\n\n")
    out.append("遊戲中的鐵匠鋪加工系統（`blacksmith.processing_dic`）具備極具特色的**層級遞歸加工機制**，玩家可將低階素材一路向上提煉：\n\n")
    out.append("```mermaid\ngraph LR\n")
    out.append("    subgraph ⛏️ 鑄塊鏈 (Ingot)\n")
    out.append("        I0[\"粗鐵錠 (ingot_rough)<br>硬化岩石 x2\"] --> I1[\"優質鋼錠 (ingot_quality)<br>粗鐵錠x4 + 沙礦石x2 + 堅石果實x2\"]\n")
    out.append("        I1 --> I2[\"精煉鋼錠 (ingot_refined)<br>優質鋼錠x4 + 鐵礦石x2 + 枷鎖碎片x2\"]\n")
    out.append("        I2 --> I_SP[\"特殊高級金屬錠<br>冰霜/惡魔/熔岩/誓約/黃金\"]\n")
    out.append("    end\n")
    out.append("    subgraph 🦌 皮革鏈 (Leather)\n")
    out.append("        L0[\"輕皮革 (leather_light)<br>生皮 x2 或 蝙蝠翅膀 x4\"] --> L1[\"中皮革 (leather_medium)<br>輕皮革x4 + 花豹皮x2 + 石化鱗片x2\"]\n")
    out.append("        L1 --> L2[\"重皮革 (leather_heavy)<br>中皮革x4 + 巨獸/巨人/熊皮x2\"]\n")
    out.append("        L2 --> L_SP[\"特殊高級皮革<br>獸人皮革 / 龍鱗皮革\"]\n")
    out.append("    end\n")
    out.append("    subgraph 🧵 布匹鏈 (Fabric)\n")
    out.append("        F0[\"粗製布匹 (fabric_rough)<br>粗亞麻x2 + 蜘蛛絲x2\"] --> F1[\"優質布匹 (fabric_quality)<br>粗製布匹x4 + 霜蛛絲/藤蔓/怨魂布x2\"]\n")
    out.append("        F1 --> F2[\"精編布匹 (fabric_finely_woven)<br>優質布匹x4 + 沼澤織布x2\"]\n")
    out.append("        F2 --> F3[\"冰織布匹 (fabric_iceweave)<br>霜蛛絲x8\"]\n")
    out.append("    end\n")
    out.append("    subgraph ☠️ 骨粉鏈 (Bone Powder)\n")
    out.append("        B0[\"基礎骨粉 (basic)<br>野獸獠牙x1\"] --> B1[\"強化骨粉 (enhanced)<br>基礎x2 + 獠牙/巨人牙x1\"]\n")
    out.append("        B1 --> B2[\"高級骨粉 (advanced)<br>強化x2 + 熊骨/巨獸骨/惡魔角x1\"]\n")
    out.append("        B2 --> B3[\"史詩骨粉 (epic)<br>龍骨 + 食屍鬼牙 + 獸人牙\"]\n")
    out.append("        B3 --> B4[\"傳說骨粉 (legendary)<br>史詩x2 + 墮落之心 + 狼王齒\"]\n")
    out.append("        B4 --> B5[\"神秘骨粉 (mystic)<br>傳說x2 + 地獄犬齒 + 殉道顱骨 + 腐臭心\"]\n")
    out.append("    end\n")
    out.append("```\n\n")

    out.append("---\n\n")
    out.append("## 📑 相關文件索引\n\n")
    out.append("- 原始數據來源：[meta_datas.tres](../../raw_tres/meta_datas.tres)\n")
    out.append("- 掉落率總綱手冊：[Drop_rate.md](Drop_rate.md)\n")
    out.append("- 鑄塊專題手冊：[ingot/ALL.md](ingot/ALL.md)\n")
    out.append("- 重皮革專題手冊：[leather/leather_heavy.md](leather/leather_heavy.md)\n")
    out.append("- 武器強化石獲取指南：[weapon_upgrade_shards_guide.md](../../../docs/guides/weapon_upgrade_shards_guide.md)\n")
    out.append("- 全裝備強化定價指南：[GEAR_ENHANCEMENT_PRICE_GUIDE.md](../Gear/Enhancement/GEAR_ENHANCEMENT_PRICE_GUIDE.md)\n")

    final_md = "".join(out)
    target_dir = os.path.join(BASE_DIR, 'meta_data', 'Game_docs', 'Meterial')
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, 'ALL_MATERIALS.md')
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(final_md)

    print(f"[OK] Material documentation generated: {target_path} ({len(final_md)} bytes)")


if __name__ == "__main__":
    main()
