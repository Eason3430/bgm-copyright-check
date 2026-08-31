#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_fpcalc.py —— 首次使用 bgm-copyright-check 前，运行本脚本获取 Chromaprint fpcalc 二进制。

fpcalc 是 AcoustID 官方的声学指纹计算工具（开源，https://github.com/acoustid/chromaprint）。
本脚本只下载、不涉及任何密钥。

- Windows (x64)：自动下载并校验 SHA256，解压到 bin/fpcalc.exe
- macOS / Linux：给出官方下载页，手动下载后把 fpcalc 放进 bin/ 或加入 PATH
"""
import hashlib
import os
import sys
import urllib.request
import zipfile

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(SKILL_DIR, "bin")
WIN_URL = "https://github.com/acoustid/chromaprint/releases/download/v1.6.1/chromaprint-fpcalc-1.6.1-windows-x86_64.zip"
# 校验的是「解压后的 fpcalc.exe」的 SHA256（稳定值，不受上游 zip 重新打包影响）。
# 注意：上游 zip 包本身的 SHA256 会随重新打包变化，因此不要校验 zip，只校验 exe 本体。
WIN_EXE_SHA256 = "00dcc56d911f2dea84737aa9dc8e2d118c9eb7a037d815d1ed001d8593e8fbee"


def _download(url, dest, timeout=120, retries=3):
    last = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "bgm-copyright-check/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            with open(dest, "wb") as f:
                f.write(data)
            return len(data)
        except Exception as e:
            last = e
            print("  第 %d 次下载失败：%s%s" % (attempt, e, "，重试…" if attempt < retries else ""))
    raise last


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    plat = sys.platform
    if plat.startswith("win"):
        os.makedirs(BIN_DIR, exist_ok=True)
        zip_path = os.path.join(BIN_DIR, "fpcalc.zip")
        print("下载 fpcalc (Windows x64) ...")
        try:
            n = _download(WIN_URL, zip_path)
        except Exception as e:
            print("下载失败：", e)
            sys.exit(1)
        print("下载完成 (%d 字节)，解压并校验 fpcalc.exe 的 SHA256 ..." % n)
        with zipfile.ZipFile(zip_path) as z:
            target = [n for n in z.namelist() if n.lower().endswith("fpcalc.exe")]
            if not target:
                print("zip 内未找到 fpcalc.exe")
                sys.exit(1)
            z.extract(target[0], BIN_DIR)
        extracted = os.path.join(BIN_DIR, target[0])
        actual = _sha256(extracted)
        if actual.lower() != WIN_EXE_SHA256.lower():
            print("⚠️ fpcalc.exe SHA256 不匹配！可能下载被篡改或版本变更。")
            print("  期望:", WIN_EXE_SHA256)
            print("  实际:", actual)
            if os.path.exists(extracted):
                os.remove(extracted)
            os.remove(zip_path)
            sys.exit(1)
        final = os.path.join(BIN_DIR, "fpcalc.exe")
        if extracted != final and os.path.exists(extracted):
            if os.path.exists(final):
                os.remove(final)
            os.replace(extracted, final)
        os.remove(zip_path)
        print("✅ fpcalc.exe 已就位（SHA256 校验通过）：", final)
    else:
        print("当前平台：", plat)
        print("fpcalc 需手动获取（脚本仅内置 Windows 自动下载）：")
        print("  1. 打开 https://github.com/acoustid/chromaprint/releases/tag/v1.6.1")
        print("  2. 下载对应平台的 chromaprint-fpcalc-1.6.1-*.zip")
        print("  3. 解压出 fpcalc，放到本目录的 bin/ 下，或加入系统 PATH")
        print("  完成后即可运行 check_bgm.py")


if __name__ == "__main__":
    main()
