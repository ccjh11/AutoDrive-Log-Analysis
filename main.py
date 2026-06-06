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

# 导入 output 层
from output import report_generator

# 导入 gui 层
from gui import gui_main

def analyze_log_and_generate_report(log_csv_path, output_dir="output_result", report_title="台架自动化日志分析报告", callback=None):
    """
    日志分析主流程：读取日志，清洗数据，规则引擎检测，输出HTML & Word报告
    增加callback回调通知主线程（GUI）任务结束
    """
    try:
        # 步骤1: 加载数据并清洗
        print(f"[主流程] 加载并清洗日志: {log_csv_path}")
        frames = data_processor.load_and_clean_log(log_csv_path)
        print(f"[主流程] 日志帧加载完成，共 {len(frames)} 条")

        # 步骤2: 自动化规则分析
        print(f"[主流程] 执行自动化规则检测...")
        engine = rule_engine.RuleEngine(frames)
        rules_report = engine.analyze()
        print(f"[主流程] 检测完成，发现异常 {len(rules_report)} 个")

        # 步骤3: 生成报告
        print(f"[主流程] 生成测试报告至 {output_dir}")
        report_generator.main(
            log_path=log_csv_path,
            report_title=report_title,
            output_dir=output_dir
        )
        print(f"[主流程] 日志分析与报告生成完毕！")
        if callback:
            callback(success=True, msg="分析与报告生成完毕")
    except Exception as e:
        print(f"[主流程] 分析异常: {e}")
        if callback:
            callback(success=False, msg=str(e))

def run_analysis_in_thread(log_csv_path, output_dir="output_result", report_title="台架自动化日志分析报告", callback=None):
    """
    在线程中运行分析逻辑，避免阻塞主线程（GUI）
    """
    thread = threading.Thread(target=analyze_log_and_generate_report, args=(log_csv_path, output_dir, report_title, callback))
    thread.setDaemon(True)  # 守护进程，主进程退出时子线程自动关闭
    thread.start()
    return thread

if __name__ == "__main__":
    # 主线程只负责GUI事件循环，实际分析在子线程
    # 需要gui_main这个模块支持异步log分析任务的触发（需在GUI层调用run_analysis_in_thread）
    from gui import gui_main

    # 直接把你的主流水线函数名塞进去！
    # （如果你在 main.py 里定义的主函数叫 analyze_log_and_generate_report，就填这个名字）
    gui_main.start_gui(analyze_log_and_generate_report)
    # 如果你的gui_main.start_gui暂不支持run_analysis参数，需在GUI代码自行调用run_analysis_in_thread

    # # 如需直接命令行参数硬编码运行分析（此时无GUI，仍可用线程示例）
    # def print_callback(success, msg):
    #     print(f"[子线程回调] {msg}")
    # LOG_PATH = "data/chaos_log.csv"
    # OUTPUT_DIR = "output_result"
    # REPORT_TITLE = "台架自动化日志分析报告"
    # t = run_analysis_in_thread(LOG_PATH, output_dir=OUTPUT_DIR, report_title=REPORT_TITLE, callback=print_callback)
    # t.join()  # 等待分析线程结束