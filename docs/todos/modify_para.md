# TODO: PARS / Story 文件改進規格（口語敘事化與 Commit 追蹤）

## 1. 背景與目標
現有 `docs/storys/` 中的 PARS 文檔術語密集、以條列式程式細節為主，難以在對外分享或口語交流時「一開口就講出好懂的故事」。
**目標**：在保留原 PARS 架構規範的前提下，為每篇 Story 新增一段「純文字口語化故事摘要」，並附帶精確的「Git Commit ID 清單」，兼顧真人表達與 AI 現場還原歷史情境的需求。

---

## 2. Before vs After 對照

| 維度 | Before（現有 PARS） | After（改進後目標） |
| :--- | :--- | :--- |
| **表達形式** | 多層 Markdown 條列點、程式碼符號密集 | **純文字流暢段落**，無條列點、無冷僻術語符號 |
| **語言風格** | 書面技術規格（如「底層 Handler 越權搶跑」、「Precondition Livelock」） | **口語講故事**，用一般開發者聽得懂的比喻與場景直接說明白 |
| **修飾詞彙** | 包含「徹底收斂」、「架構隱患」等形容詞 | **去除無謂修飾**，僅客觀描述遭遇問題、思考轉折與解法 |
| **上下文復原** | 需人工 `git log` 逐一比對分支提交 | 文末提供 **`Related Commits` 清單**，讓 AI 秒查當時 diff 與上下文 |

---

## 3. 口語化故事規範（Narrative Guidelines）
1. **純文字段落**：整篇故事為 1~2 段連續文字，**禁止使用條列清單（bullet points）**。
2. **通俗易懂**：將專業名詞轉譯為直白語言（例如：把「Precondition 未滿足」轉譯為「角色還在地牢深處，肉身還沒到城鎮」）。
3. **無贅詞形容**：去除誇飾語氣，聚焦「原本怎麼做 ➔ 遇到什麼坑 ➔ 為什麼換這個思路 ➔ 現在怎麼運作」。
4. **關聯 Commits**：文末附上 1~3 個核心 commit ID 與簡短 message，供 AI 接收提問時精確定位改動。

---

## 4. 驗證範本（Gold Standard）

### 口語故事段落範例：
> 一開始我們只有純狀態機，只要排程決定要做告示牌，就會直接把全局目標改寫成告示牌模式。因為狀態機本身具備自癒能力，不管角色人在哪裡都會邊走邊修正，所以過去並不需要前置條件。但隨著場景變多，這種做法導致主流程塞滿了各種特例判斷，代碼越來越難維護。後來我們想引入 BDI 搭配狀態機的混合模式，讓意圖和執行分開。然而在改動過程中發現，BDI 要求一個意圖必須在確認滿足前置條件後，才能派發第一步動作，不能像以前一樣先偷跑改狀態。為了解決這個衝突，我們加入了前置條件導航機制，在角色真正回到城鎮並看見目標之前，先保留原本正在跑的活動配置，透過預先建好的場景導航圖主動把角色帶回城鎮，直到實際核驗到目標建築與紅點，才正式把狀態切換過去。

### 關聯 Commit 範例：
- `b084c53`: `fix(navigation): resolve 08:05 reset dispatch, boss subflow preemption, and exit_battle town false positive`
- `d95f9db`: `feat(navigation): complete town subflow on missing red dot and unify bulletin board red-dot gating`

---

## 5. 待執行事項（Action Items）
- [ ] 檢視 `docs/storys/` 內代表性 PARS 文件。
- [ ] 在每篇 PARS 開頭或結尾統一增設 `## Story in Plain Words（口語故事）` 與 `## Related Commits` 區塊。
- [ ] 更新 `branch_completion_workflow` skill 模板，將口語故事納入收尾標配。