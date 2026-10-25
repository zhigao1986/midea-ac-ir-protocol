#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对抓包做结构化分析：帧、校验、字段、温度序列差异。"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "captures")
SRC = CAP if os.path.isdir(CAP) else ROOT


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
    return bits


def to_bytes(bits):
    out = []
    for i in range(0, len(bits) - len(bits) % 8, 8):
        v = 0
        for b in bits[i:i + 8]:
            v = (v << 1) | b
        out.append(v)
    return out


def hx(bs):
    return " ".join(f"{b:02X}" for b in bs)


def parse_name(name):
    m = re.match(r"(制冷|制热)(\d+(?:\.\d+)?)", name)
    mode = m.group(1) if m else "?"
    temp = float(m.group(2)) if m else None
    aux = None
    if "无电辅热" in name:
        aux = "无"
    elif "电辅热" in name:
        aux = "有"
    return mode, temp, aux


def xor_chk(b):
    x = 0
    for v in b[:5]:
        x ^= v
    return (~x) & 0xFF


def sum_chk(b):
    return sum(b[:5]) & 0xFF


def main():
    files = [p for p in os.listdir(SRC) if p.lower().endswith(".json")]
    rows = []
    for name in files:
        tick, us = load(os.path.join(SRC, name))
        frames = split_frames(us)
        dec = [to_bytes(decode(fr)) for fr in frames]
        mode, temp, aux = parse_name(name)
        rows.append(dict(name=name, tick=tick, n=len(us), frames=len(frames),
                         dec=dec, mode=mode, temp=temp, aux=aux))

    rows.sort(key=lambda r: (r["mode"], r["aux"] or "", r["temp"] or 0))

    print(f"{'文件':<28} {'mode':<4} {'temp':<5} {'aux':<3} {'帧':<2} {'F0':<20} {'F2':<20} chk0 chk2")
    for r in rows:
        f0 = r["dec"][0] if r["dec"] else []
        f2 = r["dec"][2] if len(r["dec"]) > 2 else (r["dec"][-1] if r["dec"] else [])
        c0 = (xor_chk(f0) == f0[5]) if len(f0) >= 6 else False
        c2 = (sum_chk(f2) == f2[5]) if len(f2) >= 6 else False
        print(f"{r['name'][:-5]:<28} {r['mode']:<4} {r['temp']!s:<5} {r['aux'] or '-':<3} "
              f"{r['frames']:<2} {hx(f0):<20} {hx(f2):<20} {str(c0):<5} {c2}")

    # 温度序列差异（同模式、同电辅热）
    print("\n--- 同组温度差异（F0 / F2 的位变化）---")
    groups = {}
    for r in rows:
        groups.setdefault((r["mode"], r["aux"]), []).append(r)

    for key, g in groups.items():
        if len(g) < 2:
            continue
        g.sort(key=lambda r: r["temp"])
        base = g[0]
        print(f"\n[{key[0]} aux={key[1]}] 基准 {base['temp']}℃")
        for r in g[1:]:
            d0 = [i for i in range(min(len(base['dec'][0]), len(r['dec'][0])))
                  if base['dec'][0][i] != r['dec'][0][i]]
            f2a = base['dec'][2] if len(base['dec']) > 2 else []
            f2b = r['dec'][2] if len(r['dec']) > 2 else []
            d2 = [i for i in range(min(len(f2a), len(f2b))) if f2a[i] != f2b[i]]
            print(f"  {r['temp']}℃: F0 差异字节 {d0}  F2 差异字节 {d2}")


if __name__ == "__main__":
    main()
