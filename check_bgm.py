#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bgm-copyright-check —— 免费 BGM 版权查重工具（双平台：AcoustID + AudioTag）

原理：
    1. AcoustID 后端：本地用 Chromaprint(fpcalc) 算声学指纹 → 提交 AcoustID 免费 API 撞全球曲库。
    2. AudioTag 后端：上传音频到 AudioTag 免费 API（每月 3 小时音频≈1000首，允许商用）识别。
    两个平台任一命中即报警，互为背书。

重要局限：
    * 指纹/识别只能抓「几乎一模一样 / 被曲库收录」的碰撞（训练数据泄漏、意外复现某首已知录音），
      抓不了「旋律/风格相似但非同一录音」。它是安全网，不是商业免责金牌。
    * 真正降低版权风险靠流程：prompt 避免写 "in the style of XXX 歌手/某歌"、每次换 seed、
      保留 prompt 记录做溯源、查重报警就重生成。
    * AcoustID 免费档 TOS 限非商业用途；商用发布前清样优先用 AudioTag（允许商用）或付费商业服务。

免费 & 隐私：
    * AcoustID：只上传指纹（整型数列），不上传音频。
    * AudioTag：需上传音频本体（其 API 即识别音频），额度 3 小时/月。
    * 仅标准库，无需 pip 装任何包。

配置（config.json 或环境变量，二选一/可并存）：
    {
      "acoustid_api_key": "你的 AcoustID APPLICATION key（https://acoustid.org/new-application 注册应用后获取）",
      "audiotag_api_key": "你的AudioTag key（https://user.audiotag.info 注册后获取，需 active）"
    }
    环境变量：ACOUSTID_API_KEY / AUDIOTAG_API_KEY

用法：
    python check_bgm.py <音频文件或目录> [更多...] [--backends both|acoustid|audiotag] [--report 报告.md]
    python check_bgm.py "E:/bgm/ep01.mp3" --backends both --report "E:/bgm/查重报告.md"
    python check_bgm.py "E:/bgm"                # 有哪个 key 跑哪个，缺 key 的后端自动跳过
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
import glob

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_FPCALC = os.path.join(SKILL_DIR, "bin", "fpcalc.exe")
FPCALC = LOCAL_FPCALC if os.path.exists(LOCAL_FPCALC) else "fpcalc"

ACOUSTID_API = "https://api.acoustid.org/v2/lookup"
AUDIOTAG_API = "https://audiotag.info/api"

# 置信度阈值（AcoustID）：>=0.8 高概率碰撞；0.5~0.8 疑似；<0.5 基本干净
THRESH_HIGH = 0.8
THRESH_MID = 0.5
# AudioTag 轮询
AT_POLL_INTERVAL = 2.0
AT_POLL_TIMEOUT = 45.0


# ----------------------------------------------------------------------------
# 密钥
# ----------------------------------------------------------------------------
def load_keys(explicit_acoustid=None, explicit_audiotag=None):
    keys = {"acoustid": explicit_acoustid or os.environ.get("ACOUSTID_API_KEY"),
            "audiotag": explicit_audiotag or os.environ.get("AUDIOTAG_API_KEY")}
    cfg = os.path.join(SKILL_DIR, "config.json")
    if os.path.exists(cfg):
        try:
            data = json.load(open(cfg, "r", encoding="utf-8"))
            for k in ("acoustid", "audiotag"):
                envk = k + "_api_key"
                if not keys[k] and data.get(envk):
                    keys[k] = data[envk]
        except Exception:
            pass
    return keys


# ----------------------------------------------------------------------------
# AcoustID 后端（指纹）
# ----------------------------------------------------------------------------
def fingerprint(path):
    try:
        out = subprocess.check_output([FPCALC, "-json", path], stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"fpcalc 执行失败：{e}")
    except FileNotFoundError:
        raise RuntimeError("找不到 fpcalc。请确认 bin/fpcalc.exe 存在，或把 fpcalc 加入 PATH。")
    data = json.loads(out.decode("utf-8", "ignore"))
    return data["fingerprint"], int(round(float(data["duration"])))


