import time
import os
import sys
import logging
from states.handlers.base import BaseStateHandler

class JewelryWorkshopHandler(BaseStateHandler):
    """
    珠寶加工廠出售 (Jewelry Workshop) 處理器：
    1. 於城鎮點擊珠寶加工廠建築 (Jewelry_workshop.png) 進入建築。
    2. 點擊出售選單按鈕 (sell_out.png) 進入出售選單。
    3. 商品輪詢與出售子流程 (SELL_MENU_OPEN)：
       - 遍歷 goods 模板 (Sandworm_scales, Spider_silk, Spider_venom_glands, The_cloth_wrapped_around_the_dead, Warcraft_Fang, lizard_skin, scrap)。
       - 頂層未找到 ➔ 向下滑動兩下 ➔ 若仍未找到 ➔ 向上滑動兩下還原高度 ➔ 繼續下一個商品。
       - 找到商品 ➔ 點擊商品 ➔ 點擊 sell.png ➔ 點擊 sell_max.png ➔ 點擊 ok.png / confirm.png。
    4. 退出階段 (ALL_DONE_EXITING)：
       - 點擊離開建築按鈕 (exitfromhouse_and_to_town.png) 返回城鎮。
       - 完成獨立模式並安全退出程式。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"  # INIT, ENTERED_BUILDING, SELL_MENU_OPEN, ALL_DONE_EXITING
        self.last_action_time = 0.0
        self.current_goods_idx = 0
        self.goods_scroll_state = "TOP"  # TOP, SCROLLED_DOWN
        self.sell_scan_stage = "PAGE_TOP"  # PAGE_TOP, PAGE_BOTTOM, PAGE_TOP_FINAL
        self.current_selling_item = None
        self.sold_summary = {}  # {"gray": set(), "green": set(), ...}
        self.summary_logged = False
        self.item_sub_step = "SEARCH"    # SEARCH, CLICKED_ITEM, CLICKED_SELL, CLICKED_MAX
        self.repeat_sell_count = 0
        self.pre_tidy_done = False
        self.current_shop_id = "jewelry_workshop"
        self.current_building_btn = "town_building/Jewelry_workshop/Jewelry_workshop.png"
        from states.handlers.bag_cleaning import BagCleaningHandler
        self.bag_handler = BagCleaningHandler(machine)
        self.bag_handler.matcher = self.matcher
        self.bag_handler.mouse = self.mouse
        self.bag_handler.capturer = self.capturer
        from utils.merchant_gold_detector import MerchantGoldDetector
        self.gold_detector = MerchantGoldDetector()

    def reset_state(self):
        self.step_phase = "INIT"
        self.last_action_time = 0.0
        self.current_goods_idx = 0
        self.goods_scroll_state = "TOP"
        self.sell_scan_stage = "PAGE_TOP"
        self.current_selling_item = None
        self.sold_summary = {}
        self.summary_logged = False
        self.item_sub_step = "SEARCH"
        self.repeat_sell_count = 0
        self.pre_tidy_done = False
        self.current_shop_id = "jewelry_workshop"
        self.current_building_btn = "town_building/Jewelry_workshop/Jewelry_workshop.png"

    def _record_completion(self):
        """記錄 DailyManager 珠寶加工廠今日已完成，並累加該商店造訪次數"""
        self._log_settlement_summary()
        dm = getattr(self.machine, "daily_manager", None)
        if dm:
            if hasattr(dm, "record_subflow_completed"):
                dm.record_subflow_completed("jewelry_workshop")
            if hasattr(dm, "record_shop_visit") and self.current_shop_id:
                dm.record_shop_visit(self.current_shop_id)

    def _log_settlement_summary(self):
        """輸出高語意之結構化商店出售結算日誌"""
        if self.summary_logged:
            return
        self.summary_logged = True

        if not self.sold_summary or not any(self.sold_summary.values()):
            logging.info("💎 [商店出售結算] 經全頁面雙向掃描，背包無商品需要出售。")
            return

        total_types = sum(len(items) for items in self.sold_summary.values())

        logging.info("💎 =================== [商店出售結算清單] ===================")
        for q_key in ["gray", "green", "blue", "purple"]:
            items = sorted(list(self.sold_summary.get(q_key, set())))
            if items:
                items_str = ", ".join(items)
                logging.info(f"💎 品質 [{q_key}]：已賣出 [{items_str}] 皆已處置完畢")
            else:
                logging.info(f"💎 品質 [{q_key}]：(無符合或未持有)")
        logging.info(f"💎 總計出售：{total_types} 種商品品項全數成功賣出！")
        logging.info("💎 =========================================================")

    def _get_enabled_goods(self, goods_dir, goods_settings):
        """
        掃描 goods_dir (含顏色子資料夾 gray/, green/, blue/, purple/ 或直接平鋪檔案)，
        並根據 goods_settings 字典中各顏色區塊下每一個商品的 True/False 狀態，
        整理出需要出售的相對模板路徑清單。
        """
        full_dir = os.path.join("templates", goods_dir)
        if not os.path.exists(full_dir):
            return []

        if not isinstance(goods_settings, dict):
            return []

        enabled_goods = []
        for color, items in goods_settings.items():
            if isinstance(items, dict):
                for item_name, is_enabled in items.items():
                    if is_enabled:
                        rel_path_sub = os.path.join(color, item_name)
                        if os.path.exists(os.path.join(full_dir, f"{rel_path_sub}.png")):
                            enabled_goods.append(rel_path_sub)
                        elif os.path.exists(os.path.join(full_dir, f"{item_name}.png")):
                            enabled_goods.append(item_name)
            elif isinstance(items, bool) and items:
                # 平鋪格式相容
                item_name = color
                if os.path.exists(os.path.join(full_dir, f"{item_name}.png")):
                    enabled_goods.append(item_name)

        return enabled_goods

    def _ensure_in_town(self, screen_img, rect=None):
        """
        獨立導航輔助函式：若目前位於大廳 (看得到 goback_town.png)，點擊返回城鎮 (配對確認直到消失)。
        """
        pos_goback, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.8)
        if pos_goback:
            logging.info("💎 [珠寶加工廠] 偵測到目前處於大廳畫面，點擊 [goback_town.png] 返回城鎮 (配對確認直到消失)...")
            left = rect["left"] if rect else 0
            top = rect["top"] if rect else 0
            self.click_and_wait_until_gone("goback_town.png", left + pos_goback[0], top + pos_goback[1], rect)
            self.last_action_time = time.time()
            return False
        return True

    def _find_visible_good(self, screen_img, enabled_goods, goods_dir, goods_threshold=0.75, max_repeat=5):
        """
        在當前畫面中尋找可售商品。
        若有當前連續出售之品項且未達重複次數上限，優先檢查是否仍在畫面中；
        若無或已售罄，依序在畫面中比對所有授權商品。
        """
        # 1. 優先檢查是否在同一商品多堆連續出售中
        if self.current_selling_item and self.repeat_sell_count < max_repeat:
            template_path = os.path.join(goods_dir, f"{self.current_selling_item}.png")
            if os.path.exists(os.path.join("templates", template_path)):
                pos, conf = self.matcher.match(screen_img, template_path, threshold=goods_threshold)
                if pos:
                    return self.current_selling_item, pos, conf

        # 若原商品已售罄或達上限，重置計數
        self.current_selling_item = None
        self.repeat_sell_count = 0

        # 2. 遍歷授權商品清單，尋找當前畫面中可見的第一個商品
        for goods_name in enabled_goods:
            template_path = os.path.join(goods_dir, f"{goods_name}.png")
            if not os.path.exists(os.path.join("templates", template_path)):
                continue
            pos, conf = self.matcher.match(screen_img, template_path, threshold=goods_threshold)
            if pos:
                return goods_name, pos, conf

        return None, None, 0.0

    def _execute_sell_sequence(self, rect, pos_goods, sell_btn, sell_max_btn, screen_img=None):
        """
        執行點選商品 ➔ sell ➔ sell_max ➔ ok/confirm 彈窗消失閉環。
        """
        left = rect["left"] if rect else 0
        top = rect["top"] if rect else 0

        # 點擊選擇商品
        self.mouse.click(left + pos_goods[0], top + pos_goods[1])
        time.sleep(0.3)

        latest_img = self.capturer.capture(rect) if (self.capturer and rect) else screen_img
        if latest_img is None:
            return

        # 點擊 sell.png
        pos_sell, _ = self.matcher.match(latest_img, sell_btn, threshold=0.75)
        if pos_sell:
            logging.debug(f"💎 [珠寶加工廠] 點擊出售按鈕 [{sell_btn}]...")
            self.mouse.click(left + pos_sell[0], top + pos_sell[1])
            time.sleep(0.2)
            latest_img = self.capturer.capture(rect) if (self.capturer and rect) else latest_img

        # 點擊 sell_max.png
        if latest_img is not None:
            pos_max, _ = self.matcher.match(latest_img, sell_max_btn, threshold=0.75)
            if pos_max:
                logging.debug(f"💎 [珠寶加工廠] 點擊 MAX 數量按鈕 [{sell_max_btn}]...")
                self.mouse.click(left + pos_max[0], top + pos_max[1])
                time.sleep(0.2)
                latest_img = self.capturer.capture(rect) if (self.capturer and rect) else latest_img

        # 點擊 confirm/ok (配對確認直到彈窗徹底消失)
        for conf_btn in ["common/ok.png", "common/confirm.png"]:
            if latest_img is not None and os.path.exists(os.path.join("templates", conf_btn)):
                pos_c, _ = self.matcher.match(latest_img, conf_btn, threshold=0.75)
                if pos_c:
                    logging.debug(f"💎 [珠寶加工廠] 點擊確認出售按鈕 [{conf_btn}] (配對確認直到消失)...")
                    self.click_and_wait_until_gone(conf_btn, left + pos_c[0], top + pos_c[1], rect, post_delay=0.3)
                    time.sleep(0.3)
                    latest_img = self.capturer.capture(rect) if (self.capturer and rect) else latest_img
                    break

        # 二次防呆：若出現第二層 confirm/ok 彈窗
        for conf_btn in ["common/confirm.png", "common/ok.png"]:
            if latest_img is not None and os.path.exists(os.path.join("templates", conf_btn)):
                pos_c2, _ = self.matcher.match(latest_img, conf_btn, threshold=0.75)
                if pos_c2:
                    logging.debug(f"💎 [珠寶加工廠] 點擊二次確認按鈕 [{conf_btn}] (配對確認直到消失)...")
                    self.click_and_wait_until_gone(conf_btn, left + pos_c2[0], top + pos_c2[1], rect, post_delay=0.3)
                    time.sleep(0.3)

        # 沉澱等待動畫結束
        time.sleep(0.4)

    def _scroll_sell_menu(self, rect, direction="down"):
        """
        平滑拖曳出售選單列表 (down: 向下滾動檢視底部, up: 向上滾動還原頂部)。
        """
        left = rect["left"] if rect else 0
        top = rect["top"] if rect else 0
        center_x = left + (rect["width"] // 2 if rect and "width" in rect else 960)
        height = rect["height"] if rect and "height" in rect else 1080
        drag_start_y = top + int(height * 0.75)
        drag_end_y = top + int(height * 0.25)

        if direction == "down":
            self.mouse.drag(center_x, drag_start_y, center_x, drag_end_y, duration=0.5, inertia=False)
        else:
            self.mouse.drag(center_x, drag_end_y, center_x, drag_start_y, duration=0.5, inertia=False)
        time.sleep(0.8)

    def _handle_sell_menu(self, screen_img, rect, cfg, enabled_goods, goods_dir, sell_btn, sell_max_btn, now):
        """
        SELL_MENU_OPEN 階段：雙頁式畫面驅動 (Vision-Driven) 批次收割流轉。
        PAGE_TOP ➔ PAGE_BOTTOM ➔ PAGE_TOP_FINAL ➔ ALL_DONE_EXITING
        """
        goods_threshold = cfg.get("goods_threshold", 0.75)
        max_repeat = cfg.get("max_repeat_per_item", 5)

        # 1. 嘗試在當前畫面比對可售商品
        goods_name, pos_goods, conf_goods = self._find_visible_good(
            screen_img, enabled_goods, goods_dir, goods_threshold, max_repeat
        )

        # 若當前畫面有商品，執行出售閉環
        if pos_goods:
            self.current_selling_item = goods_name
            self.repeat_sell_count += 1
            if goods_name in enabled_goods:
                self.current_goods_idx = enabled_goods.index(goods_name)

            parts = goods_name.replace("\\", "/").split("/")
            quality = parts[0] if len(parts) >= 2 else "gray"
            item_name = parts[1] if len(parts) >= 2 else parts[0]

            if quality not in self.sold_summary:
                self.sold_summary[quality] = set()
            self.sold_summary[quality].add(item_name)

            logging.info(f"💎 [商店出售] 賣出 [{quality}: {item_name}]")
            self._execute_sell_sequence(rect, pos_goods, sell_btn, sell_max_btn, screen_img)
            self.last_action_time = now
            self.machine.notify_ui_progress()

            # 出售後二次確認：若該品項已售罄或達上限，及時重置並推進索引
            template_path = os.path.join(goods_dir, f"{goods_name}.png")
            post_img = self.capturer.capture(rect) if (self.capturer and rect) else None
            still_exists = False
            if post_img is not None and os.path.exists(os.path.join("templates", template_path)):
                pos_again, _ = self.matcher.match(post_img, template_path, threshold=goods_threshold)
                if pos_again:
                    still_exists = True

            if not still_exists or self.repeat_sell_count >= max_repeat:
                self.current_selling_item = None
                self.repeat_sell_count = 0
                if goods_name in enabled_goods:
                    self.current_goods_idx = enabled_goods.index(goods_name) + 1
            return

        # 2. 當前畫面無任何可售商品，依階段切換
        if self.sell_scan_stage == "PAGE_TOP":
            logging.info("💎 [商店出售] 頂部畫面可售商品已全數清空，向下滑動檢視底部...")
            self._scroll_sell_menu(rect, direction="down")
            self.sell_scan_stage = "PAGE_BOTTOM"
            self.goods_scroll_state = "SCROLLED_DOWN"
            self.current_selling_item = None
            self.repeat_sell_count = 0
            self.last_action_time = now
            self.machine.notify_ui_progress()
            return

        if self.sell_scan_stage == "PAGE_BOTTOM":
            logging.info("💎 [商店出售] 底部畫面可售商品已全數清空，向上滑動還原頂部進行二次複查...")
            self._scroll_sell_menu(rect, direction="up")
            self.sell_scan_stage = "PAGE_TOP_FINAL"
            self.goods_scroll_state = "TOP"
            self.current_selling_item = None
            self.repeat_sell_count = 0
            self.last_action_time = now
            self.machine.notify_ui_progress()
            return

        if self.sell_scan_stage == "PAGE_TOP_FINAL":
            self._log_settlement_summary()
            self.step_phase = "ALL_DONE_EXITING"
            self.sell_scan_stage = "PAGE_TOP"
            self.goods_scroll_state = "TOP"
            self.current_selling_item = None
            self.repeat_sell_count = 0
            if enabled_goods:
                self.current_goods_idx = len(enabled_goods)
            self.last_action_time = now
            self.machine.notify_ui_progress()
            return

    def handle(self, screen_img=None, rect=None):
        if screen_img is None and self.capturer:
            rect = rect or self.capturer.get_window_rect()
            if rect:
                screen_img = self.capturer.capture(rect)
        if screen_img is None:
            return

        # 防死鎖門禁：若獨立模式或城鎮流水線已不需要珠寶加工廠出售 且處於 INIT 階段，直接 return！
        cfg_type = self.machine.config.get("type") if getattr(self.machine, "config", None) else None
        is_needed = getattr(self.machine, "need_jewelry_workshop", False) or cfg_type == "jewelry_workshop"
        if not is_needed and self.step_phase == "INIT":
            return

        now = time.time()
        if now - self.last_action_time < 0.6:
            return

        # 🛡️ 場景感知防護 (Scene Guard)：若非 INIT/EXITING 階段但畫面上已看見 common/door.png (確定在城鎮 Town)，代表已離場
        if self.step_phase in ["SELL_MENU_OPEN", "ENTERED_BUILDING"]:
            pos_door_chk, conf_door_chk = self.matcher.match(screen_img, "common/door.png", threshold=0.80)
            if pos_door_chk:
                logging.warning(f"💎 [珠寶加工廠] 防護攔截 - 處於 [{self.step_phase}] 階段但畫面上已看見城鎮大門 [common/door.png] ({conf_door_chk:.4f})，結束出售流程。")
                self._record_completion()
                self.reset_state()
                self.machine.need_jewelry_workshop = False
                self.last_action_time = now
                self.machine.pop_and_next_town_subflow()
                return

        # 優先檢查是否需要從小圖示大廳退回城鎮
        if not self._ensure_in_town(screen_img, rect):
            return


        left = rect["left"] if rect else 0
        top = rect["top"] if rect else 0

        cfg = self.machine.config or {}
        building_btn = cfg.get("building_btn", "town_building/Jewelry_workshop/Jewelry_workshop.png")
        shops_cfg = cfg.get("shops")
        if not shops_cfg:
            from config import GAME_CONFIGS
            workshop_config = GAME_CONFIGS.get("jewelry_workshop", {})
            shops_cfg = workshop_config.get("shops", [
                {"id": "jewelry_workshop", "name": "珠寶加工廠", "template": building_btn}
            ])
        sell_out_btn = cfg.get("sell_out_btn", "town_building/sell_out.png")
        sell_btn = cfg.get("sell_btn", "town_building/sell.png")
        sell_max_btn = cfg.get("sell_max_btn", "town_building/sell_max.png")
        exit_building_btn = cfg.get("exit_building_btn", "town_building/exitfromhouse_and_to_town.png")

        goods_settings = cfg.get("sell_goods", cfg.get("goods_settings"))
        if goods_settings is None:
            from config import GAME_CONFIGS
            workshop_config = GAME_CONFIGS.get("jewelry_workshop", {})
            goods_settings = workshop_config.get(
                "sell_goods", workshop_config.get("goods_settings", {})
            )
        goods_dir = cfg.get("goods_dir", "town_building/Jewelry_workshop/goods")

        # 整理要出售的商品清單 (支援品質子目錄 gray/green/blue/purple 與特例覆蓋)
        enabled_goods = self._get_enabled_goods(goods_dir, goods_settings)

        # 0. 通用防呆：若出現 common/confirm.png 彈窗，點擊確認
        conf_name = "common/confirm.png"
        if os.path.exists(os.path.join("templates", conf_name)):
            pos_conf, _ = self.matcher.match(screen_img, conf_name, threshold=0.8)
            if pos_conf:
                logging.info(f"💎 [珠寶加工廠] 點擊確認按鈕 [{conf_name}]...")
                self.mouse.click(left + pos_conf[0], top + pos_conf[1])
                self.last_action_time = now
                self.machine.notify_ui_progress()

                return

        # =========================================================================
        # 1. 出售選單開啟狀態 (SELL_MENU_OPEN) - 雙頁畫面驅動批次出售閉環
        # =========================================================================
        if self.step_phase == "SELL_MENU_OPEN":
            self._handle_sell_menu(
                screen_img, rect, cfg, enabled_goods, goods_dir, sell_btn, sell_max_btn, now
            )
            return

        # =========================================================================
        # 2. 退出階段 (ALL_DONE_EXITING)
        # =========================================================================
        if self.step_phase == "ALL_DONE_EXITING":
            pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75)
            pos_building, _ = self.matcher.match(screen_img, self.current_building_btn, threshold=0.75)
            if pos_door or pos_building:
                logging.info("✅ [珠寶加工廠] 偵測到目前已處於城鎮大門畫面，視為已退回城鎮，完成出售流程！")
                self._record_completion()
                self.reset_state()
                self.machine.need_jewelry_workshop = False
                self.last_action_time = now
                self.machine.notify_ui_progress()

                logging.info("💎 [珠寶加工廠] 出售流程完成，消費城鎮佇列中的下一個任務...")
                self.machine.pop_and_next_town_subflow()
                return

            pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.8)
            if pos_quit:
                logging.info("💎 [珠寶加工廠] 點擊關閉視窗 [common/quit.png]...")
                self.mouse.click(left + pos_quit[0], top + pos_quit[1])
                self.last_action_time = now
                self.machine.notify_ui_progress()

                return

            pos_exit, _ = self.matcher.match(screen_img, exit_building_btn, threshold=0.75)
            if pos_exit:
                # 離店前更新商人扣減後的最新金幣
                ocr_reader = getattr(self.machine, "get_ocr_reader", lambda: None)
                final_gold = self.gold_detector.detect_merchant_gold(
                    screen_img, ocr_reader=ocr_reader, debug_tag=f"{self.current_shop_id}_exit"
                )
                if final_gold is not None:
                    dm = getattr(self.machine, "daily_manager", None)
                    if dm and hasattr(dm, "record_shop_gold"):
                        dm.record_shop_gold(self.current_shop_id, final_gold)

                logging.info(f"💎 [珠寶加工廠] 點擊離開建築按鈕 [{exit_building_btn}] 返回城鎮...")
                self.mouse.click(left + pos_exit[0], top + pos_exit[1])
                self._record_completion()
                self.reset_state()
                self.machine.need_jewelry_workshop = False
                self.last_action_time = now
                self.machine.notify_ui_progress()

                logging.info("💎 [珠寶加工廠] 出售流程完成，消費城鎮佇列中的下一個任務...")
                self.machine.pop_and_next_town_subflow()
                return
            return

        # =========================================================================
        # 3. 城鎮與建築內起點階段 (INIT / ENTERED_BUILDING)
        # =========================================================================
        # 3.1 檢查是否已開啟出售選單 (畫面上有 sell_btn 或 sell_max_btn)
        pos_sell_chk, _ = self.matcher.match(screen_img, sell_btn, threshold=0.75)
        pos_max_chk, _ = self.matcher.match(screen_img, sell_max_btn, threshold=0.75)
        if pos_sell_chk or pos_max_chk:
            logging.info("💎 [珠寶加工廠] 辨識到目前已處於出售選單畫面，直接進入出售階段...")
            self.step_phase = "SELL_MENU_OPEN"
            self.current_goods_idx = 0
            self.goods_scroll_state = "TOP"
            self.last_action_time = now
            return

        # 3.2 檢查是否已在建築內部 (sell_out.png 與 exitfromhouse_and_to_town.png 同時存在)
        pos_sell_out, conf_so = self.matcher.match(screen_img, sell_out_btn, threshold=0.80)
        pos_exit_init, conf_exit = self.matcher.match(screen_img, exit_building_btn, threshold=0.80)
        if pos_sell_out and pos_exit_init:
            # 進入房間時先辨識商人頭頂看板金幣
            ocr_reader = getattr(self.machine, "get_ocr_reader", lambda: None)
            init_gold = self.gold_detector.detect_merchant_gold(
                screen_img, ocr_reader=ocr_reader, debug_tag=f"{self.current_shop_id}_init"
            )
            if init_gold is not None:
                dm = getattr(self.machine, "daily_manager", None)
                if dm and hasattr(dm, "record_shop_gold"):
                    dm.record_shop_gold(self.current_shop_id, init_gold)

            logging.info(f"💎 [珠寶加工廠] 辨識到已在建築物內部 (sell_out.png 可見)，點擊開啟出售選單...")
            self.mouse.click(left + pos_sell_out[0], top + pos_sell_out[1])
            self.step_phase = "SELL_MENU_OPEN"
            self.current_goods_idx = 0
            self.goods_scroll_state = "TOP"
            time.sleep(0.8)
            self.last_action_time = now
            return

        # 3.3 城鎮點擊珠寶加工廠建築 (Jewelry_workshop.png) (進場前優先發起城鎮背包預先整理)
        if is_needed:
            # 3.3.1 若目前背包已處於開啟狀態（不受城鎮大門/建築被背包遮擋影響），優先執行「整理」與「退出」
            if self.bag_handler.is_backpack_opened(screen_img):
                if not getattr(self.machine, "bag_tidied", False):
                    if self.bag_handler.tidy_backpack(screen_img, rect):
                        self.last_action_time = now
                        return
                else:
                    pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.7)
                    if pos_quit:
                        logging.info("💎 [珠寶加工廠] 城鎮背包預先整理完畢，點擊關閉退出背包...")
                        self.click_and_wait_until_gone("common/quit.png", left + pos_quit[0], top + pos_quit[1], rect, threshold=0.7)
                    self.machine.bag_tidied = False
                    self.machine.bag_opened_clicked = False
                    self.pre_tidy_done = True
                    self.last_action_time = now
                    return

            # 3.3.2 若背包未開啟，且處於城鎮 (pos_door 可見)
            pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75)
            if pos_door:
                if not self.pre_tidy_done:
                    logging.info("💎 [城鎮商店] 進入前執行城鎮背包預先整理，優先開啟背包...")
                    if self.bag_handler.open_backpack(screen_img, rect):
                        self.last_action_time = now
                        return

                # 依商人持有金幣由多至少貪婪排序 (未探勘者優先)，並於畫面中尋找可見建築
                dm = getattr(self.machine, "daily_manager", None)
                gold_balances = dm.get_shop_gold_balances() if (dm and hasattr(dm, "get_shop_gold_balances")) else {}
                from utils.shop_selector import sort_shops_by_gold_balance
                sorted_shops = sort_shops_by_gold_balance(shops_cfg, gold_balances)

                matched_shop = None
                matched_pos = None
                matched_conf = 0.0

                screen_w = screen_img.shape[1] if hasattr(screen_img, "shape") and len(screen_img.shape) >= 2 else 1920
                candidate_scales = (
                    self.matcher.compute_candidate_scales(screen_w)
                    if hasattr(self.matcher, "compute_candidate_scales")
                    else None
                )

                for s in sorted_shops:
                    tmpl = s.get("template", building_btn)
                    if not tmpl:
                        continue
                    pos_b, conf_b = self.matcher.match(
                        screen_img, tmpl, threshold=0.65, brightness_threshold=0.0,
                        scales=candidate_scales, quiet=True
                    )
                    if pos_b:
                        matched_shop = s
                        matched_pos = pos_b
                        matched_conf = conf_b
                        break
                    else:
                        logging.debug(f"💎 [城鎮商店] 候選商店 [{s.get('name')}] 未達標 (信心度: {conf_b:.4f} < 0.65)")

                # 相容性 fallback：若未比對到任何輪換商店，比對預設 building_btn
                if not matched_shop:
                    pos_b, conf_b = self.matcher.match(
                        screen_img, building_btn, threshold=0.65, brightness_threshold=0.0,
                        scales=candidate_scales, quiet=True
                    )
                    if pos_b:
                        matched_shop = {"id": "jewelry_workshop", "name": "珠寶加工廠", "template": building_btn}
                        matched_pos = pos_b
                        matched_conf = conf_b

                if matched_shop and matched_pos:
                    self.current_shop_id = matched_shop.get("id", "jewelry_workshop")
                    self.current_building_btn = matched_shop.get("template", building_btn)
                    shop_name = matched_shop.get("name", self.current_shop_id)
                    cur_gold = gold_balances.get(self.current_shop_id, "未探勘")
                    logging.info(f"💎 [城鎮商店] 於城鎮發現目標商店 [{shop_name}] ({self.current_building_btn}) (記錄金幣: {cur_gold}, 信心度: {matched_conf:.4f})，點擊進入...")
                    self.mouse.click(left + matched_pos[0], top + matched_pos[1])
                    self.step_phase = "ENTERED_BUILDING"
                    self.last_action_time = now
                    self.machine.notify_ui_progress()
                    return

        if pos_sell_out:
            logging.info(f"💎 [珠寶加工廠] 發現出售選單按鈕 [{sell_out_btn}]，點擊開啟選單...")
            self.mouse.click(left + pos_sell_out[0], top + pos_sell_out[1])
            self.step_phase = "SELL_MENU_OPEN"
            self.current_goods_idx = 0
            self.goods_scroll_state = "TOP"
            time.sleep(0.8)
            self.last_action_time = now
            return
