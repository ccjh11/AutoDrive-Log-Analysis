import os
import numpy as np
import matplotlib.pyplot as plt
from core.rule_engine import RuleEngine, generate_report

from datetime import datetime
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from io import BytesIO

def plot_signals_and_save(cleaned_df, output_dir="output_figures"):
    """
    生成曲线: 车速(Speed)、目标距离(Target_Distance)、AEB触发(AEB_Trigger)、制动压力(Brake_Pressure)、DTC码(DTC_Code)
    返回每个曲线的图片路径dict
    画图部分每10个点取1个点采样绘图以提升速度
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 字段不区分大小写匹配DataFrame的列名
    def extract_col(col_key):
        for c in cleaned_df.columns:
            if c.lower() == col_key.lower():
                return cleaned_df[c]
        return [None] * len(cleaned_df)
    
    # 时间字段支持不同大小写
    times = extract_col('time')
    speeds = extract_col('Speed')
    distances = extract_col('Target_Distance')
    aeb_triggers = extract_col('AEB_Trigger')
    brake_pressures = extract_col('Brake_Pressure')
    dtc_codes = extract_col('DTC_Code')

    # aeb, brake欠缺值填充
    aeb_triggers = np.array([0 if (v is None or (isinstance(v, float) and np.isnan(v))) else v for v in aeb_triggers])
    brake_pressures = np.array([0 if (v is None or (isinstance(v, float) and np.isnan(v))) else v for v in brake_pressures])

    # 转np.array，其他字段nan填充
    times_array = np.array([x for x in times])
    speeds_array = np.array([np.nan if (x is None) else x for x in speeds])
    distances_array = np.array([np.nan if (x is None) else x for x in distances])
    aeb_triggers_array = aeb_triggers
    brake_pressures_array = np.array([np.nan if (x is None) else x for x in brake_pressures])
    # dtc_codes原样用

    # 若时间轴全空则构造序号
    if np.all([x is None or (isinstance(x, float) and np.isnan(x)) for x in times]):
        times_array = np.arange(len(cleaned_df))

    paths = {}

    # ====== 加采样：只取每10个数据 ======
    step = 10
    times_sample = times_array[::step]
    speeds_sample = speeds_array[::step]
    distances_sample = distances_array[::step]
    aeb_triggers_sample = aeb_triggers_array[::step]
    brake_pressures_sample = brake_pressures_array[::step]
    # DTC码原样导出

    # 车速曲线
    plt.figure(figsize=(10, 4))
    plt.plot(times_sample, speeds_sample, label="Speed (km/h)", color='b')
    plt.xlabel("Time (s)")
    plt.ylabel("Speed (km/h)")
    plt.title("Vehicle Speed Curve")
    plt.grid(True)
    plt.tight_layout()
    speed_path = os.path.join(output_dir, "speed_curve.png")
    plt.savefig(speed_path)
    plt.close()
    paths['Speed'] = speed_path

    # 目标距离曲线
    plt.figure(figsize=(10, 4))
    plt.plot(times_sample, distances_sample, label="Target Distance (m)", color='g')
    plt.xlabel("Time (s)")
    plt.ylabel("Target Distance (m)")
    plt.title("Target Distance Curve")
    plt.grid(True)
    plt.tight_layout()
    distance_path = os.path.join(output_dir, "target_distance_curve.png")
    plt.savefig(distance_path)
    plt.close()
    paths['Target_Distance'] = distance_path

    # AEB触发状态曲线
    plt.figure(figsize=(10, 2))
    plt.step(times_sample, aeb_triggers_sample, label="AEB Trigger", color='r', where="post")
    plt.xlabel("Time (s)")
    plt.ylabel("AEB Trigger")
    plt.title("AEB Trigger Status Curve")
    plt.yticks([0, 1], ["Off", "On"])
    plt.grid(True, which='both', axis='x')
    plt.tight_layout()
    aeb_path = os.path.join(output_dir, "aeb_trigger_curve.png")
    plt.savefig(aeb_path)
    plt.close()
    paths['AEB_Trigger'] = aeb_path

    # 制动压力曲线
    plt.figure(figsize=(10, 4))
    plt.plot(times_sample, brake_pressures_sample, label="Brake Pressure", color='m')
    plt.xlabel("Time (s)")
    plt.ylabel("Brake Pressure")
    plt.title("Brake Pressure Curve")
    plt.grid(True)
    plt.tight_layout()
    brake_pressure_path = os.path.join(output_dir, "brake_pressure_curve.png")
    plt.savefig(brake_pressure_path)
    plt.close()
    paths['Brake_Pressure'] = brake_pressure_path

    # DTC Code list
    dtc_code_txt_path = os.path.join(output_dir, "dtc_code_list.txt")
    with open(dtc_code_txt_path, "w", encoding="utf-8") as f:
        for t, dtc in zip(times, dtc_codes):
            f.write(f"{t},{dtc}\n")
    paths['DTC_Code'] = dtc_code_txt_path

    return paths

def html_escape(text):
    """简单过滤HTML中的特殊字符"""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))

def generate_html_report(
        report_title,
        run_time,
        rule_reports,
        signal_figs,
        exception_figs):
    """
    自动生成html形式的报告
    - report_title: 测试名称
    - run_time: 测试时间
    - rule_reports: 自动化检测结果（list of dict）
    - signal_figs: dict of curve png paths
    - exception_figs: (可选)每个异常的截图，list of png path
    """

    html_lines = []
    html_lines.append(f'<h1>{html_escape(report_title)}</h1>')
    html_lines.append(f'<p><b>测试时间：</b>{html_escape(run_time)}<br>')
    html_lines.append(f'<b>异常总数：</b>{len(rule_reports)}<br></p>')

    # 曲线插图
    html_lines.append('<h2>测试主要信号曲线</h2>')
    # 参数名与展示
    param_label_map = {
        'Speed': "车速(Speed)",
        'Target_Distance': "目标距离(Target_Distance)",
        'AEB_Trigger': "AEB触发(AEB_Trigger)",
        'Brake_Pressure': "制动压力(Brake_Pressure)",
        'DTC_Code': "DTC故障码(DTC_Code)"
    }
    for label, path in signal_figs.items():
        display_label = html_escape(param_label_map.get(label, label))
        if label == 'DTC_Code':
            html_lines.append(f'<div><b>{display_label}:</b></div>')
            html_lines.append(f'<a href="{path}" target="_blank">下载DTC故障码表</a><br>')
        else:
            html_lines.append(f'<div><b>{display_label}:</b></div>')
            html_lines.append(f'<img src="{path}" width="720"/><br>')

    # 异常详情
    html_lines.append('<h2>异常检测与分析</h2>')
    if not rule_reports:
        html_lines.append("<p>所有检查通过，未发现异常。</p>")
    else:
        for idx, rep in enumerate(rule_reports, 1):
            risk = html_escape(rep.get("risk", ""))
            fault = html_escape(rep.get("type", ""))
            desc = html_escape(rep.get("desc", ""))
            cause = html_escape(rep.get("cause", ""))
            time = html_escape(rep.get("time", ""))
            html_lines.append(f'<div style="border:1px solid #ddd; margin:10px 0; padding:8px;">')
            html_lines.append(f'<b>{idx}. [{risk}] {fault} @ {time}</b><br>')
            html_lines.append(f'<span>说明：{desc}</span><br>')
            if cause:
                html_lines.append(f'原因：{cause}<br>')
            # 异常截图（如有）
            if exception_figs and idx-1 < len(exception_figs):
                html_lines.append(f'<img src="{exception_figs[idx-1]}" width="400"/><br>')
            html_lines.append('</div>')

    return '\n'.join(html_lines)

def main(
    cleaned_df,
    report_title="台架自动化日志分析报告",
    output_dir="output_result"
):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"[系统] 已获得清洗后的DataFrame，行数：{len(cleaned_df)}")
    # 1. 画图 & 保存
    figs = plot_signals_and_save(cleaned_df, output_dir=os.path.join(output_dir, "figures"))

    # 2. 执行规则检测
    engine = RuleEngine(cleaned_df)
    rules_report = engine.analyze()
    print(f"[系统] 自动检测完成，异常数量: {len(rules_report)}")

    # 3. 每个异常可进一步做局部截图/可选，本例仅输出全图
    exception_figs = []  # 可扩展，每个异常生成专属截图

    # 4. 输出html报告
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = generate_html_report(
        report_title=report_title,
        run_time=now_str,
        rule_reports=rules_report,
        signal_figs=figs,
        exception_figs=exception_figs
    )
    html_path = os.path.join(output_dir, "report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[系统] HTML测试报告已生成：{html_path}")

    # 5. 生成Word报告（含主要曲线和异常摘要）
    # 限制 Word 报告遍历异常只输出前100条
    try:
        doc = Document()
        doc.add_heading(report_title, 0)
        doc.add_paragraph(f"测试时间：{now_str}")
        doc.add_paragraph(f"异常总数：{len(rules_report)}")

        doc.add_heading("测试主要信号曲线", level=1)
        param_label_map = {
            'Speed': "车速(Speed)",
            'Target_Distance': "目标距离(Target_Distance)",
            'AEB_Trigger': "AEB触发(AEB_Trigger)",
            'Brake_Pressure': "制动压力(Brake_Pressure)",
            'DTC_Code': "DTC故障码(DTC_Code)"
        }
        for label, path in figs.items():
            display_label = param_label_map.get(label, label)
            if label == 'DTC_Code':
                doc.add_paragraph(f"{display_label}：见文件 {os.path.basename(path)}")
            else:
                doc.add_paragraph(f"{display_label}曲线：")
                doc.add_picture(path, width=Inches(6.0))

        doc.add_heading("异常检测与分析", level=1)
        if not rules_report:
            doc.add_paragraph("所有检查通过，未发现异常。")
        else:
            # 只输出前100条异常
            for idx, rep in enumerate(rules_report[:100], 1):
                doc.add_heading(f"{idx}. [{rep.get('risk', '')}] {rep.get('type', '')} @ {rep.get('time', '')}", level=2)
                doc.add_paragraph(rep.get('desc', ''))
                cause = rep.get('cause', '')
                if cause:
                    doc.add_paragraph(f"原因：{cause}")
                evidence = rep.get('evidence', '')
                if evidence:
                    doc.add_paragraph(f"证据关键：{str(evidence)}")
            if len(rules_report) > 100:
                doc.add_paragraph(f"...... 共{len(rules_report)}条，仅显示前100条")
        word_path = os.path.join(output_dir, "report.docx")
        doc.save(word_path)
        print(f"[系统] Word测试报告已生成：{word_path}")
    except Exception as e:
        print(f"[警告] 生成Word报告失败: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="自动日志分析系统")
    parser.add_argument("--name", help="测试名称", default="台架自动化日志分析报告")
    parser.add_argument("--out", help="结果输出目录", default="output_result")
    # 注意：现在不再在此接收 --log 参数
    args = parser.parse_args()
    print("错误：此脚本现在要求由主调度用 cleaned_df 直接调用 main()，不应直接命令行运行。")