def acoustid_lookup(api_key, fp, duration):
    params = urllib.parse.urlencode({
        "client": api_key,
        "meta": "recordings+releases+tracks",
        "fingerprint": fp,
        "duration": duration,
    })
    url = ACOUSTID_API + "?" + params
    req = urllib.request.Request(url, headers={"User-Agent": "bgm-copyright-check/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "ignore")
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code}: {body or e.reason}")


def acoustid_check(api_key, path):
    try:
        fp, dur = fingerprint(path)
        res = acoustid_lookup(api_key, fp, dur)
    except Exception as e:
        msg = str(e)
        if "invalid API key" in msg:
            msg += (
                "\n[提示] AcoustID 查重要用 application key（https://acoustid.org/new-application 注册应用获取），"
                "你当前填入的很可能是 /api-key 页面的 user key，后者只能提交指纹，不能用于 lookup。"
            )
        return {"verdict": "error", "message": msg}
    if res.get("status") != "ok":
        return {"verdict": "error", "message": str(res)}
    result = res.get("result")
    if not result or not result.get("recordings"):
        return {"verdict": "clean", "score": result.get("score") if result else None}
    score = float(result.get("score", 0))
    matches = []
    for rec in result["recordings"][:5]:
        arts = rec.get("artists") or []
        artist = "、".join(a.get("name", "") for a in arts if a.get("name")) or "未知艺术家"
        matches.append({"title": rec.get("title", "未知标题"), "artist": artist, "id": rec.get("id")})
    verdict = "hit" if score >= THRESH_HIGH else ("suspect" if score >= THRESH_MID else "clean")
    return {"verdict": verdict, "score": score, "matches": matches}


# ----------------------------------------------------------------------------
# AudioTag 后端（上传音频识别）
# ----------------------------------------------------------------------------
def _post_multipart(url, fields, files):
    boundary = "----bgmcheck" + uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += ("--%s\r\n" % boundary).encode()
        body += ('Content-Disposition: form-data; name="%s"\r\n\r\n' % k).encode()
        body += str(v).encode("utf-8") + b"\r\n"
    for k, (fname, fdata) in files.items():
        body += ("--%s\r\n" % boundary).encode()
        body += ('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (k, fname)).encode()
        body += b"Content-Type: application/octet-stream\r\n\r\n"
        body += fdata + b"\r\n"
    body += ("--%s--\r\n" % boundary).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary,
                 "User-Agent": "bgm-copyright-check/1.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8", "ignore"))


def _post_form(url, fields):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "bgm-copyright-check/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", "ignore"))


def audiotag_identify(api_key, path):
    fname = os.path.basename(path)
    with open(path, "rb") as f:
        fdata = f.read()
    fields = {"apikey": api_key, "action": "identify"}
    res = _post_multipart(AUDIOTAG_API, fields, {"file": (fname, fdata)})
    if not res.get("success"):
        raise RuntimeError("identify 失败: %s" % res.get("error"))
    token = res.get("token")
    if not token:
        raise RuntimeError("identify 未返回 token: %s" % res)
    return token


def audiotag_poll(api_key, token):
    deadline = time.time() + AT_POLL_TIMEOUT
    while True:
        res = _post_form(AUDIOTAG_API, {"apikey": api_key, "action": "get_result", "token": token})
        if not res.get("success"):
            return {"error": res.get("error") or "get_result 失败"}
        r = res.get("result")
        if r == "found":
            return {"result": "found", "data": res.get("data")}
        if r == "not found":
            return {"result": "not found"}
        if "invalid token" in str(res.get("error", "")).lower() or "no recognition" in str(res.get("error", "")).lower():
            return {"result": "not found"}
        if time.time() > deadline:
            return {"error": "轮询超时（%ss）" % AT_POLL_TIMEOUT}
        time.sleep(AT_POLL_INTERVAL)


