"""Scoped detector groups for low-cost scene perception."""

from enum import Enum

from utils.scene_snapshot import DetectionProfileId


class DetectorGroup(str, Enum):
    SAFETY = "safety"
    TOWN = "town"
    LOBBY = "lobby"
    TABS = "tabs"
    DUNGEON = "dungeon"
    OTHER = "other"


class DetectorRegistry:
    """管理並解析不同感知場景（DetectionProfileId）所允許啟用的偵測器群組（DetectorGroup）。
    透過選擇性感知（Selective Perception）機制，在特定控制階段或導航場景下
    僅執行必要的 Detector 白名單群組，避免全量模板比對造成的 FPS 損耗與誤判。
    職責邊界：
    - 維護 Profile 與 DetectorGroup 集合的靜態對應關係。
    - 提供以 Profile 或其別名查詢允許群組集合的介面。
    - 不持有 Detector 實例，亦不介入具體比對執行。
    """

    _PROFILE_GROUPS = {
        DetectionProfileId.UNKNOWN: frozenset(DetectorGroup),
        DetectionProfileId.TOWN: frozenset(
            {DetectorGroup.SAFETY, DetectorGroup.TOWN}
        ),
        DetectionProfileId.LOBBY: frozenset(
            {
                DetectorGroup.SAFETY,
                DetectorGroup.TOWN,
                DetectorGroup.LOBBY,
                DetectorGroup.TABS,
            }
        ),
        DetectionProfileId.STAGE_SELECT: frozenset(
            {
                DetectorGroup.SAFETY,
                DetectorGroup.TOWN,
                DetectorGroup.LOBBY,
                DetectorGroup.TABS,
            }
        ),
        DetectionProfileId.DUNGEON_SELECT: frozenset(
            {
                DetectorGroup.SAFETY,
                DetectorGroup.TOWN,
                DetectorGroup.LOBBY,
                DetectorGroup.TABS,
                DetectorGroup.DUNGEON,
            }
        ),
        DetectionProfileId.DOMAIN_SELECT: frozenset(
            {
                DetectorGroup.SAFETY,
                DetectorGroup.TOWN,
                DetectorGroup.LOBBY,
                DetectorGroup.TABS,
            }
        ),
        DetectionProfileId.LORD_SELECT: frozenset(
            {
                DetectorGroup.SAFETY,
                DetectorGroup.TOWN,
                DetectorGroup.LOBBY,
                DetectorGroup.TABS,
            }
        ),
        DetectionProfileId.DEMON_LORD_SELECT: frozenset(
            {
                DetectorGroup.SAFETY,
                DetectorGroup.TOWN,
                DetectorGroup.LOBBY,
                DetectorGroup.TABS,
            }
        ),
        DetectionProfileId.LOADING: frozenset({DetectorGroup.SAFETY}),
        DetectionProfileId.BATTLE: frozenset({DetectorGroup.SAFETY}),
        DetectionProfileId.RESULT: frozenset({DetectorGroup.SAFETY}),
    }

    def groups_for(self, profile: DetectionProfileId):
        return self._PROFILE_GROUPS[profile]

    def allows_group(self, profile, group):
        return group in self.groups_for(profile)

    def allows_template(self, profile, template_name, runtime_templates=()):
        if profile == DetectionProfileId.UNKNOWN:
            return True
        group = self.classify(template_name, runtime_templates)
        return self.allows_group(profile, group)

    @staticmethod
    def classify(template_name, runtime_templates=()):
        if template_name in {"task_complete.png", "dungeons/dungeons_complete.png"}:
            return DetectorGroup.SAFETY
        if template_name in {"common/door.png", "diamond.png"}:
            return DetectorGroup.TOWN
        if template_name in {
            "goback_town.png",
            "common/bread.png",
            "common/quit.png",
        }:
            return DetectorGroup.LOBBY
        if template_name in runtime_templates:
            return runtime_templates[template_name]
        if template_name in {
            "common/select_stage.png",
            "common/select_stage_after.png",
            "dungeons/dungeon.png",
            "dungeons/dungeon_after.png",
            "domains/Domains_entry.png",
            "domains/Domains_entry_after.png",
            "load/Lord_entry.png",
            "load/Lord_entry_after.png",
            "demon_lords/demon_lords_entry.png",
            "demon_lords/demon_lords_entry_after.png",
            "common/locked_entry.png",
        }:
            return DetectorGroup.TABS
        if template_name.startswith("dungeons/"):
            return DetectorGroup.DUNGEON
        return DetectorGroup.OTHER
