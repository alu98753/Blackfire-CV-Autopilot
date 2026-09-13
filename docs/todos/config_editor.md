對，你的痛點其實不是 Git，而是目前把兩種完全不同的設定混在一起了：

* **產品預設**：程式作者認為一般情況應該怎麼跑。
* **個人政策**：你的帳號到底哪些東西分解、哪些保留、打哪關、哪些 Boss 要打。

後者有些資料很長，而且你會頻繁人工調整。這種資料如果叫你每次只在 sparse override 裡補幾行，確實很難用；但如果直接改 `defaults.toml`，又會讓 Git 一直髒掉。

我不建議做一份完整的：

```text
config/defaults.toml        tracked
user_data/native/defaults.toml   untracked
```

然後兩份內容幾乎一模一樣。

因為會出現另一個更麻煩的問題：

```text
Git defaults 新增設定
        ↓
你的 native/defaults.toml 還是舊版本
        ↓
到底誰是 authoritative？
        ↓
久了兩份 drift
```

你會變成在手動同步兩份 defaults。

---

## 我比較推薦：把「長的個人政策」獨立成 Profile-owned data

像這樣：

```text
config/
├─ defaults.toml                  # Git track
│
├─ policies/
│  └─ item_policy.default.toml    # Git track，官方預設政策
│
user_data/
├─ native/
│  ├─ config.toml                 # 不 track，小型 override
│  └─ item_policy.toml            # 不 track，帳號自己的大型政策
│
└─ sandbox/
   ├─ config.toml
   └─ item_policy.toml
```

責任變成：

```text
defaults.toml
= 程式怎麼運作

config.toml
= 這個帳號的小型差異

item_policy.toml
= 這個帳號「我要什麼 / 不要什麼」
```

這其實很適合你的「分解 / 不分解」問題。

---

# 更重要的是：大型清單不要用「整份覆寫」

例如假設官方有 100 個物品：

```toml
[items]
wolf_skin = "keep"
bat_wing = "keep"
slime = "keep"
...
100 個
```

你不應該為了改三個東西，就複製 100 個到自己的檔案。

### 方法 A：Boolean map + deep merge

官方：

```toml
[disassemble.items]
wolf_skin = false
bat_wing = false
slime = false
old_sword = true
broken_ring = true
```

你的帳號只需要：

```toml
# user_data/native/item_policy.toml

[disassemble.items]
wolf_skin = true
bat_wing = true
```

最後：

```text
official policy
      +
native policy
      ↓
effective policy
```

因為你現在的 `_deep_merge()` 對 dictionary/table 本來就很適合這種結構。

這是我最喜歡的方案。

---

## 如果它本質是「集合」，甚至可以做 add/remove

例如預設：

```toml
disassemble = [
    "gray_sword",
    "gray_armor",
    "green_ring"
]
```

問題是 TOML array override 通常就是**整個取代**。

所以你可以定義：

```toml
# account_main

[disassemble]
add = [
    "wolf_skin",
    "bat_wing"
]

remove = [
    "green_ring"
]
```

Runtime：

```text
effective
=
default set
+ add
- remove
```

這對「可分解 / 不可分解」這種 set-like policy 特別舒服。

---

# 但你還有另一個需求：「我想看到完整資料，很方便改」

這才是你真正喜歡直接開 `defaults.toml` 的原因。

因為它：

> **完整、集中、看得到所有選項。**

Sparse override 最大 UX 問題就是：

```text
我自己的 config.toml 只有 5 行
→ 我根本不知道還有哪些東西可以改
```

所以我會另外做一個 **Effective Config View**：

```powershell
python tools/config.py show --profile native
```

產生：

```text
scratch/effective_config_native.toml
```

裡面是：

```text
defaults
+ native override
+ native item policy
```

完整展開。

你可以拿它來：

* 查目前所有設定
* 搜尋某個 item
* 比較兩帳號
* debug

但：

> **它不是 source of truth，不手動 commit。**

這樣你同時得到：

```text
完整可讀性
+
Git 不會髒
+
profile 不用複製全部 defaults
```

---

# 如果未來願意再做一步，我甚至建議做「Config Editor」

你的需求其實很適合：

```text
左邊：完整 effective config
右邊：哪些值是 Default / Profile Override

修改一項
↓
只寫入 user_data/native/config.toml
```

也就是 UI 看起來像你現在開完整 `defaults.toml`：

```text
✓ wolf_skin       分解
✗ purple_armor    保留
✓ bat_wing        分解
...
```

但儲存時只存：

```toml
[disassemble.items]
wolf_skin = true
purple_armor = false
bat_wing = true
```

甚至只保存「與 default 不同」的項目。

這是最好的 UX。

---

# 所以我會把你的設定架構定成 4 層

```text
① Product Defaults
config/defaults.toml
Git tracked
完整、穩定、全使用者預設

        ↓

② Shared Policy Defaults
config/policies/*.toml
Git tracked
大量 item catalog / 預設分解政策

        ↓

③ Profile Overrides
user_data/native/config.toml
user_data/sandbox/config.toml
Git ignored
只保存帳號差異

        ↓

④ Runtime State
cooldown / progress / history
Git ignored
不是 configuration
```

而且：

> **Profile 不需要再複製一份完整 defaults.toml。**

只有「這個帳號真正擁有的大型政策」才值得獨立一份完整/半完整 profile file。

---

## 以你現在的例子，我最推薦這個判斷

假設：

> 「藍裝哪些分解、紫裝哪些保留」

如果這件事兩帳號可能不同，而且你會常改：

**它就不該繼續只是 `defaults.toml` 裡的一坨設定。**

它其實是一個 domain concept：

```text
Item Disposal Policy
```

可以正式抽成：

```text
config/item_policy.default.toml
user_data/native/item_policy.toml
user_data/sandbox/item_policy.toml
```

而不是繼續讓 `defaults.toml` 無限長。

---

### 最後給你一個很好用的判斷方式

不要問：

> 「這設定要不要放 defaults？」

改問：

> **「這是軟體預設，還是玩家帳號的策略？」**

例如：

```text
OCR threshold
navigation timeout
watchdog timeout
→ 軟體預設
→ defaults.toml

打哪關
哪些 Boss
哪些裝備分解
哪些素材出售
→ 玩家策略
→ profile-owned config/policy

上次打 Boss 時間
Dungeon cooldown
今日完成狀態
→ runtime state
```

我認為這才是你目前 config 最大的架構分界。你不是需要「另一份完整 default」，而是需要把 **Product Configuration** 和 **Player Policy** 正式拆開。
