import os
import time
import logging
from enum import Enum
from states.handlers.base import BaseStateHandler
from utils.debug_artifacts import write_debug_image

class DemonSubScene(str, Enum):
    """深淵魔王子場景定義 (Greenfield-lite v1)"""
    UNKNOWN = "UNKNOWN"
    TOWN = "TOWN"
    LOBBY_OTHER_TAB = "LOBBY_OTHER_TAB"
    CARD_SELECTION = "CARD_SELECTION"
    PREPARE_MODAL = "PREPARE_MODAL"
    STONE_DIALOG = "STONE_DIALOG"

class DemonLordsHandler(BaseStateHandler):
    """深淵魔王狀態處理器 (Greenfield-lite v1)"""
    TAB_THRESHOLD = 0.70
    BOSS_CARD_THRESHOLD = 0.78
    SLOT_THRESHOLD = 0.70
    STONE_THRESHOLD = 0.75
    CHOOSE_THRESHOLD = 0.90
    START_THRESHOLD = 0.80

    DEFAULT_STONE_TEMPLATES = {
        "1": "demon_lords/meterial/demon_seal_stone_1.png",
        "2": "demon_lords/meterial/demon_seal_stone_2.png",
        "3": "demon_lords/meterial/demon_seal_stone_3.png",
        "4": "demon_lords/meterial/demon_seal_stone_4.png",
    }

    def __init__(self, machine):
        super().__init__(machine)
        self.current_target_boss = None
        self.pending_stone_queue = []

    def reset_state(self):
        self.current_target_boss = None
        self.pending_stone_queue = []

    def handle(self, screen_img, rect):
        dm = getattr(self.machine, "daily_manager", None)
        if dm and hasattr(dm, "is_demon_lords_available"):
            avail, reason = dm.is_demon_lords_available()
            if not avail:
                logging.info(f"🎉 [深淵魔王] {reason}！結束子流程並切換下一任務...")
                if hasattr(dm, "record_subflow_completed"):
                    dm.record_subflow_completed("demon_lords")
                self.reset_state()
                self.machine.pop_and_next_town_subflow()
                return True

        if self._handle_popup_guards(screen_img, rect):
            return True

        subscene = self.classify_subscene(screen_img)
        return self._dispatch_navigation(subscene, screen_img, rect)

    def classify_subscene(self, screen_img) -> DemonSubScene:
        """純感知分類器：宏觀錨點優先，無點擊副作用"""
        pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.85, quiet=True)
        if pos_door:
            return DemonSubScene.TOWN

        choose_btn = self.machine.config.get("choose_btn", "common/choose.png")
        if os.path.exists(os.path.join("templates", choose_btn)):
            pos_choose, _ = self.matcher.match(screen_img, choose_btn, threshold=self.CHOOSE_THRESHOLD, quiet=True)
            if pos_choose:
                return DemonSubScene.STONE_DIALOG

        stone_container = self.machine.config.get("stone_container_btn", "demon_lords/meterial/stone_slot.png")
        if os.path.exists(os.path.join("templates", stone_container)):
            if self.matcher.match(screen_img, stone_container, threshold=0.70, quiet=True)[0]:
                return DemonSubScene.PREPARE_MODAL

        empty_slot = self.machine.config.get("empty_slot_btn", "demon_lords/meterial/slot.png")
        if os.path.exists(os.path.join("templates", empty_slot)):
            if self.matcher.match(screen_img, empty_slot, threshold=self.SLOT_THRESHOLD, quiet=True)[0]:
                return DemonSubScene.PREPARE_MODAL

        start_btn = self.machine.config.get("start_btn", "stages/start.png")
        if self.current_target_boss and os.path.exists(os.path.join("templates", start_btn)):
            if self.matcher.match(screen_img, start_btn, threshold=self.START_THRESHOLD, quiet=True)[0]:
                return DemonSubScene.PREPARE_MODAL

        entry_after = self.machine.config.get("entry_after_btn", "demon_lords/demon_lords_entry_after.png")
        entry_before = self.machine.config.get("entry_btn", "demon_lords/demon_lords_entry.png")
        is_opened, _, _, _ = self.match_mutually_exclusive_tabs(
            screen_img, entry_after, entry_before, margin=0.02, threshold=self.TAB_THRESHOLD
        )
        if is_opened:
            return DemonSubScene.CARD_SELECTION

        if os.path.exists(os.path.join("templates", entry_before)):
            if self.matcher.match(screen_img, entry_before, threshold=0.75, quiet=True)[0]:
                return DemonSubScene.LOBBY_OTHER_TAB

        return DemonSubScene.UNKNOWN

    def _dispatch_navigation(self, subscene: DemonSubScene, screen_img, rect):
        dispatch_table = {
            DemonSubScene.TOWN: self._step_enter_lobby,
            DemonSubScene.LOBBY_OTHER_TAB: self._step_switch_to_demon_tab,
            DemonSubScene.CARD_SELECTION: self._step_select_boss_card,
            DemonSubScene.PREPARE_MODAL: self._step_handle_prepare_modal,
            DemonSubScene.STONE_DIALOG: self._step_handle_stone_dialog,
        }
        handler_step = dispatch_table.get(subscene)
        return handler_step(screen_img, rect) if handler_step else False

    def _step_enter_lobby(self, screen_img, rect):
        pos_door, conf = self.matcher.match(screen_img, "common/door.png", threshold=0.85, quiet=True)
        if pos_door:
            logging.info(f"🚪 [深淵魔王] 城鎮點擊大廳門入口 [{conf:.4f}]...")
            self.mouse.click(rect["left"] + pos_door[0], rect["top"] + pos_door[1])
            time.sleep(0.4)
            return True
        return False

    def _step_switch_to_demon_tab(self, screen_img, rect):
        entry_before = self.machine.config.get("entry_btn", "demon_lords/demon_lords_entry.png")
        pos_entry, conf = self.matcher.match(screen_img, entry_before, threshold=0.75, quiet=True)
        if pos_entry:
            logging.info(f"👑 [深淵魔王] 點擊魔王頁籤入口 [{conf:.4f}]...")
            self.mouse.click(rect["left"] + pos_entry[0], rect["top"] + pos_entry[1])
            time.sleep(0.4)
            return True
        return False

    def _step_select_boss_card(self, screen_img, rect):
        target_key = self.machine.config.get("target_boss", "voidborn_elres")
        boss_cfg = self.machine.config.get("bosses", {}).get(target_key, {})
        card_template = boss_cfg.get("template", "demon_lords/voidborn_elres.png")
        if os.path.exists(os.path.join("templates", card_template)):
            pos_card, conf = self.matcher.match(screen_img, card_template, threshold=self.BOSS_CARD_THRESHOLD, quiet=True)
            if pos_card:
                boss_name = boss_cfg.get("name", target_key)
                logging.info(f"🎯 [深淵魔王] 點擊魔王卡片 [{boss_name}] ({conf:.4f}) 進入準備介面...")
                self.mouse.click(rect["left"] + pos_card[0], rect["top"] + pos_card[1])
                self.current_target_boss = target_key
                time.sleep(0.6)
                return True
        return False

    def _step_handle_prepare_modal(self, screen_img, rect):
        pos_slot, conf_slot = self._find_empty_slot(screen_img)
        if pos_slot:
            if not self.pending_stone_queue:
                self.pending_stone_queue = self._build_stone_plan_queue()
                logging.info(f"📋 [深淵魔王] 初始化鑲嵌計畫: {self.pending_stone_queue}")

            empty_slot_btn = self.machine.config.get("empty_slot_btn", "demon_lords/meterial/slot.png")
            logging.info(f"👉 [深淵魔王] 點擊空插槽 [{empty_slot_btn}] ({conf_slot:.4f})...")
            self.mouse.click(rect["left"] + pos_slot[0], rect["top"] + pos_slot[1])
            time.sleep(0.5)
            return True

        start_btn = self.machine.config.get("start_btn", "stages/start.png")
        if os.path.exists(os.path.join("templates", start_btn)):
            pos_start, conf_start = self.matcher.match(screen_img, start_btn, threshold=self.START_THRESHOLD, quiet=True)
            if pos_start:
                return self._launch_demon_battle(rect, pos_start, conf_start)
        return False

    def _step_handle_stone_dialog(self, screen_img, rect):
        """STONE_DIALOG 躍遷：Scoped ROI 選取封印石並確認，診斷圖輸出至 scratch/debug"""
        h, w = screen_img.shape[:2]
        left_half = screen_img[:, :w // 2]
        choose_btn = self.machine.config.get("choose_btn", "common/choose.png")

        # 輸出診斷搜尋範圍截圖
        write_debug_image("debug_demon_stone_search.png", left_half)
        scale_val = getattr(self.matcher, "_compute_auto_scale", lambda _: 1.0)(w)
        try:
            full_scale = float(scale_val)
        except (TypeError, ValueError):
            full_scale = 1.0

        if not self.pending_stone_queue:
            self.pending_stone_queue = self._build_stone_plan_queue()
        target_tier = self.pending_stone_queue[0]
        stone_template = self._get_stone_template(target_tier)

        pos_stone, conf_stone = None, 0.0
        if os.path.exists(os.path.join("templates", stone_template)):
            pos_stone, conf_stone = self.matcher.match(
                left_half, stone_template, threshold=self.STONE_THRESHOLD, scale=full_scale, quiet=True
            )
            logging.info(
                f"🔍 [深淵魔王・選石診斷] {target_tier} 階封印石 [{stone_template}] "
                f"相似度: {conf_stone:.4f} (門檻: {self.STONE_THRESHOLD}, Scale: {full_scale:.3f}, 座標: {pos_stone})"
            )

        if not pos_stone and target_tier not in ["1", "demon_seal_stone_1"]:
            fallback = self._get_stone_template("1")
            logging.warning(
                f"⚠️ [深淵魔王] 未檢測到 {target_tier} 階石 (最高相似度: {conf_stone:.4f} < {self.STONE_THRESHOLD})，"
                f"搜尋範圍已存至 scratch/debug/debug_demon_stone_search.png，嘗試降級 1 階 [{fallback}]..."
            )
            if os.path.exists(os.path.join("templates", fallback)):
                pos_stone, conf_stone = self.matcher.match(
                    left_half, fallback, threshold=self.STONE_THRESHOLD, scale=full_scale, quiet=True
                )
                logging.info(f"🔍 [深淵魔王・選石診斷] 降級 1 階石 [{fallback}] 相似度: {conf_stone:.4f}, 座標: {pos_stone}")

        if pos_stone:
            logging.info(f"💎 [深淵魔王] 選取封印石 ({conf_stone:.4f})...")
            self.mouse.click(rect["left"] + pos_stone[0], rect["top"] + pos_stone[1])
            time.sleep(0.3)

        if os.path.exists(os.path.join("templates", choose_btn)):
            pos_choose, conf_choose = self.matcher.match(screen_img, choose_btn, threshold=self.CHOOSE_THRESHOLD, quiet=True)
            if pos_choose:
                logging.info(f"✅ [深淵魔王] 點擊確認選擇 [{choose_btn}] ({conf_choose:.4f})...")
                self.mouse.click(rect["left"] + pos_choose[0], rect["top"] + pos_choose[1])
                if self.pending_stone_queue:
                    popped = self.pending_stone_queue.pop(0)
                    logging.info(f"📌 [深淵魔王] 已鑲嵌: {popped} 階石，剩餘待鑲嵌: {self.pending_stone_queue}")
                time.sleep(0.6)
                return True
        return False

    def _build_stone_plan_queue(self):
        selection = self.machine.config.get("stone_selection", {"2": 1, "1": 2})
        normalized = []
        for k, count in selection.items():
            tier_str = str(k).replace("demon_seal_stone_", "")
            try:
                tier_num = int(tier_str)
            except ValueError:
                tier_num = 1
            normalized.append((tier_num, str(k), int(count)))

        normalized.sort(key=lambda x: x[0], reverse=True)
        queue = []
        for _, raw_key, count in normalized:
            for _ in range(count):
                queue.append(raw_key)

        return queue if queue else ["1", "1", "1"]

    def _get_stone_template(self, tier_or_key):
        templates = self.machine.config.get("stone_templates", self.DEFAULT_STONE_TEMPLATES)
        key_str = str(tier_or_key)
        tier_only = key_str.replace("demon_seal_stone_", "")
        if key_str in templates:
            return templates[key_str]
        if tier_only in templates:
            return templates[tier_only]
        return self.DEFAULT_STONE_TEMPLATES.get(tier_only, "demon_lords/meterial/demon_seal_stone_1.png")

    def _find_empty_slot(self, screen_img):
        empty_slot_btn = self.machine.config.get("empty_slot_btn", "demon_lords/meterial/slot.png")
        stone_container = self.machine.config.get("stone_container_btn", "demon_lords/meterial/stone_slot.png")

        if not os.path.exists(os.path.join("templates", empty_slot_btn)):
            return None, 0.0

        if os.path.exists(os.path.join("templates", stone_container)):
            pos_c, _ = self.matcher.match(screen_img, stone_container, threshold=0.70, quiet=True)
            if pos_c:
                h, w = screen_img.shape[:2]
                cx, cy = pos_c
                y1, y2 = max(0, cy - 100), min(h, cy + 100)
                x1, x2 = max(0, cx - 350), min(w, cx + 350)
                crop = screen_img[y1:y2, x1:x2]
                pos_in_crop, conf_in_crop = self.matcher.match(crop, empty_slot_btn, threshold=self.SLOT_THRESHOLD, quiet=True)
                if pos_in_crop:
                    return (x1 + pos_in_crop[0], y1 + pos_in_crop[1]), conf_in_crop

        pos_slot, conf_slot = self.matcher.match(screen_img, empty_slot_btn, threshold=self.SLOT_THRESHOLD, quiet=True)
        return (pos_slot, conf_slot) if pos_slot else (None, 0.0)

    def _launch_demon_battle(self, rect, pos_start, conf_start):
        boss_key = self.current_target_boss or self.machine.config.get("target_boss", "voidborn_elres")
        logging.info(f"🚀 [深淵魔王] 封印石全滿，開始戰鬥 [{conf_start:.4f}] 討伐 [{boss_key}]...")
        self.mouse.click(rect["left"] + pos_start[0], rect["top"] + pos_start[1])

        features = ["battle/battle_features_1.png", "battle/battle_features_2.png", "common/auto.png"]
        start_t = time.time()
        while time.time() - start_t < 2.5:
            time.sleep(0.3)
            if not self.capturer or not rect:
                continue
            fresh = self.capturer.capture(rect)
            if fresh is None:
                continue
            for feat in features:
                if os.path.exists(os.path.join("templates", feat)):
                    p, _ = self.matcher.match(fresh, feat, threshold=0.85, quiet=True)
                    if p:
                        logging.info(f"⚔️ [深淵魔王] 確認進入戰鬥！轉移至 STATE_BATTLE [{boss_key}]...")
                        self.machine.current_demon_lord_key = boss_key
                        self.machine.transition_to(self.machine.STATE_BATTLE)
                        return True
        return False

    def _handle_popup_guards(self, screen_img, rect):
        for popup_btn in ["common/confirm.png", "common/ok.png"]:
            if os.path.exists(os.path.join("templates", popup_btn)):
                pos, conf = self.matcher.match(screen_img, popup_btn, threshold=0.90, quiet=True)
                if pos:
                    logging.info(f"👉 [深淵魔王] 關閉干擾彈窗 [{popup_btn}] ({conf:.4f})...")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    time.sleep(0.4)
                    return True
        return False
