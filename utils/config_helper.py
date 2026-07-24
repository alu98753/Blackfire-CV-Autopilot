import os

BASE_STAGE_LEVELS = {
    "1": {"name": "蒼穹平原", "entry": "stages/level1_sky_plains.png"},
    "2": {"name": "荒蕪岩地", "entry": "stages/level2_barren_rocks.png"},
    "3": {"name": "古樹森林", "entry": "stages/level3_ancient_forest.png"},
    "4": {"name": "沙漠廢墟", "entry": "stages/level4_desert_ruins.png"},
    "5": {"name": "幽暗沼澤", "entry": "stages/level5_gloomy_swamp.png"},
    "6": {"name": "冰雪洞窟", "entry": "stages/level6_ice_cave.png"},
}

def get_stage_configs(templates_dir="templates"):
    """
    動態根據檔案系統中的實際模板圖片，解析出目前允許選擇的大關與小關卡對應表
    命名規範：
      - 第一小關 (first):  stages/first_stage.png
      - 中間小關 (middle): stages/level{X}_middle.png
      - 第六小關 (six):    stages/six_stage.png
      - 魔王關卡 (final):  stages/level{X}_final.png
    """
    configs = {}
    for lvl_id, lvl_info in BASE_STAGE_LEVELS.items():
        sub_stages = {}
        
        # 1. 第一小關 (通用固定名稱)
        if os.path.exists(os.path.join(templates_dir, "stages/first_stage.png")):
            sub_stages["first"] = "stages/first_stage.png"
            
        # 2. 中間小關 (大關獨立名稱: levelX_middle.png)
        mid_path = f"stages/level{lvl_id}_middle.png"
        if os.path.exists(os.path.join(templates_dir, mid_path)):
            sub_stages["middle"] = mid_path
            
        # 3. 第六小關 (通用固定名稱)
        if os.path.exists(os.path.join(templates_dir, "stages/six_stage.png")):
            sub_stages["six"] = "stages/six_stage.png"
            
        # 4. 魔王關卡 (大關獨立名稱: levelX_final.png)
        final_path = f"stages/level{lvl_id}_final.png"
        if os.path.exists(os.path.join(templates_dir, final_path)):
            sub_stages["final"] = final_path
            
        configs[lvl_id] = {
            "name": lvl_info["name"],
            "entry": lvl_info["entry"],
            "sub_stages": sub_stages
        }
    return configs
