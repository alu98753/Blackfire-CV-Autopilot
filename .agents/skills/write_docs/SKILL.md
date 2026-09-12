---
name: write_docs
description: 規範撰寫自然、客觀且受證據嚴格約束的文件、技術規格、架構契約與遊戲分析文章。適用於全專案 docs/ 與 meta_data/Game_docs/ 等所有 Markdown 產出。嚴禁誇大斷言、過度推論、人造權威、浮誇標籤與無效清單條列，確保文字確定性不超過既有證據。
---

# Evidence-Bound Natural Writing

## Goal

Write concise, natural prose whose certainty never exceeds the available
evidence. Preserve useful concrete details without turning the result into
an AI-style tutorial, summary, or authoritative-sounding guide.

This skill applies universally across this repository, including:
- Technical specifications, architecture contracts, and ADRs (`docs/architecture/`, `docs/features/`)
- TODOs, RFCs, and planning documents (`docs/todos/`)
- Post-mortem stories and developer logs (`docs/storys/`)
- Game data analyses, QA guides, and town building references (`meta_data/Game_docs/`)
- Any other Markdown or documentation artifacts.

---

## 1. Evidence controls certainty

Before writing a factual or prescriptive claim, determine how strongly the
available evidence supports it.

### Strongly established
When the claim is directly verified by reliable evidence, write it directly.

Example:
"Hero Coin becomes scarce later in the game."

Do not unnecessarily weaken established facts with:
"it seems", "possibly", "some people suggest", etc.

### Supported recommendation
When evidence supports a useful strategy but does not establish it as a
universal fact, write it as advice.

Use natural forms such as:
- 建議……
- 可以先……
- 優先考慮……
- 通常更值得……
- 比較不建議……

Example:
"建議把 Hero Coin 留給 VII 英雄。"

Do NOT upgrade this into:
"Hero Coin 一張都不能浪費在 VII 以下英雄。"

### Limited / uncertain evidence
If evidence is incomplete, conflicting, indirect, or based on too few
observations, preserve that uncertainty.

Use wording proportional to the actual uncertainty.

Never use hedging merely as decoration. If there is insufficient evidence
even to support a qualified claim, omit the claim or state that it is unknown.

---

## 2. Never increase evidence strength during rewriting

Rewriting may improve clarity, but must not make a claim stronger.

Examples:

"I suggest not upgrading X"
→ "不建議升級 X"        ✓
→ "X 絕對不要升級"      ✗

"X worked well in this case"
→ "X 在這種情況下效果不錯" ✓
→ "X 是最佳選擇"           ✗

"Resource X is valuable"
→ "Resource X 很珍貴"       ✓
→ "Resource X 是全遊戲最稀缺資源" ✗

The rewritten sentence must remain within the evidentiary boundary of the
source material.

---

## 3. Never fill evidence gaps

Do not invent plausible details to make an article feel complete.

Especially never invent or silently infer:
- numbers
- prices
- rankings
- causes
- mechanisms
- names
- dates
- probabilities
- optimal strategies
- categorical classifications
- motivations
- consensus

If a useful detail cannot be established, omit it.

Completeness is less important than correctness.

---

## 4. Do not expose research scaffolding unless needed

Evidence should control the writing internally, but the final prose should
not automatically talk about its sources.

Avoid unnecessary phrases such as:
- 「某玩家表示」
- 「根據社群」
- 「有人認為」
- 「資料來源指出」
- 「從上述資訊可知」

unless attribution itself is important to understanding the claim.

Instead, calibrate the sentence itself:

Weak:
"某玩家建議 Hero Coin 留給 VII 英雄。"

Better:
"建議把 Hero Coin 留給 VII 英雄。"

If the evidence is not strong enough to support even that recommendation,
weaken or omit it rather than hiding uncertainty behind anonymous attribution.

---

## 5. Preserve concrete information

Do not abstract useful details into generic advice.

Source:
"V heroes only need skill 1–3 upgraded."

