from utils.sub_stage_navigator import UNIVERSAL_SUB_STAGES


def get_stage_configs(base_levels=None, templates_dir="templates"):
    """
    動態根據關卡清單，解析出目前允許選擇的大關與小關卡對應表。
    全關卡統一使用核心通用子關卡模板：
      - 第一小關 (first):  stages/first_stage.png
      - 中間小關 (middle): stages/boss_skull.png
      - 第六小關 (six):    stages/six_stage.png
      - 魔王關卡 (final):  stages/boss_skull.png
    """
    if base_levels is None:
        from config import BASE_STAGE_LEVELS
        base_levels = BASE_STAGE_LEVELS

    configs = {}
    for lvl_id, lvl_info in base_levels.items():
        configs[lvl_id] = {
            "name": lvl_info["name"],
            "entry": lvl_info["entry"],
            "sub_stages": dict(UNIVERSAL_SUB_STAGES),
        }
    return configs
