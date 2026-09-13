## 目標

使 Bulletin Board detector 在一次真實 runtime failure 後，能回答：

1. 哪個 feature 沒有通過？
2. 差 threshold 多少？
3. 是 ROI 問題、scale 問題，還是 template similarity 問題？
4. 哪項 evidence 最接近成功？
5. 為何最後得到該 classification？

## Feature Evidence

每個 detection channel 應保留：

```python
FeatureEvidence:
    template
    threshold

    roi
    roi_best_score
    roi_best_position
    roi_best_scale

    global_best_score
    global_best_position
    global_best_scale

    passed
```

至少涵蓋：

```text
quit
reset
task
task_after
bag_tidy
bag_disassembly
```

## 決策契約

### ROI 與 Global 必須分離

ROI-scoped feature：

```text
reset
task
task_after
quit
```

其 classification **只能使用 ROI match 結果**。

Global match：

```text
只能用於 diagnostics。
```

禁止：

```text
ROI miss
→ global hit
→ 當作 ROI feature success
```

## Semantic Diagnosis

Diagnostic formatter 應產生 reason。

例如：

```text
PASS
SCORE_BELOW_THRESHOLD
NEAR_THRESHOLD
STRONG_MATCH_OUTSIDE_ROI
NO_MEANINGFUL_MATCH
KNOWN_NEGATIVE_FEATURE
```

建議 near miss：

```text
threshold - score <= 0.05
```

只作 diagnostics，不改 detection threshold。

## Runtime Log

UNKNOWN 時應輸出：

```text
[BulletinBoardDetector] classification=UNKNOWN_OVERLAY

quit       PASS       score=.94 / threshold=.80 (+.14)
reset      FAIL       score=.31 / threshold=.65 (-.34)
task       NEAR_MISS  score=.62 / threshold=.65 (-.03)
task_after FAIL       score=.43 / threshold=.65 (-.22)

bag_tidy        ABSENT
bag_disassembly ABSENT

Strongest positive evidence:
task=.62, short by .03

Diagnosis:
TASK_NEAR_THRESHOLD

Candidate scales:
[...]
Best scale:
...

Debug artifact:
debug_bulletin_board_verify.png
```

若：

```text
ROI task=.40
Global task=.82
```

則：

```text
Diagnosis:
STRONG_TASK_MATCH_OUTSIDE_EXPECTED_ROI

Possible cause:
ROI/layout mismatch
```

## UNKNOWN Overlay Safety

`UNKNOWN_OVERLAY` 不代表 `KNOWN_INTERFERENCE`。

不得在 log 或 decision 中描述為「干擾層」。

若 overlay 是在本次 `bulletin_board` click 後立即出現：

```text
target click
→ quit transition
→ no known negative evidence
```

應保留 causal context，標記為：

```text
SUSPECTED_TARGET_OVERLAY
```

或等價語意。

首先保存 diagnostics；不得僅因 positive template miss 就立即視為錯誤 UI。

## 驗收

一次真實失敗 log 必須能直接回答至少其中一種：

```text
template mismatch
threshold near miss
ROI mismatch
scale mismatch
known interference
no overlay opened
```

不得再只得到：

```text
task=0.58
```

而不知道下一步應修哪一層。
