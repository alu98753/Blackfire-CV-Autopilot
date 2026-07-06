import os
import time
import logging
from states.handlers.base import BaseStateHandler

class BagCleaningHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        背包清理狀態處理邏輯。
        依序執行：打開背包 -> 大量分解 -> 全選 -> 分解 -> 確認 -> 整理 -> 退出背包。
        """
        # 1. 優先處理確認與 OK 彈窗 (例如大量分解確認、整理確認等)
        pos_conf, conf_conf = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
        if pos_conf:
            logging.info(f"🎒 背包清理：偵測到確認彈窗 [{conf_conf:.4f}]，點擊確認。")
            self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
            if not getattr(self.machine, "bag_disassembled", False):
                self.machine.bag_disassembled = True
                self.machine.bag_select_all_clicked = False  # 重設全選狀態
                logging.info("🎒 背包清理：已完成分解確認，標記 bag_disassembled = True。")
            time.sleep(0.1)
            return

        pos_ok, conf_ok = self.matcher.match(screen_img, "common/ok.png", threshold=0.8)
        if pos_ok:
            logging.info(f"🎒 背包清理：偵測到 OK 彈窗 [{conf_ok:.4f}]，點擊確認。")
            self.mouse.click(rect["left"] + pos_ok[0], rect["top"] + pos_ok[1])
            if not getattr(self.machine, "bag_disassembled", False):
                self.machine.bag_disassembled = True
                self.machine.bag_select_all_clicked = False  # 重設全選狀態
                logging.info("🎒 背包清理：已完成分解確認，標記 bag_disassembled = True。")
            time.sleep(0.1)
            return

        # 2. 如果已經整理過，尋找退出按鈕關閉背包
        if getattr(self.machine, "bag_tidied", False):
            # 優先嘗試 common/quit.png 作為關閉按鈕
            for quit_btn in ["common/quit.png"]:
                if os.path.exists(os.path.join("templates", quit_btn)):
                    pos_quit, conf_quit = self.matcher.match(screen_img, quit_btn, threshold=0.8)
                    if pos_quit:
                        logging.info(f"🎒 背包清理：已整理完畢，點擊退出按鈕 [{quit_btn}] (信心度: {conf_quit:.4f}) 關閉背包。")
                        self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                        self.machine.need_bag_cleaning = False
                        self.machine.bag_tidied = False
                        self.machine.bag_disassembled = False  # 重設分解狀態
                        self.machine.bag_select_all_clicked = False  # 重設全選狀態
                        time.sleep(0.1)
                        
                        # 回歸原本的掛機狀態
                        if self.machine.config["type"] == "dungeon":
                            self.machine.transition_to(self.machine.STATE_DUNGEON_EXPLORING)
                        else:
                            self.machine.transition_to(self.machine.STATE_LOBBY)
                        return

        # 3. 如果已經分解完畢，則進行「整理」
        if getattr(self.machine, "bag_disassembled", False):
            if os.path.exists(os.path.join("templates", "common/tidy.png")):
                pos_tidy, conf_tidy = self.matcher.match(screen_img, "common/tidy.png", threshold=0.8)
                if pos_tidy:
                    logging.info(f"🎒 背包清理：偵測到整理按鈕 [{conf_tidy:.4f}]，點擊整理。")
                    self.mouse.click(rect["left"] + pos_tidy[0], rect["top"] + pos_tidy[1])
                    self.machine.bag_tidied = True
                    time.sleep(0.1)
                    return

        # 4. 如果尚未分解，則執行分解流程：大量分解 -> 全選 -> 分解
        else:
            # 4.1 如果尚未點擊過「全選」，優先檢查與點擊「全選」
            if not getattr(self.machine, "bag_select_all_clicked", False):
                if os.path.exists(os.path.join("templates", "common/select_all.png")):
                    pos_all, conf_all = self.matcher.match(screen_img, "common/select_all.png", threshold=0.8)
                    if pos_all:
                        logging.info(f"🎒 背包清理：偵測到全選按鈕 [{conf_all:.4f}]，點擊全選。")
                        self.mouse.click(rect["left"] + pos_all[0], rect["top"] + pos_all[1])
                        self.machine.bag_select_all_clicked = True
                        time.sleep(0.1)
                        return

            # 4.2 如果已經點擊過「全選」，則檢查與點擊「分解」
            else:
                if os.path.exists(os.path.join("templates", "common/Disassembly.png")):
                    pos_dis, conf_dis = self.matcher.match(screen_img, "common/Disassembly.png", threshold=0.8)
                    if pos_dis:
                        logging.info(f"🎒 背包清理：偵測到分解按鈕 [{conf_dis:.4f}]，點擊分解。")
                        self.mouse.click(rect["left"] + pos_dis[0], rect["top"] + pos_dis[1])
                        time.sleep(0.1)
                        return

            # 4.3 檢查大量分解按鈕 (打開背包後會看見)
            if os.path.exists(os.path.join("templates", "common/Backpack_Disassembly.png")):
                pos_mass, conf_mass = self.matcher.match(screen_img, "common/Backpack_Disassembly.png", threshold=0.8)
                if pos_mass:
                    logging.info(f"🎒 背包清理：偵測到大量分解按鈕 [{conf_mass:.4f}]，點擊進入大量分解。")
                    self.mouse.click(rect["left"] + pos_mass[0], rect["top"] + pos_mass[1])
                    time.sleep(0.1)
                    return

        # 5. 檢查背包按鈕 (若背包尚未打開，在大廳或探索畫面點擊打開)
        if os.path.exists(os.path.join("templates", "common/bag.png")):
            pos_bag, conf_bag = self.matcher.match(screen_img, "common/bag.png", threshold=0.8)
            if pos_bag:
                logging.info(f"🎒 背包清理：偵測到背包入口按鈕 [{conf_bag:.4f}]，點擊打開背包。")
                self.mouse.click(rect["left"] + pos_bag[0], rect["top"] + pos_bag[1])
                time.sleep(0.1)
                return

        logging.info("⌛ 背包清理流程中，正在等待背包相關畫面或按鈕載入...")
        time.sleep(0.05)
