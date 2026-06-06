import pandas as pd

class TestFrame:
    """
    台架测试数据帧结构（推荐用class而不是裸dict）
    对应原始csv日志抬头: time, Speed, Target_Distance, AEB_Trigger, Brake_Pressure, DTC_Code
    """
    def __init__(self, time, speed, target_distance, aeb_trigger, brake_pressure, dtc_code):
        self.time = time
        self.speed = speed
        self.target_distance = target_distance
        self.aeb_trigger = aeb_trigger   # 0/1，表示AEB动作
        self.brake_pressure = brake_pressure
        self.dtc_code = dtc_code

    def __repr__(self):
        # 展示所有字段
        return (f"TestFrame(time={self.time}, speed={self.speed}, target_distance={self.target_distance}, "
                f"aeb_trigger={self.aeb_trigger}, brake_pressure={self.brake_pressure}, dtc_code={self.dtc_code})")

def load_and_clean_log(csv_path):
    """
    读取并清洗台架测试log日志，返回TestFrame对象列表
    字段严格对齐原始csv日志（time, Speed, Target_Distance, AEB_Trigger, Brake_Pressure, DTC_Code）
    """
    # 读取csv为DataFrame
    df = pd.read_csv(csv_path)
    # 丢弃全空行
    df = df.dropna(how='all')
    # 用合适的方式填充空值（数值字段用0填充，字符串用空字符串填充）
    df = df.fillna({
        'time': 0,
        'Speed': 0,
        'Target_Distance': 0,
        'AEB_Trigger': 0,
        'Brake_Pressure': 0,
        'DTC_Code': ''
    })
    # 转换数据类型，保证一致性
    df['time'] = df['time'].astype(float)
    df['Speed'] = df['Speed'].astype(float)
    df['Target_Distance'] = df['Target_Distance'].astype(float)
    df['AEB_Trigger'] = df['AEB_Trigger'].astype(int)
    df['Brake_Pressure'] = df['Brake_Pressure'].astype(int)
    df['DTC_Code'] = df['DTC_Code'].astype(str)

    frame_list = []
    for _, row in df.iterrows():
        frame = TestFrame(
            time=row['time'],
            speed=row['Speed'],
            target_distance=row['Target_Distance'],
            aeb_trigger=row['AEB_Trigger'],
            brake_pressure=row['Brake_Pressure'],
            dtc_code=row['DTC_Code']
        )
        frame_list.append(frame)
    return frame_list

# ========== 示例调用 ==========
if __name__ == "__main__":
    log_path = "example_adas_log.csv"  # 可根据实际需要更改
    test_frames = load_and_clean_log(log_path)
    print("[系统日志] 成功清洗并加载日志帧：")
    for f in test_frames[:5]:  # 只看前几帧
        print(f)