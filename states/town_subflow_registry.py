"""Town workflow entry contracts, separate from route topology."""

from dataclasses import dataclass

from states.navigation_table import NavigationGoal


@dataclass(frozen=True)
class TownSubflowSpec:
    flow_key: str
    navigation_goal: NavigationGoal = NavigationGoal.REACH_TOWN
    building_template: str | None = None
    requires_red_dot: bool = False
    dispatch_on_town: bool = False


TOWN_SUBFLOW_SPECS = {
    "chest": TownSubflowSpec(
        "chest",
        building_template="town_building/mysterious_treasure/mysterious_treasure.png",
        requires_red_dot=True,
    ),
    "hero_draw": TownSubflowSpec(
        "hero_draw",
        building_template="town_building/Tavern/Tavern.png",
        requires_red_dot=True,
    ),
    "blood_altar": TownSubflowSpec(
        "blood_altar",
        building_template="town_building/Blood_Altar/Blood_Altar.png",
        requires_red_dot=True,
    ),
    "bulletin_board": TownSubflowSpec(
        "bulletin_board",
        building_template="town_building/bulletin_board/bulletin_board.png",
        requires_red_dot=True,
    ),
    "blood_sacrifice": TownSubflowSpec(
        "blood_sacrifice",
        building_template="town_building/Blood_Altar/Blood_Altar.png",
        requires_red_dot=False,
    ),
    "jewelry_workshop": TownSubflowSpec(
        "jewelry_workshop",
        dispatch_on_town=True,
    ),
    "bag_tidy": TownSubflowSpec(
        "bag_tidy",
        dispatch_on_town=True,
    ),
}


def spec_for(flow_key: str) -> TownSubflowSpec:
    return TOWN_SUBFLOW_SPECS.get(
        flow_key,
        TownSubflowSpec(flow_key, dispatch_on_town=True),
    )
