import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os

def start_gui(pipeline_func):
    import sys
    # 如果是在打包的exe中，修正工作路径
    if getattr(sys, 'frozen', False):
        os.chdir(sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.getcwd())

    root = tk.Tk()
    root.title("自动日志分析系统 - GUI")
    root.geometry('520x270')
    root.resizable(False, False)

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

        log_csv_path = log_path_var.get()
        report_title = report_name_var.get()
        output_dir = output_dir_var.get()

        # 修改：on_analysis_done 支持 **kwargs，且确保进度条完整走到100%（彻底完善）
        def on_analysis_done(success, msg, **kwargs):
            def update_ui():
                if success:
                    # 不论是否主流程传了progress，都手动拉满进度条
                    progress_var.set(100)
                    progress_bar['value'] = 100
                    progress_label.config(text="进度: 100%")
                    root.update_idletasks()
                    messagebox.showinfo(
                        "完成",
                        f"报告生成成功！\nHTML: {os.path.join(output_dir, 'report.html')}\n"
                        f"Word: {os.path.join(output_dir, 'report.docx')}"
                    )
                else:
                    # 失败则归零
                    progress_var.set(0)
                    progress_bar['value'] = 0
                    progress_label.config(text="进度: 0%")
                    root.update_idletasks()
                    messagebox.showerror("分析失败", f"发生异常：{msg}")
            root.after(0, update_ui)

        def analysis_task():
            show_progress(10)
            pipeline_func(
                log_csv_path=log_csv_path,
                output_dir=output_dir,
                report_title=report_title,
                callback=on_analysis_done,
            )
            show_progress(100)

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
    def dummy_pipeline(log_csv_path, output_dir, report_title, callback, signal_dynamic_map=None):
        print(f"Pipeline received: {log_csv_path}")
        if callback:
            callback(success=True, msg="dummy done")
    start_gui(dummy_pipeline)
