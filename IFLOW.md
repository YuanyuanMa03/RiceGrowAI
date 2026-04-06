# 水稻生长与CH4排放模拟系统 - 项目文档

## 项目概述

这是一个基于 Streamlit 的水稻生长与甲烷排放模拟系统，用于农业科研和精准农业应用。系统通过模拟不同水稻品种的生长过程和甲烷排放量，帮助研究人员和农业工作者进行品种对比和优化决策。

### 主要功能
- 🌱 多品种水稻生长模拟
- 💨 甲烷排放量预测
- 📊 数据可视化与对比分析
- ⚙️ 多种灌溉模式配置
- 🏜️ 土壤参数自定义
- 📁 自定义数据文件上传

### 技术栈
- **UI框架**: Streamlit >= 1.28.0
- **数据处理**: Pandas >= 1.5.0
- **数据可视化**: Plotly >= 5.15.0
- **数值计算**: NumPy >= 1.21.0
- **Excel处理**: OpenPyXL >= 3.0.0
- **Python版本**: 3.13

## 项目结构

```
R_C_N/
├── app.py                    # 主应用文件（Streamlit应用入口）
├── config.py                 # 配置模块（常量、路径、错误消息）
├── session_manager.py        # Session State管理模块
├── ui_components.py          # 可复用UI组件模块
│
├── models/                   # 模型目录
│   ├── RG2CH4.py            # CH4排放模型
│   └── Ricegrow_py_v1_0.py  # 水稻生长模型
│
├── data/                     # 数据文件目录
│   ├── 调参数据.csv
│   ├── 气象数据.csv
│   ├── 土壤数据.csv
│   ├── 秸秆数据.csv
│   ├── 管理数据_多种方案.csv
│   ├── 施肥数据.csv
│   └── 品种参数.csv
│
├── docs/                     # 文档目录
│   ├── QUICKSTART.md        # 快速开始指南
│   ├── DESIGN_DOCUMENTATION.md  # 设计文档
│   ├── DEPLOYMENT.md        # 部署文档
│   ├── TESTING_REPORT.md    # 测试报告
│   └── README_TUNNEL.md     # Cloudflare Tunnel配置
│
├── tests/                    # 测试目录
│   ├── test_config.py       # 配置模块测试
│   ├── test_session_manager.py  # Session管理测试
│   └── test_ui_components.py    # UI组件测试
│
├── scripts/                  # 脚本目录
│   ├── start.sh             # 启动脚本
│   ├── stop.sh              # 停止脚本
│   ├── deploy.sh            # 部署脚本
│   └── quick-start.sh       # 快速启动脚本
│
├── uploads/                  # 用户上传文件目录
├── logs/                     # 日志目录
└── BatchTemplate/            # 批处理模板目录
```

## 构建和运行

### 环境准备

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装开发依赖（可选）
pip install -r requirements-dev.txt

# 3. 确保Python版本 >= 3.13
python3 --version
```

### 运行应用

```bash
# 方式1: 直接运行
streamlit run app.py

# 方式2: 使用快速启动脚本
./scripts/quick-start.sh

# 方式3: 使用start脚本
./scripts/start.sh
```

应用将在 `http://localhost:8501` 启动。

### 测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=. --cov-report=html

# 运行特定测试文件
pytest tests/test_config.py

# 运行特定标记的测试
pytest -m unit  # 单元测试
pytest -m integration  # 集成测试
```

### 代码质量检查

```bash
# 代码格式化
black app.py config.py session_manager.py ui_components.py

# 导入排序
isort app.py config.py session_manager.py ui_components.py

# 代码检查
flake8 app.py config.py session_manager.py ui_components.py

# 类型检查
mypy app.py config.py session_manager.py ui_components.py
```

### 部署

```bash
# 使用部署脚本
./scripts/deploy.sh

# 或使用快速开始指南中的命令
# 详见 docs/QUICKSTART.md
```

## 开发规范

### 代码风格
- **格式化**: Black (line-length=100, target-version=py313)
- **导入排序**: isort (black profile)
- **类型注解**: 鼓励使用类型注解，mypy检查
- **文档字符串**: 使用Google风格或NumPy风格

### 模块化设计
- `config.py`: 集中管理所有配置常量、路径和魔术数字
- `session_manager.py`: 管理Streamlit Session State，防止内存泄漏
- `ui_components.py`: 可复用的Streamlit UI组件

### 错误处理
- 使用自定义异常类（在config.py中定义）:
  - `RiceSimulationError`: 基础异常类
  - `FileReadError`: 文件读取错误
  - `EncodingError`: 编码错误
  - `ValidationError`: 验证错误
  - `SimulationError`: 模拟运行错误

### 日志记录
- 使用logging模块，配置在config.py中
- 日志文件保存在 `logs/` 目录
- 文件日志级别: DEBUG
- 控制台日志级别: WARNING

### 文件编码
- 读取文件时自动尝试多种编码: `['utf-8', 'gbk', 'gb2312', 'gb18030', 'utf-8-sig', 'latin1']`
- 默认写入编码: 'gbk'

### 测试规范
- 测试文件命名: `test_*.py`
- 测试函数命名: `test_*`
- 测试类命名: `Test*`
- 使用pytest标记: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`

