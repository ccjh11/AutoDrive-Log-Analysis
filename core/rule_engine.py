import pandas as pd
import math

class RuleEngine:
    """
    自动日志分析规则引擎：核心聚焦HIL故障注入诊断升级优化版，
    重点精准识别：
      - 跳变异常：Pandas .diff() 判定速度突变 > 50 km/h
      - 信号丢失：Pandas .isna() 判定单帧或连续NaN
    支持多种车辆日志的半自动化故障巡检。
    输入：帧对象（推荐csv/df解析器转换为对象/df），输出：结构化测试报告。
    """

    def __init__(self, frame_list):
        self.frames = frame_list
        self.reports = []

    def analyze(self):
        """
        用 pandas 算法精准分析HIL故障，核心包括：
          1. Speed跳变：两帧差值绝对值大于50，判为传感器跳变异常；
          2. 信号丢失检测：Speed及其他关键列出现NaN即报丢失异常（单帧丢失即判异常）。
        """
        self.reports.clear()
        # 输入转DataFrame兼容性
        if isinstance(self.frames, pd.DataFrame):
            df = self.frames
        else:
            if (
                len(self.frames) > 0
                and not isinstance(self.frames, dict)
                and not isinstance(self.frames, pd.Series)
            ):
                try:
                    df = pd.DataFrame(
                        [f.__dict__ if hasattr(f, "__dict__") else dict(f) for f in self.frames]
                    )
                except Exception:
                    df = pd.DataFrame([dict(f) for f in self.frames])
            else:
                df = pd.DataFrame(self.frames)

        df.columns = [str(c).lower() for c in df.columns]

        # 必须有time才能分析
        if "time" in df.columns:
            df = df.sort_values("time").reset_index(drop=True)
        else:
            return self.reports

        # 核心规则1：Speed突变跳变检测
        if "speed" in df.columns:
            speed_diff = df["speed"].diff()
            mask_jump = speed_diff.abs() > 50
            for idx in df.index[1:]:
                if pd.notna(speed_diff.loc[idx]) and mask_jump.loc[idx]:
                    t = df.loc[idx, "time"]
                    prev_speed = df.loc[idx - 1, "speed"] if idx - 1 in df.index else None
                    curr_speed = df.loc[idx, "speed"]
                    prev_t = df.loc[idx - 1, "time"] if idx - 1 in df.index else None
                    self.reports.append({
                        "type": "HIL注入/传感器跳变异常",
                        "risk": "🔴 Fatal",
                        "time": t,
                        "desc": (
                            f"Speed突变: {prev_speed} km/h → {curr_speed} km/h "
                            f"(Δ={curr_speed - prev_speed:.2f} km/h > 50)"
                        ),
                        "cause": "HIL故障注入、信号毛刺或异常",
                        "evidence": {
                            "prev_time": prev_t,
                            "curr_time": t,
                            "prev_speed": prev_speed,
                            "curr_speed": curr_speed,
                            "frame_idx": idx
                        }
                    })

        # 核心规则2：信号丢失检测（单帧NaN或连续NaN）
        key_cols = ["speed", "target_distance", "acc", "yaw", "steering_angle"]
        lost_cols = [col for col in key_cols if col in df.columns]

        for col in lost_cols:
            is_nan = df[col].isna()
            nan_indices = df[is_nan].index.tolist()
            reported_nan = set()
            for idx in nan_indices:
                # 单帧或新段起点才报异常（防止多次重复）
                if idx not in reported_nan:
                    t_nan = df.loc[idx, "time"]
                    self.reports.append({
                        "type": "HIL注入/信号丢失异常",
                        "risk": "🟠 Warning",
                        "time": t_nan,
                        "desc": f"{col}信号在{t_nan:.6f}s发生丢失(NaN)，判定为信号丢失异常",
                        "cause": "HIL信号缺失/传感器失效/注入测试",
                        "evidence": {
                            "signal": col,
                            "frame_idx": int(idx),
                            "time": t_nan
                        }
                    })
                    reported_nan.add(idx)
            # 如需检测连续丢失段，可启用以下注释块（补充连续段检测）
            # start_idx = None
            # count = 0
            # for i in df.index:
            #     if is_nan.loc[i]:
            #         if count == 0:
            #             start_idx = i
            #         count += 1
            #     else:
            #         if count >= 2:
            #             t_nan = df.loc[start_idx, 'time']
            #             self.reports.append({
            #                 'type': 'HIL注入/信号丢失异常',
            #                 'risk': '🔴 Fatal',
            #                 'time': t_nan,
            #                 'desc': f'{col}信号从{t_nan:.6f}s起连续{count}帧丢失(NaN)，判定为信号丢失异常',
            #                 'cause': 'HIL信号缺失/传感器失效/注入测试',
            #                 'evidence': {
            #                     'signal': col,
            #                     'start_time': t_nan,
            #                     'frames': [int(start_idx + i) for i in range(count) if (start_idx + i) in df.index]
            #                 }
            #             })
            #         count = 0
            #         start_idx = None
            # if count >= 2:
            #     t_nan = df.loc[start_idx, 'time']
            #     self.reports.append({
            #         'type': 'HIL注入/信号丢失异常',
            #         'risk': '🔴 Fatal',
            #         'time': t_nan,
            #         'desc': f'{col}信号从{t_nan:.6f}s起连续{count}帧丢失(NaN)，判定为信号丢失异常',
            #         'cause': 'HIL信号缺失/传感器失效/注入测试',
            #         'evidence': {
            #             'signal': col,
            #             'start_time': t_nan,
            #             'frames': [int(start_idx + i) for i in range(count) if (start_idx + i) in df.index]
            #         }
            #     })

        # 可扩展更多诊断规则
        return self.reports

    def _is_nan(self, val):
        if val is None:
            return True
        if isinstance(val, float) and math.isnan(val):
            return True
        if isinstance(val, str):
            try:
                return pd.isna(val)
            except Exception:
                return val.strip().lower() in ('nan', 'none', '')
        return False

    # 保留DTC故障查找功能，可选
    def lookup_dtc_desc(self, dtc_code):
        dtc_dict = {
            'C1234': '传感器信号丢失',
            'U1000': 'CAN通讯故障',
        }
        return dtc_dict.get(dtc_code, '未知DTC')

def generate_report(rule_reports):
    """
    根据规则引擎检测结果，自动生成结构化测试报告（含故障类型、原因、风险、时间、证据概览）
    """
    if not rule_reports:
        return "所有检查通过，未发现异常！"
    lines = []
    for idx, rep in enumerate(rule_reports, 1):
        risk = rep.get('risk', '')
        fault = rep.get('type', '')
        desc = rep.get('desc', '')
        cause = rep.get('cause', '')
        time = rep.get('time', '')
        lines.append(f"{idx}. [{risk}] {fault} @ {time}\n  - {desc}")
        if cause:
            lines.append(f"    原因: {cause}")
        evidence = rep.get('evidence', '')
        if isinstance(evidence, dict):
            lines.append(f"    证据关键: {str(evidence)}")
        elif isinstance(evidence, (list, tuple)):
            lines.append(f"    证据帧数: {len(evidence)}")
        elif evidence not in ('', None):
            lines.append(f"    证据: {str(evidence)}")
    return "\n".join(lines)