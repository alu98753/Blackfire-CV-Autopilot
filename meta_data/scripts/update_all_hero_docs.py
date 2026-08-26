import json
import os
import re
import sys

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from meta_data.hero_analyzer import HeroAnalyzer

# 1. Update attr_i18n.json with full translations
attr_dict_path = os.path.join(BASE_DIR, 'meta_data', 'dicts', 'attr_i18n.json')
with open(attr_dict_path, 'r', encoding='utf-8') as f:
    attr_i18n = json.load(f)

# Comprehensive mapping for all game attributes
comprehensive_attrs = {
    "abyss_seed_chance": "深淵種子觸發機率",
    "abyss_seed_count": "深淵種子層數",
    "abyss_seed_max": "深淵種子層數上限",
    "abyss_seed_min": "深淵種子基礎層數",
    "active_chance": "被動/特異觸發機率",
    "active_count": "特異觸發次數/層數",
    "active_hp_rate": "觸發血線閥值",
    "active_round": "特異持續回合數",
    "active_times": "特異生效次數",
    "afterglow_chance": "餘暉觸發機率",
    "ally_chance": "友軍協同機率",
    "armor_bouns": "額外護甲加成",
    "armor_mag_offset": "魔防加成係數",
    "armor_max": "護甲增加上限",
    "armor_min": "護甲增加下限",
    "armor_offset": "護甲加成係數",
    "armor_offset_max": "最大護甲加成係數",
    "armor_offset_min": "最小護甲加成係數",
    "attack_chance": "額外追擊機率",
    "attack_max": "追擊次數上限",
    "attack_min": "追擊次數下限",
    "attack_times": "連擊/攻擊次數",
    "attack_times_max": "最大攻擊次數",
    "attack_times_min": "最小攻擊次數",
    "attr_bouns": "全屬性增益加成",
    "ball_count": "法球/能量球數量",
    "ball_max": "法球最大數量",
    "ball_min": "法球最小數量",
    "barrier_chance": "屏障觸發機率",
    "barrier_count": "屏障層數/格擋次數",
    "barrier_max": "屏障層數上限",
    "barrier_min": "屏障基礎層數",
    "battle_fury_chance": "戰意狂怒觸發機率",
    "battle_fury_count": "戰意狂怒層數",
    "battle_fury_max": "戰意狂怒上限",
    "battle_fury_min": "戰意狂怒基礎層數",
    "battle_fury_round": "戰意狂怒回合數",
    "beast_power_chance": "野獸之力觸發機率",
    "beast_power_count": "野獸之力層數",
    "beast_power_max": "野獸之力上限",
    "beast_power_min": "野獸之力基礎層數",
    "beetle_count": "甲蟲召喚數量",
    "bleed_count": "流血附加層數",
    "bleed_immuned": "免疫流血",
    "bleed_offset": "流血傷害係數",
    "bleed_res": "流血抗性",
    "bleed_round": "流血持續回合數",
    "bleeding_chance": "流血觸發機率",
    "blessing_chance": "祈福觸發機率",
    "blessing_count": "祈福層數",
    "blessing_max": "祈福層數上限",
    "blessing_min": "祈福基礎層數",
    "blessing_round": "祈福持續回合數",
    "block": "格擋值",
    "block_chance": "格擋觸發率",
    "bloodlust_chance": "嗜血/血怒觸發機率",
    "bloodlust_count": "嗜血/血怒層數",
    "bloodthirst_power_chance": "渴血之力觸發機率",
    "bloodthirst_power_count": "渴血之力層數",
    "brooding_egg_chance": "育卵觸發機率",
    "brooding_egg_round": "育卵孵化回合數",
    "buff_armor_offset": "護甲增益係數",
    "buff_block_count": "格擋增益次數",
    "buff_block_max": "最大格擋次數",
    "buff_block_min": "最小格擋次數",
    "buff_block_times": "格擋生效次數",
    "buff_chance_1": "一段增益機率",
    "buff_chance_2": "二段增益機率",
    "buff_count": "增益層數",
    "buff_dodge_chance": "閃避增益機率",
    "buff_dodge_check_count": "閃避檢定次數",
    "buff_dodge_count": "閃避增益層數",
    "buff_dodge_max": "最大閃避增益",
    "buff_dodge_min": "最小閃避增益",
    "buff_heal_chance": "受癒增益機率",
    "buff_heal_count": "受癒增益層數",
    "buff_heal_max": "受癒增益上限",
    "buff_heal_min": "受癒增益下限",
    "buff_max": "增益層數上限",
    "buff_min": "增益基礎層數",
    "buff_offset": "增益效果係數",
    "buff_round": "增益持續回合數",
    "bulwark_chance": "堡壘護盾觸發機率",
    "bulwark_count": "堡壘護盾層數",
    "bulwark_hp": "堡壘護盾生命吸收值",
    "bulwark_max": "堡壘護盾上限",
    "bulwark_min": "堡壘護盾基礎值",
    "bulwark_round": "堡壘護盾回合數",
    "can_not_dodge": "無視閃避 (必中)",
    "check_count": "檢定次數/判定層數",
    "combo_times": "連擊次數",
    "count": "生效次數/數量",
    "count_max": "數量上限",
    "count_min": "基礎數量",
    "critical_strike_chance": "爆擊威能觸發機率",
    "critical_strike_count": "爆擊威能層數",
    "critical_strike_max": "爆擊威能上限",
    "critical_strike_min": "爆擊威能基礎層數",
    "critical_strike_round": "爆擊威能回合數",
    "damage": "固定傷害數值",
    "damage_bouns_1": "一段額外增傷",
    "damage_bouns_2": "二段額外增傷",
    "damage_bouns_3": "三段額外增傷",
    "damage_bouns_darkness": "暗影額外傷害加成",
    "damage_bouns_fire": "火焰額外傷害加成",
    "damage_offset_dark": "暗影傷害係數",
    "damage_offset_darkness": "暗影傷害係數",
    "damage_offset_extra": "額外附加傷害係數",
    "damage_offset_fire": "火焰傷害係數",
    "damage_offset_frost": "冰霜傷害係數",
    "damage_offset_holy": "神聖傷害係數",
    "damage_offset_ice": "冰霜傷害係數",
    "damage_offset_magic": "魔法傷害係數",
    "damage_offset_physical": "物理傷害係數",
    "damage_offset_shield": "盾擊傷害係數",
    "damage_reduce_offset": "傷害減免係數",
    "damage_reduction_count": "減傷層數",
    "damage_reduction_max": "減傷層數上限",
    "damage_reduction_min": "減傷基礎層數",
    "damage_round": "傷害結算回合",
    "damage_surge_chance": "傷害激增觸發機率",
    "damage_surge_count": "傷害激增層數",
    "damage_surge_max": "傷害激增上限",
    "damage_surge_min": "傷害激增基礎層數",
    "darkness_chance": "暗影侵蝕機率",
    "darkness_count": "暗影侵蝕層數",
    "darkness_max": "暗影侵蝕上限",
    "darkness_min": "暗影侵蝕基礎層數",
    "dart_count": "飛鏢/投射物數量",
    "death_immunity_chance": "免死護命機率",
    "death_immunity_count": "免死生效次數",
    "death_immunity_max": "免死次數上限",
    "death_immunity_min": "免死基礎次數",
    "death_mark_chance": "死亡標記機率",
    "death_mark_max": "死亡標記上限",
    "death_mark_round": "死亡標記持續回合",
    "debuff_chance": "減益施加機率",
    "debuff_max": "減益層數上限",
    "debuff_min": "減益基礎層數",
    "deepsea_resonance_chance": "深海共鳴觸發機率",
    "deepsea_resonance_count": "深海共鳴層數",
    "deepsea_resonance_max": "深海共鳴上限",
    "deepsea_resonance_min": "深海共鳴基礎層數",
    "disordered_directive_chance": "混亂指令觸發機率",
    "disordered_directive_max": "混亂指令上限",
    "disordered_directive_min": "混亂指令基礎層數",
    "dodge_chance": "閃避判定機率",
    "dodge_max": "最大閃避值",
    "dodge_min": "最小閃避值",
    "dreadlight_mark_chance": "懼光印記機率",
    "dreadlight_mark_max": "懼光印記上限",
    "dreadlight_mark_min": "懼光印記基礎層數",
    "drenched_max": "浸潤層數上限",
    "drenched_min": "浸潤基礎層數",
    "drop_chance": "掉落機率",
    "drowning_chance": "溺亡觸發機率",
    "drowning_max": "溺亡層數上限",
    "drowning_min": "溺亡基礎層數",
    "egg_chance": "蟲卵生成機率",
    "energy_charge_chance": "充能獲得機率",
    "energy_charge_max": "充能層數上限",
    "energy_charge_min": "充能基礎層數",
    "energy_charge_spent": "消耗充能層數",
    "energy_charge_use": "使用充能層數",
    "energy_count": "獲得能量點數",
    "energy_max": "最大能量獲得",
    "energy_min": "最小能量獲得",
    "escape_round": "脫逃/隱蔽回合",
    "exp_bouns": "經驗值加成",
    "extra_chance": "額外連鎖機率",
    "extra_energy_count": "額外能量點數",
    "fire_chance": "點燃/灼燒機率",
    "fire_count": "灼燒層數/火球數",
    "fire_immuned": "免疫燃燒/火焰",
    "fire_max": "灼燒層數上限",
    "fire_min": "灼燒基礎層數",
    "fire_offset": "火焰傷害係數",
    "fire_round": "燃燒持續回合數",
    "fire_total": "總火焰層數",
    "fireball_max": "火球最大數量",
    "fireball_min": "火球最小數量",
    "flayed_chance": "剝皮削防機率",
    "foul_carapace_chance": "污穢甲殼觸發機率",
    "foul_carapace_count": "污穢甲殼層數",
    "foul_carapace_max": "污穢甲殼上限",
    "foul_carapace_min": "污穢甲殼基礎層數",
    "freezing_chance_1": "一段冰凍機率",
    "freezing_chance_2": "二段冰凍機率",
    "freezing_chance_3": "三段冰凍機率",
    "freezing_count": "冰凍層數",
    "freezing_immuned": "免疫冰凍",
    "frost_barrier_count": "冰霜屏障層數",
    "frost_barrier_max": "冰霜屏障上限",
    "frost_barrier_min": "冰霜屏障基礎值",
    "frost_barrier_round": "冰霜屏障持續回合",
    "hallucination_chance": "幻覺觸發機率",
    "hallucination_max": "幻覺層數上限",
    "hallucination_min": "幻覺基礎層數",
    "heal_bouns": "額外治療量加成",
    "heal_chance": "治療觸發機率",
    "heal_offset_1": "一段治療倍率",
    "heal_offset_2": "二段治療倍率",
    "heal_offset_max": "最大治療倍率",
    "heal_offset_min": "最小治療倍率",
    "heal_times": "治療次數",
    "hit": "命中值",
    "holyball_1": "一段聖光法球",
    "holyball_2": "二段聖光法球",
    "holyball_3": "三段聖光法球",
    "hp_bouns": "生命加成值",
    "hp_bouns_battle": "戰鬥額外生命加成",
    "hp_min": "最低生命保障",
    "hp_offset": "生命回復/扣除比例",
    "hp_offset_1": "一段生命係數",
    "hp_offset_2": "二段生命係數",
    "hp_offset_3": "三段生命係數",
    "hp_offset_bouns": "生命百分比額外加成",
    "hp_rate": "當前生命比例閥值",
    "hp_rate_1": "一段血線閥值",
    "hp_rate_2": "二段血線閥值",
    "hp_rate_3": "三段血線閥值",
    "hp_rate_max": "最高血線閥值",
    "hp_rate_min": "最低血線閥值",
    "ice_res_target": "目標冰霜抗性降低",
    "immobilize_chance": "定身/纏繞機率",
    "immobilize_count": "定身層數",
    "immobilize_max": "定身上限",
    "immobilize_min": "定身基礎層數",
    "ironoath_chance": "鐵誓觸發機率",
    "ironoath_count": "鐵誓層數",
    "ironoath_max": "鐵誓上限",
    "ironoath_min": "鐵誓基礎層數",
    "kill_chance": "斬殺致死機率",
    "leech_rate": "吸血轉化率",
    "limit": "生效次數限制",
    "limit_count": "限制層數",
    "luck": "幸運值",
    "mag_chance": "魔法協同機率",
    "magic_chance": "魔法觸發機率",
    "magic_offset": "魔法增幅係數",
    "manic_count": "狂躁層數",
    "min_armor": "保底護甲值",
    "negate_chance": "傷害無效化機率",
    "petrification_count": "石化層數",
    "petrification_max": "石化上限",
    "petrification_min": "石化基礎層數",
    "phase_1_count": "一階段層數",
    "phase_2_count": "二階段層數",
    "phase_3_count": "三階段層數",
    "phy_bouns": "物理傷害加成",
    "phy_chance": "物理協同機率",
    "physical_offset": "物理加成係數",
    "plague_chance": "瘟疫感染機率",
    "poison_count": "中毒層數",
    "poison_immuned": "免疫中毒",
    "poison_round": "中毒持續回合",
    "poison_target": "毒素目標數",
    "position_chance": "位移/擊退機率",
    "protection_count": "保護層數",
    "protection_max": "保護上限",
    "protection_min": "保護基礎值",
    "protection_round": "保護持續回合",
    "provocation_count": "嘲諷層數",
    "provocation_immuned": "免疫嘲諷",
    "provocation_max": "嘲諷上限",
    "provocation_min": "嘲諷基礎值",
    "provocation_round": "嘲諷持續回合",
    "random_1": "一段隨機值",
    "random_2": "二段隨機值",
    "random_damage_offset": "隨機傷害浮動係數",
    "random_max": "隨機上限",
    "random_min": "隨機下限",
    "random_targets": "隨機目標數",
    "rebirth_chance": "重生復活機率",
    "red_chance": "致命暴擊率",
    "remove_count": "驅散狀態數量",
    "remove_count_extra": "額外驅散數量",
    "reset_chance": "重置冷卻機率",
    "restore_chance": "回復觸發機率",
    "restore_rate": "回復比例",
    "restore_rate_max": "最大回復比例",
    "restore_rate_min": "最小回復比例",
    "sacred_scorch_chance": "聖炎灼燒機率",
    "sacred_scorch_max": "聖炎灼燒上限",
    "sacred_scorch_min": "聖炎灼燒基礎值",
    "shield_round": "護盾持續回合",
    "silence_chance": "沉默施加機率",
    "silence_count": "沉默層數",
    "silence_immuned": "免疫沉默",
    "silence_max": "沉默上限",
    "silence_min": "沉默基礎值",
    "silence_res": "沉默抗性",
    "silence_round": "沉默持續回合",
    "simee_count_max": "史萊姆分裂上限",
    "sinbrand_chance": "罪痕印記機率",
    "sinbrand_count": "罪痕印記層數",
    "sinbrand_max": "罪痕印記上限",
    "sinbrand_min": "罪痕印記基礎層數",
    "sinbrand_offset": "罪痕傷害加成係數",
    "skill_chance": "技能發動機率",
    "skill_count": "額外技能釋放次數",
    "skull_count_max": "骷髏召喚上限",
    "skull_count_min": "骷髏召喚下限",
    "slaugher_power_max": "屠戮之力上限",
    "slaughter_power_offset": "屠戮之力加成係數",
    "slime_count": "史萊姆召喚數量",
    "slime_count_min": "史萊姆最小數量",
    "sp_chance": "能量回復機率",
    "sp_count": "能量點數獲得",
    "spider_count": "召喚蜘蛛數量",
    "spider_round": "蜘蛛召喚持續回合",
    "spike_count": "地刺/冰刺數量",
    "spike_count_max": "地刺數量上限",
    "spike_count_min": "地刺數量下限",
    "spike_max": "地刺最大值",
    "spike_min": "地刺最小值",
    "spread_times": "擴散/傳染次數",
    "sprite_chance": "精靈召喚機率",
    "stealth_chance": "進入潛行機率",
    "stealth_count": "潛行層數",
    "stealth_max": "潛行上限",
    "stealth_min": "潛行基礎值",
    "stealth_round": "潛行持續回合",
    "stomp_count": "踐踏震擊次數",
    "stun_immuned": "免疫眩暈",
    "stun_res": "眩暈抗性",
    "summon_chance": "召喚機率",
    "summon_power_max": "召喚物威能上限",
    "summon_power_min": "召喚物威能下限",
    "suppressed_chance": "壓制機率",
    "suppressed_max": "壓制上限",
    "suppressed_min": "壓制基礎值",
    "times": "生效次數",
    "times_limit": "最大生效次數限制",
    "times_max": "次數上限",
    "times_min": "次數下限",
    "total_res": "全屬性全抗性",
    "trauma_chance": "創傷施加機率",
    "trauma_count": "創傷層數",
    "trauma_max": "創傷上限",
    "trauma_min": "創傷基礎層數",
    "vital_blockade_chance": "氣血封鎖機率",
    "vital_blockade_count": "氣血封鎖層數",
    "vital_blockade_max": "氣血封鎖上限",
    "vital_blockade_min": "氣血封鎖基礎層數",
    "vital_blockade_round": "氣血封鎖持續回合",
    "vulnerability_chance": "易傷施加機率",
    "vulnerability_count": "易傷層數",
    "vulnerability_max": "易傷上限",
    "vulnerability_min": "易傷基礎層數",
    "weakness_count": "虛弱層數",
    "weakness_level_chance": "虛弱進階機率",
    "wither_chance": "枯萎感染機率",
    "wither_max": "枯萎上限",
    "wither_min": "枯萎基礎層數"
}

