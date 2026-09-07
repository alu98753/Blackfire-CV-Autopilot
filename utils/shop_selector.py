"""
城鎮商店出售輪換選擇策略模組 (Shop Rotation Selector Policy)

依據 Greenfield-lite v1 架構原則：
- 確定性純策略 (Deterministic Policy)：給定商店清單與訪問計數，產出確定性決策。
- 無副作用：不執行 IO、不依賴外部可變 runtime 狀態。
- 穩定排序與平手打破 (Tie-break)：依清單宣告原始順序打破平手。
"""

from __future__ import annotations
from typing import Any, Mapping


def sort_shops_by_visit_count(
    shops: list[dict[str, Any]],
    visit_counts: Mapping[str, int] | None = None
) -> list[dict[str, Any]]:
    """
    依據各商店的歷史出售造訪次數由少至多排序。
    若次數相同，依商店清單原始宣告順序穩定 tie-break。

    :param shops: 商店配置清單，每個項目包含 'id', 'name', 'template'
    :param visit_counts: 商店 id 映射造訪次數字典 (例如 {'jewelry_workshop': 3, ...})
    :return: 排序後的新商店清單 (由造訪次數最少者排在最前)
    """
    if not shops:
        return []

    counts = visit_counts or {}

    indexed_shops = list(enumerate(shops))
    sorted_indexed = sorted(
        indexed_shops,
        key=lambda item: (int(counts.get(item[1].get("id", ""), 0)), item[0])
    )
    return [shop for _, shop in sorted_indexed]


def select_least_visited_shop(
    shops: list[dict[str, Any]],
    visit_counts: Mapping[str, int] | None = None
) -> dict[str, Any] | None:
    """
    從候選商店清單中選出歷史出售造訪次數最少的商店。

    :param shops: 商店配置清單
    :param visit_counts: 商店 id 映射造訪次數字典
    :return: 造訪次數最少的商店字典，若清單為空則回傳 None
    """
    sorted_shops = sort_shops_by_visit_count(shops, visit_counts)
    if not sorted_shops:
        return None
    return sorted_shops[0]
