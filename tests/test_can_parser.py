import pandas as pd
import numpy as np
import sys
import os

# 引入解析逻辑（假设解析函数已在 core/can_parser.py 定义）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.can_parser import parse_can_raw_long_table

def test_parse_can_raw_long_table_aligns_and_fills():
    # 构造乱序、错开时间戳的“CAN报文长表”
    raw = [
        {"Timestamp": 0.00, "CAN_ID": 288, "Signal": "Speed", "Value": 10.5},
        {"Timestamp": 0.02, "CAN_ID": 288, "Signal": "Speed", "Value": 12.0},
        {"Timestamp": 0.03, "CAN_ID": 384, "Signal": "AEB_Trigger", "Value": 0},
        {"Timestamp": 0.01, "CAN_ID": 384, "Signal": "AEB_Trigger", "Value": 1},
        {"Timestamp": 0.04, "CAN_ID": 288, "Signal": "Speed", "Value": 13.7},
        {"Timestamp": 0.05, "CAN_ID": 384, "Signal": "AEB_Trigger", "Value": 1},
    ]
    # 刻意乱序
    df = pd.DataFrame(raw).sample(frac=1, random_state=42).reset_index(drop=True)

    # 构造伪 signal_dynamic_map（此处未用到，但保留参数形式）
    signal_dynamic_map = {}

    # 调用解析函数（只会返回标准信号长表 df: [Timestamp, CAN_ID, Signal, Value]，实际宽表一般需透视/旋转）
    long_table = parse_can_raw_long_table(df, signal_dynamic_map)
    # 转为宽表（以 Timestamp 为 index，Signal 为列），缺省向前填充
    wide = long_table.pivot_table(index="Timestamp", columns="Signal", values="Value", aggfunc="first").sort_index()
    wide = wide.ffill()

    # 检查宽表（wide）结构与 ffill 行为
    # 1. 时间戳升序且数量对
    assert list(wide.index) == sorted(set(df['Timestamp']))
    # 2. 必须有 'Speed' 和 'AEB_Trigger' 两列
    assert 'Speed' in wide.columns
    assert 'AEB_Trigger' in wide.columns
    # 3. 断言 ffill: 时间早于AEB_Trigger第一次出现的时间，AEB_Trigger应为np.nan
    first_trigger_time = df[df['Signal'] == 'AEB_Trigger']['Timestamp'].min()
    for t in wide.index:
        if t < first_trigger_time:
            assert pd.isna(wide.loc[t, 'AEB_Trigger'])
    # 4. 检查 ffill 行为: AEB_Trigger应能向前填充，后续行为正确
    last_val = np.nan
    for t in wide.index:
        val = wide.loc[t, 'AEB_Trigger']
        if not pd.isna(val):
            last_val = val
        else:
            # 填充的应等于last_val
            assert val == last_val or (pd.isna(val) and pd.isna(last_val))
    # 5. Speed频繁，有填充逻辑（可选性检查）
    assert not wide['Speed'].isna().all()

    # 6. 时间戳升序 check
    time_array = np.array(wide.index)
    assert np.all(np.diff(time_array) > 0)

if __name__ == "__main__":
    test_parse_can_raw_long_table_aligns_and_fills()
    print("✅ test_parse_can_raw_long_table_aligns_and_fills passed!")