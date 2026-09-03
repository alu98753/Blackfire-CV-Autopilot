import os
import time
import logging
from enum import Enum
from states.handlers.base import BaseStateHandler
from utils.debug_artifacts import write_debug_image

class DemonSubScene(str, Enum):
    """深淵魔王子場景定義 (Greenfield-lite v1)"""
    UNKNOWN, TOWN, LOBBY_OTHER_TAB = "UNKNOWN", "TOWN", "LOBBY_OTHER_TAB"
    CARD_SELECTION, PREPARE_MODAL, STONE_DIALOG = "CARD_SELECTION", "PREPARE_MODAL", "STONE_DIALOG"

class DemonLordsHandler(BaseStateHandler):
    """深淵魔王狀態處理器 (Greenfield-lite v1)"""
    TAB_THRESHOLD, BOSS_CARD_THRESHOLD = 0.70, 0.78
    SLOT_THRESHOLD, STONE_THRESHOLD = 0.85, 0.75
    CHOOSE_THRESHOLD, START_THRESHOLD = 0.90, 0.80

    DEFAULT_STONE_TEMPLATES = {str(i): f"demon_lords/meterial/demon_seal_stone_{i}.png" for i in range(1, 5)}

    def __init__(self, machine):
        super().__init__(machine)
        self.current_target_boss = None
        self.pending_stone_queue = None
        self.stone_insert_completed = False
        self.slot_no_reaction_count = 0
        self.launch_pending = False
        self.launch_started_at = None

    def reset_state(self):
        self.current_target_boss = None
        self.pending_stone_queue = None
        self.stone_insert_completed = False
        self.slot_no_reaction_count = 0
        self.launch_pending = False
        self.launch_started_at = None

    def _get_configured_targets(self):
        cfg = self.machine.config or {}
        return cfg.get("targets") or [cfg.get("target_boss", "voidborn_elres")]

    def handle(self, screen_img, rect):
        dm = getattr(self.machine, "daily_manager", None)
        if dm and hasattr(dm, "is_demon_lords_available"):
            targets = self._get_configured_targets()
            avail, reason = dm.is_demon_lords_available(targets)
            if not avail:
                logging.info(f"🎉 [深淵魔王] {reason}！結束子流程並切換下一任務...")
                if hasattr(dm, "record_subflow_completed"):
                    dm.record_subflow_completed("demon_lords")
                self.reset_state()
                self.machine.pop_and_next_town_subflow()
                return True

        if self._handle_popup_guards(screen_img, rect):
            return True

        if self.launch_pending:
            return self._observe_launch_outcome(screen_img)

        subscene = self.classify_subscene(screen_img)
        dispatch = {
            DemonSubScene.TOWN: self._step_enter_lobby,
            DemonSubScene.LOBBY_OTHER_TAB: self._step_switch_to_demon_tab,
            DemonSubScene.CARD_SELECTION: self._step_select_boss_card,
            DemonSubScene.PREPARE_MODAL: self._step_handle_prepare_modal,
            DemonSubScene.STONE_DIALOG: self._step_handle_stone_dialog,
        }
        fn = dispatch.get(subscene)
        return fn(screen_img, rect) if fn else False

    def classify_subscene(self, screen_img) -> DemonSubScene:
        """純感知分類器：宏觀錨點優先，無點擊副作用"""
        if self.matcher.match(screen_img, "common/door.png", threshold=0.85, quiet=True)[0]:
            return DemonSubScene.TOWN

        choose_btn = self.machine.config.get("choose_btn", "common/choose.png")
        if os.path.exists(os.path.join("templates", choose_btn)) and self.matcher.match(screen_img, choose_btn, threshold=self.CHOOSE_THRESHOLD, quiet=True)[0]:
            return DemonSubScene.STONE_DIALOG

        for key, thresh, def_t in [("stone_container_btn", 0.70, "demon_lords/meterial/stone_slot.png"), ("empty_slot_btn", self.SLOT_THRESHOLD, "demon_lords/meterial/slot.png")]:
            btn = self.machine.config.get(key, def_t)
            if os.path.exists(os.path.join("templates", btn)) and self.matcher.match(screen_img, btn, threshold=thresh, quiet=True)[0]:
                return DemonSubScene.PREPARE_MODAL

        start_btn = self.machine.config.get("start_btn", "stages/start.png")
        if self.current_target_boss and os.path.exists(os.path.join("templates", start_btn)) and self.matcher.match(screen_img, start_btn, threshold=self.START_THRESHOLD, quiet=True)[0]:
            return DemonSubScene.PREPARE_MODAL

        entry_after, entry_before = self.machine.config.get("entry_after_btn", "demon_lords/demon_lords_entry_after.png"), self.machine.config.get("entry_btn", "demon_lords/demon_lords_entry.png")
        if self.match_mutually_exclusive_tabs(screen_img, entry_after, entry_before, margin=0.02, threshold=self.TAB_THRESHOLD)[0]:
            return DemonSubScene.CARD_SELECTION
        if os.path.exists(os.path.join("templates", entry_before)) and self.matcher.match(screen_img, entry_before, threshold=0.75, quiet=True)[0]:
            return DemonSubScene.LOBBY_OTHER_TAB

        return DemonSubScene.UNKNOWN

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
        targets = self._get_configured_targets()
        dm = getattr(self.machine, "daily_manager", None)
        avail = dm.get_available_demon_lords(targets) if dm and hasattr(dm, "get_available_demon_lords") else targets
        target_key = avail[0] if avail else targets[0]

        boss_cfg = self.machine.config.get("bosses", {}).get(target_key, {})
        card_template = boss_cfg.get("template", f"demon_lords/{target_key}.png")
        if os.path.exists(os.path.join("templates", card_template)):
            pos_card, conf = self.matcher.match(screen_img, card_template, threshold=self.BOSS_CARD_THRESHOLD, quiet=True)
            if pos_card:
                boss_name = boss_cfg.get("name", target_key)
                logging.info(f"🎯 [深淵魔王] 點擊魔王卡片 [{boss_name}] ({conf:.4f}) 進入準備介面...")
                self.mouse.click(rect["left"] + pos_card[0], rect["top"] + pos_card[1])
                self.current_target_boss = target_key
                self.pending_stone_queue = self._build_stone_plan_queue()
                self.stone_insert_completed = False
                self.slot_no_reaction_count = 0
                logging.info(f"📋 [深淵魔王] 初始化鑲嵌計畫: {self.pending_stone_queue}")
                time.sleep(0.6)
                return True
        return False

    def _step_handle_prepare_modal(self, screen_img, rect):
        """PREPARE_MODAL 躍遷：若鑲嵌完成則啟動戰鬥；未完成則點擊插槽或判定無反應退出"""
        if getattr(self, "stone_insert_completed", False) or (self.pending_stone_queue is not None and len(self.pending_stone_queue) == 0):
            return self._try_click_start(screen_img, rect)

        pos_slot, conf_slot = self._find_empty_slot(screen_img)
        if pos_slot:
            if self.slot_no_reaction_count >= 2:
                logging.warning(f"⚠️ [深淵魔王] 連續 2 次點擊插槽均無反應，判定魔王 [{self.current_target_boss}] 今日次數已耗盡！")
                return self._step_exit_exhausted_boss(screen_img, rect)
            if self.pending_stone_queue is None:
                self.pending_stone_queue = self._build_stone_plan_queue()
            self.slot_no_reaction_count += 1
            logging.info(f"👉 [深淵魔王] 點擊空插槽 (第 {self.slot_no_reaction_count}/2 次, 信心度: {conf_slot:.4f})...")
            self.mouse.click(rect["left"] + pos_slot[0], rect["top"] + pos_slot[1])
            time.sleep(0.5)
            return True

        return self._try_click_start(screen_img, rect)

    def _try_click_start(self, screen_img, rect):
        start_btn = self.machine.config.get("start_btn", "stages/start.png")
        if os.path.exists(os.path.join("templates", start_btn)):
            pos_start, conf_start = self.matcher.match(screen_img, start_btn, threshold=self.START_THRESHOLD, quiet=True)
            if pos_start:
                return self._launch_demon_battle(rect, pos_start, conf_start)
        return False

    def _step_exit_exhausted_boss(self, screen_img, rect):
        boss_key = self.current_target_boss or self.machine.config.get("target_boss", "voidborn_elres")
        dm = getattr(self.machine, "daily_manager", None)
        if dm and hasattr(dm, "mark_demon_lord_completed"):
            dm.mark_demon_lord_completed(boss_key)

        for btn in ["common/quit.png", "common/ok.png", "common/confirm.png"]:
            if os.path.exists(os.path.join("templates", btn)):
                pos, _ = self.matcher.match(screen_img, btn, threshold=0.75, quiet=True)
                if pos:
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    time.sleep(0.4)
                    break

        self.reset_state()
        targets = self._get_configured_targets()
        remaining = dm.get_available_demon_lords(targets) if dm and hasattr(dm, "get_available_demon_lords") else []
        if not remaining:
            logging.info("🎉 [深淵魔王] 所有配置魔王今日挑戰皆已結束，退出子流程並切換下一任務...")
            self.machine.pop_and_next_town_subflow()
        else:
            logging.info(f"👉 [深淵魔王] 尚有可挑戰魔王: {remaining}，返回卡片介面續行...")
        return True

    def _step_handle_stone_dialog(self, screen_img, rect):
        h, w = screen_img.shape[:2]
        left_half = screen_img[:, :w // 2]
        choose_btn = self.machine.config.get("choose_btn", "common/choose.png")
        write_debug_image("debug_demon_stone_search.png", left_half)
        full_scale = float(getattr(self.matcher, "_compute_auto_scale", lambda _: 1.0)(w) or 1.0)

        if not self.pending_stone_queue:
            self.pending_stone_queue = self._build_stone_plan_queue()
        target_tier = self.pending_stone_queue[0]
        stone_template = self._get_stone_template(target_tier)

        pos_stone, conf_stone = None, 0.0
        if os.path.exists(os.path.join("templates", stone_template)):
            pos_stone, conf_stone = self.matcher.match(left_half, stone_template, threshold=self.STONE_THRESHOLD, scale=full_scale, quiet=True)
            logging.info(f"🔍 [深淵魔王・選石診斷] {target_tier} 階石 [{stone_template}] 相似度: {conf_stone:.4f}")

        if not pos_stone and target_tier not in ["1", "demon_seal_stone_1"]:
            fallback = self._get_stone_template("1")
            logging.warning(f"⚠️ [深淵魔王] 未檢測到 {target_tier} 階石，嘗試降級 1 階 [{fallback}]...")
            if os.path.exists(os.path.join("templates", fallback)):
                pos_stone, conf_stone = self.matcher.match(left_half, fallback, threshold=self.STONE_THRESHOLD, scale=full_scale, quiet=True)

        if pos_stone:
            logging.info(f"💎 [深淵魔王] 選取封印石 ({conf_stone:.4f})...")
            self.mouse.click(rect["left"] + pos_stone[0], rect["top"] + pos_stone[1])
            time.sleep(0.3)

        if os.path.exists(os.path.join("templates", choose_btn)):
            pos_choose, conf_choose = self.matcher.match(screen_img, choose_btn, threshold=self.CHOOSE_THRESHOLD, quiet=True)
            if pos_choose:
                logging.info(f"✅ [深淵魔王] 點擊確認選擇 [{choose_btn}] ({conf_choose:.4f})...")
                self.mouse.click(rect["left"] + pos_choose[0], rect["top"] + pos_choose[1])
                self.slot_no_reaction_count = 0
                if self.pending_stone_queue:
                    self.pending_stone_queue.pop(0)
                    if len(self.pending_stone_queue) == 0:
                        self.stone_insert_completed = True
                        logging.info("🎉 [深淵魔王] 封印石已全數鑲嵌完成！準備發起戰鬥...")
                time.sleep(0.6)
                return True
        return False

    def _build_stone_plan_queue(self):
        selection = self.machine.config.get("stone_selection", {"2": 1, "1": 2})
        queue = []
        for k in sorted(selection.keys(), key=lambda x: int(str(x).replace("demon_seal_stone_", "") or 1), reverse=True):
            queue.extend([str(k)] * int(selection[k]))
        return queue if queue else ["1", "1", "1"]

    def _get_stone_template(self, tier_or_key):
        cfg_templates = self.machine.config.get("stone_templates", self.DEFAULT_STONE_TEMPLATES)
        k = str(tier_or_key)
        tier = k.replace("demon_seal_stone_", "")
        return cfg_templates.get(k) or cfg_templates.get(tier) or self.DEFAULT_STONE_TEMPLATES.get(tier, "demon_lords/meterial/demon_seal_stone_1.png")

    def _find_empty_slot(self, screen_img):
        empty_slot = self.machine.config.get("empty_slot_btn", "demon_lords/meterial/slot.png")
        container = self.machine.config.get("stone_container_btn", "demon_lords/meterial/stone_slot.png")
        if not os.path.exists(os.path.join("templates", empty_slot)):
            return None, 0.0
        h, w = screen_img.shape[:2]
        full_scale = float(getattr(self.matcher, "_compute_auto_scale", lambda _: 1.0)(w))
        if os.path.exists(os.path.join("templates", container)):
            pos_c, _ = self.matcher.match(screen_img, container, threshold=0.70, quiet=True)
            if pos_c:
                cx, cy = pos_c
                x1, y1 = max(0, cx - 400), max(0, cy - 120)
                crop = screen_img[y1:min(h, cy + 120), x1:min(w, cx + 400)]
                pos_c_slot, conf_c = self.matcher.match(crop, empty_slot, threshold=self.SLOT_THRESHOLD, scale=full_scale, quiet=True)
                return ((x1 + pos_c_slot[0], y1 + pos_c_slot[1]), conf_c) if pos_c_slot else (None, 0.0)
        pos_s, conf_s = self.matcher.match(screen_img, empty_slot, threshold=self.SLOT_THRESHOLD, quiet=True)
        return (pos_s, conf_s) if pos_s else (None, 0.0)

    def _launch_demon_battle(self, rect, pos_start, conf_start):
        boss_key = self.current_target_boss or self.machine.config.get("target_boss", "voidborn_elres")
        logging.info(f"🚀 [深淵魔王] 封印石全滿，開始戰鬥 [{conf_start:.4f}] 討伐 [{boss_key}]...")
        self.mouse.click(rect["left"] + pos_start[0], rect["top"] + pos_start[1])
        self.stone_insert_completed = False
        self.pending_stone_queue = None
        self.slot_no_reaction_count = 0
        self.launch_pending = True
        self.launch_started_at = time.monotonic()
        logging.info("[DemonLords] Start committed; awaiting BATTLE or stamina-overlay observation.")
        return True

    def _observe_launch_outcome(self, screen_img):
        """Resolve the Start action on a later frame without recapturing here."""
        features = ["battle/battle_features_1.png", "battle/battle_features_2.png", "common/auto.png"]
        for feat in features:
            if os.path.exists(os.path.join("templates", feat)):
                position, _ = self.matcher.match(screen_img, feat, threshold=0.85, quiet=True)
                if position:
                    boss_key = self.current_target_boss or self.machine.config.get("target_boss", "voidborn_elres")
                    logging.info(f"⚔️ [深淵魔王] Start postcondition met; entering BATTLE [{boss_key}].")
                    self.machine.current_demon_lord_key = boss_key
                    self.machine.transition_to(self.machine.STATE_BATTLE)
                    return True

        timeout = float((self.machine.config or {}).get("demon_start_timeout_seconds", 5.0))
        if self.launch_started_at is not None and time.monotonic() - self.launch_started_at >= timeout:
            logging.warning("[DemonLords] Start action timed out without BATTLE or stamina overlay; returning to UNKNOWN for bounded recovery.")
            self.machine.transition_to(self.machine.STATE_UNKNOWN)
            return True
        return True

    def _handle_popup_guards(self, screen_img, rect):
        # The state-machine stamina recovery owns no_bread overlays.  A generic
        # confirm click here would hide their evidence and lose the retreat
        # intent, so this guard must leave them untouched.
        for no_bread in ["no_bread/no_bread.png", "no_bread/no_bread2.png"]:
            if os.path.exists(os.path.join("templates", no_bread)):
                if self.matcher.match(screen_img, no_bread, threshold=0.85, quiet=True)[0]:
                    return False
        for popup_btn in ["common/confirm.png", "common/ok.png"]:
            if os.path.exists(os.path.join("templates", popup_btn)):
                pos, conf = self.matcher.match(screen_img, popup_btn, threshold=0.90, quiet=True)
                if pos:
                    logging.info(f"👉 [深淵魔王] 關閉干擾彈窗 [{popup_btn}] ({conf:.4f})...")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    time.sleep(0.4)
                    return True
        return False
