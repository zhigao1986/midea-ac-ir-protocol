# 抓包样本

`*.json` 为一次按键的完整波形：

```json
{"tick_us": 2, "len": 299, "us": [4406, 4428, 536, 1620, ...]}
```

- `tick_us`：采样精度（2 µs）
- `len`：跳变个数
- `us`：交替的 mark / space 微秒值，从第一个 mark 开始

命名：`制冷16 风速自动.json`、`制热16.5 风速自动 电辅热.json`。

分析：

```bash
python tools/analyze2.py      # 帧结构、校验、温度差异
python tools/analyze_raw.py   # 逐帧十六进制
python tools/export_csv.py    # 生成 decoded.csv
```

结论见 [../README.md](../README.md) 和 [../ANALYSIS.md](../ANALYSIS.md)。