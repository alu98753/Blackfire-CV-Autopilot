import time
import os
import logging
from states.handlers.base import BaseStateHandler

class LoadingHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        過渡載入狀態 (STATE_LOADING)：
        此狀態下只偵測：
        1. 戰鬥特徵是否出現。若出現，零延遲轉移至 STATE_BATTLE。
        2. 超時安全閥（15秒），避免卡死。
        注意：體力不足 (no_bread.png) 的偵測已在 state_machine.py 中作為全域處理攔截，
        本 Handler 不需要重複做體力檢索，只需專心檢索戰鬥特徵與處理超時。
        """
        # 1. 檢索實體戰鬥特徵
        for feat in ["common/auto.png", "battle/battle_features_1.png", "battle/battle_features_2.png"]:
            if os.path.exists(os.path.join("templates", feat)):
                thresh = 0.65 if feat == "common/auto.png" else 0.70
                pos, conf = self.matcher.match(screen_img, feat, threshold=thresh)
                if pos:
                    logging.info(f"⚔️ 載入完成！偵測到戰鬥特徵 [{feat}] (相似度: {conf:.4f})，轉移至 BATTLE 狀態。")
                    self.machine.battle_start_time = time.time()
                    self.machine.transition_to(self.machine.STATE_BATTLE)
                    return

        # 2. 超時判定安全閥
        elapsed = time.time() - getattr(self.machine, "loading_start_time", 0.0)
        if elapsed > 15.0:
            logging.warning("⚠️ 載入超時 (已等待超過 15 秒)，判定可能已卡死或跳轉失敗，將狀態重置為 UNKNOWN 進行自癒定位。")
            self.machine.transition_to(self.machine.STATE_UNKNOWN)
            return

        logging.info(f"⌛ 畫面載入中... (已等待 {elapsed:.1f} 秒)")
