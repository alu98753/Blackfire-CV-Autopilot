"""Canonical scene metadata for the Greenfield-lite runtime."""

from dataclasses import dataclass
from types import MappingProxyType

from utils.scene_snapshot import DetectionProfileId, SceneId


@dataclass(frozen=True)
class SceneDefinition:
    scene_id: SceneId
    detection_profile: DetectionProfileId


class SceneCatalog:
    """Own the single SceneId-to-detection-profile mapping."""

    _DEFINITIONS = MappingProxyType(
        {
            SceneId.UNKNOWN: SceneDefinition(
                SceneId.UNKNOWN, DetectionProfileId.UNKNOWN
            ),
            SceneId.TOWN: SceneDefinition(SceneId.TOWN, DetectionProfileId.TOWN),
            SceneId.LOBBY: SceneDefinition(
                SceneId.LOBBY, DetectionProfileId.LOBBY
            ),
            SceneId.DIAMOND_WINDOW: SceneDefinition(
                SceneId.DIAMOND_WINDOW, DetectionProfileId.TOWN
            ),
            SceneId.BREAD_WINDOW: SceneDefinition(
                SceneId.BREAD_WINDOW, DetectionProfileId.LOBBY
            ),
            SceneId.STAGE_SELECT: SceneDefinition(
                SceneId.STAGE_SELECT, DetectionProfileId.STAGE_SELECT
            ),
            SceneId.DUNGEON_SELECT: SceneDefinition(
                SceneId.DUNGEON_SELECT, DetectionProfileId.DUNGEON_SELECT
            ),
            SceneId.DOMAIN_SELECT: SceneDefinition(
                SceneId.DOMAIN_SELECT, DetectionProfileId.DOMAIN_SELECT
            ),
            SceneId.LORD_SELECT: SceneDefinition(
                SceneId.LORD_SELECT, DetectionProfileId.LORD_SELECT
            ),
            SceneId.DEMON_LORD_SELECT: SceneDefinition(
                SceneId.DEMON_LORD_SELECT, DetectionProfileId.DEMON_LORD_SELECT
            ),
            SceneId.STAGE_LOBBY: SceneDefinition(
                SceneId.STAGE_LOBBY, DetectionProfileId.STAGE_SELECT
            ),
            SceneId.DUNGEON_LOBBY: SceneDefinition(
                SceneId.DUNGEON_LOBBY, DetectionProfileId.DUNGEON_SELECT
            ),
            SceneId.DUNGEON_EXPLORING: SceneDefinition(
                SceneId.DUNGEON_EXPLORING, DetectionProfileId.DUNGEON_SELECT
            ),
            SceneId.LOADING: SceneDefinition(
                SceneId.LOADING, DetectionProfileId.LOADING
            ),
            SceneId.BATTLE: SceneDefinition(
                SceneId.BATTLE, DetectionProfileId.BATTLE
            ),
            SceneId.RESULT: SceneDefinition(
                SceneId.RESULT, DetectionProfileId.RESULT
            ),
            SceneId.DOMAIN_EXPLORE: SceneDefinition(
                SceneId.DOMAIN_EXPLORE, DetectionProfileId.DOMAIN
            ),
        }
    )

    @classmethod
    def definition_for(cls, scene_id):
        return cls._DEFINITIONS.get(scene_id, cls._DEFINITIONS[SceneId.UNKNOWN])

    @classmethod
    def profile_for(cls, scene_id):
        return cls.definition_for(scene_id).detection_profile

    @classmethod
    def registered_scenes(cls):
        return frozenset(cls._DEFINITIONS)
