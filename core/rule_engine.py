import pandas as pd

class RuleEngine:
    """
    自动日志分析规则引擎：核心聚焦四大判据（心跳超时、信号畸变、因果违背、诊断爆发）。
    支持多种车辆日志的半自动化故障巡检。
    输入：帧对象（推荐csv/df解析器转换为对象），输出：结构化测试报告。
    """

    def __init__(self, frame_list):
        self.frames = frame_list
        self.reports = []

    def analyze(self):
        self.reports.clear()
        self.check_network_timeout()
        self.check_signal_implausibility()
        self.check_action_reaction_violation()
        self.check_dtc_nrc_detection()
        return self.reports

    # 判生死：网络超时检测（Network Timeout/ECU掉线）
    def check_network_timeout(self, id_field='msg_id', timestamp_field='time', target_id=None, max_gap_ms=100):
        """
        检查网络CAN或ECU心跳帧的超时（掉线）：同一CAN ID（target_id），相邻两帧时间差超max_gap_ms视为掉线。
        target_id: 必须外部指定需监控的CAN ID。
        """
        if target_id is None:
            return
        filtered = [f for f in self.frames if hasattr(f, id_field) and getattr(f, id_field) == target_id]
        filtered = sorted(filtered, key=lambda f: getattr(f, timestamp_field, 0))
        last_ts = None
        for f in filtered:
            ts = getattr(f, timestamp_field, None)
            if last_ts is not None and ts is not None:
                delta_ms = (ts - last_ts) * 1000
                if delta_ms > max_gap_ms:
                    self.reports.append({
                        'type': '硬件/网络掉线',
                        'risk': '🔴 Fatal',
                        'time': ts,
                        'desc': f'网络帧({target_id})超时丢失：{last_ts:.6f} → {ts:.6f}（Δ={delta_ms:.1f}ms > {max_gap_ms}ms）',
                        'cause': 'CAN物理连接断开或ECU死机',
                        'evidence': {'last_ts': last_ts, 'curr_ts': ts}
                    })
            last_ts = ts

    # 判感知：信号物理畸变（超界/突变）
    def check_signal_implausibility(self):
        """
        检查典型信号的物理超界+非理性跳变
        - 速度/距离等 不应出现负值（硬边界）
        - 非理性跳变，如target_distance 在极短时间内剧烈变化
        """
        # 配置可根据实际log字段做适当修改
        limits = {
            'speed': (0, 250),  # km/h，硬边界
            'target_distance': (0, 300),  # m
        }

        # --------- （1）硬边界检测 ----------
        for f in self.frames:
            for field, (mini, maxi) in limits.items():
                if hasattr(f, field):
                    val = getattr(f, field)
                    if (val is not None) and (val < mini or val > maxi):
                        self.reports.append({
                            'type': '感知信号异常/毛刺',
                            'risk': '🟠 High',
                            'time': getattr(f, 'time', ''),
                            'desc': f'{field}={val} 超出物理硬界({mini}~{maxi})',
                            'cause': '传感器受干扰或底层解码错误',
                            'evidence': f
                        })
        # --------- （2）极端跳变检测（以 speed/target_distance为例） ----------
        jump_config = [
            {
                'field': 'speed',
                'max_grad': 120,  # km/h/s
            },
            {
                'field': 'target_distance',
                'max_grad': 150,  # m/s（如有该字段）
            }
        ]
        for config in jump_config:
            field = config['field']
            max_grad = config['max_grad']
            prev_val = None
            prev_ts = None
            for f in self.frames:
                if hasattr(f, field) and hasattr(f, 'time'):
                    val = getattr(f, field)
                    ts = getattr(f, 'time')
                    if prev_val is not None and prev_ts is not None:
                        dt = ts - prev_ts
                        if dt > 0:
                            grad = abs(val - prev_val) / dt
                            if grad > max_grad:
                                self.reports.append({
                                    'type': '感知信号异常/毛刺',
                                    'risk': '🟠 High',
                                    'time': ts,
                                    'desc': f'{field}非理性突变: {prev_val}->{val}, Δt={dt:.3f}s, grad={grad:.2f} > {max_grad}',
                                    'cause': '信号毛刺/EMI干扰/刷写错误',
                                    'evidence': {'prev': (prev_ts, prev_val), 'curr': (ts, val)}
                                })
                    prev_val = val
                    prev_ts = ts

    # 判决策：核心因果违背（Action-Reaction）
    def check_action_reaction_violation(self,
            trigger_field='AEB_Trigger',
            trigger_val=1,
            window_sec=0.2,
            response_field='Brake_Pressure',
            min_response=0.1):
        """
        触发AEB后（AEB_Trigger==1），200ms内压力必须提升>min_response
        """
        # 检查是否所有frame均有response_field，有则必检
        has_response = any(hasattr(f, response_field) for f in self.frames)
        if not has_response:
            return

        for i, f in enumerate(self.frames):
            if getattr(f, trigger_field, None) == trigger_val:
                t0 = getattr(f, 'time', None)
                base_response = getattr(f, response_field, 0.0)
                # 检查未来window_sec秒内是否有>min_response的增长
                triggered = False
                for j in range(i+1, len(self.frames)):
                    fj = self.frames[j]
                    dt = getattr(fj, 'time', 0) - t0 if (t0 is not None) else 0
                    if dt > window_sec:
                        break
                    val = getattr(fj, response_field, None)
                    if val is not None and val > base_response + min_response:
                        triggered = True
                        break
                if not triggered:
                    self.reports.append({
                        'type': '业务逻辑失效/执行器未响应',
                        'risk': '🔴 Fatal',
                        'time': t0,
                        'desc': f"触发{trigger_field}=1后{window_sec*1000:.0f}ms内{response_field}无显著提升",
                        'cause': '算法状态机卡死或底盘拒绝响应',
                        'evidence': self.frames[i: min(i + int(window_sec * 1000), len(self.frames))]
                    })

    # 判自检：诊断故障码/NRC爆发（DTC/NRC Detection）
    def check_dtc_nrc_detection(self, id_field='msg_id', diag_prefix='0x7', dtc_field='dtc_code', data_field='raw_data', dtc_window_sec=5):
        """
        检索诊断总线ECU的DTC故障码或NRC爆发
        diag_prefix: 诊断帧ID前缀，如0x7开头
        """
        # DTC窗口/证据：中心±dtc_window_sec/2
        for i, f in enumerate(self.frames):
            msgid = str(getattr(f, id_field, ''))
            if msgid.startswith(str(diag_prefix)):
                # DTC检测
                dtc = getattr(f, dtc_field, None)
                if dtc:
                    t0 = getattr(f, 'time', None)
                    win = [f2 for f2 in self.frames if abs(getattr(f2, 'time', 0)-t0) <= dtc_window_sec/2]
                    self.reports.append({
                        'type': '系统自检报错/DTC',
                        'risk': '🟡 Medium',   # 可进一步匹配dtc定义后决定风险
                        'time': t0,
                        'desc': f'DTC上报码: {dtc}',
                        'cause': f"DTC定义: {self.lookup_dtc_desc(dtc)}" if hasattr(self, 'lookup_dtc_desc') else '',
                        'evidence': win
                    })
                # NRC检测（被7F/NRC码拒绝）
                raw = getattr(f, data_field, '')
                if isinstance(raw, (int, float)):
                    raw = str(raw)
                if str(raw).startswith('7F'):
                    self.reports.append({
                        'type': '系统自检报错/NRC',
                        'risk': '🔴 Fatal',
                        'time': getattr(f, 'time', None),
                        'desc': f'NRC诊断否定响应(7F): {raw}',
                        'cause': f'ECU自检发现严重异常/服务被拒绝 ({raw})',
                        'evidence': f
                    })

    # 可根据DTC码查表输出原因（可选功能）
    def lookup_dtc_desc(self, dtc_code):
        # 示例：实际应加载DTC词典
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
        # 证据仅显示类型或主键信息，避免太大
        evidence = rep.get('evidence', '')
        if isinstance(evidence, dict):
            lines.append(f"    证据关键: {str(evidence)}")
        elif isinstance(evidence, (list, tuple)):
            lines.append(f"    证据帧数: {len(evidence)}")
        elif evidence not in ('', None):
            lines.append(f"    证据: {str(evidence)}")
    return "\n".join(lines)