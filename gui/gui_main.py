import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os

def start_gui(pipeline_func):
    import sys
    import time
    # 如果是在打包的exe中，修正工作路径
    if getattr(sys, 'frozen', False):
        os.chdir(sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.getcwd())

    # 动态import防止循环依赖
    import_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output', 'report_generator.py'))
    if os.path.exists(import_path):
        import importlib.util
        spec = importlib.util.spec_from_file_location('report_generator', import_path)
        report_generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(report_generator)
    else:
        messagebox.showerror("错误", "未找到 report_generator.py！")
        return

    root = tk.Tk()
    root.title("自动日志分析系统 - GUI")
    root.geometry('520x270')
    root.resizable(False, False)
    
    # 用一个对象window来存储一些全局状态，如选定的文件
    class WindowState:
        def __init__(self):
            self.selected_file = ""
    window = WindowState()

    log_path_var = tk.StringVar()
    report_name_var = tk.StringVar(value="台架自动化日志分析报告")
    output_dir_var = tk.StringVar(value="output_result")

    def select_log_file():
        path = filedialog.askopenfilename(
            title='选择日志csv文件',
            filetypes=[('CSV文件', '*.csv'), ('所有文件', '*.*')]
        )
        if path:
            log_path_var.set(path)
            log_file_label.config(text=os.path.basename(path))
            window.selected_file = path  # 保存选中的文件路径

    def select_output_dir():
        path = filedialog.askdirectory(title='选择报告输出目录')
        if path:
            output_dir_var.set(path)
            output_label.config(text=path)

    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(root, maximum=100, variable=progress_var, length=400)
    progress_label = tk.Label(root, text="进度: 0%")

    def show_progress(p):
        progress_var.set(p)
        progress_label.config(text=f"进度: {int(p)}%")
        root.update_idletasks()

    def run_analysis_thread():
        if not log_path_var.get():
            messagebox.showerror("错误", "请先选择日志文件！")
            return

        def analysis_task():
            try:
                show_progress(0)
                # 0-20%: 加载
                time.sleep(0.2)
                show_progress(10)
                log_path = log_path_var.get()
                report_title = report_name_var.get()
                output_dir = output_dir_var.get()
                # 20-30%: 加载日志（粗略估算）
                show_progress(20)
                # 把界面选好的文件路径传给流水线去跑
                pipeline_func(window.selected_file)
                # 30-85%: 报告生成
                report_generator.main(
                    log_path=log_path,
                    report_title=report_title,
                    output_dir=output_dir
                )
                show_progress(100)
                messagebox.showinfo("完成", f"报告生成成功！\nHTML: {os.path.join(output_dir, 'report.html')}\nWord: {os.path.join(output_dir, 'report.docx')}")
            except Exception as e:
                show_progress(0)
                messagebox.showerror("分析失败", f"发生异常：{str(e)}")

        threading.Thread(target=analysis_task, daemon=True).start()

    # --- GUI构建 ---
    frm = tk.Frame(root, padx=20, pady=10)
    frm.pack()

    # 1. 日志选择
    tk.Label(frm, text="1. 选择日志csv文件：").grid(row=0, column=0, sticky="w")
    tk.Button(frm, text="选择文件", command=select_log_file).grid(row=0, column=1)
    log_file_label = tk.Label(frm, text="", width=32, anchor="w", foreground="#555")
    log_file_label.grid(row=0, column=2, padx=(5,0))

    # 2. 报告名称
    tk.Label(frm, text="2. 输入报告名称：").grid(row=1, column=0, sticky="w")
    name_entry = tk.Entry(frm, textvariable=report_name_var, width=34)
    name_entry.grid(row=1, column=1, columnspan=2, sticky="w")

    # 3. 输出目录
    tk.Label(frm, text="3. 选择输出目录：").grid(row=2, column=0, sticky="w")
    tk.Button(frm, text="选择目录", command=select_output_dir).grid(row=2, column=1, sticky="w")
    output_label = tk.Label(frm, text=output_dir_var.get(), width=32, anchor="w", foreground="#555")
    output_label.grid(row=2, column=2, padx=(5,0))

    # 4. 分析按钮
    analyze_btn = tk.Button(frm, text="开始分析并生成报告", bg="#228B22", fg='white', height=2, font=("微软雅黑", 12), width=25, command=run_analysis_thread)
    analyze_btn.grid(row=3, column=0, columnspan=3, pady=(16,2))

    # 5. 进度条
    progress_bar.pack(pady=(5, 0))
    progress_label.pack()

    root.mainloop()

if __name__ == "__main__":
    def dummy_pipeline(path):
        # 可替换为真实流水线逻辑
        print(f"Pipeline received: {path}")
    start_gui(dummy_pipeline)