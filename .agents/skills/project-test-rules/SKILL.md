---
name: project-test-rules
description: 指導如何在本地執行最小直接相關的聚焦單元測試，並嚴格禁止 AI 自行執行全套測試。
---

# Project Focused Test Rules

## 核心原則 (Strict Rule)

> [!WARNING]
> **AI 嚴禁自行執行全套測試套件 (`python -m unittest discover tests`)！**

1. **僅限最小聚焦測試**：在實作或除錯時，AI 僅能執行與改動最直接相關的測試檔案、類別或單一測試方法：
   ```powershell
   # 執行單一測試檔案
   .\.venv\Scripts\python -m unittest tests.test_behavior_xxx

   # 執行單一測試類別或方法
   .\.venv\Scripts\python -m unittest tests.test_behavior_xxx.TestClassName.test_method_name
   ```
2. **收尾提醒使用者**：所有工作完成後，AI 必須在對話中生成指令，**提醒使用者手動執行全套測試**：
   ```powershell
   .venv\Scripts\python -m unittest discover tests
   ```
3. **保持測試結構一致**：新增測試時，請對齊既有 `unittest` 架構與 Mock 規範。

---

## Test-Induced Production Logic Prohibition

> [!CRITICAL]
> 測試失敗時，嚴禁為了配合 Mock、Fixture 或測試資料而在 Production Code 中加入測試專用特判。

禁止例如：

- `if mock_image_is_black: pass`
- `if test_mode: ...`
- 針對測試 fixture 特徵繞過真實 validation
- 為了讓既有 test 綠燈而放寬 production contract

修復前必須先判斷：

1. Production behavior 是否違反已確認的 Spec / Contract？
2. 還是 Test Fixture / Mock 已不符合 Production Contract？

若 Production 正確而測試資料失真：
→ 修 Test / Fixture / Mock。

若 Production 行為錯誤：
→ 修 Production。

不得以「測試目前會失敗」本身作為修改 Production Behavior 的理由。

