# bgm-copyright-check

> 免费、本地的 **BGM 版权查重工具**。给 AI 生成的 BGM 做「是否意外复现了某首已知商业录音」的版权安全网。
> 基于 **Chromaprint 声学指纹（AcoustID）+ AudioTag 在线识别** 双平台，任一命中即报警。

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows%20(x64)-blue.svg)](bin/)

📖 **完整图文教程（从安装到生成即查重）**：[docs/tutorial.md](docs/tutorial.md)

---

## 它解决什么问题

你用 ACE-Step / Suno / Udio 等模型生成 BGM 做 AI 漫剧、短剧、视频配乐。这类模型偶尔会在训练中
"记住"某些旋律，生成结果会与已有录音高度相似。本工具在**生成之后、发布之前**自动撞库，
把「训练数据泄漏 / 意外复现」挡在门外。

- ✅ 抓「几乎一模一样」的碰撞（防训练数据泄漏、意外复现商业歌）
- ✅ 双平台互为背书：AcoustID（指纹撞库，3000 万+ 曲库）+ AudioTag（上传音频识别，允许商用）
- ✅ 纯本地运行，零付费 API；只上传指纹不上传音频（AcoustID 侧）

---

## ⚠️ 重要局限（务必读）

> 指纹/识别比对只能抓「几乎一模一样 / 已被曲库收录」的碰撞，
> **抓不了「旋律/风格相似但非同一录音」**。它是安全网，不是商业免责金牌。

真正降低版权风险靠流程：

- prompt 避免写 `in the style of XXX 歌手/某歌`；
- 每次生成换 `seed`；
- 保留 prompt 记录做溯源；
- 查重报警就重生成 BGM。

若要把成品发到 YouTube，发布前可再用 YouTube Content ID 扫一遍（免费，只扫 YT 曲库）。

---

## 合规提示（商用场景必看）

| 平台 | 免费额度 | 是否允许商用 | 备注 |
|---|---|---|---|
| **AcoustID** | 无每月上限，限流 ≤3 次/秒 | ❌ 免费档仅限**非商业** | 仅作个人/开发期内部校验；商用请用 AcoustID.biz 付费档 |
| **AudioTag** | 每月 **3 小时音频**（≈1000 首） | ✅ 允许商用 | 免费、无订阅，超额才付费 |

**结论**：个人练习 / 开发期 → AcoustID 免费足够；**商用发布前清样 → 优先用 AudioTag 免费档**或付费商业服务。

---

## 文件结构

```
bgm-copyright-check/
├── SKILL.md                  # WorkBuddy 技能描述（含 YAML frontmatter）
├── README.md                # 本文件
├── check_bgm.py             # 双平台查重引擎（仅标准库，无需 pip）
├── config.example.json      # key 配置模板（复制为 config.json 填入你的 key，勿提交真实 key）
├── download_fpcalc.py       # 首次使用前运行，自动获取 Chromaprint fpcalc 二进制
└── bin/
    └── fpcalc.exe           # 由 download_fpcalc.py 生成（不纳入 git，见 .gitignore）
```

> 其他平台（macOS / Linux）：运行 `python download_fpcalc.py` 会给出官方下载页，手动把 fpcalc 放到 `bin/` 或加入 `PATH`。

---

## 快速开始

### 1. 安装

方式 A — WorkBuddy 客户端「导入技能」：
把本目录打包成 `.zip`（需包含 `SKILL.md`），在 WorkBuddy 左侧【技能市场】→「导入技能」上传即可。

方式 B — 直接放进 skills 目录：
```bash
cp -r bgm-copyright-check "$HOME/.workbuddy/skills/"
```

需要 Python 3（仅用标准库，无需 `pip install`）。

### 1.5 获取 fpcalc（声学指纹工具）

`check_bgm.py` 依赖 Chromaprint 的 `fpcalc` 二进制（**不纳入 git**）。首次使用前运行：

```bash
python download_fpcalc.py
```

Windows 会自动下载并校验 SHA256；macOS / Linux 会给出官方下载页，手动放置即可。

### 2. 申请两个免费 key（二选一 / 可并存）

