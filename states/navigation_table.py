"""Static v1 adjacency tables for intent actions and shared destinations."""

from dataclasses import dataclass
from enum import Enum

from states.navigation_intent import (
    ActionId,
    IntentId,
    PostconditionId,
    ReasonCode,
)
from utils.scene_snapshot import ElementId, SceneId, TabId


@dataclass(frozen=True)
class NavigationEdge:
    intent_id: IntentId
    source: SceneId
    target: SceneId
    required_element: ElementId
    action: ActionId
    postcondition: PostconditionId
    reason: ReasonCode


class NavigationGoal(str, Enum):
    """Task-agnostic destinations shared by multiple workflows."""

    REACH_TOWN = "reach_town"


@dataclass(frozen=True)
class GoalNavigationEdge:
    goal: NavigationGoal
    source: SceneId
    target: SceneId
    required_element: ElementId
    action: ActionId
    postcondition: PostconditionId
    reason: ReasonCode


@dataclass(frozen=True)
class LobbyTabNavigationEdge:
    source: SceneId
    target_tab: TabId
    required_element: ElementId
    action: ActionId
    postcondition: PostconditionId
    reason: ReasonCode


_TAB_SCENES = {
    TabId.STAGE: SceneId.STAGE_SELECT,
    TabId.DUNGEON: SceneId.DUNGEON_SELECT,
    TabId.DOMAIN: SceneId.DOMAIN_SELECT,
    TabId.LORD: SceneId.LORD_SELECT,
    TabId.DEMON_LORD: SceneId.DEMON_LORD_SELECT,
}

_TAB_ELEMENTS = {
    TabId.STAGE: ElementId.TAB_STAGE,
    TabId.DUNGEON: ElementId.TAB_DUNGEON,
    TabId.DOMAIN: ElementId.TAB_DOMAIN,
    TabId.LORD: ElementId.TAB_LORD,
    TabId.DEMON_LORD: ElementId.TAB_DEMON_LORD,
}

LOBBY_TAB_NAVIGATION_EDGES = tuple(
    LobbyTabNavigationEdge(
        source=source,
        target_tab=target,
        required_element=_TAB_ELEMENTS[target],
        action=ActionId.SWITCH_LOBBY_TAB,
        postcondition=PostconditionId.LOBBY_TAB_ACTIVE,
        reason=ReasonCode.PRIMARY_SWITCH_LOBBY_TAB,
    )
    for source in (SceneId.LOBBY, *_TAB_SCENES.values())
    for target in TabId
    if source != _TAB_SCENES[target]
)


V1_NAVIGATION_EDGES = (
    NavigationEdge(
        IntentId.COLLECT_DIAMOND,
        SceneId.LOBBY,
        SceneId.LOBBY,
        ElementId.CLOSE_OVERLAY,
        ActionId.DISMISS_OVERLAY,
        PostconditionId.OVERLAY_CLOSED,
        ReasonCode.DIAMOND_CLOSE_OVERLAY,
    ),
    NavigationEdge(
        IntentId.COLLECT_DIAMOND,
        SceneId.LOBBY,
        SceneId.TOWN,
        ElementId.GOBACK_TOWN,
        ActionId.RETURN_TOWN,
        PostconditionId.TOWN,
        ReasonCode.DIAMOND_RETURN_TO_TOWN,
    ),
    NavigationEdge(
        IntentId.COLLECT_DIAMOND,
        SceneId.TOWN,
        SceneId.DIAMOND_WINDOW,
        ElementId.DIAMOND_ENTRY,
        ActionId.OPEN_DIAMOND,
        PostconditionId.DIAMOND_WINDOW,
        ReasonCode.DIAMOND_ENTRY_READY,
    ),
    NavigationEdge(
        IntentId.COLLECT_BREAD,
        SceneId.TOWN,
        SceneId.LOBBY,
        ElementId.DOOR,
        ActionId.ENTER_LOBBY,
        PostconditionId.LOBBY,
        ReasonCode.BREAD_ENTER_LOBBY,
    ),
    NavigationEdge(
        IntentId.COLLECT_BREAD,
        SceneId.LOBBY,
        SceneId.BREAD_WINDOW,
        ElementId.BREAD_ENTRY,
        ActionId.OPEN_BREAD,
        PostconditionId.BREAD_WINDOW,
        ReasonCode.BREAD_ENTRY_READY,
    ),
    NavigationEdge(
        IntentId.PRIMARY_NAVIGATION,
        SceneId.TOWN,
        SceneId.LOBBY,
        ElementId.DOOR,
        ActionId.ENTER_LOBBY,
        PostconditionId.LOBBY,
        ReasonCode.PRIMARY_ENTER_LOBBY,
    ),
    NavigationEdge(
        IntentId.PRIMARY_NAVIGATION,
        SceneId.LOBBY,
        SceneId.LOADING,
        ElementId.START,
        ActionId.START_PRIMARY,
        PostconditionId.LOADING_OR_BATTLE,
        ReasonCode.PRIMARY_START_READY,
    ),
    *(
        NavigationEdge(
            IntentId.COLLECT_DIAMOND,
            source,
            SceneId.TOWN,
            ElementId.GOBACK_TOWN,
            ActionId.RETURN_TOWN,
            PostconditionId.TOWN,
            ReasonCode.DIAMOND_RETURN_TO_TOWN,
        )
        for source in (
            SceneId.STAGE_SELECT,
            SceneId.DUNGEON_SELECT,
            SceneId.DOMAIN_SELECT,
            SceneId.LORD_SELECT,
            SceneId.DEMON_LORD_SELECT,
        )
    ),
    *(
        NavigationEdge(
            IntentId.COLLECT_BREAD,
            source,
            SceneId.BREAD_WINDOW,
            ElementId.BREAD_ENTRY,
            ActionId.OPEN_BREAD,
            PostconditionId.BREAD_WINDOW,
            ReasonCode.BREAD_ENTRY_READY,
        )
        for source in (
            SceneId.STAGE_SELECT,
            SceneId.DUNGEON_SELECT,
            SceneId.DOMAIN_SELECT,
            SceneId.LORD_SELECT,
            SceneId.DEMON_LORD_SELECT,
        )
    ),
    NavigationEdge(
        IntentId.PRIMARY_NAVIGATION,
        SceneId.STAGE_SELECT,
        SceneId.LOADING,
        ElementId.START,
        ActionId.START_PRIMARY,
        PostconditionId.LOADING_OR_BATTLE,
        ReasonCode.PRIMARY_START_READY,
    ),
    NavigationEdge(
        IntentId.PRIMARY_NAVIGATION,
        SceneId.DUNGEON_SELECT,
        SceneId.LOADING,
        ElementId.START,
        ActionId.START_PRIMARY,
        PostconditionId.LOADING_OR_BATTLE,
        ReasonCode.PRIMARY_START_READY,
    ),
    NavigationEdge(
        IntentId.PRIMARY_NAVIGATION,
        SceneId.DOMAIN_SELECT,
        SceneId.LOADING,
        ElementId.START,
        ActionId.START_PRIMARY,
        PostconditionId.LOADING_OR_BATTLE,
        ReasonCode.PRIMARY_START_READY,
    ),
    NavigationEdge(

        IntentId.PRIMARY_NAVIGATION,
        SceneId.LOBBY,
        SceneId.LOBBY,
        ElementId.CLOSE_OVERLAY,
        ActionId.DISMISS_OVERLAY,
        PostconditionId.OVERLAY_CLOSED,
        ReasonCode.PRIMARY_CLOSE_OVERLAY,
    ),
    NavigationEdge(
        IntentId.PRIMARY_NAVIGATION,
        SceneId.DUNGEON_SELECT,
        SceneId.DUNGEON_SELECT,
        ElementId.CLOSE_OVERLAY,
        ActionId.DISMISS_OVERLAY,
        PostconditionId.OVERLAY_CLOSED,
        ReasonCode.PRIMARY_CLOSE_OVERLAY,
    ),
)


