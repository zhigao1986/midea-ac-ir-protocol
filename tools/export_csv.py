#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 captures/ 里所有抓包解码后导出 decoded.csv。"""
import csv
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "captures")


def load(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return d.get("tick_us", 2), d["us"]


def split_frames(us, gap=3000):
    frames, cur, i = [], [], 0
    while i + 1 < len(us):
        m, s = us[i], us[i + 1]
        if m > gap and cur:
            frames.append(cur)
            cur = []
        cur += [m, s]
        i += 2
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
    return out


def hx(bs):
    return " ".join(f"{b:02X}" for b in bs)


def parse_name(name):
    m = re.match(r"(制冷|制热)(\d+(?:\.\d+)?)", name)
    mode = m.group(1) if m else ""
    temp = m.group(2) if m else ""
    aux = "无" if "无电辅热" in name else ("有" if "电辅热" in name else "")
    return mode, temp, aux


def xor_chk(b):
    x = 0
    for v in b[:5]:
        x ^= v
    return (~x) & 0xFF


def main():
    rows = []
    for name in sorted(os.listdir(CAP)):
        if not name.lower().endswith(".json"):
            continue
        tick, us = load(os.path.join(CAP, name))
        dec = [decode(fr) for fr in split_frames(us)]
        mode, temp, aux = parse_name(name)
        f0 = dec[0] if dec else []
        f2 = dec[2] if len(dec) > 2 else []
        rows.append(dict(
            file=name, mode=mode, temp=temp, aux=aux, frames=len(dec),
            f0=hx(f0), f2=hx(f2),
            chk0=("ok" if len(f0) >= 6 and xor_chk(f0) == f0[5] else ""),
            chk2=("ok" if len(f2) >= 6 and (sum(f2[:5]) & 0xFF) == f2[5] else ""),
        ))
    out = os.path.join(ROOT, "decoded.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["file", "mode", "temp", "aux", "frames", "f0", "f2", "chk0", "chk2"])
        w.writeheader()
        w.writerows(rows)
    print(f"{out}: {len(rows)} rows")


if __name__ == "__main__":
    main()
