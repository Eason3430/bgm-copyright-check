# 用 WorkBuddy 自建 Skill 给 AI 漫剧 BGM 做版权查重（双平台免费）

> 本教程配套仓库：[bgm-copyright-check](https://github.com/Eason3430/bgm-copyright-check)
> 适用：AI 漫剧 / 短剧创作者，用 ACE-Step 等模型生成 BGM 后做版权安全网。

---

## 一、背景：为什么 AI 漫剧要先查 BGM 版权

做 AI 漫剧/短剧，常用 ACE-Step 生成 BGM。但这类音乐模型偶尔会在训练时"记住"某些旋律，
生成结果会和已有商业歌高度相似——发布到抖音/火龙/红果前不查，很容易踩版权雷。

市面上"歌曲查重"技能几乎没有现成的。于是有了这个 **`bgm-copyright-check`** skill：
本地算声学指纹 + 双平台免费 API 撞库，生成 BGM 后自动排查是否撞了商业歌。

本文带你从零装好、配好 key、跑通查重，并接进 ACE-Step 实现"生成即查重"。

*（建议配图：AI 漫剧工程里 BGM 文件清单 / 一段 BGM 波形）*

---

## 二、准备工作

- 已安装 WorkBuddy（Windows 客户端）
- Python 3 已装（仅用标准库，**无需 pip 装任何包**）
- 两个免费 API key（下文步骤会教怎么拿）
  - AcoustID：https://acoustid.org/new-application
  - AudioTag：https://user.audiotag.info

---

## 三、步骤 1：安装 skill 到 WorkBuddy

两种方式，**推荐方式 A（始终最新）**：

**方式 A：从 GitHub 克隆**
```bash
git clone https://github.com/Eason3430/bgm-copyright-check.git
cd bgm-copyright-check
python download_fpcalc.py   # 自动下载 Chromaprint fpcalc 并做 SHA256 校验
```
打开 WorkBuddy → 左侧【技能】→「导入技能」→ 选中这个目录（或打包成 zip 拖入）→ 勾选"非高风险自动安装" → 导入。

**方式 B：WorkBuddy 技能市场「导入技能」**
把目录打包成 `.zip` → 左侧【技能市场】→ 右上角「导入技能」→ 拖入 zip → 勾选"非高风险自动安装"。

*（建议配图：技能市场 → 导入技能 弹窗，显示已选中目录/zip）*

> 失败预警：导入要求目录内必须有 `SKILL.md`，且 frontmatter 含 `name` 与 `description`（YAML）。
> 缺了会导入失败。本仓库已自带，直接用即可。
> 注意：仓库里**不含** `fpcalc.exe` 二进制，首次使用先跑 `python download_fpcalc.py` 自动拉取并校验；
> 若你走 SkillHub 的发布包（自带 fpcalc）则无需此步。

导入成功后，skill 会出现在本地技能列表；后续在对话里说"查重 BGM"即可触发。

---

## 四、步骤 2：申请两个免费 key（重点坑在这里）

### 4.1 AcoustID —— 必须拿 application key，不是 user key

打开 https://acoustid.org/new-application ，填应用名注册，拿到形如 `XYQSvtHabAw` 的 **application key**。

> ⚠️ 失败预警（我亲自踩过）：AcoustID 有两种 key。
> `/api-key` 页面给的是 **user key**，只能"提交指纹"，**不能用来查重**；
> 查重要用 **application key**（new-application 页面）。用错会报 `invalid API key`。
> 很多教程没讲清这点，会卡很久。

*（建议配图：new-application 注册成功页，展示 application key）*

### 4.2 AudioTag —— 允许商用，每月 3 小时

打开 https://user.audiotag.info 注册，拿到 api key（需处于 active 状态）。
额度每月 3 小时音频（约 1000 首），**允许商用**，正好适合发布前清样。

---

## 五、步骤 3：写入配置

在 skill 目录建 `config.json`：

```json
{
  "acoustid_api_key": "你的AcoustID application key",
  "audiotag_api_key": "你的AudioTag key"
}
```

也可用环境变量 `ACOUSTID_API_KEY` / `AUDIOTAG_API_KEY`。缺哪个 key，就自动跳过哪个后端。

> 提示：公开发仓库时**不要把真实 key 提交上去**，用占位符即可。

---

## 六、步骤 4：运行查重

指定要查的文件（只查你给的，不扫其他）：

```bash
python check_bgm.py "E:/bgm/ep01.mp3" --report "E:/bgm/ep01_查重报告.md"
```

输出示例：

```
🔍 待查重文件：1 个，后端：AcoustID + AudioTag
▸ ep01.mp3 ... 🟢 干净
  - AcoustID：干净
  - AudioTag：干净
```

- 🟢 干净：两平台都没命中
- 🟡 疑似：建议人工复核
- 🔴 高概率碰撞：命中的已知录音，建议换 seed 重生成

完整输出样例（含出错情形）见 [docs/sample-report.md](docs/sample-report.md)。

*（建议配图：命令行跑查重，显示 🟢 干净 的结果）*

> 失败预警：AudioTag 报 `could not process the file` 通常是音频**太短**（需 ≥10 秒）。
> 用 12 秒以上片段即可；BGM 一般几十秒不受影响。

---

## 七、步骤 5（可选）：接入 ACE-Step，生成即查重

如果你用 `comfyui-acestep-audio` 生成 BGM，它自带封装脚本 `generate_and_check.sh`：
写 spec → 生成 → **每生成一条音频立刻双平台查重**，只查本次新文件，不重复上传旧文件。

```bash
bash "$HOME/.workbuddy/skills/comfyui-acestep-audio/scripts/generate_and_check.sh" \
  "<项目>/audio/BGM_xxx_spec.json" "<项目>/audio"
```

每条音频同目录产出 `<音频名>_查重报告.md`，命中红/黄就重生成。

---

## 八、重要边界（别误当免责金牌）

指纹比对只能抓"几乎一模一样"的碰撞，**抓不了旋律相似**。它降低风险的真正抓手是流程：
prompt 不写 `in the style of XXX 歌手`、每次换 seed、保留 prompt 溯源、报警就重生成。
AcoustID 免费档 TOS 限非商用，商用清样优先 AudioTag 免费档或付费商业服务。

---

## 九、结语

这个 skill 已在 GitHub 开源（https://github.com/Eason3430/bgm-copyright-check ）。AI 漫剧同行可以"导入技能"直接用，
把版权风险挡在发布前。欢迎反馈、提 issue。

#WorkBuddy #AI漫剧 #版权 #BGM #ACE-Step