## 核心模块说明

### config.py
集中管理所有配置常量、路径和魔术数字，包括：
- 项目路径配置
- 文件名常量和映射
- 编码配置
- 灌溉模式常量
- 模拟常量
- UI常量
- 错误消息
- 自定义异常类
- 日志配置函数

### session_manager.py
管理Streamlit Session State的生命周期，防止内存泄漏：
- `init_session_state()`: 初始化session state
- `get_session_state()`: 安全获取session state值
- `set_session_state()`: 安全设置session state值
- `clear_session_state()`: 清理指定的session state键
- `cleanup_after_simulation()`: 模拟完成后清理临时数据
- `validate_session_state()`: 验证session state的完整性

### ui_components.py
可复用的Streamlit UI组件：
- `render_sidebar_header()`: 渲染侧边栏头部
- `render_variety_selector()`: 渲染品种选择组件
- `render_variety_feedback()`: 渲染品种选择反馈
- `render_water_regime_selector()`: 渲染水分管理选择器
- `render_soil_parameter_sliders()`: 渲染土壤参数滑块
- `render_run_button()`: 渲染运行模拟按钮
- `render_results_header()`: 渲染结果展示头部
- `create_comparison_chart()`: 创建对比图表
- `create_timeseries_chart()`: 创建时间序列图表

### app.py
主应用文件，包含：
- Streamlit页面配置
- 现代化CSS样式（绿色主题）
- 文件读取工具（支持多种编码）
- 临时文件管理工具
- 文件上传验证工具
- 主界面逻辑

### models/
- `RG2CH4.py`: CH4排放模型
- `Ricegrow_py_v1_0.py`: 水稻生长模型

## 数据文件说明

### 必需的数据文件
系统需要以下数据文件才能正常运行：
- `调参数据.csv`: 调节参数数据
- `气象数据.csv`: 气象数据（包含温度、降雨、太阳辐射等）
- `土壤数据.csv`: 土壤特性数据
- `秸秆数据.csv`: 秸秆数据
- `管理数据_多种方案.csv`: 多种管理方案数据
- `施肥数据.csv`: 施肥数据
- `品种参数.csv`: 品种参数数据

### 数据文件格式
所有数据文件应为CSV格式，支持多种编码（utf-8, gbk, gb2312等）。

## 配置说明

### pyproject.toml
项目配置文件，包含：
- Black配置（代码格式化）
- isort配置（导入排序）
- mypy配置（类型检查）
- pytest配置（测试框架）
- coverage配置（代码覆盖率）

### .pre-commit-config.yaml
预提交钩子配置，确保代码质量。

### .mypy.ini
mypy类型检查配置。

### pytest.ini
pytest测试框架配置。

## 常见问题

### Q: 如何添加新的水稻品种？
A: 可以通过界面的"自定义品种参数"功能手动添加，或编辑`data/品种参数.csv`文件。

### Q: 支持哪些灌溉模式？
A: 支持5种灌溉模式：
1. 淹水灌溉（最高CH4排放）
2. 间歇灌溉（中高CH4排放）
3. 湿润灌溉（中低CH4排放）
4. 控制灌溉（中等CH4排放）
5. 干湿交替（最低CH4排放，最高效率）

### Q: 如何自定义数据文件？
A: 可以在界面上传自定义的CSV文件，系统会自动验证文件格式和编码。

### Q: 模拟结果保存在哪里？
A: 模拟结果保存在`uploads/`目录，可以下载CSV格式的结果文件。

### Q: 如何查看日志？
A: 日志文件保存在`logs/`目录，文件名格式为`app_YYYYMMDD.log`。

## 相关文档

- [快速开始指南](docs/QUICKSTART.md)
- [设计文档](docs/DESIGN_DOCUMENTATION.md)
- [部署文档](docs/DEPLOYMENT.md)
- [测试报告](docs/TESTING_REPORT.md)
- [Cloudflare Tunnel配置](docs/README_TUNNEL.md)

## 版本信息

- **应用名称**: 水稻生长与CH4排放模拟系统
- **版本**: 2.0.0
- **作者**: Rice Simulation Team
- **Python版本**: 3.13+

## 许可证

本项目仅供科研和教育使用。