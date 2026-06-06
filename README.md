Markdown
# 智驾台架自动化日志分析与 HIL 故障注入系统

本项目是一款专为汽车电子台架及自动驾驶测试设计的工业级自动化日志分析中台。系统支持多源日志输入（标准宽表及 CAN 原始长表报文），具备插拔式 Pipeline 数据解析管线、高仿真 HIL 故障注入引擎、全自动化规则诊断大脑以及多格式（HTML/Word）可视化测试报告生成功能。

## 🚀 核心亮点

- **全链路插拔式架构**：业务逻辑、底层解析、高层界面及报告渲染彻底解耦。
- **CAN 原始长表高效对齐**：自主开发 CAN 原始长表解析中台，完美解决乱序报文的多信号重采样、时间戳对齐及向前填充（ffill）难题。
- **HIL 故障注入靶场**：支持在仿真流中动态注入**传感器信号跳变**、**通信超时信号丢失（NaN）**等典型故障。
- **多线程守护前端**：基于 Tkinter 打造直观 GUI，采用高效的多线程及回调机制，确保界面丝滑不卡顿。
- **现代工程保障**：全套 Pytest 单元测试质量护航，守住代码重构底线。

---

## 🏗️ 项目架构图

```mermaid
graph TD
    A[输入: 原始长表/故障日志] --> B[核心调度: main.py]
    B --> C[解析中台: can_parser]
    C --> D[宽表 DataFrame]
    D --> E[诊断大脑: rule_engine]
    E --> F[生成报告: report_generator]
    B <--> G[前端界面: gui_main]
    ```
    ---
⏱️ 核心业务时序图 (Sequence Diagram)
以下展现了用户点击“开始分析”后，数据从长表提炼、规则洗礼、再到通知 GUI 进度拉满的全生命周期异步时序：

```mermaid
sequenceDiagram
    autonumber
    actor User as 测试工程师
    participant GUI as gui_main (前端界面)
    participant Main as main.py (全管线调度)
    participant Parser as can_parser (解析中台)
    participant Engine as rule_engine (诊断大脑)
    participant Gen as report_generator (报告模块)

    User->>GUI: 选择日志并点击【开始分析并生成报告】
    GUI->>GUI: 进度条设为 10%, 启动后台子线程 analysis_task
    Note over GUI,Main: 异步多线程防止界面卡死
    GUI->>Main: 调用 analyze_log_and_generate_report()
    Main->>Parser: pd.read_csv() 读入原始长表数据
    Main->>Parser: parse_can_raw_long_table() 对齐与重采样
    Parser-->>Main: 返回物理值宽表 DataFrame (契约数据)
    Main->>Engine: 初始化 RuleEngine(frames) 并执行 analyze()
    Note over Engine: 激活HIL故障诊断算法 (差分跳变/NaN超时)
    Engine-->>Main: 返回诊断出的异常报告列表
    Main->>Gen: 传入变量进行数据渲染，严禁重读硬盘文件
    Gen->>Gen: 画图并落盘输出 report.html & report.docx
    Main->>GUI: 回调通知 on_analysis_done(success=True)
    GUI->>GUI: 拦截信号, 进度条秒变 100%, 弹出成功弹窗
    GUI-->>User: 完美展现报告生成成功喜报！
📂 项目目录结构说明
Plaintext
自动日志分析系统/
├── core/                       # 🧠 核心算法层
│   ├── __init__.py
│   ├── can_parser.py           # CAN 总线原始日志高精度重采样与时间对齐中台
│   ├── data_processor.py       # 老旧款标准宽表加载器（已解耦兼容）
│   └── rule_engine.py          # 诊断大脑（集成HIL传感器跳变与超时丢失检测规则）
├── data/                       # 📊 数据仓储
│   ├── chaos_can_raw_log.csv   # 仿真 CAN 总线原始长表日志
│   └── massive_chaos_fault_injection.csv # 注入突变、空值的故障注入日志
├── gui/                        # 🎨 界面皮囊层
│   └── gui_main.py             # Tkinter 前端（多线程异步调度与回调控制中心）
├── output/                     # 📄 输出渲染层
│   └── report_generator.py     # 报告生成器
├── tests/                      # 🚀 单元测试护航层
│   └── test_can_parser.py      # Pytest 自动化测试用例
├── generate_mock_data.py       # 🧪 混沌数据流与 HIL 故障注入靶场生成脚本
└── main.py                     # 🎛️ 项目主干与总调度控台入口
💻 GUI 界面展示(gui_screenshot.png)

🛠️ 快速开始
1. 环境准备
确保你的本地环境安装了 Python 3.8+，并执行以下命令极速安装核心依赖库：

Bash
pip install pandas matplotlib python-docx pytest
2. 启动故障注入靶场（可选）
如果你想重新生成干净的模拟数据或带毒的故障测试文件，可直接运行假数据生成器：

Bash
python generate_mock_data.py
运行后将在 data/ 目录下安全导出 chaos_can_raw_log.csv 和 massive_chaos_fault_injection.csv。

3. 运行单元测试质量守底
在开发或修改底层解析逻辑后，一键运行 Pytest 护航单元测试：

Bash
python -m pytest tests/test_can_parser.py -v
4. 启动 GUI 全链路分析
双击运行或在控制台键入以下命令打开主界面：

Bash
python main.py
操作指南：

点击“选择文件”，选择 data/massive_chaos_fault_injection.csv。

点击“开始分析并生成报告”。

见证进度条丝滑冲到 100%，并在 output_result/ 下查看最终的 report.html 与 report.docx 报告！

🛡️ HIL 故障注入实验规范
系统通过 generate_mock_data.py 和 rule_engine.py 的闭环，支持以下 HIL 测试用例：

故障类型	注入机制 (Injection)	诊断规则 (Diagnostic)	预期结果
跳变异常 (突变)	在稳定车速流中突然强插一帧 300 km/h 的极端突变值	利用 .diff() 检查相邻帧车速突变绝对值 >50	精准捕获突变时间戳，写入报告并标记传感器异常
信号丢失 (超时)	故意截断连续数帧的核心信号报文，使其在宽表中表现为 NaN	利用 .isna() 检查关键信号的连续空值率	抓获超时丢失帧，触发诊断降级通报

---