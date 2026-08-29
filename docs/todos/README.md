# 專案待辦事項與臨時草稿專區 (Todos & Scratch Notes) 📝

本目錄集中收納《黑火遠征》專案在開發、測試、長掛機與除錯過程中的**待辦事項 (Todos)**、**臨時分析 (Temp Notes)**、**測試防護網計畫 (Test Matrix Plans)** 與**資源變化草稿 (Scratch Records)**。

---

## 📂 檔案清單與用途索引

| 檔案名稱 | 內容摘要與維護目的 | 當前狀態 |
| :--- | :--- | :--- |
| [future_work.md](future_work.md) | **待辦事項與未來規劃**：包含長掛機注意事項、高/低優先度優化、已解決但觀察中項目與暫時擱置需求。 | 📌 長期維護 |
| [test_dev_temp.md](test_dev_temp.md) | **輕量化行為測試防護網建構計畫**：依 Google 軟體工程標準定義的 5 大領域行為測試開發矩陣與勾選清單。 | 🧪 測試開發計畫 |
| [exception_watchdog_todo.md](exception_watchdog_todo.md) | **例外處理與卡死臨時分析**：深度剖析 Watchdog 卡死未觸發遊戲重開原因與救援機制優化建議。 | 🔍 除錯筆記 |
| [resource_record.md](resource_record.md) | **資源變化草稿**：紀錄鑽石、抽卡或特定活動的即時消耗草稿。 | 📋 臨時草稿 |

---

## 🛠️ 維護與生命週期規範

1. **草稿與除錯筆記**：
   - 當特定問題（如卡死問題）完成修復並於 `docs/storys/` 產出正式 PARS 開發故事後，可將對應的筆記更新或歸檔。
2. **待辦與優化項目**：
   - 新增待辦需求時，統一記錄於 [future_work.md](future_work.md)。
   - 功能完成後，請於收尾時更新狀態為 `[已完成]`，並在 `docs/storys/` 撰寫 PARS 故事。
