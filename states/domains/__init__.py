from states.domains.base_domain import BaseDomainStrategy
from states.domains.golden_empire import GoldenEmpireStrategy

DOMAIN_STRATEGIES = {
    "golden_empire": GoldenEmpireStrategy,
}

def get_domain_strategy(domain_name: str, handler) -> BaseDomainStrategy:
    """
    領地策略工廠方法。
    依據 domain_name 實例化對應的策略物件，若未指定則預設為 GoldenEmpireStrategy。
    """
    strategy_cls = DOMAIN_STRATEGIES.get(domain_name, GoldenEmpireStrategy)
    return strategy_cls(handler)

__all__ = [
    "BaseDomainStrategy",
    "GoldenEmpireStrategy",
    "get_domain_strategy",
]