REACH_TOWN_EDGES = (
    GoalNavigationEdge(
        NavigationGoal.REACH_TOWN,
        SceneId.TOWN_BUILDING,
        SceneId.TOWN,
        ElementId.EXIT_BUILDING_TO_TOWN,
        ActionId.EXIT_BUILDING_TO_TOWN,
        PostconditionId.TOWN,
        ReasonCode.TOWN_SUBFLOW_EXIT_BUILDING,
    ),
    *(
        GoalNavigationEdge(
            NavigationGoal.REACH_TOWN,
            source,
            SceneId.TOWN,
            ElementId.GOBACK_TOWN,
            ActionId.RETURN_TOWN,
            PostconditionId.TOWN,
            ReasonCode.TOWN_SUBFLOW_RETURN_TO_TOWN,
        )
        for source in (
            SceneId.LOBBY,
            SceneId.STAGE_SELECT,
            SceneId.DUNGEON_SELECT,
            SceneId.LORD_SELECT,
            SceneId.DEMON_LORD_SELECT,
        )
    ),
    GoalNavigationEdge(
        NavigationGoal.REACH_TOWN,
        SceneId.DOMAIN_EXPLORE,
        SceneId.LOBBY,
        ElementId.EXIT_TO_LOBBY,
        ActionId.EXIT_DOMAIN_TO_LOBBY,
        PostconditionId.LOBBY,
        ReasonCode.TOWN_SUBFLOW_EXIT_DOMAIN,
    ),
)


class NavigationTable:
    """Return the first declared edge satisfied by one immutable snapshot."""

    def __init__(
        self,
        edges=V1_NAVIGATION_EDGES,
        goal_edges=REACH_TOWN_EDGES,
        tab_edges=LOBBY_TAB_NAVIGATION_EDGES,
    ):
        self.edges = tuple(edges)
        self.goal_edges = tuple(goal_edges)
        self.tab_edges = tuple(tab_edges)

    def next_tab_edge(self, scene, target_tab):
        for edge in self.tab_edges:
            if (
                edge.source == scene.scene
                and edge.target_tab == target_tab
                and scene.has(edge.required_element)
            ):
                return edge
        return None

    def next_edge(self, scene, intent_id):
        for edge in self.edges:
            if (
                edge.intent_id == intent_id
                and edge.source == scene.scene
                and scene.has(edge.required_element)
            ):
                return edge
        return None

    def next_goal_edge(self, scene, goal):
        for edge in self.goal_edges:
            if (
                edge.goal == goal
                and edge.source == scene.scene
                and scene.has(edge.required_element)
            ):
                return edge
        return None
