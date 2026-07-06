import os
import time
import logging
from states.handlers.base import BaseStateHandler

class NavigationHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        尋路導航與自動領體力邏輯。
        """
        # A. 如果啟用且需要領體力，執行領體力分支流程
        if self.machine.enable_bread and self.machine.need_bread_collection:
            # 依優先級檢查領體力相關按鈕
            # 1. 彈窗內的確認按鈕 (Cannot get more bread confirm)
            pos_cannot, conf_cannot = self.matcher.match(screen_img, "common/cannor_get_more_bread_confirm.png", threshold=0.8)
            if pos_cannot:
                logging.info(f"🍞 領體力：偵測到體力已滿提示 [{conf_cannot:.4f}]，點擊確認。")
                self.mouse.click(rect["left"] + pos_cannot[0], rect["top"] + pos_cannot[1])
                time.sleep(1.0)
                return
                
            # 2. 領完體力的確認按鈕 (bread confirm)
            pos_conf, conf_conf = self.matcher.match(screen_img, "common/bread_confirm.png", threshold=0.8)
            if pos_conf:
                logging.info(f"🍞 領體力：偵測到獲得體力確認 [{conf_conf:.4f}]，點擊確認。")
                self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
                time.sleep(1.0)
                return

            # 3. 領體力按鈕 (bread collection)
            pos_coll, conf_coll = self.matcher.match(screen_img, "common/bread_collection.png", threshold=0.8)
            if pos_coll:
                logging.info(f"🍞 領體力：偵測到領體力按鈕 [{conf_coll:.4f}]，進行點擊領取。")
                self.mouse.click(rect["left"] + pos_coll[0], rect["top"] + pos_coll[1])
                time.sleep(1.0)
                return

            # 4. 關閉體力視窗按鈕 (quit bread)
            pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit_bread.png", threshold=0.8)
            if pos_quit:
                logging.info(f"🍞 領體力：偵測到退出體力按鈕 [{conf_quit:.4f}]，點擊關閉，領取體力流程結束。")
                self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                self.machine.need_bread_collection = False
                self.machine.last_bread_collection_time = time.time()
                time.sleep(1.5)
                return

            # 5. 打開體力視窗按鈕 (bread)
            pos_bread, conf_bread = self.matcher.match(screen_img, "common/bread.png", threshold=0.8)
            if pos_bread:
                logging.info(f"🍞 領體力：在大廳偵測到體力按鈕 [{conf_bread:.4f}]，點擊打開體力視窗。")
                self.mouse.click(rect["left"] + pos_bread[0], rect["top"] + pos_bread[1])
                time.sleep(1.5)
                return

            # 6. 入口按鈕 (door)
            pos_door, conf_door = self.matcher.match(screen_img, "dungeons/door.png", threshold=0.8)
            if pos_door:
                logging.info(f"🍞 領體力：在主畫面偵測到入口按鈕 [{conf_door:.4f}]，點擊進入大廳。")
                self.mouse.click(rect["left"] + pos_door[0], rect["top"] + pos_door[1])
                time.sleep(1.5)
                return

            logging.info("⌛ 領體力流程中，正在等待體力畫面或按鈕載入...")
            time.sleep(0.5)
            return

        # B. 原本的尋路導航邏輯
        nav_path = self.machine.config.get("navigation_path", [])
        if not nav_path:
            # 如果沒有設定尋路路徑 (例如普通關卡)，直接進入大廳狀態
            self.machine.transition_to(self.machine.STATE_LOBBY)
            return

        # 主動判定：如果我們已經看到任何地下城探索或結束按鈕，說明點擊已經成功並進入內部，直接轉移狀態！
        if self.machine.config["type"] == "dungeon":
            for check_btn in ["dungeons/dungeon_fight.png", "dungeons/dungeon_bless.png", "dungeons/Treasure.png", "dungeons/gungeon_godown.png", "dungeons/dungeons_complete.png"]:
                if os.path.exists(os.path.join("templates", check_btn)):
                    pos, conf = self.matcher.match(screen_img, check_btn, threshold=0.8)
                    if pos:
                        logging.info(f"🧭 尋路中偵測到地下城專屬按鈕 [{check_btn}] (信心度: {conf:.4f})，判定已進入地下城。")
                        self.machine.transition_to(self.machine.STATE_DUNGEON_EXPLORING)
                        return

        # 逆序掃描導航路徑中可見的按鈕，點擊最深層的那個
        clicked_any = False
        for btn in reversed(nav_path):
            pos, conf = self.matcher.match(screen_img, btn, threshold=0.8)
            if pos:
                logging.info(f"🧭 尋路中：在畫面中找到 [{btn}] (信心度: {conf:.4f})，點擊跳轉。")
                self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                clicked_any = True
                time.sleep(1.5) # 等待跳轉動畫
                break

        if not clicked_any:
            # 如果畫面上任何尋路按鈕都找不到了，代表我們已經跳轉進去
            logging.info("🧭 尋路按鈕已不在畫面上，判斷已成功抵達副本內部。")
            if self.machine.config["type"] == "dungeon":
                self.machine.transition_to(self.machine.STATE_DUNGEON_EXPLORING)
            else:
                self.machine.transition_to(self.machine.STATE_LOBBY)
