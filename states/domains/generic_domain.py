from states.domains.base_domain import BaseDomainStrategy

class GenericDomainStrategy(BaseDomainStrategy):
    """
    通用領域策略 (Generic Domain Strategy)。
    專為尚未具備專屬策略之合法領域（如淵獸之巢 abyss_beast_nest、冷誓要塞 coldoath_citadel）提供通用行為。
    直接繼承 BaseDomainStrategy 的通用探索 (domains/common/explore_btn.png)
    與通用隨機挖寶事件 (DomainTreasureSubflow)，並維護自身 domain_name，
    絕不無聲 fallback 偽裝成 GoldenEmpireStrategy。
    """
    def __init__(self, handler, domain_name: str = "generic"):
        super().__init__(handler)
        self.domain_name = domain_name