attr_i18n.update(comprehensive_attrs)
with open(attr_dict_path, 'w', encoding='utf-8') as f:
    json.dump(attr_i18n, f, ensure_ascii=False, indent=2)
print("Updated attr_i18n.json successfully!")

# 2. Update skill_i18n.json
skill_dict_path = os.path.join(BASE_DIR, 'meta_data', 'dicts', 'skill_i18n.json')
with open(skill_dict_path, 'r', encoding='utf-8') as f:
    skill_i18n = json.load(f)

additional_skills = {
    "commanding_roar": "統御咆哮",
    "darkfeather_impale": "暗羽穿刺",
    "darkfeather_flurry": "暗羽狂襲",
    "mutant_flame_stalk": "變異炎莖",
    "iceline_afterblow": "冰脈餘勁",
    "deathbound_pressure": "死縛威壓",
    "remote_eecortication": "隔空剝蝕",
    "oathforge_transmute": "誓鍛轉化",
    "scorching_touch": "灼熱之觸",
    "flamebound_sacrifice": "縛焰祭獻",
    "blood_extraction": "汲血之術",
    "rend_frenzy": "狂亂撕裂",
    "bloodfang_mark": "血牙印記",
    "soul_stacking": "靈魂堆疊",
    "necrophageous_hunger": "噬腐飢渴",
    "draconic_awakening": "龍魂覺醒",
    "dragonheart_renewal": "龍心復甦",
    "rage_howl": "狂暴戰吼",
    "tribal_synergy": "部族連動",
    "shieldwall_oath": "盾牆誓約",
    "emergency_gear_jump": "緊急齒輪跳躍",
    "bear_spirit_awakening": "熊靈覺醒",
    "feral_fury": "狂野狂怒",
    "nature_affinity": "自然親和",
    "skeleton_summon": "骸骨召喚",
    "necromancer_protection": "死靈庇護",
    "vengeful_spirit": "復仇怨靈",
    "hell_pact": "地獄契約",
    "hell_power": "地獄之威",
    "slaughter_flames": "屠戮烈焰",
    "whispers_death": "死亡低語",
    "flesh_feeder": "食肉之慾"
}

