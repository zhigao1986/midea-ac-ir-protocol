#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析 /raw.json 导出的原始波形：切帧、解位、对比温度/模式差异。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "captures")
SRC = CAP if os.path.isdir(CAP) else ROOT


def load(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return d.get("tick_us", 2), d["us"]


def split_frames(us, gap=3000):
    """以引导头 mark(>3ms) 为新帧起点切分。"""
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
    """frame 以 mark 开头；跳过引导头，按 560/1680 解码。"""
    bits = []
    i = 2
    while i + 1 < len(frame):
        m, s = frame[i], frame[i + 1]
        if not (300 <= m <= 1000):      # 帧尾 mark 或噪声
            break
        if s < 300:
            break
        if s < 1000:
            bits.append(0)
        elif s < 2300:
            bits.append(1)
        else:
            break
        i += 2
    return bits


def bits_to_bytes(bits):
    out = []
    for i in range(0, len(bits) - len(bits) % 8, 8):
        v = 0
        for b in bits[i:i + 8]:
            v = (v << 1) | b
        out.append(v)
    return out


def hexs(bs):
    return " ".join(f"{b:02X}" for b in bs)


def main():
    files = sorted(
        [p for p in os.listdir(SRC) if p.lower().endswith(".json")],
        key=lambda p: p,
    )
    if not files:
        print("没有 JSON")
        return

    table = {}
    for name in files:
        tick, us = load(os.path.join(SRC, name))
        frames = split_frames(us)
        decoded = []
        for fr in frames:
            bits = decode(fr)
            decoded.append((bits, bits_to_bytes(bits)))
        table[name] = (tick, us, frames, decoded)
        print("=" * 70)
        print(name, f"  tick={tick}us len={len(us)} frames={len(frames)}")
        for idx, (bits, bs) in enumerate(decoded):
            print(f"  F{idx}: {len(bits)}bit  {hexs(bs)}")
        if len(decoded) >= 2 and decoded[0][1] and decoded[1][1]:
            inv = all((~a) & 0xFF == b for a, b in zip(decoded[0][1], decoded[1][1]))
            print(f"  F0/F1 是否反码: {inv}")

    # 温度对比（同模式同电辅热/风速）
    print("\n" + "=" * 70)
    print("按文件排序的逐字节差异（以第一个为基准的位差异）")


if __name__ == "__main__":
    main()
