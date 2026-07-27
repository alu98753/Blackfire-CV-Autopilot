# 珠寶加工廠新增綠色素材「蟾蜍毒液 (Toad_Venom)」可處置/可分解白名單 PARS 故事 💎

---

## 🎯 P - Purpose (目的)

新增綠色品質素材 `Toad_Venom.png` (蟾蜍毒液) 至 `templates/town_building/Jewelry_workshop/goods/green/` 目錄，並在 `config.py` 的珠寶加工廠出售白名單 (`goods_settings["green"]`) 中啟用 `"Toad_Venom": True`，實現自動化辨識與批量出售/分解。

---

## 🏃 A - Action (行動)

1. **分支建立**：創立功能開發分支 `feat/add-toad-venom-dismantle`。
2. **範本配置**：確認模板檔案 `templates/town_building/Jewelry_workshop/goods/green/Toad_Venom.png` 存在。
3. **配置更新**：
   - 於 `config.py` 的 `SUBFLOW_CONFIGS["jewelry_workshop"]["goods_settings"]["green"]` 加入 `"Toad_Venom": True`。
4. **文檔更新**：
   - 更新 `docs/town_building/Jewelry_workshop.md` 的品質目錄結構與配置說明。
5. **品質驗證**：
   - 執行全套單元測試，確保 `JewelryWorkshopHandler` 與 `_get_enabled_goods` 解析邏輯 100% 綠燈運作。

---

## 📊 R - Result (結果)

- **配置生效**：`_get_enabled_goods` 能自動識別並組合相對路徑 `green/Toad_Venom`。
- **全套單元測試**：全數測試 CLEAN PASS。

---

## 💡 S - So What (經驗與影響)

- **擴充便利性**：透過品質分級目錄 (`gray`, `green`, `blue`, `purple`) 與 `goods_settings` 鍵值對設計，新增素材僅需 1 行配置即可完成擴充。
- **防呆與彈性**：預設為 `True`，使用者若想保留可隨時切換為 `False`，維持腳本高客製化防護。

---

## ⚡ I - Influence (影響範圍)

- `config.py`
- `docs/town_building/Jewelry_workshop.md`
- `templates/town_building/Jewelry_workshop/goods/green/Toad_Venom.png`
