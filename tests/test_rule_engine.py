import pytest
import pandas as pd
from core import can_parser

def test_can_parser_parse_can_raw_long_table_with_asynchronous_timestamps():
    # 1. 构造非同步时间戳的 CAN 报文长表数据
    # 假设有三个信号，不同时间采样
    data = [
        {"timestamp": 0.0,   "can_id": 1, "signal_name": "Speed",           "signal_value": 10.0},
        {"timestamp": 0.1,   "can_id": 2, "signal_name": "Target_Distance", "signal_value": 20.0},
        {"timestamp": 0.15,  "can_id": 3, "signal_name": "Brake_Pressure",  "signal_value": 0.3},
        {"timestamp": 0.25,  "can_id": 1, "signal_name": "Speed",           "signal_value": 12.0},
        {"timestamp": 0.27,  "can_id": 2, "signal_name": "Target_Distance", "signal_value": 21.0},
        {"timestamp": 0.32,  "can_id": 3, "signal_name": "Brake_Pressure",  "signal_value": 0.4},
        # 故意缺少某帧的 Target_Distance（0.5 前只有 Speed 有，0.6 前只有 Brake_Pressure 有）
        {"timestamp": 0.5,   "can_id": 1, "signal_name": "Speed",           "signal_value": 11.0},
        {"timestamp": 0.6,   "can_id": 3, "signal_name": "Brake_Pressure",  "signal_value": 0.35},
    ]
    df = pd.DataFrame(data)

    # 2. 构造信号动态映射（通常用于解析时确定哪些 CAN_ID 属于哪些物理信号）
    # 这里按最简单的一对一映射
    signal_dynamic_map = {
        "Speed": {"can_id": 1},
        "Target_Distance": {"can_id": 2},
        "Brake_Pressure": {"can_id": 3},
        "AEB_Trigger": {"can_id": 4},     # 故意没有此信号帧
        "DTC_Code": {"can_id": 5},        # 故意没有此信号帧
    }

    # 3. 解析
    result = can_parser.parse_can_raw_long_table(df, signal_dynamic_map)

    # 4. 断言字段列头是否齐全
    expected_columns = ['time', 'Speed', 'Target_Distance', 'AEB_Trigger', 'Brake_Pressure', 'DTC_Code']
    assert list(result.columns) == expected_columns

    # 5. 断言出现时间行是否涵盖所有主轴（Speed）采样点，对齐后无重复
    speed_times = df[df.signal_name == "Speed"].timestamp.round(4).tolist()
    assert all(t in result['time'].tolist() for t in [round(tt, 4) for tt in speed_times])
    assert result['time'].is_unique

    # 6. 检查宽表对齐策略
    # 比如 0.25 时行，Speed 应为 12.0，Target_Distance 最近一次是 20.0，AEB_Trigger 应该是 NA，Brake_Pressure 最近一次 0.3
    row = result[result['time'].round(4) == 0.25]
    assert pytest.approx(float(row['Speed'])) == 12.0
    assert pytest.approx(float(row['Target_Distance'])) == 20.0
    assert pd.isna(row['AEB_Trigger']).all()
    assert pytest.approx(float(row['Brake_Pressure'])) == 0.3
    assert pd.isna(row['DTC_Code']).all()

    # 7. 检查时间精度、无空缺、填充逻辑
    # 如 0.5 时只更新了 Speed，Brake_Pressure 应维持上一次 0.4，Target_Distance 仍是 21.0
    row = result[result['time'].round(4) == 0.5]
    assert pytest.approx(float(row['Speed'])) == 11.0
    assert pytest.approx(float(row['Target_Distance'])) == 21.0
    assert pytest.approx(float(row['Brake_Pressure'])) == 0.4

    # 8. 检查缺失信号字段自动补齐并全为 NA
    assert result['AEB_Trigger'].isna().all()
    assert result['DTC_Code'].isna().all()