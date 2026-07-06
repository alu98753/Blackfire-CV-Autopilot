import os
import time
import logging
from states.handlers.base import BaseStateHandler

class NavigationHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        尋路導航與自動領體力邏輯。
        """
        # A1. 如果需要領鑽石，執行領鑽石分支流程 (優先於領體力)
        if self.machine.need_diamond_collection:
            # 情況一：如果已經點過免費鑽石並確認了，我們尋找退出按鈕關閉彈窗
            if self.machine.diamond_collected_this_run:
                for quit_btn in ["dungeons/quit.png", "common/quit_bread.png"]:
                    if os.path.exists(os.path.join("templates", quit_btn)):
                        pos_quit, conf_quit = self.matcher.match(screen_img, quit_btn, threshold=0.8)
                        if pos_quit:
                            logging.info(f"💎 領鑽石：偵測到退出按鈕 [{quit_btn}] ({conf_quit:.4f})，點擊關閉，領鑽石流程結束。")
                            self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                            self.machine.need_diamond_collection = False
                            self.machine.diamond_collected_this_run = False
                            self.machine.last_diamond_collection_time = time.time()
                            time.sleep(0.03)
                            return
            else:
                # 情況二：尚未領取或確認，進行領取步驟
                # 1. 彈窗內的確認按鈕 (獲得鑽石確認)
                pos_conf, conf_conf = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
                if pos_conf:
                    logging.info(f"💎 領鑽石：偵測到確認按鈕 [{conf_conf:.4f}]，點擊確認。")
                    self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
                    self.machine.diamond_collected_this_run = True  # 標記本次已確認領取
                    time.sleep(0.03)
                    return
                
                pos_ok, conf_ok = self.matcher.match(screen_img, "common/ok.png", threshold=0.8)
                if pos_ok:
                    logging.info(f"💎 領鑽石：偵測到 OK 按鈕 [{conf_ok:.4f}]，點擊 OK。")
                    self.mouse.click(rect["left"] + pos_ok[0], rect["top"] + pos_ok[1])
                    self.machine.diamond_collected_this_run = True  # 標記本次已確認領取
                    time.sleep(0.03)
                    return

                # 檢查是否在領鑽石彈窗內 (尋找退出/關閉按鈕)
                in_diamond_window = False
                active_quit_btn = None
                quit_pos = None
                for quit_btn in ["common/quit_bread.png", "dungeons/quit.png"]:
                    if os.path.exists(os.path.join("templates", quit_btn)):
                        pos_quit, conf_quit = self.matcher.match(screen_img, quit_btn, threshold=0.8)
                        if pos_quit:
                            # 有退出按鈕在畫面上，高機率已經在彈窗內
                            in_diamond_window = True
                            active_quit_btn = quit_btn
                            quit_pos = pos_quit
                            break

                if in_diamond_window:
                    # 2. 如果在彈窗內，只嘗試領取免費鑽石 (diamond_free.png)
                    # 使用較高閥值 (0.90) 以避免誤判到付費的 $4.99 按鈕
                    if os.path.exists(os.path.join("templates", "diamond_free.png")):
                        pos_free, conf_free = self.matcher.match(screen_img, "diamond_free.png", threshold=0.90)
                        if pos_free:
                            logging.info(f"💎 領鑽石：在視窗內偵測到免費鑽石按鈕 [{conf_free:.4f}]，點擊領取。")
                            self.mouse.click(rect["left"] + pos_free[0], rect["top"] + pos_free[1])
                            time.sleep(0.03)
                            return

                    # 3. 如果在彈窗內但沒有免費鑽石按鈕，說明鑽石正處於冷卻，點點退出按鈕關閉
                    logging.info(f"💎 領鑽石：鑽石視窗已開啟但無免費按鈕 (處於冷卻)，點擊退出按鈕 [{active_quit_btn}] 退出。")
                    self.mouse.click(rect["left"] + quit_pos[0], rect["top"] + quit_pos[1])
                    self.machine.need_diamond_collection = False
                    self.machine.diamond_collected_this_run = False
                    self.machine.last_diamond_collection_time = time.time()
                    time.sleep(0.08)
                    return

                # 4. 如果不在彈窗內，再嘗試點擊鑽石入口或返回城鎮
                # 3. 鑽石按鈕 (diamond.png)
                if os.path.exists(os.path.join("templates", "diamond.png")):
                    pos_dia, conf_dia = self.matcher.match(screen_img, "diamond.png", threshold=0.8)
                    if pos_dia:
                        logging.info(f"💎 領鑽石：在畫面偵測到鑽石按鈕 [{conf_dia:.4f}]，點擊打開領取畫面。")
                        self.mouse.click(rect["left"] + pos_dia[0], rect["top"] + pos_dia[1])
                        time.sleep(0.03)
                        return

                # 4. 返回城鎮按鈕 (goback_town.png)
                if os.path.exists(os.path.join("templates", "goback_town.png")):
                    pos_town, conf_town = self.matcher.match(screen_img, "goback_town.png", threshold=0.8)
                    if pos_town:
                        logging.info(f"💎 領鑽石：在畫面中偵測到返回城鎮按鈕 [{conf_town:.4f}]，點擊返回。")
                        self.mouse.click(rect["left"] + pos_town[0], rect["top"] + pos_town[1])
                        time.sleep(0.03)
                        return

            logging.info("⌛ 領鑽石流程中，正在等待鑽石畫面或按鈕載入...")
            time.sleep(0.01)
            return

        # A. 如果啟用且需要領體力，執行領體力分支流程
        if self.machine.enable_bread and self.machine.need_bread_collection:
            # 依優先級檢查領體力相關按鈕
            
            # 情況一：如果已經確認領過體力（或體力已滿確認了），我們只專心尋找退出按鈕，不要重複按領取或體力按鈕
            if self.machine.bread_collected_this_run:
                # 4. 關閉體力視窗按鈕 (quit bread)
                pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit_bread.png", threshold=0.8)
                if pos_quit:
                    logging.info(f"🍞 領體力：偵測到退出體力按鈕 [{conf_quit:.4f}]，點擊關閉，領取體力流程結束。")
                    self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                    self.machine.need_bread_collection = False
                    self.machine.bread_collected_this_run = False  # 重設狀態
                    self.machine.last_bread_collection_time = time.time()
                    time.sleep(0.03)
                    return
            else:
                # 情況二：尚未領取或尚未點擊確認，正常進行領取步驟
                # 1. 彈窗內的確認按鈕 (獲得體力確認或體力已滿提示確認)
                pos_conf, conf_conf = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
                if pos_conf:
                    logging.info(f"🍞 領體力：偵測到體力確認按鈕 [{conf_conf:.4f}]，點擊確認。")
                    self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
                    self.machine.bread_collected_this_run = True  # 標記本次已確認領取
                    time.sleep(0.03)
                    return

                # 2. 彈窗內的 OK 按鈕 (同樣代表確認)
                pos_ok, conf_ok = self.matcher.match(screen_img, "common/ok.png", threshold=0.8)
                if pos_ok:
                    logging.info(f"🍞 領體力：偵測到體力 OK 按鈕 [{conf_ok:.4f}]，點擊 OK。")
                    self.mouse.click(rect["left"] + pos_ok[0], rect["top"] + pos_ok[1])
                    self.machine.bread_collected_this_run = True  # 標記本次已確認領取
                    time.sleep(0.03)
                    return

                # 3. 領體力按鈕 (bread collection)
                pos_coll, conf_coll = self.matcher.match(screen_img, "common/bread_collection.png", threshold=0.8)
                if pos_coll:
                    logging.info(f"🍞 領體力：偵測到領體力按鈕 [{conf_coll:.4f}]，進行點擊領取。")
                    self.mouse.click(rect["left"] + pos_coll[0], rect["top"] + pos_coll[1])
                    time.sleep(0.03)
                    return

                # 如果體力視窗已經打開 (看見退出按鈕) 但找不到領取按鈕 (說明體力已領取過，處於冷卻或已滿)
                # 則自動點點退出關閉視窗，重置定時器與標記，避免無限重試。
                pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit_bread.png", threshold=0.8)
                if pos_quit:
                    logging.info(f"🍞 領體力：體力視窗已開啟但無領取按鈕 (處於冷卻或已領完)，點擊退出體力按鈕 [{conf_quit:.4f}] 退出。")
                    self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                    self.machine.need_bread_collection = False
                    self.machine.bread_collected_this_run = False
                    self.machine.last_bread_collection_time = time.time()
                    time.sleep(0.03)
                    return

                # 5. 打開體力視窗按鈕 (bread)
                pos_bread, conf_bread = self.matcher.match(screen_img, "common/bread.png", threshold=0.8)
                if pos_bread:
                    logging.info(f"🍞 領體力：在大廳偵測到體力按鈕 [{conf_bread:.4f}]，點擊打開體力視窗。")
                    self.mouse.click(rect["left"] + pos_bread[0], rect["top"] + pos_bread[1])
                    time.sleep(0.03)
                    return

                # 6. 入口按鈕 (door)
                pos_door, conf_door = self.matcher.match(screen_img, "common/door.png", threshold=0.8)
                if pos_door:
                    logging.info(f"🍞 領體力：在主畫面偵測到入口按鈕 [{conf_door:.4f}]，點擊進入大廳。")
                    self.mouse.click(rect["left"] + pos_door[0], rect["top"] + pos_door[1])
                    time.sleep(0.03)
                    return

            logging.info("⌛ 領體力流程中，正在等待體力畫面或按鈕載入...")
            time.sleep(0.01)
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
                time.sleep(0.03) # 等待跳轉動畫
                break

        if not clicked_any:
            # 如果是地下城模式，我們不應該僅因「找不到尋路按鈕」就判定已進入副本，因為可能正處於通關退出的加載黑屏中。
            # 我們應該完全依賴上方的主動判定 (偵測到地下城物件才轉入 EXPLORING)。
            if self.machine.config["type"] == "dungeon":
                logging.info("⌛ 尋路按鈕已不在畫面上，正在等待地下城畫面載入或尋路按鈕出現...")
                time.sleep(0.05)
            else:
                logging.info("🧭 尋路按鈕已不在畫面上，判斷已成功抵達關卡大廳。")
                self.machine.transition_to(self.machine.STATE_LOBBY)