Prefer:
"V 階英雄如果只是過渡，可以先提升技能約 1～3 次。"

Avoid:
"前期應合理分配資源，避免過度培養低階英雄。"

Concrete information is usually more useful than generalized lessons.

---

## 6. No redundant recap

Do not repeat information that the article has already communicated.

If a paragraph already explains the recommendation and reasoning, do NOT
append:
- 重點整理
- 簡單來說
- 懶人包
- 核心策略
- TL;DR
- 「所以你只要記住……」
- a bullet list repeating the same claims

### List rule

If the preceding prose already contains the information, converting the same
information into bullets is prohibited.

Use a list only when:
1. the information has not already been presented in prose; AND
2. the content is genuinely easier to understand as parallel items,
   steps, options, requirements, or comparisons.

Do not use lists merely to make an answer look structured.

---

## 7. Avoid manufactured authority

Do not make prose sound more authoritative than the evidence permits.

Avoid unsupported expressions such as:
- 絕對
- 必須
- 千萬不要
- 唯一
- 最佳
- 必拿
- 必練
- 終局
- 公認
- Meta
- 最划算
- 穩賺
- 一定

These words are allowed when sufficiently supported by evidence.

The rule is not "never sound certain."
The rule is:

CERTAINTY <= EVIDENCE.

---

## 8. Avoid AI-style embellishment

Do not add dramatic labels, slogans, metaphors, or gamer slang merely to
make the writing lively.

Avoid transformations such as:

"前期英雄"
→ "過渡打工人"

"不要投入太多資源"
→ "千萬別把珍貴資源砸進無底洞"

"先保留 Hero Coin"
→ "停手！一枚都別花！"

Prefer plain, specific language.

Natural writing does not need artificial excitement.

---

## 9. Use engineering terminology in technical documents

For technical specifications, architecture documents, RFCs, contracts, and TODOs,
prefer established software-engineering terminology over product copy, slogans,
or ad-hoc metaphors.

### Prefer operationally precise names

Names should describe the actual system concept, state, responsibility, or mechanism.

Prefer:

- `Milestone Notification`
- `Operator Action Required`
- `Recovery Policy`
- `Event Ownership`
- `Completion Handoff`
- `Steady-State Mode`

Avoid inventing expressive labels such as:

- 安心通報
- 人工介入求救
- 責任交割
- 圓滿完成
- 發射權

unless the phrase is explicitly user-facing product copy.

### Do not replace established SWE terms merely because they are metaphorical

Terms such as `heartbeat`, `watchdog`, `health check`, `self-healing`,
`supervisor`, and `handshake` are established engineering vocabulary and are allowed.

The rule is:

TECHNICAL NAME = PRECISE + CONVENTIONAL + CONSISTENT

not:

TECHNICAL NAME = LITERALLY NON-METAPHORICAL

### Keep user-facing language separate from system terminology

A specification may contain natural-language notification examples,
but those phrases must not automatically become architecture names,
event identifiers, states, or interface names.

Example:

User-facing text:
"今天的日常已完成，可以不用查看遊戲。"

System terminology:
`DAILY_MILESTONE_COMPLETED`

Do not derive:
`SAFE_TO_IGNORE_CONTRACT`
or
`安心責任交割事件`.

## 10. Prefer continuous prose

Default to short, cohesive paragraphs.

Do not turn every idea into:
- headings
- bullets
- numbered rules
- callout boxes
- summaries

Structure should follow the content rather than being imposed on it.

For a simple Q&A, one or two paragraphs may be enough.

---

## 11. Final evidence audit

Before producing the final text, silently inspect every meaningful claim:

1. What evidence supports this?
2. Did I make it stronger than the evidence?
3. Did I add a detail that was never established?
4. Am I presenting an inference as a fact?
5. Is this sentence actually useful?
6. Did I already say this elsewhere?
7. Am I adding structure or emphasis only because it "looks like an article"?

Delete or rewrite anything that fails this audit.

Never output the audit unless explicitly requested.