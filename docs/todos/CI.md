有，而且你現在這個 repo 的情況其實很明確：

**目前沒有 GitHub remote CI。** 我查了 `fix/town-building-egress-normalization`，repo 根目錄沒有 `.github/workflows/`；所以我前面看到 commit 的 CI status 是空的，不是「CI 通過」，而是 **根本沒有 remote workflow 在跑**。你根目錄的 `actions/` 是專案程式目錄，不是 GitHub Actions 設定。

### Local tests、Remote CI、我的 code review 是三種不同東西

| 東西                         | 主要回答                                     |
| -------------------------- | ---------------------------------------- |
| 你 / Codex 跑 local tests    | 「在這個 worktree、這台電腦，這些測試有沒有過？」            |
| GitHub CI                  | 「乾淨 clone 下來，固定環境，自動跑，這個 commit 到底有沒有過？」 |
| 我看 GitHub diff + 架構 review | 「即使測試過了，設計是不是錯的？測試是不是漏掉真正 failure path？」 |

你最近這個 case 正好是最好的例子。

Codex 可以說：

```text
59 tests PASS
```

但我看 code 後仍抓到：

```text
Chest test 測的是 INIT 已經在錯房間
但真正 bug 是：
點入口 → phase 已前進 → 才進錯房間
```

這種問題 **CI 抓不到，除非你已經寫了那條 test**。

所以：

> **CI 不能取代架構 review。架構 review 也不能取代 CI。**

---

### 那我現在直接看 GitHub diff + 你回報 local tests，夠不夠？

目前開發階段，**其實已經相當有價值，而且比單純 CI status 更重要。**

因為你這個專案目前主要風險不是：

```text
Python syntax error
```

而是：

```text
ownership 搶錯
state lifecycle 漏洞
CV evidence semantic 搞錯
physical failure 污染 business intent
測試只測 simplified path
```

這些都需要人工/AI architecture review。

但 local tests 有一個弱點：

> 我只能相信你貼給我的結果。

例如 Coding Agent 說：

```text
Ran 59 tests → OK
```

我無法從 GitHub commit 本身證明：

```text
這 59 個真的就是 commit 2a2b443 的 code 跑的
```

也不能保證它沒有：

```text
未 commit 的 local modification
環境殘留
漏跑其他 tests
不同 worktree
```

尤其你現在又是 **multi-worktree + AI coding agent**，這正是 CI 特別有價值的地方。

Remote CI 是：

```text
GitHub checkout 這個 commit
↓
乾淨環境
↓
安裝 dependencies
↓
跑固定 test command
↓
PASS / FAIL 綁在這個 SHA 上
```

所以它提供的是：

> **可重現、不可嘴砲的 commit-level evidence。**

---

# 我認為你的專案很值得加 CI，但先做很小

不要現在搞 Kubernetes、Docker pipeline、coverage gate、十種 lint。

Blackfire 現階段我只會做一個：

```text
.github/workflows/tests.yml
```

先有三層就夠。

### 1. Import / syntax sanity

例如：

```text
python -m compileall states runtime utils actions
```

抓：

```text
syntax error
壞 import
merge 後檔案殘缺
```

---

### 2. 核心 architecture regression tests

這個對你最重要。

例如固定跑：

```text
test_behavior_reach_town_normalization
test_town_subflow_precondition_navigation
test_behavior_handler_mislocation_relinquish
test_behavior_login_and_town_boundary_regression
```

這就是：

> **Architecture Contract Suite**

未來我們 freeze invariant，就放這裡。

例如：

```text
physical failure must not mutate business intent
only one physical owner
Login WORLD_READY != TOWN
UNKNOWN does not blind click
Town Ready required before dispatch
```

這些比一般 unit coverage % 對你更有價值。

---

### 3. Full test suite

例如：

```bash
python -m unittest discover -s tests
```

你之前已經有上千個 tests；如果 execution time 還合理，我會直接每個 PR 跑完整套。

這可以抓：

```text
「我只改 BloodAltar」
但意外打爆 HeroDraw / Daily pipeline / old compatibility tests
```

---

## 但你的 CI 不應該測什麼

暫時不要讓 GitHub CI 真正：

```text
開 Blackfire Crusade
操作滑鼠
抓 Windows 遊戲視窗
跑真實 CV gameplay
登入 Steam
```

這些是 **system / manual / hardware-dependent tests**。

你的測試架構應該分成：

```text
CI
├─ pure policy
├─ state machine
├─ fake SceneSnapshot
├─ mocked matcher/input
├─ architecture regressions
└─ full deterministic unit/integration suite

Local Windows validation
├─ real screenshot
├─ real template matching
├─ real game window
├─ mouse/input
└─ actual gameplay smoke test
```

這個界線很重要。

---

# 我會建議你的最終驗證流程變成

每個 Checkpoint：

```text
Coding Agent
→ 寫 red test
→ production fix
→ focused local tests
→ full local tests（必要時）
→ commit/push

GitHub CI
→ clean environment 自動驗證

我
→ 看實際 commit diff
→ 比 architecture/spec
→ review ownership/state/timing/test quality
```

三層都過：

```text
Local        ✅
Remote CI    ✅
Architecture ✅

→ Approve
```

這會比現在：

```text
Agent 說「59 tests PASS」
+
我看 diff
```

再多一層非常便宜、但很有價值的可信度。

---

### 你現在不需要做很複雜的 CI

以你的專案，我會把優先級定成：

```text
P0  Full deterministic tests
P0  Architecture regression suite
P1  compile/import sanity
P2  lint / formatting
P3  coverage threshold
P4  Windows real-game automation
```

**P4 根本不用放 GitHub CI。**

所以我的建議是：**Checkpoint B.1 做完之後或這個 feature merge 前，加第一版 GitHub Actions CI。**

而且我會把它當成專案架構的一部分：之後我 review commit 時，就能同時說：

```text
code/diff：✅
architecture：✅
focused local tests：✅
remote clean CI：✅
```

這比單純看一個綠色勾勾可靠得多。
