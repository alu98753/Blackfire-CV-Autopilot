import logging
from states.domains.base_domain import BaseDomainStrategy

class GoldenEmpireStrategy(BaseDomainStrategy):
    """
    🏛️ 黃金古國 (Golden Empire - Domain 1) 策略。
    繼承 BaseDomainStrategy 提供的通用領域探索按鈕與通用挖寶隨機事件處理 (DomainTreasureSubflow)。
    保留擴充空間以承載黃金古國專有之特異邏輯（如專屬卡片入口、專屬祭壇等）。
    """
    def __init__(self, handler):
        super().__init__(handler)
        self.domain_name = "golden_empire"
