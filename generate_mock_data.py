import pandas as pd
import numpy as np
import random
import os

def generate_chaos_can_bus_log():
    print("🚀 正在启动引擎，捏造高度模拟 CAN 总线的混沌原始报文日志，请稍候...")

    n_speed = 90000  # roughly 900 seconds at 100Hz
    n_aeb = 9000     # roughly 900 seconds at 10Hz

    # 模拟不同 CAN ID 信号
    frame_defs = [
        {
            "can_id": 0x120,
            "signal": "Speed",
            "freq_hz": 100,
            "n": n_speed,
            "start_offset_ms": 0,   # Speed 信号与整数时间戳对齐
        },
        {
            "can_id": 0x121,
            "signal": "Target_Distance",
            "freq_hz": 100,
            "n": n_speed,
            "start_offset_ms": 0,   # 跟 Speed 同步
        },
        {
            "can_id": 0x180,
            "signal": "AEB_Trigger",
            "freq_hz": 10,
            "n": n_aeb,
            "start_offset_ms": 5,   # AEB 信号刻意错开发车速，以模拟异步帧到达（本质就是0.005s偏移）
        },
        {
            "can_id": 0x181,
            "signal": "Brake_Pressure",
            "freq_hz": 10,
            "n": n_aeb,
            "start_offset_ms": 5,   # 与 AEB_Trigger 同步
        },
        {
            "can_id": 0x700,
            "signal": "DTC_Code",
            "freq_hz": 1,
            "n": 10,
            "start_offset_ms": 30, # DTC 偶发
        }
    ]

    payloads = []

    # 1. 生成高频 Speed 和 Target_Distance 信号 (100Hz)
    t_speed = np.round(np.arange(0, n_speed) * 0.01 + frame_defs[0]["start_offset_ms"]/1000.0, 5)
    speed_val = np.random.normal(60, 1.5, n_speed)
    distance_val = np.linspace(1000, 10, n_speed)
    for i in range(n_speed):
        payloads.append({
            'Timestamp': t_speed[i],
            'CAN_ID': frame_defs[0]["can_id"],
            'Signal': 'Speed',
            'Value': speed_val[i]
        })
        payloads.append({
            'Timestamp': t_speed[i],
            'CAN_ID': frame_defs[1]["can_id"],
            'Signal': 'Target_Distance',
            'Value': distance_val[i]
        })

    # 2. 生成低频 AEB_Trigger 和 Brake_Pressure (10Hz)，时间刻意错开，与100Hz信号不同步
    t_aeb = np.round(np.arange(0, n_aeb) * 0.1 + frame_defs[2]["start_offset_ms"]/1000.0, 5)
    aeb_trigger = np.zeros(n_aeb, dtype=int)
    brake_pressure = np.zeros(n_aeb, dtype=int)

    # 随机选 6 个区块制造 AEB 真实触发（且制造下游失效故障）
    chaos_triggers = sorted(random.sample(range(1000, n_aeb - 1000), 6))
    for strike, idx in enumerate(chaos_triggers):
        aeb_trigger[idx:idx+10] = 1  # 连续10帧 AEB触发
        if strike < 3:
            brake_pressure[idx:idx+10] = 0  # 故意制造 "AEB有动作，压力不上升" 故障
        else:
            brake_pressure[idx:idx+10] = [random.randint(200, 300) for _ in range(10)]

    for i in range(n_aeb):
        payloads.append({
            'Timestamp': t_aeb[i],
            'CAN_ID': frame_defs[2]["can_id"],
            'Signal': 'AEB_Trigger',
            'Value': aeb_trigger[i]
        })
        payloads.append({
            'Timestamp': t_aeb[i],
            'CAN_ID': frame_defs[3]["can_id"],
            'Signal': 'Brake_Pressure',
            'Value': brake_pressure[i]
        })

    # 3. 偶发 DTC 故障帧（如同标准 CAN 诊断帧）
    t_dtc = np.round(np.linspace(10, n_speed/100-10, 10) + frame_defs[4]["start_offset_ms"]/1000.0, 5)
    dtc_vals = [np.nan] * 10
    dtc_vals[2] = "U0100_LostComm"
    dtc_vals[7] = "P0500_SpeedSensor"
    for i in range(10):
        payloads.append({
            'Timestamp': t_dtc[i],
            'CAN_ID': frame_defs[4]["can_id"],
            'Signal': 'DTC_Code',
            'Value': dtc_vals[i]
        })

    # 4. 故意埋雷：距离毛刺（如 CAN 信号畸变），随机选 50帧某帧 Target_Distance = 0
    td_indices = sorted(random.sample(range(1000, n_speed-1000), 50))
    for idx in td_indices:
        payloads.append({
            'Timestamp': t_speed[idx]+0.0008,  # 微小偏移以真乱序
            'CAN_ID': frame_defs[1]["can_id"],
            'Signal': 'Target_Distance',
            'Value': 0.0
        })

    # 5. 心跳断层（制造局部时间戳跳跃/数据缺口）: 在100Hz信号流里，随机选5个点，后面时间全部突变漂移0.5s
    cutoff_idx = sorted(random.sample(range(1000, n_speed - 2000), 5))
    for j, idx in enumerate(cutoff_idx):
        drift = 0.5*(j+1)
        for k in range(idx+1, n_speed):
            # Speed
            payloads.append({
                'Timestamp': t_speed[k] + drift,
                'CAN_ID': frame_defs[0]["can_id"],
                'Signal': 'Speed',
                'Value': speed_val[k]
            })
            # Target_Distance
            payloads.append({
                'Timestamp': t_speed[k] + drift,
                'CAN_ID': frame_defs[1]["can_id"],
                'Signal': 'Target_Distance',
                'Value': distance_val[k]
            })

    # 6. 最终打乱所有报文顺序（按真实时间戳递增重新排序）
    df = pd.DataFrame(payloads)
    df = df.sort_values(by="Timestamp", kind="mergesort").reset_index(drop=True)

    # 导出为 csv
    os.makedirs('data', exist_ok=True)
    output_path = 'data/chaos_can_raw_log.csv'
    df.to_csv(output_path, index=False)
    print(f"✅ 仿真 CAN 总线原始日志生成完毕！文件已安全保存至: {output_path}")
    print(f"📊 总报文帧数: {len(df)}，赶紧用你的算法和 GUI 去挑战它吧！")

    # ---------------------- 故障注入 MASSIVE FAULT INJECTION 扩展 -------------------------

    df_fault = df.copy()

    # === 保证故障注入边界的安全余量 ===
    safe_margin = 100
    n_fault = len(df_fault)
    safe_len = max(0, n_fault - safe_margin)  # 用于选取索引安全范围

    # --- 跳变异常注入（信号突变）: 选取 Speed 数据大约1/2处，确保索引合法 ---
    speed_mask = (df_fault['Signal'] == 'Speed')
    speed_indices = df_fault[speed_mask].index.to_list()
    n_speed_rows = len(speed_indices)
    safe_n_speed_rows = max(0, n_speed_rows - safe_margin)

    if safe_n_speed_rows > 10:
        # 1/2处，且保证末尾有足够余量给3帧操作
        pos = min(safe_n_speed_rows // 2, n_speed_rows - 3)  # 不会跨过倒数三帧
        if pos >= 0 and (pos + 2 < n_speed_rows):
            jump_middle = speed_indices[pos]
            df_fault.loc[jump_middle, 'Value'] = 20

            jump_next = speed_indices[pos+1]
            df_fault.loc[jump_next, 'Value'] = 300

            jump_next2 = speed_indices[pos+2]
            # 恢复为和主log同样的 Speed 值（防止越界）
            real_idx = (pos+2) % len(speed_val) if len(speed_val) > 0 else 0
            df_fault.loc[jump_next2, 'Value'] = speed_val[real_idx]
        # 若数据量不足连续三帧，只修改当前合法帧
        elif pos >= 0 and pos < n_speed_rows:
            jump_middle = speed_indices[pos]
            df_fault.loc[jump_middle, 'Value'] = 20

    # --- 信号丢失（NaN注入）: 选取 Speed/Target_Distance 信号大约3/4处, 保证安全余量 ---
    # 连续 up_to_5 帧为NaN，但不得越界且不得越过 safe_len 上限
    if safe_n_speed_rows > 10:
        nan_seq_start = min((safe_n_speed_rows * 3) // 4, n_speed_rows - 5)
        max_n = min(5, n_speed_rows - nan_seq_start, n_speed_rows - safe_margin)
        for offset in range(max_n):
            idx = speed_indices[nan_seq_start + offset]
            df_fault.loc[(df_fault['Signal']=='Speed') & (df_fault.index==idx), 'Value'] = np.nan

            # 找 Target_Distance 在这个 index 的时间戳同行，且有额外的安全保护
            row_ts = df_fault.loc[idx, 'Timestamp']
            td_idx = df_fault[(df_fault['Signal']=='Target_Distance') & (df_fault['Timestamp']==row_ts)].index
            for tidx in td_idx:
                if tidx < len(df_fault):
                    df_fault.loc[tidx, 'Value'] = np.nan

    # --- 信号完全丢失（丢帧）：只移除 Target_Distance 的 up_to_5 帧（第1/5段附近，保证不越界）---
    target_mask = (df_fault['Signal']=='Target_Distance')
    td_indices_for_drop = df_fault[target_mask].index.to_list()
    n_td_rows = len(td_indices_for_drop)
    safe_n_td_rows = max(0, n_td_rows - safe_margin)
    drop_from = min(n_td_rows // 5, n_td_rows - 5) if n_td_rows > 5 else 0  # 靠前1/5且留余量
    drop_total = min(5, n_td_rows - drop_from) if n_td_rows - drop_from > 0 else 0
    drop_range_indices = td_indices_for_drop[drop_from:drop_from + drop_total]
    if drop_total > 0:
        df_fault = df_fault.drop(drop_range_indices).reset_index(drop=True)

    # 导出故障注入数据
    fault_output_path = 'data/massive_chaos_fault_injection.csv'
    df_fault.to_csv(fault_output_path, index=False)
    print(f"🧨 故障注入（Fault Injection）数据生成完毕！文件已安全保存至: {fault_output_path}")
    print(f"⚡ 带故障报文帧数: {len(df_fault)}，挑战你的鲁棒算法吧！")


if __name__ == "__main__":
    generate_chaos_can_bus_log()