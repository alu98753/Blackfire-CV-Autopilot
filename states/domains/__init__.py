from states.domains.base_domain import BaseDomainStrategy
from states.domains.golden_empire import GoldenEmpireStrategy
from states.domains.generic_domain import GenericDomainStrategy
from states.domains.treasure_subflow import DomainTreasureSubflow

DOMAIN_STRATEGIES = {
    "golden_empire": GoldenEmpireStrategy,
}

def get_domain_strategy(domain_name: str, handler) -> BaseDomainStrategy:
    """
    領地策略工廠方法。
    依據 domain_name 實例化對應的策略物件。
    - 若為已知專屬領地（如 golden_empire），回傳對應特化策略實例；
    - 若為未註冊專屬策略之合法領域（如 abyss_beast_nest），回傳 GenericDomainStrategy，
      維持其自身 domain_name，嚴禁 fallback 偽裝成 GoldenEmpireStrategy。
    """
    strategy_cls = DOMAIN_STRATEGIES.get(domain_name)
    if strategy_cls is not None:
        return strategy_cls(handler)
    return GenericDomainStrategy(handler, domain_name=domain_name)

__all__ = [
    "BaseDomainStrategy",
    "GoldenEmpireStrategy",
    "GenericDomainStrategy",
    "DomainTreasureSubflow",
    "get_domain_strategy",
]
