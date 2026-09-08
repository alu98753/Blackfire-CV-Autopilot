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


def sort_shops_by_gold_balance(
    shops: list[dict[str, Any]],
    gold_balances: Mapping[str, int | None] | None = None
) -> list[dict[str, Any]]:
    """
    依據各商店商人的金幣餘額進行排序 (貪婪算法 Greedy + 探勘優先)：
    1. 未知 (None 或未在字典中) 優先：代表今日尚未探訪，優先進去探勘商人資金。
    2. 已知金幣降序 (Greedy)：金幣越多的商人排越前面。
    3. 平手打破 (Tie-break)：若金幣相同（或均為未知），依商店清單原始宣告順序穩定 tie-break。

    :param shops: 商店配置清單，每個項目包含 'id', 'name', 'template'
    :param gold_balances: 商店 id 映射金幣餘額字典 (例如 {'jewelry_workshop': 21413, 'alchemy_hut': None, ...})
    :return: 排序後的新商店清單 (未探勘優先，其次金幣最多者排在最前)
    """
    if not shops:
        return []

    balances = gold_balances or {}

    indexed_shops = list(enumerate(shops))

    def _calc_sort_key(item: tuple[int, dict[str, Any]]) -> tuple[int, int, int]:
        idx, shop = item
        sid = shop.get("id", "")
        gold = balances.get(sid, None)

        # 優先級 0: 未知金幣 (None) 優先探勘
        if gold is None:
            return (0, 0, idx)

        # 優先級 1: 已知金幣，數值越大負值越小，排在越前面
        return (1, -int(gold), idx)

    sorted_indexed = sorted(indexed_shops, key=_calc_sort_key)
    return [shop for _, shop in sorted_indexed]


def select_best_shop_by_gold(
    shops: list[dict[str, Any]],
    gold_balances: Mapping[str, int | None] | None = None
) -> dict[str, Any] | None:
    """
    從候選商店清單中選出最優商店 (未探勘優先，其次金幣最多者)。

    :param shops: 商店配置清單
    :param gold_balances: 商店 id 映射金幣餘額字典
    :return: 最優首選商店字典，若清單為空則回傳 None
    """
    sorted_shops = sort_shops_by_gold_balance(shops, gold_balances)
    if not sorted_shops:
        return None
    return sorted_shops[0]

