---
name: bgm-copyright-check
summary: 免费 BGM 版权查重（双平台：AcoustID 指纹撞库 + AudioTag 上传识别）—— 接在 ACE-Step 等生成 BGM 之后，自动排查是否撞了商业歌曲。
description: >
  用 Chromaprint(fpcalc) 对 AI 生成的 BGM 算声学指纹，提交到 AcoustID 免费 API
  比对其全球曲库（3000万+ 已知录音）；同时把音频上传到 AudioTag 免费 API
  （每月 3 小时音频≈1000首，允许商用）做交叉识别。两个平台任一命中即报警。
  纯标准库 Python、零付费 API、不上传敏感信息（AcoustID 只传指纹）。
  用于 AI 漫剧/短剧产线中 ACE-Step 生成 BGM 后的版权安全网。
read_when:
  - 用户用 ACE-Step / Suno / Udio 等生成 BGM 或歌曲，想排查版权风险
  - 用户问"歌曲查重""音频比对""是否撞歌""版权检测"
  - 在音频生成后做发布前合规核查
---

# bgm-copyright-check

免费、本地的 BGM 版权查重工具。基于 **Chromaprint 声学指纹 + AcoustID 在线曲库**，
专用于「AI 生成的 BGM 是否意外复现了某首已知商业录音」这一风险点。

## 为什么需要它（你的场景）
你用 `comfyui-acestep-audio` 生成 BGM 做 AI 漫剧/短剧。ACE-Step 等模型可能在训练中
"记住"了某些旋律，生成结果偶尔会与已有录音高度相似。本 skill 在生成后自动撞库，
把这种「训练数据泄漏 / 意外复现」挡在发布之前。

## 重要局限（务必读）
- 指纹比对只抓**几乎一模一样**的碰撞，**抓不了"旋律/风格相似但非同一录音"**。
  它是安全网，不是商业免责金牌。
- 真正降低版权风险靠流程：prompt 避免写 `in the style of XXX 歌手/某歌`、每次换 seed、
  保留 prompt 记录做溯源、查重报警就重生成。
- 若要把剧发到 YouTube，发布前可再用 YouTube Content ID 扫一遍（免费，只扫 YT 曲库）。

## 合规提示（商用场景必看）
- **AcoustID 免费档仅限「非商业用途」**。官方 Web Service 准则明确：
  "No commercial usage — This service is provided for free for non-commercial use only."
  你做的是发到火龙/抖音/红果的商业化短剧，严格说用 AcoustID 免费 key 清商用 BGM 违反 TOS。
  合规路径二选一：
  1. 把查重当成**个人/开发期内部校验**工具（不对外宣称依赖其合规结论），接受该 TOS 边界；
  2. 商用合规请用 **AudioTag 免费档**（见下，允许商用，每月 3 小时音频 ≈ 1000 首）或 **acoustid.biz 商业付费档**。
- **AudioTag（audiotag.info）免费档**：完全免费、无订阅、允许商用，每月额度 **3 小时音频**（约 10s 音频即可识别，
  故约可识别 ~1000 首/月），超额才付费。曲库约 2000 万首。其 API 走「上传音频文件」而非指纹，
  与本 skill 的 AcoustID 指纹链路不同，可作为第二背书源。需要的话可加一个 AudioTag 后端。
- 结论：个人练习/开发期 → AcoustID 免费足够；商用发布前清样 → 优先 AudioTag 免费档或付费商业服务。

## 依赖（已自带）
- `bin/fpcalc.exe`：Chromaprint 1.6.1 声学指纹工具。**首次使用前运行 `python download_fpcalc.py` 自动获取**
  （Windows 自动下载并校验 SHA256；macOS/Linux 按脚本提示从官方 release 手动放置）。
  也可从 https://github.com/acoustid/chromaprint/releases 手动下载对应平台 fpcalc，放到 `bin/` 或加入 PATH。
- Python 标准库即可，无需 pip 装任何包。

