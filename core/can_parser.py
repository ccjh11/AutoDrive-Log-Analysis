import pandas as pd

def parse_can_raw_long_table(can_long_df, signal_dynamic_map):
    """
    解析原始 CAN 报文长表，结合信号动态映射，输出“标准信号表”
    can_long_df: DataFrame, 包含 CAN_ID, Timestamp, Signal, Value
    signal_dynamic_map: dict, {signal_name: {can_id, ...}} 来自 DBC 映射
    返回：DataFrame，列字段为 ['time', 'speed', 'target_distance', 'aeb_trigger', 'brake_pressure', 'dtc_code']
    """
    can_long_df = can_long_df.rename(columns={
        'timestamp': 'Timestamp',
        'can_id': 'CAN_ID',
        'signal_name': 'Signal',
        'signal_value': 'Value'
    })
    can_long_df['Timestamp'] = pd.to_numeric(can_long_df['Timestamp'], errors='coerce')
    can_long_df['CAN_ID'] = pd.to_numeric(can_long_df['CAN_ID'], errors='coerce')

    standard_cols = ['Timestamp', 'CAN_ID', 'Signal', 'Value']
    for col in standard_cols:
        if col not in can_long_df.columns:
            can_long_df[col] = pd.NA
    can_long_df = can_long_df[standard_cols]
    can_long_df = can_long_df.sort_values('Timestamp').reset_index(drop=True)

    signal_map = {
        'speed': ['vehicle_speed', 'Speed', 'VEHICLE_SPEED'],
        'target_distance': ['distance', 'Target_Distance', 'TGT_DIST'],
        'aeb_trigger': ['aeb_status', 'AEB_Trigger', 'AEB_STATUS'],
        'brake_pressure': ['brake_pressure', 'Brake_Pressure', 'BRAKE_PRESSURE'],
        'dtc_code': ['dtc_code', 'DTC_Code', 'DTC'],
    }
    downstream_columns = ['time'] + list(signal_map.keys())

    times = can_long_df['Timestamp'].drop_duplicates().sort_values().reset_index(drop=True)
    output_df = pd.DataFrame({'time': times})

    for col_name, matched_signals in signal_map.items():
        mask = can_long_df['Signal'].isin(matched_signals)
        signal_df = can_long_df.loc[mask, ['Timestamp', 'Value']].copy()
        if signal_df.empty:
            output_df[col_name] = pd.NA
            continue
        if col_name != 'dtc_code':
            signal_df['Value'] = pd.to_numeric(signal_df['Value'], errors='coerce')
        last_vals = signal_df.groupby('Timestamp', sort=False)['Value'].last()
        output_df[col_name] = output_df['time'].map(last_vals)

    return output_df[downstream_columns]

if __name__ == "__main__":
    can_long_df = pd.read_csv('data/chaos_can_raw_log.csv')
    signal_dynamic_map = {}
    cleaned_df = parse_can_raw_long_table(can_long_df, signal_dynamic_map)
    print(cleaned_df.head(10))