def _parse_audiotag_data(data):
    """data: list of {tracks:[[tn,an,al,ay],...], confidence, time}"""
    out = []
    if not isinstance(data, list):
        return out
    for cand in data[:5]:
        tracks = cand.get("tracks") or []
        top = tracks[0] if tracks else []
        title = top[0] if len(top) > 0 else "未知标题"
        artist = top[1] if len(top) > 1 else "未知艺术家"
        album = top[2] if len(top) > 2 else ""
        year = top[3] if len(top) > 3 else ""
        out.append({
            "title": title, "artist": artist,
            "album": album, "year": year,
            "confidence": cand.get("confidence"),
            "time": cand.get("time"),
        })
    return out


def audiotag_check(api_key, path):
    try:
        token = audiotag_identify(api_key, path)
    except Exception as e:
        return {"verdict": "error", "message": str(e)}
    res = audiotag_poll(api_key, token)
    if res.get("error"):
        return {"verdict": "error", "message": res["error"]}
    if res.get("result") == "not found":
        return {"verdict": "clean"}
    if res.get("result") == "found":
        matches = _parse_audiotag_data(res.get("data"))
        conf = matches[0]["confidence"] if matches else None
        # AudioTag 仅 'found' 即正匹配；confidence 为相对分，越高越稳
        verdict = "hit" if (conf is None or conf >= 100) else "suspect"
        return {"verdict": verdict, "confidence": conf, "matches": matches}
    return {"verdict": "error", "message": "意外结果: %s" % res}


# ----------------------------------------------------------------------------
# 合并 & 报告
# ----------------------------------------------------------------------------
def combine(verdicts):
    if any(v == "hit" for v in verdicts):
        return "🔴 高概率碰撞"
    if any(v == "suspect" for v in verdicts):
        return "🟡 疑似碰撞"
    if any(v == "error" for v in verdicts):
        return "⚠️ 查重出错(见明细)"
    return "🟢 基本干净"


def backend_label(b):
    return "AcoustID" if b == "acoustid" else "AudioTag"


def check_one(backends, keys, path):
    sub = {}
    for b in backends:
        if b == "acoustid":
            sub["acoustid"] = acoustid_check(keys["acoustid"], path)
        else:
            sub["audiotag"] = audiotag_check(keys["audiotag"], path)
    verdicts = [sub[b].get("verdict") for b in backends if b in sub]
    return {"file": path, "status": combine(verdicts), "backends": sub}


