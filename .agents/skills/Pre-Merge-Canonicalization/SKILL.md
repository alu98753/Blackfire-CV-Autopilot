---

name: pre_merge_canonicalization
description: >
在功能尚未 merge 到主線或尚未形成穩定公開契約前，
清理 feature/fix branch 內因重構產生的 alias、compatibility facade、
re-export、舊 method 名稱與重複入口，將所有內部 caller、tests、docs、CLI
一次性遷移至唯一 canonical API，避免把過渡相容層永久帶入 main。
-----------------------------------------

# Pre-Merge Canonicalization

## 目的

當一個功能仍處於 feature / fix branch，且尚未成為正式公開或主線契約時，

不要為了「相容這個 branch 之前的 commit」保留：

* backward-compatible alias
* deprecated-but-still-new API
* compatibility facade
* duplicate import path
* re-export-only module
* 同義 factory / helper 名稱
* 舊 CLI entrypoint

應優先在 merge 前完成一次 **Atomic Migration**：

> 全 repo 遷移至唯一 canonical API，然後刪除過渡層。

目標是讓進入 main 的版本本身就是乾淨的 SSOT，而不是把 branch 開發過程中的歷史痕跡永久化。

---

# 適用情境

當出現以下任一情況時使用本 Skill：

* 重構後留下：

  ```python
  old_name = new_name
  ```

* 出現：

  ```python
  # Backward-compatible alias
  ```

* 某 module 只剩：

  ```python
  from new_module import *
  ```

* 新舊 import path 同時存在：

  ```python
  from runtime.notifier import NotificationPort
  from ports.notification import NotificationPort
  ```

* CLI 已搬家但仍保留舊 wrapper。

* feature branch 尚未 merge main，但 AI 為了「backward compatibility」保留舊 API。

* 同一個 capability 有兩個名字，例如：

  ```python
  get_notifier()
  create_notification_port()
  ```

---

# 核心判斷

在做任何刪除前，先回答：

## 1. 這個舊 API 是否已經是正式契約？

檢查：

* 是否已存在於 main / release branch
* 是否已發布給外部使用者
* 是否被其他 repo 使用
* 是否被 plugin / script / automation 外部依賴
* 是否存在穩定文件承諾
* 是否屬於 public library API

若答案為 **是**：

> 不可直接刪除，改走正式 deprecation / migration 流程。

若答案為 **否**，且只是目前 branch 內曾經存在：

> 不需要 backward compatibility。

---

# 執行流程

## Phase 1 — 找出候選過渡層

搜尋：

```text
Backward-compatible
backward compatibility
deprecated
alias
re-export
compatibility
old_name
legacy
```

並針對具體 symbol 搜尋：

```bash
git grep "get_notifier"
git grep "runtime.notifier"
```

或其他對應名稱。

---

## Phase 2 — 建立 Consumer Inventory

所有命中需分類：

```text
production code
tests
docs
CLI / tools
scripts
config
external integration
```

不可只改 production code 而漏掉 tests / docs。

---

## Phase 3 — 指定 Canonical API

每個 capability 必須明確指定唯一 canonical source。

例如：

```text
Canonical type:
ports.notification.NotificationPort

Canonical factory:
create_notification_port

Canonical CLI:
python -m tools.notifier_cli
```

禁止同時保留兩個「都可以用」的正式入口。

---

## Phase 4 — Atomic Migration

一次完成：

1. 修改所有 production callers
2. 修改 tests
3. 修改 docs / examples
4. 修改 CLI / scripts
5. 修改 type hints
6. 修改 mocks / fixtures
7. 修改 import paths
8. 執行 focused tests
9. 執行全 repo 搜尋確認舊 symbol 已清零

---

## Phase 5 — 移除過渡層

若舊 API 已無 consumer，刪除：

```python
old_name = new_name
```

刪除：

```python
# Backward-compatible alias
```

若某 module 只剩 compatibility re-export，整個 module 刪除。

例如：

```text
runtime/notifier.py
```

如果已無真正職責，只剩：

```python
from ports.notification import ...
from runtime.discord_webhook_adapter import ...
```

則應評估直接刪除。

---

# SSOT 驗收條件

完成後必須滿足：

* 一個 capability 只有一個 canonical 名稱。
* 一個 public type 只有一個 canonical import path。
* 不存在 branch-local backward compatibility alias。
* 不存在純 re-export compatibility module。
* production code 不依賴 deprecated path。
* tests 使用 canonical API，而不是特別測 legacy API。
* docs / CLI example 不再出現舊入口。
* `git grep <old_symbol>` 無有效命中。
* focused tests 通過。
* 行為不因此次 canonicalization 改變。

---

# 不可做事項

不要因為以下理由保留 alias：

> 「之前這個 branch 用過。」

Git history 已經保存歷史，不需要讓 production code 保存開發過程。

不要為同一 feature branch 的舊 commit 提供 backward compatibility。

不要把：

```text
alias
facade
shim
re-export
deprecated wrapper
```

誤認為「更安全」。

每增加一個相容入口，都增加：

* API ambiguity
* 文件漂移
* AI coder 選錯入口的機率
* 未來 migration 成本
* SSOT 破壞風險

---

# 例外：何時應保留 Compatibility Layer

只有在存在真實 consumer 時保留，例如：

* API 已進 main
* 已發布 package
* 外部 repo 已使用
* 使用者已有 config / script 依賴
* 第三方 plugin 使用
* CLI 已對外承諾
* 正處於正式 migration window

此時應改為：

```text
Deprecation Plan
→ Warning
→ Migration Guide
→ Removal Version / Deadline
```

而不是直接套用本 Skill 的刪除策略。

---

# 建議 AI 回報格式

執行前先回報：

```text
Canonical API:
- ...

Legacy / Transitional API:
- ...

Consumers found:
- production:
- tests:
- docs:
- scripts:
- external:

Compatibility required?
- Yes / No
- Evidence:

Migration plan:
1.
2.
3.

Removal candidates:
- ...
```

若無外部 consumer 且尚未 merge main，應優先選擇：

> Remove compatibility layer before merge.

---

# 一句話原則

> Branch history belongs in Git; canonical APIs belong in production code.