- **AcoustID**（指纹撞库）：去 **https://acoustid.org/new-application** 注册一个应用，
  拿到 **application API key**（形如 `XYQSvtHabAw`）。
  > ⚠️ 注意：`/api-key` 页面给的是 **user key**，只能提交指纹、**不能用于查重 lookup**。
  > 用错会报 `invalid API key`。
- **AudioTag**（上传音频识别，允许商用）：去 **https://user.audiotag.info** 注册，
  拿到 api key（需处于 active 状态）。

### 3. 配置

在 skill 目录建 `config.json`（或设环境变量）：
```json
{
  "acoustid_api_key": "你的AcoustID application key",
  "audiotag_api_key": "你的AudioTag key"
}
```
环境变量等价：`set ACOUSTID_API_KEY=...` / `set AUDIOTAG_API_KEY=...`
缺哪个 key，就自动跳过哪个后端。

---

## 用法

### 模式一：单独查重（指定文件）

```bash
# 单个文件
python check_bgm.py "E:/bgm/ep01.mp3" --report "E:/bgm/ep01_查重报告.md"

# 一次多个（仅查这些）
python check_bgm.py "E:/bgm/ep01.mp3" "E:/bgm/ep02.wav" "E:/bgm/ep03.flac"

# 指定目录（递归扫 wav/mp3/flac/ogg/m4a/aac/opus）
python check_bgm.py "E:/bgm"
```

> 单独使用时，建议**只查本次要发布的片段**——尤其 AudioTag 按上传时长计费（3 小时/月）。

### 模式二：搭配 ACE-Step（生成即查重，逐条即时查）

`comfyui-acestep-audio` 的封装脚本 `scripts/generate_and_check.sh` 在**每生成一条音频后立刻查重**，
只查本次新生成的文件，不扫整个输出目录（避免重复上传、浪费 AudioTag 额度）：

```bash
bash "$HOME/.workbuddy/skills/comfyui-acestep-audio/scripts/generate_and_check.sh" \
  "<项目>/audio/BGM_xxx_spec.json" "<项目>/audio"
```

- 流程：写 spec → `build_params` → `run.js` 生成 MP3 → 从 run.js 的 JSON 提取**本次生成路径** → 立即双平台查重。
- 报告：每条音频同目录生成 `<音频名>_查重报告.md`，不混成大目录报告。
- 脚本已内置 Windows 路径转换（Git Bash 的 POSIX 路径 → Windows 原生路径），Windows 本机可直接跑。

---

## 输出含义

综合状态 = 两平台最坏情况：

| 状态 | 含义 | 建议 |
|---|---|---|
| 🟢 基本干净 | 两平台均未命中 | 可发布 |
| 🟡 疑似碰撞 | AcoustID 0.5~0.8 / AudioTag 低置信 | 人工复核 |
| 🔴 高概率碰撞 | AcoustID ≥0.8 / AudioTag 命中 | 重生成 BGM |

明细分别列出 AcoustID（曲名/艺术家/id/score）与 AudioTag（曲名/艺术家/专辑/年份/confidence）。

`--backends acoustid|audiotag` 可强制单平台；`--report` 写 Markdown 报告。

---

## 常见问题（踩坑记录）

**Q：AcoustID 报 `invalid API key`？**
A：你填的大概率是 `/api-key` 页面的 **user key**。查重要用 **application key**，去
https://acoustid.org/new-application 注册应用后获取。

**Q：AudioTag 报 `could not process the file`？**
A：音频太短。AudioTag 需要约 **10 秒以上** 的音频才能识别；BGM 通常几十秒~几分钟不受影响。

**Q：双平台都失败了？**
A：检查 `config.json` 的 key 是否正确、网络能否访问 `api.acoustid.org` 与 `audiotag.info`。

---

## 隐私

- AcoustID 链路：仅上传 Chromaprint 指纹（整型数列），**不上传音频本体**。
- AudioTag 链路：需上传音频本体（其 API 即识别音频），受 3 小时/月额度限制。

---

## License

MIT —— 自由使用、修改、再分发。商用查重请以 AudioTag 免费档或付费商业服务为准，遵守各平台 TOS。
