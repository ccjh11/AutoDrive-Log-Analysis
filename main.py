# main.py 的最开头

import matplotlib
matplotlib.use('Agg')  # 强制全局使用非交互式后台画图
import matplotlib.pyplot as plt

import os
import sys
import threading

# 导入 data 模块（数据结构与示例日志）
import data

# 导入 core 层
from core import data_processor
from core import rule_engine
from core import can_parser  # 新增插拔管线：can_parser

# 导入 output 层
from output import report_generator

# 导入 gui 层
from gui import gui_main

def analyze_log_and_generate_report(
    log_csv_path,
    output_dir,
    report_title,
    callback,
    signal_dynamic_map=None,
):
    """
    日志分析主流程（支持插拔式Pipeline）：读取日志，清洗->信号解析（can_parser）->规则引擎检测->报告
    增加callback回调通知主线程（GUI）任务结束
    始终将处理好的 DataFrame 全流程传递，严禁报告阶段重新读取文件。
    """
    try:
        if not log_csv_path:
            raise ValueError("[主流程] 必须提供 log_csv_path 参数！")

        print(f"[主流程] 加载日志: {log_csv_path}")

        # ==== 修改：根据文件名强制适配 can_parser 管线 ====
        basename = os.path.basename(log_csv_path)
        should_use_can_parser = (
            ("fault_injection" in basename) or
            ("raw_log" in basename)
        )

        # 步骤1: 文件只读入一次，并解析为标准宽表 frames
        if should_use_can_parser:
            print("[主流程] 检测到 fault_injection 或 CAN 原始长表，强制用 can_parser 解析转换成标准信号宽表")
            import pandas as pd
            # 加入 low_memory=False 防止类型混乱导致解析错位
            raw_df = pd.read_csv(log_csv_path, low_memory=False)
            if signal_dynamic_map is None:
                print("[主流程] 未传入 signal_dynamic_map，使用默认信号映射（如有）")
            frames = can_parser.parse_can_raw_long_table(raw_df, signal_dynamic_map)
            print(f"[主流程] can_parser 输出标准信号表，形状: {frames.shape}")
        else:
            frames = data_processor.load_and_clean_log(log_csv_path)
            print(f"[主流程] 日志帧加载完成，共 {len(frames)} 条")

      # 步骤2: 自动化规则分析
        print(f"[主流程] 执行自动化规则检测...")
        
        # ==== 加上下面这三行“显形代码” ====
        speed_col = 'speed' if 'speed' in frames.columns else 'Speed'
        print("【架构师Debug】送入规则引擎的数据最大车速是:", frames[speed_col].max())
        print("【架构师Debug】送入规则引擎的数据包含空值（NaN）的数量是:", frames[speed_col].isna().sum())
        # ==================================

        engine = rule_engine.RuleEngine(frames)
        rules_report = engine.analyze()
        print(f"[主流程] 检测完成，发现异常 {len(rules_report)} 个")

        # 步骤3: 生成报告——只用已清洗的 DataFrame，不再重读原文件
        print(f"[主流程] 生成测试报告至 {output_dir}")
        report_generator.main(
            cleaned_df=frames,    # 只传递所需参数，不传 log_path
            report_title=report_title,
            output_dir=output_dir
        )
        print(f"[主流程] 日志分析与报告生成完毕！")
        # 新增：分析结束时，通知GUI更新进度条到100%（如果GUI支持）
        if callback:
            # 回调时附加progress=100, 便于GUI收到回调直接把进度条拉满
            callback(success=True, msg="分析与报告生成完毕", progress=100)
    except Exception as e:
        print(f"[主流程] 分析异常: {e}")
        if callback:
            callback(success=False, msg=str(e))

def run_analysis_in_thread(
    log_csv_path,
    output_dir,
    report_title,
    callback,
    signal_dynamic_map=None,
):
    """
    在线程中运行分析逻辑，避免阻塞主线程（GUI）
    支持Pipeline参数插拔。可自动适配 CAN 原始长表和宽表两种格式。
    """
    thread = threading.Thread(
        target=analyze_log_and_generate_report,
        kwargs={
            'log_csv_path': log_csv_path,
            'output_dir': output_dir,
            'report_title': report_title,
            'callback': callback,
            'signal_dynamic_map': signal_dynamic_map,
        }
    )
    thread.setDaemon(True)  # 守护进程，主进程退出时子线程自动关闭
    thread.start()
    return thread

if __name__ == "__main__":
    # 主线程只负责GUI事件循环，实际分析在子线程
    # 需要gui_main这个模块支持异步log分析任务的触发（需在GUI层调用run_analysis_in_thread）
    from gui import gui_main

    # 补充说明：请确保 gui_main.py 里的 on_analysis_done 回调函数定义为：
    # def on_analysis_done(success, msg, **kwargs):
    #     # 其余逻辑...
    #     if 'progress' in kwargs:
    #         # 假设你的进度条控件名为 progress_bar
    #         try:
    #             progress = kwargs['progress']
    #             if hasattr(gui_main, "progress_bar") and gui_main.progress_bar is not None:
    #                 gui_main.progress_bar.setValue(progress)
    #         except Exception as e:
    #             print(f"[GUI] 更新进度条异常: {e}")

    # 可通过修改 start_gui 的签名，支持传递 signal_dynamic_map 或其他管道扩展参数
    gui_main.start_gui(analyze_log_and_generate_report)
    # 如果你的gui_main.start_gui暂不支持 run_analysis 参数，需在GUI代码自行调用 run_analysis_in_thread

    # # 如需直接命令行参数硬编码运行分析（此时无GUI，仍可用线程示例）
    # def print_callback(success, msg):
    #     print(f"[子线程回调] {msg}")
    # LOG_PATH = "data/chaos_log.csv"
    # OUTPUT_DIR = "output_result"
    # REPORT_TITLE = "台架自动化日志分析报告"
    # t = run_analysis_in_thread(log_csv_path=LOG_PATH, output_dir=OUTPUT_DIR, report_title=REPORT_TITLE, callback=print_callback, signal_dynamic_map=your_signal_map)
    # t.join()  # 等待分析线程结束