## 一次性配置：两个免费 key（二选一/可并存）
本 skill 默认**双平台都跑**（AcoustID + AudioTag），任一命中即报警。两个 key 都免费：

- **AcoustID**（指纹撞库，非商用 TOS）：必须去 **https://acoustid.org/new-application** 注册一个应用，拿到 **application API key**（形如 `XYQSvtHabAw`）。注意 `/api-key` 页面给的是 **user API key**，只能用来提交指纹，**不能用于查重 lookup**。
- **AudioTag**（上传音频识别，允许商用，3 小时/月≈1000 首）：https://user.audiotag.info 注册 → 拿到 api key（需处于 active 状态）

配置方式（环境变量或 config.json，可并存；缺哪个 key 就自动跳过哪个后端）：
```json
{
  "acoustid_api_key": "你的AcoustID application key",
  "audiotag_api_key": "你的AudioTag key"
}
```
或环境变量：`set ACOUSTID_API_KEY=...` / `set AUDIOTAG_API_KEY=...`

## 两种使用模式

### 模式一：单独使用（在 WorkBuddy 里指定文件查重）
你直接在 WorkBuddy 指定要查的文件/目录，工具**只查你给的那些**，不会去扫其他文件：
```bash
# 指定单个文件
python check_bgm.py "E:/bgm/ep01.mp3" --report "E:/bgm/ep01_查重报告.md"

# 一次指定多个文件（空格分隔，仅查这些）
python check_bgm.py "E:/bgm/ep01.mp3" "E:/bgm/ep02.wav" "E:/bgm/ep03.flac"

# 也可以指定一个目录（递归扫 wav/mp3/flac/ogg/m4a/aac/opus）
python check_bgm.py "E:/bgm"
```
> 单独使用时，建议**每次只查本次要发布/复核的片段**，别丢整个大目录——尤其 AudioTag 按上传音频时长计费（3 小时/月）。

### 模式二：搭配 ACE-Step（生成即查重，逐条即时查）
`comfyui-acestep-audio` 的封装脚本 `scripts/generate_and_check.sh` 会在**每生成一条音频后立刻对该条做查重**，
只查本次新生成的文件，绝不扫整个输出目录（避免重复上传旧文件、浪费 AudioTag 额度）：
```bash
bash "$HOME/.workbuddy/skills/comfyui-acestep-audio/scripts/generate_and_check.sh" \
  "<项目>/audio/BGM_xxx_spec.json" "<项目>/audio"
```
- 流程：写 spec → build_params → run.js 生成 MP3 → 从 run.js 的 JSON 输出里提取**本次生成的文件路径** → 立即双平台查重。
- 报告：每条音频在同目录生成 `<音频名>_查重报告.md`（如 `ep01_theme_查重报告.md`），不混进一个大目录报告。
- 脚本已内置 Windows 路径转换（Git Bash 的 POSIX 路径 → Windows 原生路径），在本机 Windows 上可直接运行。
- 命中 🔴/🟡 的片段人工确认或换 seed 重生成。

## 输出含义（综合状态 = 两平台最坏情况）
- 🟢 基本干净：两平台均未命中已知录音
- 🟡 疑似碰撞（AcoustID 0.5~0.8 / AudioTag 低置信）：建议人工复核
- 🔴 高概率碰撞（AcoustID ≥0.8 / AudioTag 命中）：命中的已知录音，建议重生成 BGM
- 明细里分别列出 AcoustID（曲名/艺术家/id/score）与 AudioTag（曲名/艺术家/专辑/年份/confidence）。

`--report` 额外写 Markdown 报告；`--backends acoustid|audiotag` 可强制单平台。

## 实现要点（给想改的人）
- 指纹：`fpcalc -json <file>` → `{duration, fingerprint}`。
- 撞库：`GET https://api.acoustid.org/v2/lookup?client=KEY&meta=recordings+releases+tracks&fingerprint=...&duration=...`
- 只上传指纹（整型数列），**不上传音频本体**，隐私安全。
- 阈值见 `check_bgm.py` 顶部 `THRESH_HIGH / THRESH_MID`。
