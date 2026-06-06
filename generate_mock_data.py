import pandas as pd
import numpy as np
import random
import os

def generate_massive_chaos_log():
    print("🚀 正在启动引擎，捏造 10 万行海量混沌数据集，请稍候...")
    
    rows = 100000
    # 模拟 50ms 一帧的真实时间戳
    timestamps = np.round(np.linspace(0.00, rows*0.05, rows), 2)
    
    # 模拟车速在 60km/h 左右正态分布微小波动
    speed = np.random.normal(60, 1.5, rows)
    
    # 模拟目标距离慢慢靠近
    distance = np.linspace(1000, 10, rows)
    
    # 初始状态全为 0
    aeb = np.zeros(rows, dtype=int)
    pressure = np.zeros(rows, dtype=int)
    # 故障码初始全为空 (NaN)
    dtc = [np.nan] * rows

    # ==========================================
    # 😈 开始在 10 万行正常数据中“随机埋雷”
    # ==========================================
    
    # 🔪 埋雷 1：制造 50 处信号毛刺脏数据 (Rule 2: 物理畸变)
    for _ in range(50):
        idx = random.randint(1000, 90000)
        distance[idx] = 0.0  # 距离突然变成 0

    # 🔪 埋雷 2：制造 5 处网络卡顿/掉线 (Rule 1: 心跳超时)
    for _ in range(5):
        idx = random.randint(1000, 90000)
        # 强行把后面的时间往后推 0.5 秒，制造时间断层
        timestamps[idx:] += 0.5  

    # 🔪 埋雷 3：制造 3 处致命逻辑失效 (Rule 3: AEB触发但无压力)
    for _ in range(3):
        idx = random.randint(1000, 90000)
        aeb[idx:idx+10] = 1       # 连续 10 帧发出刹车指令
        pressure[idx:idx+10] = 0  # 但底盘压力死活不上升

    # 🔪 埋雷 4：制造 2 处偶发故障码 (Rule 4: DTC)
    dtc[50000] = "U0100_LostComm"
    dtc[85000] = "P0500_SpeedSensor"

    # ==========================================
    # 📦 打包并导出 CSV
    # ==========================================
    df = pd.DataFrame({
        'Timestamp': timestamps,
        'Vehicle_Speed': speed,
        'Target_Distance': distance,
        'AEB_Trigger': aeb,
        'Brake_Pressure': pressure,
        'DTC_Code': dtc
    })

    # 确保 data 文件夹存在
    os.makedirs('data', exist_ok=True)
    output_path = 'data/massive_chaos_log.csv'
    
    df.to_csv(output_path, index=False)
    print(f"✅ 生成完毕！文件已安全保存至: {output_path}")
    print(f"📊 总数据量: {rows} 行，赶紧用你的 GUI 去挑战它吧！")

if __name__ == "__main__":
    generate_massive_chaos_log()