# 水稻生长与CH4排放模拟系统

**Rice Growth & Methane Emission Simulation System**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

一个集成水稻生长模型（RiceGrow）与甲烷排放预测的专业农业模拟系统，提供Web界面进行品种对比、水管理方案评估和多种先进参数校准算法。

**在线演示**: https://rice.mayuanyuan.top

---

## 系统概述

本系统耦合了两个核心模型：

- **RiceGrow模型**: 模拟水稻生长过程（生物量积累、叶面积指数、产量形成等）
- **CH4排放模型**: 基于水稻生长输出预测稻田甲烷排放

### 主要功能

| 功能模块 | 描述 |
|---------|------|
| **品种对比** | 支持多品种同时模拟，对比生长表现和产量 |
| **水管理评估** | 5种灌溉模式对比，评估对产量和CH4排放的影响 |
| **参数校准** | MCMC贝叶斯、PSO粒子群、混合优化等先进算法 |
| **敏感性分析** | Sobol全局敏感性分析，识别关键参数 |
| **多目标优化** | 同时优化生物量、CH4、产量等多个目标 |
| **结果可视化** | 动态图表展示生长曲线、CH4排放趋势 |

---

## 快速开始

### 环境要求

- Python 3.9+
- 推荐使用 Anaconda 或 Miniconda

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/R_C_N.git
cd R_C_N

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt
```

### 准备数据

确保 `data/` 目录包含以下CSV文件（GBK编码）：

```
data/
├── 气象数据.csv
├── 调参数据.csv
├── 品种参数.csv
├── 土壤数据.csv
├── 施肥数据.csv
├── 秸秆数据.csv
└── 管理数据_多种方案.csv
```

### 运行应用

```bash
# 开发模式
streamlit run app.py

# 生产部署（使用脚本）
./scripts/start.sh
```

访问 http://localhost:8501

---

## 项目结构

```
R_C_N/
├── app.py                      # Streamlit主应用
├── config.py                   # 配置管理
├── ui_components.py            # UI组件库
├── session_manager.py          # 会话状态管理
│
├── core/                       # 核心业务逻辑 (NEW)
│   ├── data/
│   │   └── loader.py          # 统一数据加载
│   ├── simulation/
│   │   └── model_service.py   # 模型服务层
│   └── exceptions.py          # 统一异常处理
│
├── calibration_page.py         # 参数校准页面
├── calibration/               # 校准算法模块
│   ├── pymc_calibrator.py     # MCMC贝叶斯推断
│   ├── pso_optimizer.py       # PSO粒子群优化
│   ├── hybrid_optimizer.py    # PSO-MCMC混合优化
│   ├── multi_objective.py     # 多目标优化
│   ├── sensitivity.py         # Sobol敏感性分析
│   ├── metrics.py             # 评估指标
│   ├── visualization.py       # 可视化
│   ├── priors.py              # 先验分布
│   └── constraints.py         # 约束条件
│
├── models/                    # 作物模型
│   ├── Ricegrow_py_v1_0.py    # 水稻生长模型
│   └── RG2CH4.py              # CH4排放模型
│
├── data/                      # 数据文件
├── docs/                      # 文档
├── tests/                     # 测试代码 (NEW)
│   ├── unit/                  # 单元测试
│   └── fixtures/              # 测试数据
│
└── scripts/                   # 部署脚本
    ├── start.sh               # 启动服务
    ├── stop.sh                # 停止服务
    └── deploy.sh              # 部署配置
```

---

## 优化算法

| 算法 | 类型 | 说明 | 适用场景 |
|------|------|------|----------|
| **随机搜索** | 基础 | 简单稳定，无外部依赖 | 快速测试、初步探索 |
| **差分进化** | 高级 | 收敛快，精度高 | 精确校准 |
| **MCMC** | 贝叶斯 | 不确定性量化、后验分布 | 科学研究 |
| **PSO** | 群智能 | 全局搜索能力 | 复杂优化问题 |
| **PSO-MCMC** | 混合 | 两阶段优化 | 高精度+不确定性 |
| **多目标** | 多目标 | 同时优化多变量 | 综合决策 |
| **Sobol** | 敏感性 | 全局敏感性分析 | 参数重要性排序 |

---

## 技术架构

### 后端技术
- **语言**: Python 3.9+
- **Web框架**: Streamlit 1.28+
- **科学计算**: NumPy, Pandas
- **优化算法**: SALib, PyMC (可选)
- **可视化**: Plotly

### 核心模型
- **RiceGrow**: Python 1.0版本 (3183行)
- **CH4模型**: 耦合版本 (RG2CH4)

### 部署方案
- **内网穿透**: Cloudflare Tunnel
- **域名**: rice.mayuanyuan.top
- **端口**: 8501

---

## 开发指南

### 代码规范

项目遵循以下规范：
- **PEP 8**: Python代码风格
- **类型注解**: 使用 `typing` 模块
- **文档字符串**: Google风格docstring
- **日志**: 使用 `logging` 模块

### 测试

```bash
# 运行测试
pytest tests/

# 生成覆盖率报告
pytest --cov=. --cov-report=html
```

### 代码审查

```bash
# 代码格式化
black .
isort .

# 类型检查
mypy core/
```

---

## 常见问题

### Q1: 数据文件编码错误
**A**: 确保所有数据文件使用GBK编码。转换命令：
```bash
iconv -f UTF-8 -t GBK input.csv > output.csv
```

### Q2: 模拟结果异常
**A**: 检查以下项目：
- 气象数据日期范围是否完整
- 品种参数是否在合理范围
- 土壤参数是否正确

### Q3: 参数校准不收敛
**A**: 尝试以下方法：
- 增加迭代次数
- 检查观测数据质量
- 使用更宽松的参数边界
- 尝试混合优化算法

---

## 版本历史

### v2.0.0 (2024-01-13)
- ✨ 新增PSO粒子群优化
- ✨ 新增PSO-MCMC混合优化
- ✨ 新增多目标优化
- ✨ 新增Sobol敏感性分析
- 🏗️ 重构核心模块架构
- 🐛 修复图表显示问题
- 📝 完善项目文档
- ♻️ 代码优化和去重

### v1.5.0 (2023-12-01)
- 添加CH4排放耦合
- 支持多品种对比
- 改进UI组件

### v1.0.0 (2023-10-01)
- 初始版本
- 基础RiceGrow模拟

---

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 联系方式

- **作者**: Mayuanyuan
- **项目主页**: https://github.com/yourusername/R_C_N
- **在线演示**: https://rice.mayuanyuan.top

---

## 致谢

- RiceGrow模型原作者
- Streamlit团队
- PyMC和SALib社区
- 所有贡献者
