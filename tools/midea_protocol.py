#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""美的空调三帧协议参考实现 + 抓包自检。

用法：
    python tools/midea_protocol.py             # 打印 16.0–30.0 的码
    python tools/midea_protocol.py --verify    # 用 captures/ 自检
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "captures")


def xor_chk(b):
    x = 0
    for v in b[:5]:
        x ^= v
    return (~x) & 0xFF


def sum_chk(b):
    return sum(b[:5]) & 0xFF


def build(t10, heat=False):
    """生成 F0/F2。

    t10: 温度 × 10（160..300，步进 5）
    返回 (f0: bytes[6], f2: bytes[6])
    """
    if t10 < 160 or t10 > 300 or t10 % 5:
        raise ValueError("temperature must be 160..300 step 5")

    whole, frac = divmod(t10, 10)
    n = max(0, whole - 17)          # 16/16.5 也取 0
    gray = (n ^ (n >> 1)) & 0x0F

    f0 = [0xB2, 0x4D, 0xBF, 0x40,
          (gray << 4) | (0x0C if heat else 0x00), 0]
    f0[5] = xor_chk(f0)

    f2 = [0xD5, 0x66, 0x00, 0x00, 0x00, 0x00]
    if frac == 5:
        f2[2] |= 0x20               # 半度
    if whole == 16:
        f2[3] |= 0x10               # 16℃
    f2[5] = sum_chk(f2)

    return bytes(f0), bytes(f2)


def message(t10, heat=False):
    """一次按键的 3 帧：F0, F0, F2。"""
    f0, f2 = build(t10, heat)
    return [f0, f0, f2]


# ---------------- 自检 ----------------

def split_frames(us, gap=3000):
    frames, cur = [], []
    for i in range(0, len(us) - 1, 2):
        m, s = us[i], us[i + 1]
        if m > gap and cur:
            frames.append(cur)
            cur = []
        cur += [m, s]
    if cur:
        frames.append(cur)
    return frames


def decode(frame):
    bits, i = [], 2
    while i + 1 < len(frame):
        m, s = frame[i], frame[i + 1]
        if not (300 <= m <= 1000) or s < 300:
            break
        if s < 1000:
            bits.append(0)
        elif s < 2300:
            bits.append(1)
        else:
            break
        i += 2
    out = []
    for k in range(0, len(bits) - len(bits) % 8, 8):
        v = 0
        for b in bits[k:k + 8]:
            v = (v << 1) | b
        out.append(v)
    return bytes(out)


def verify():
    ok = bad = skip = 0
    for name in sorted(os.listdir(CAP)):
        if not name.endswith(".json"):
            continue
        m = re.match(r"(制冷|制热)(\d+(?:\.\d+)?)", name)
        if not m:
            continue
        heat = m.group(1) == "制热"
        t10 = int(round(float(m.group(2)) * 10))
        with open(os.path.join(CAP, name), encoding="utf-8") as f:
            us = json.load(f)["us"]
        dec = [decode(fr) for fr in split_frames(us)]
        if len(dec) < 3:
            print(f"SKIP  {name}  ({len(dec)} frames)")
            skip += 1
            continue
        f0, f2 = build(t10, heat)
        if dec[0] == f0 and dec[2] == f2:
            ok += 1
        else:
            bad += 1
            print(f"FAIL  {name}")
            print(f"  expect F0 {f0.hex(' ').upper()}  F2 {f2.hex(' ').upper()}")
            print(f"  got    F0 {dec[0].hex(' ').upper()}  F2 {dec[2].hex(' ').upper()}")
    print(f"\nverify: ok={ok} fail={bad} skip={skip}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    if "--verify" in sys.argv:
        sys.exit(verify())
    for t in range(160, 301, 5):
        f0, f2 = build(t)
        print(f"{t/10:5.1f}C  F0 {f0.hex(' ').upper()}   F2 {f2.hex(' ').upper()}")
