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
    """Resolve the bounded detector groups allowed for one control phase."""

    _PROFILE_GROUPS = {
        DetectionProfileId.UNKNOWN: frozenset(DetectorGroup),
        DetectionProfileId.TOWN: frozenset(
            {DetectorGroup.SAFETY, DetectorGroup.TOWN}
        ),
        DetectionProfileId.LOBBY: frozenset(
            {
                DetectorGroup.SAFETY,
                DetectorGroup.LOBBY,
                DetectorGroup.TABS,
            }
        ),
        DetectionProfileId.STAGE_SELECT: frozenset(
            {DetectorGroup.SAFETY, DetectorGroup.LOBBY, DetectorGroup.TABS}
        ),
        DetectionProfileId.DUNGEON_SELECT: frozenset(
            {
                DetectorGroup.SAFETY,
                DetectorGroup.LOBBY,
                DetectorGroup.TABS,
                DetectorGroup.DUNGEON,
            }
        ),
        DetectionProfileId.DOMAIN_SELECT: frozenset(
            {DetectorGroup.SAFETY, DetectorGroup.LOBBY, DetectorGroup.TABS}
        ),
        DetectionProfileId.LORD_SELECT: frozenset(
            {DetectorGroup.SAFETY, DetectorGroup.LOBBY, DetectorGroup.TABS}
        ),
        DetectionProfileId.DEMON_LORD_SELECT: frozenset(
            {DetectorGroup.SAFETY, DetectorGroup.LOBBY, DetectorGroup.TABS}
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
        if template_name == "task_complete.png":
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
            "common/select_stage_after.png",
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