def collect_inputs(paths):
    exts = (".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".opus")
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                for n in names:
                    if n.lower().endswith(exts):
                        files.append(os.path.join(root, n))
        else:
            expanded = glob.glob(p)
            if expanded:
                for f in expanded:
                    if os.path.isfile(f) and f.lower().endswith(exts):
                        files.append(f)
            elif os.path.isfile(p):
                files.append(p)
    return sorted(set(files))


def fmt_matches(sub):
    lines = []
    for b in ("acoustid", "audiotag"):
        if b not in sub:
            continue
        r = sub[b]
        lab = backend_label(b)
        if r["verdict"] == "error":
            lines.append(f"  - {lab}：出错 {r.get('message')}")
            continue
        if r["verdict"] == "clean":
            extra = ""
            if r.get("score") is not None:
                extra = f"（score={r['score']}）"
            elif r.get("confidence") is not None:
                extra = f"（conf={r['confidence']}）"
            lines.append(f"  - {lab}：干净 {extra}")
            continue
        tag = "🔴" if r["verdict"] == "hit" else "🟡"
        sc = r.get("score") if r.get("score") is not None else r.get("confidence")
        scs = f" score={sc}" if sc is not None else ""
        lines.append(f"  - {lab}：{tag} 命中{scs}")
        for m in r.get("matches", [])[:3]:
            extra = ""
            if m.get("album"):
                extra += f" / 专辑《{m['album']}》"
            if m.get("year"):
                extra += f" ({m['year']})"
            lines.append(f"      《{m['title']}》 - {m['artist']}{extra}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="BGM 版权查重（AcoustID + AudioTag 双平台）")
    ap.add_argument("inputs", nargs="+", help="音频文件或目录（可多个）")
    ap.add_argument("--backends", default="both", help="both | acoustid | audiotag（默认 both）")
    ap.add_argument("--acoustid-key", help="AcoustID application key（https://acoustid.org/new-application 注册应用后获取）")
    ap.add_argument("--audiotag-key", help="AudioTag API key（或环境变量/ config.json）")
    ap.add_argument("--report", help="把结果写成 Markdown 报告到该路径")
    args = ap.parse_args()

    keys = load_keys(args.acoustid_key, args.audiotag_key)
    want = args.backends.lower()
    if want in ("both", "all"):
        want_set = {"acoustid", "audiotag"}
    elif want == "acoustid":
        want_set = {"acoustid"}
    elif want == "audiotag":
        want_set = {"audiotag"}
    else:
        print(f"❌ 未知 --backends={args.backends}", file=sys.stderr)
        sys.exit(2)

    enabled = [b for b in ("acoustid", "audiotag") if b in want_set and keys.get(b)]
    skipped = [b for b in want_set if b not in enabled]
    if not enabled:
        print(
            "❌ 没有可用的后端 key。请至少配置一个：\n"
            "   AcoustID（免费，非商用）：https://acoustid.org/new-application 注册应用获取 application key\n"
            "   AudioTag（免费，允许商用，3h/月）：https://user.audiotag.info 注册拿 key\n"
            "   配置方式：环境变量 ACOUSTID_API_KEY / AUDIOTAG_API_KEY，或 skill 目录 config.json。",
            file=sys.stderr,
        )
        sys.exit(2)
    if skipped:
        print("⚠️ 跳过未配置 key 的后端：%s\n" % "、".join(backend_label(b) for b in skipped))

    files = collect_inputs(args.inputs)
    if not files:
        print("⚠️ 没有找到可检查的音频文件。", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 待查重文件：{len(files)} 个，后端：%s\n" % " + ".join(backend_label(b) for b in enabled))

    results = []
    for f in files:
        print(f"▸ {os.path.basename(f)} ...", end=" ", flush=True)
        try:
            r = check_one(enabled, keys, f)
        except Exception as e:
            r = {"file": f, "status": "⚠️ 查重出错(见明细)", "backends": {"_": {"verdict": "error", "message": str(e)}}}
        results.append(r)
        if r["status"].startswith("🔴"):
            print(r["status"])
        elif r["status"].startswith("🟡"):
            print(r["status"])
        elif r["status"].startswith("🟢"):
            print("🟢 干净")
        else:
            print(r["status"])
        detail = fmt_matches(r.get("backends", {}))
        if detail:
            print(detail)

    hits = [r for r in results if r["status"].startswith("🔴") or r["status"].startswith("🟡")]
    print(f"\n=== 汇总：{len(results)} 检查，{len(hits)} 命中/疑似 ===")
    if hits:
        print("⚠️ 以下文件建议人工复核或重生成 BGM：")
        for r in hits:
            print(f"  - {os.path.basename(r['file'])}  {r['status']}")
            print(fmt_matches(r.get("backends", {})))

    if args.report:
        write_report(args.report, results)
        print(f"\n📄 报告已写出：{args.report}")


def write_report(path, results):
    lines = ["# BGM 版权查重报告（AcoustID + AudioTag 双平台）", "", f"文件数：{len(results)}", ""]
    for r in results:
        lines.append(f"## {os.path.basename(r['file'])}")
        lines.append(f"- 综合状态：{r['status']}")
        detail = fmt_matches(r.get("backends", {}))
        if detail:
            lines.append(detail)
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
