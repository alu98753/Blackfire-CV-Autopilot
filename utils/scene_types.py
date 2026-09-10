"""Domain contracts and declarative scene types for scene recognition.

This module defines pure data contracts (Enums, dataclasses) without any
OpenCV, image processing, or TemplateMatcher dependencies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class SceneId(str, Enum):
    """Canonical identifier for recognized scenes across the system."""

    UNKNOWN = "unknown"
    TOWN = "town"
    TOWN_BUILDING = "town_building"
    LOBBY = "lobby"
    DIAMOND_WINDOW = "diamond_window"
    BREAD_WINDOW = "bread_window"
    STAGE_SELECT = "stage_select"
    DUNGEON_SELECT = "dungeon_select"
    DOMAIN_SELECT = "domain_select"
    LORD_SELECT = "lord_select"
    DEMON_LORD_SELECT = "demon_lord_select"
    STAGE_LOBBY = "stage_lobby"
    DUNGEON_LOBBY = "dungeon_lobby"
    DUNGEON_EXPLORING = "dungeon_exploring"
    LOADING = "loading"
    BATTLE = "battle"
    RESULT = "result"
    DOMAIN_EXPLORE = "domain_explore"
    POPUP_TASK_COMPLETE = "popup_task_complete"
    POPUP_UNEXPECTED = "popup_unexpected"

    # Backward compatibility aliases (attribute aliases)
    LOBBY_STAGE = STAGE_SELECT
    LOBBY_DUNGEON = DUNGEON_SELECT
    LOBBY_OTHER = LOBBY
    IN_DUNGEON = DUNGEON_EXPLORING
    DUNGEON_PREPARE = DUNGEON_LOBBY
    WINDOW_DIAMOND = DIAMOND_WINDOW
    WINDOW_BREAD = BREAD_WINDOW


# Global type alias for seamless backward compatibility
SceneType = SceneId


@dataclass(frozen=True)
class LobbyTabDefinition:
    """Declarative definition for an active/inactive tab button pair in Lobby."""

    name: str
    active_template: str
    inactive_template: str
    scene_type: SceneId
    config_active_key: Optional[str] = None
    config_inactive_key: Optional[str] = None


LOBBY_TAB_DEFINITIONS: Tuple[LobbyTabDefinition, ...] = (
    LobbyTabDefinition(
        name="stage",
        active_template="common/select_stage_after.png",
        inactive_template="common/select_stage.png",
        scene_type=SceneId.STAGE_SELECT,
    ),
    LobbyTabDefinition(
        name="dungeon",
        active_template="dungeons/dungeon_after.png",
        inactive_template="dungeons/dungeon.png",
        scene_type=SceneId.DUNGEON_SELECT,
    ),
    LobbyTabDefinition(
        name="domain",
        active_template="domains/Domains_entry_after.png",
        inactive_template="domains/Domains_entry.png",
        scene_type=SceneId.DOMAIN_SELECT,
        config_active_key="domain_tab_after_btn",
        config_inactive_key="domain_tab_btn",
    ),
    LobbyTabDefinition(
        name="lord",
        active_template="load/Lord_entry_after.png",
        inactive_template="load/Lord_entry.png",
        scene_type=SceneId.LORD_SELECT,
        config_active_key="entry_after_btn",
        config_inactive_key="entry_btn",
    ),
    LobbyTabDefinition(
        name="demon_lord",
        active_template="demon_lords/demon_lords_entry_after.png",
        inactive_template="demon_lords/demon_lords_entry.png",
        scene_type=SceneId.DEMON_LORD_SELECT,
        config_active_key="entry_after_btn",
        config_inactive_key="entry_btn",
    ),
)


@dataclass(frozen=True)
class SceneAnchorSpec:
    """Declarative anchor rules for a scene (evidence-driven, zero priority)."""

    scene_id: SceneId
    required_any: Tuple[str, ...] = ()
    required_all: Tuple[str, ...] = ()
    excluded_any: Tuple[str, ...] = ()
    min_confidence: float = 0.70


@dataclass
class SceneInfo:
    """Observation result of a single frame produced by SceneDetector."""

    scene_type: SceneId
    is_town: bool = False
    is_lobby: bool = False
    is_in_dungeon: bool = False
    is_dungeon_prepare: bool = False
    active_tabs: List[str] = field(default_factory=list)
    matched_elements: Dict[str, Tuple[Tuple[int, int], float]] = field(default_factory=dict)

    @property
    def scene_id(self) -> SceneId:
        """Canonical property alias for scene_type."""
        return self.scene_type

    def to_snapshot(
        self,
        *,
        frame_id: int = 0,
        captured_at: float = 0.0,
        start_template: Optional[str] = None,
    ):
        """Adapt this observation into an immutable Greenfield-lite SceneSnapshot."""
        from utils.scene_snapshot import snapshot_from_scene_info

        return snapshot_from_scene_info(
            self,
            frame_id=frame_id,
            captured_at=captured_at,
            start_template=start_template,
        )
