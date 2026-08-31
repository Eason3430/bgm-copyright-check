# 查重报告示例（示例输出）

> 本文件是 `check_bgm.py` 生成报告的**格式示例**，用于说明三种判定状态长什么样。
> 真实运行请用 `python check_bgm.py "你的音频或目录" --report "报告.md"`。

---

## 示例 1：全部干净（最常见）

```text
🔍 待查重文件：4 个，后端：AcoustID + AudioTag

▸ ep01_theme.mp3 ... 🟢 干净
  - AcoustID：干净
  - AudioTag：干净
▸ ep01_bgm2.wav ... 🟢 干净
  - AcoustID：干净
  - AudioTag：干净
▸ ep02_transition.mp3 ... 🟢 干净
  - AcoustID：干净
  - AudioTag：干净
▸ ep02_bgm.wav ... 🟢 干净
  - AcoustID：干净
  - AudioTag：干净

=== 汇总：4 检查，0 命中/疑似 ===
```

→ 两平台都没命中，可发布。

---

## 示例 2：某文件疑似（建议人工复核）

```text
🔍 待查重文件：1 个，后端：AcoustID + AudioTag

▸ ep03_suspect.mp3 ... 🟡 疑似碰撞
  - AcoustID：0.62（曲名：Unknown Track / 艺术家：Various）
  - AudioTag：低置信，未明确命中

=== 汇总：1 检查，1 疑似 ===
```

→ AcoustID 命中分 0.5~0.8 之间，可能是片段相似或元数据噪声。**人工听一下**，拿不准就换 seed 重生成。

---

## 示例 3：高概率碰撞（必须处理）

```text
🔍 待查重文件：1 个，后端：AcoustID + AudioTag

▸ ep04_risky.mp3 ... 🔴 高概率碰撞
  - AcoustID：0.91（曲名：Sunflower / 艺术家：Post Malone, Swae Lee）
  - AudioTag：命中（曲名：Sunflower / 艺术家：Post Malone, Swae Lee / 专辑：Spider-Man / 年份：2018）

=== 汇总：1 检查，1 命中 ===
```

→ 两平台都明确命中同一首已知商业录音。**不要发布**，换 seed / 改写 prompt 重生成，再查重直到 🟢。

---

## 状态含义速查

| 状态 | 含义 | 建议 |
|---|---|---|
| 🟢 基本干净 | 两平台均未命中 | 可发布 |
| 🟡 疑似碰撞 | AcoustID 0.5~0.8 / AudioTag 低置信 | 人工复核，拿不准就重生成 |
| 🔴 高概率碰撞 | AcoustID ≥0.8 / AudioTag 明确命中 | 必须重生成，勿发布 |

---

## 常见「出错」情形（非命中，是流程问题）

- `AcoustID：出错 找不到 fpcalc` → 首次使用前先跑 `python download_fpcalc.py`
- `AudioTag：出错 identify 失败: audio is too short` → 音频太短（AudioTag 需 ≥10 秒）；短音效靠 AcoustID 兜底
- `AcoustID：出错 invalid API key` → 填的是 `/api-key` 的 user key，要用 new-application 的 application key
- 某后端整行 `出错` 而另一后端正常 → 缺那个 key 或网络问题，不影响另一后端结果