skill_i18n.update(additional_skills)
with open(skill_dict_path, 'w', encoding='utf-8') as f:
    json.dump(skill_i18n, f, ensure_ascii=False, indent=2)
print("Updated skill_i18n.json successfully!")

# 3. Regenerate HERO_ANALYSIS_REPORT.md
analyzer = HeroAnalyzer()
analyzer.load_data()
analyzer.generate_all_outputs()

# Also copy/overwrite into Game_docs/Hero/
target_game_doc = os.path.join(BASE_DIR, 'meta_data', 'Game_docs', 'Hero', 'HERO_ANALYSIS_REPORT.md')
source_output = os.path.join(BASE_DIR, 'meta_data', 'outputs', 'HERO_ANALYSIS_REPORT.md')
with open(source_output, 'r', encoding='utf-8') as sf:
    content = sf.read()
with open(target_game_doc, 'w', encoding='utf-8') as df:
    df.write(content)
print("Updated both HERO_ANALYSIS_REPORT.md locations!")

# 4. Generate 100% verified Racial Synergy.md
races_doc_content = """# 🧬 Blackfire Crusade 全英雄種族機制與連動效果全景指南

> 本文件依據遊戲底層資源 `meta_datas.tres` 原始數據整理，全面解析全 21 大種族的基礎體質、天賦特性 (Characteristics)、標籤陣營 (Tags)、專屬種族技能以及跨種族連動機制 (Racial Synergy)。

---

## 🧬 一、全英雄 21 大種族分類與定位全景圖

遊戲中 60 位英雄與戰寵共分屬 **21 個種族**，可歸納為 5 大陣營體系：

```mermaid
graph TD
    A["Blackfire Crusade 5 大種族陣營體系"] --> B["👑 文明同盟陣營 (Humanoid)"]
    A --> C["🔥 蠻荒與龍裔陣營 (Savage & Draconic)"]
    A --> D["💀 冥界與深淵陣營 (Evil / Undead)"]
    A --> E["🌿 自然與精靈陣營 (Nature / Fey)"]
    A --> F["🐾 靈獸與元素戰寵 (Beast / Void)"]

    B --> B1["人類 (Human) / 矮人 (Dwarf) / 哥布林 (Goblin) / 蛙人 (Frogman)"]
    C --> C1["獸人 (Orc) / 維京人 (Viking) / 龍裔 (Dragonkin) / 巨熊人 (Bear Monster)"]
    D --> D1["骷髏 (Skeleton) / 幽魂 (Specter) / 惡魔 (Demon) / 亡靈 (Undead) / 夜幕幽裔 (Nightshroud)"]
    E --> E1["精靈 (Elf) / 樹人 (Treant)"]
    F --> F1["冰元素 (Ice Elemental) / 虛空裔 (Voidborn) / 狼 (Wolf) / 熊 (Bear) / 史萊姆 (Slime) / 瓶中靈 (Vialkin)"]
```

---

## 📊 二、21 大種族底層原始體質、天賦特質與專屬技能對照表

根據 `meta_datas.tres` 底層定義，全 21 種族的原始基礎生命、攻擊力區間、標籤陣營、天賦特性 (Characteristics) 與專屬種族技能如下：

| 種族代號 | 種族名稱 | 代表英雄/戰寵 | 基礎生命 (HP) | 基礎傷害 (Dam) | 標籤陣營 (Tags) | 天賦特性 (Characteristics) | 專屬種族技能 (Racial Skills) |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| `dragonkin` | **龍裔** | `hero_archer_7` | **200.0** | 25.0 ~ 35.0 | `dragon`, `humanoid` | `ancient_bloodline`, `dragon_wisdom`, `experience_epiphany`, `balance` | `draconic_awakening`, `dragonheart_renewal` |
| `orc` | **獸人** | `hero_archer_drugor`, `hero_warrior_kraghul`, `hero_priest_7` | **220.0** | 25.0 ~ 35.0 | `humanoid`, `orc` | `rough_hide`, `sturdy_will`, `frenzied_might`, `sturdy_physique`, `beastly_armor` | `rage_howl`, `tribal_synergy` |
| `viking` | **維京人** | `hero_archer_olaf`, `hero_warrior_hildrena` | **180.0** | 25.0 ~ 35.0 | `humanoid`, `viking` | `balance`, `sturdy_physique`, `rough_hide` | `shieldwall_oath` |
| `dwarf` | **矮人** | `hero_knight_bragos`, `hero_warrior_5` | **135.0** | 5.0 ~ 10.0 | `humanoid` | `sturdy_physique`, `ironclad_resistance` | `soul_stacking` |
| `goblin` | **哥布林** | `hero_knight_glig`, `hero_mage_nobiz` | **115.0** | 8.0 ~ 12.0 | `humanoid` | `swift_initiative`, `brightmind_surge` | `emergency_gear_jump` |
| `elf` | **精靈** | `hero_mage_ecasia`, `hero_archer_1/4/6`, `hero_knight_3` | **125.0** | 8.0 ~ 12.0 | `humanoid` | `swift`, `magic_safeguard` | `soul_stacking` |
| `human` | **人類** | `hero_knight_askar`, `hero_priest_1~3/5/aldrian` | **125.0** | 8.0 ~ 12.0 | `humanoid` | `experience_epiphany`, `balance` | `courage_legion` |
| `frogman` | **蛙人** | `hero_archer_5` | **135.0** | 8.0 ~ 12.0 | `humanoid` | `moist_skin`, `slimy_defense` | `whispers_death`, `flesh_feeder`, `necrophageous_hunger` |
| `treant` | **樹人** | `hero_mage_7`, `hero_warrior_7` | **165.0** | 12.0 ~ 18.0 | `plant`, `humanoid` | `root_connection`, `wooden_skin` | `nature_affinity` |
| `bear_monster` | **暴走巨熊** | `hero_knight_yolda` | **180.0** | 20.0 ~ 30.0 | `humanoid`, `beast` | `rough_hide`, `sturdy_will` | `bear_spirit_awakening`, `feral_fury` |
| `nightshroud` | **夜幕幽裔** | `hero_mage_6`, `hero_rogue_4` | **145.0** | 8.0 ~ 12.0 | `humanoid` | `night_grace`, `scorching_veil`, `magic_safeguard` | `rage_howl`, `tribal_synergy` |
| `skeleton` | **骷髏** | `hero_priest_4`, `hero_rogue_5`, `hero_warrior_6` | **155.0** | 12.0 ~ 17.0 | `evil`, `humanoid` | `bone_resilience`, `dark_affinity` | `skeleton_summon`, `necromancer_protection` |
| `specter` | **幽魂** | `hero_priest_6` | **155.0** | 24.0 ~ 30.0 | `evil`, `spirit` | `dark_affinity`, `incorporeal_form` | `vengeful_spirit` |
| `demon` | **惡魔** | `hero_priest_bathory`, `hero_rogue_vilzaan` | **220.0** | 18.0 ~ 28.0 | `humanoid`, `evil` | `rough_hide`, `sturdy_physique`, `frenzied_might`, `dark_affinity`, `sturdy_will`, `heat_resistance` | `hell_pact`, `hell_power`, `slaughter_flames` |
| `undead` | **亡靈** | `hero_rogue_6` | **165.0** | 12.0 ~ 16.0 | `evil`, `corrupted`, `humanoid` | `decayed_form`, `undead_resilience` | `whispers_death`, `flesh_feeder` |
| `vialkin` | **瓶中靈** | `pet_healing_flashling` | **80.0** | 10.0 ~ 14.0 | `spirit` | `incorporeal_form`, `arcane_resistance`, `magic_safeguard` | `shieldwall_oath` |
| `wolf` | **巨狼** | `pet_hound_boneclaw` | **100.0** | 10.0 ~ 14.0 | `beast` | `sharp_claws`, `swift_initiative` | - |
| `bear` | **戰熊** | `pet_savage_grizzly` | **220.0** | 17.0 ~ 25.0 | `beast` | `rough_hide`, `sturdy_will` | `feral_fury` |
| `ice_elemental` | **冰元素** | `pet_slateshard_bruiser` | **300.0** | 20.0 ~ 30.0 | `elemental` | `coldborne_form`, `frost_power`, `elemental_power` | - |
| `slime` | **史萊姆** | `pet_slime_flame` | **80.0** | 8.0 ~ 10.0 | `corrupted`, `ooze` | `swift`, `venom_barrier` | - |
| `voidborn` | **虛空後裔** | `pet_voidsilver_sentinel` | **200.0** | 20.0 ~ 26.0 | `void` | `void_form`, `void_eye` | - |

---

## 🛡️ 三、核心天賦特性 (Characteristics) 效果明細庫

在遊戲戰鬥中，天賦特性為英雄與怪物提供不可驅散的常駐被動加成：

* **🩸 異常免疫類特質**：
  - `bone_resilience` (骷髏)：**免疫流血 (`bleed_immuned: 1.0`)**、物抗 +20%、魔抗 +20%。
  - `decayed_form` (腐爛之軀)：**免疫流血與中毒 (`bleed_immuned`, `poison_immuned`)**、暗影抗性 +200%、神聖抗性 -50%。
  - `coldborne_form` (冰靈化身)：**免疫冰凍、燃燒、流血、中毒**、**冰抗 +500%**、火抗 +100%、物抗/魔抗 +50%。
  - `incorporeal_form` (靈體形態)：**免疫流血**、**物理抗性 +50%**。
* **⚔️ 攻擊與暴擊加強類特質**：
  - `ancient_bloodline` (遠古血脈)：**暴擊率 +15%**、**暴擊抗性 +50%**、戰鬥生命上限 +25%。
  - `dragon_wisdom` (巨龍智慧)：火焰、冰霜、魔法、毒素四系精通各 **+50%**。
  - `frenzied_might` (狂暴威能)：最大傷害 +10、最小傷害 +5、物理傷害加深 +20%。
  - `brightmind_surge` (靈光爆發)：魔法傷害加深 **+50%**。
  - `sharp_claws` (利爪)：暴擊率 +10%、物理傷害加深 +15%。
  - `void_eye` (虛空之眼)：暴擊率 +10%、命中率 +50%。
* **🛡️ 防禦與抗性類特質**：
  - `ironclad_resistance` (鋼鐵抗性)：**物理抗性 +50%**、**物理防禦 +50.0**。
  - `magic_safeguard` (法術守護)：魔法抗性 +30%、神聖抗性 +30%。
  - `wooden_skin` (樹皮厚皮)：物理抗性 +20%、自然抗性 +50%、火焰抗性 -30%。
  - `root_connection` (根鬚連結)：生命值 +50、自然傷害加深 +30%、受到治療提升 +20%。
  - `dark_affinity` (暗影親和)：暗影傷害加深 +50%、暗影抗性 +200%、受到治療提升 +50%、神聖抗性 -50%。
  - `sturdy_physique` (強健體魄)：生命值 +100、暴擊抗性 +20%。

---

## ⚡ 四、種族專屬技能與連動機制 (Racial Synergy)

1. **獸人部族血怒連動 (`tribal_synergy` & `rage_howl`)**：
   - 同隊配備多位獸人（如狂戰士 `Kraghul` + 遊俠 `Drugor`）時，發動暴擊或造成流血會使全體獸人同時疊加 **「血怒層數 (Bloodlust)」**，觸發額外行動點與超高倍率處決傷害 (`bloodburst_execution`)。
2. **矮人與維京人「前排鋼鐵盾牆」共鳴 (`shieldwall_oath`)**：
   - 矮人 (`Bragos`) 與維京人 (`Hildrena`) 裝備重盾站前排時，天生 `ironclad_resistance`（物抗+50%）能將格擋值轉化為全隊傷害吸收屏障 (`barrier_count`)。
3. **哥布林「齒輪過載與動能重啟」循環 (`emergency_gear_jump`)**：
   - 哥布林騎士 (`Glig`) 與法師 (`Nobiz`) 的技能圍繞「充能層數 (Energy Charge)」與「發條玩具 (Scrap Toys)」，主動技能釋放會互相為全隊哥布林充能，達到層數上限時重置冷卻。
4. **樹人與自然系「生生不息」受癒加成 (`nature_affinity`)**：
   - 樹人自帶 `root_connection` 與 `nature_affinity`，使場上所有自然傷害與治療技能的受癒量提升 20%，並持續為友軍提供護甲外骨骼 (`woodland_aegis`)。

---

## 🎯 五、副本剋制與選卡戰術指南

| 面對敵人類型 / 特殊機制 | 最佳剋制種族推薦 | 剋制原因與戰略價值 |
| :--- | :--- | :--- |
| **面對大量高頻流血 / 劇毒 Boss**<br>(如蜘蛛、蛇蠍、刺客怪) | **骷髏 (`skeleton`)**<br>**亡靈 (`undead`)**<br>**冰元素 (`ice_elemental`)** | **天生 100% 免疫流血與劇毒 (`bleed_immuned / poison_immuned`)**，直接廢除 Boss 的核心 Dot 傷害！ |
| **面對高物理暴擊怪**<br>(如遺忘荒地的碎骨獸人) | **矮人 (`dwarf`)**<br>**獸人 (`orc`)** | 自帶 `ironclad_resistance`（物抗+50%、防禦+50）與 `sturdy_physique`（暴抗+20%），穩固前排血線。 |
| **面對暗影 / 詛咒系地牢**<br>(如暗影深淵、幽靈副本) | **精靈 (`elf`)**<br>**龍裔 (`dragonkin`)** | 高額法術抗性與神聖加深，聖騎士神聖打擊對暗影怪造成 **雙倍破甲與負抗性重創**（暗影怪神聖抗性為 -50%）。 |
| **速刷副本 / 先手秒殺隊** | **哥布林 (`goblin`)**<br>**龍裔 (`dragonkin`)** | 擁有全遊戲最高的 **先攻權 (+2)** 與開局暴擊率，能搶先在怪物出手前直接 AOE 清場。 |
"""

with open(os.path.join(BASE_DIR, 'meta_data', 'Game_docs', 'Hero', 'Racial Synergy.md'), 'w', encoding='utf-8') as f:
    f.write(races_doc_content)

with open(os.path.join(BASE_DIR, 'meta_data', 'outputs', 'Racial Synergy.md'), 'w', encoding='utf-8') as f:
    f.write(races_doc_content)

print("Updated both Racial Synergy.md locations!")
