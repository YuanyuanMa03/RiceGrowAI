# RiceGrow-CH4: 水稻生长与甲烷排放模拟系统

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

基于 **RiceGrow** 过程型水稻生长模型 (Tang et al., 2009) 与 **CH4MOD** 甲烷排放模型 (Huang et al., 1998, 2004) 耦合的 Web 模拟系统。支持交互式多品种比较、水分管理评估和高级参数校准，服务于稻田 CH₄ 排放研究。

**在线演示**: [rice.mayuanyuan.top](https://rice.mayuanyuan.top)

**[English Documentation](README.md)**

---

## 概述

本系统耦合了两个成熟模型，用于模拟水稻生长动态并预测稻田甲烷排放：

- **RiceGrow** (Tang et al., 2009) — 过程型水稻生长模型，模拟物候发育、生物量积累、叶面积指数 (LAI)、分蘖动态和产量形成，是品种遗传特性、气象、土壤和管理措施的函数。

- **CH4MOD** (Huang et al., 1998, 2004) — 半经验型甲烷排放模型，预测稻田逐日 CH₄ 通量，由水稻生长输出（生物量、根系分泌物）、土壤氧化还原电位、有机质分解、温度和水分管理模式驱动。

### 主要功能

| 模块 | 说明 |
|------|------|
| **多品种比较** | 同时模拟最多 8 个水稻品种，进行生长与排放的对比分析 |
| **水分管理评估** | 5 种灌溉模式（淹水、间歇、湿润、控制、干湿交替）及其 CH₄ 影响评估 |
| **参数校准** | MCMC 贝叶斯推断、PSO 粒子群优化、PSO-MCMC 混合优化和多目标优化 |
| **敏感性分析** | Sobol 全局敏感性分析，识别关键品种参数 |
| **AI 智能辅助** | 多供应商 AI 集成，提供模拟指导和参数推荐 |
| **交互式可视化** | 基于 Plotly 的动态图表，展示生长曲线、CH₄ 排放趋势和对比分析 |

---

## 快速开始

### 前置要求

- Python 3.9+（推荐使用 Anaconda/Miniconda）

### 安装

```bash
# 克隆仓库
git clone https://github.com/YuanyuanMa03/RiceGrowAI.git
cd RiceGrowAI

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 数据准备

将以下 CSV 文件（GBK 编码）放置在 `data/` 目录下：

```
data/
├── 气象数据.csv            # 气象数据（最高温、最低温、辐射、降水量）
├── 调参数据.csv            # 田间参数（纬度、播种/移栽日期）
├── 品种参数.csv            # 品种参数（PS, TS, IE, PHI, PF 等）
├── 土壤数据.csv            # 土壤属性（pH、有机质、质地）
├── 施肥数据.csv            # 施肥数据
├── 秸秆数据.csv            # 秸秆还田数据
└── 管理数据_多种方案.csv    # 管理措施（种植密度、日期）
```

用户也可通过 Web 界面上传自定义数据文件。

### 运行应用

```bash
streamlit run app.py
```

访问 [http://localhost:8501](http://localhost:8501) 使用应用。

---

## 项目结构

```
RiceGrowAI/
├── app.py                      # Streamlit 主应用
├── config.py                   # 配置管理
├── session_manager.py          # 会话状态管理
├── ui_components.py            # 共享 UI 组件
│
├── models/                     # 核心科学模型
│   ├── Ricegrow_py_v1_0.py     # RiceGrow 水稻生长模型
│   └── RG2CH4.py               # CH4MOD-based CH₄ 排放耦合模型
│
├── calibration/                # 参数校准算法
│   ├── pymc_calibrator.py      # MCMC 贝叶斯推断
│   ├── pso_optimizer.py        # PSO 粒子群优化
│   ├── hybrid_optimizer.py     # PSO-MCMC 混合优化
│   ├── multi_objective.py      # 多目标优化
│   ├── sensitivity.py          # Sobol 全局敏感性分析
│   ├── priors.py               # 贝叶斯先验分布
│   └── constraints.py          # 参数约束
│
├── ai/                         # AI 功能
│   ├── client.py               # 多供应商 AI 客户端
│   ├── features/               # AI 功能模块
│   ├── prompts/                # AI 提示模板
│   └── ui/                     # AI UI 组件
│
├── core/                       # 核心业务逻辑
│   ├── data/loader.py          # 数据加载与编码
│   ├── simulation/             # 模拟服务层
│   └── exceptions.py           # 统一异常处理
│
├── pages/                      # Streamlit 多页面应用
│   ├── simulation_page.py      # 模拟页面
│   ├── calibration_page.py     # 校准页面
│   └── ai_page.py              # AI 助手页面
│
├── ui/                         # UI 组件
│   ├── sidebar.py              # 侧边栏导航
│   ├── results.py              # 结果展示
│   └── styles.py               # CSS 样式
│
├── data/                       # 数据文件（GBK 编码 CSV）
├── docs/                       # 文档
├── tests/                      # 单元测试
└── scripts/                    # 部署脚本
```

---

## 校准算法

| 算法 | 类型 | 说明 | 适用场景 |
|------|------|------|----------|
| **随机搜索** | 基线 | 简单稳定，无外部依赖 | 快速测试 |
| **差分进化** | 进化 | 快速收敛，高精度 | 精确校准 |
| **MCMC (PyMC)** | 贝叶斯 | 不确定性量化，后验分布 | 科学研究 |
| **PSO** | 群体智能 | 全局搜索能力强 | 复杂优化 |
| **PSO-MCMC** | 混合 | 两阶段：PSO 全局搜索 → MCMC 精细采样 | 高精度 + 不确定性 |
| **多目标优化** | 多目标 | 同时优化多个变量 | 综合决策 |
| **Sobol** | 敏感性 | 全局敏感性分析 (SALib) | 参数重要性排序 |

---

## 水分管理模式

系统支持 5 种灌溉模式，各模式对 CH₄ 排放有不同影响：

| 模式 | 灌溉方式 | CH₄ 排放水平 | 说明 |
|------|----------|-------------|------|
| 1 | 淹水灌溉 | 最高 | 全生育期持续淹水 |
| 2 | 间歇灌溉 | 中高 | 淹水与排水交替进行 |
| 3 | 湿润灌溉 | 中低 | 保持土壤湿润但不淹水 |
| 4 | 控制灌溉 | 中等 | 节水灌溉，控制水层深度 |
| 5 | 干湿交替 | 最低 | 定期晒田，CH₄ 减排效果最佳 |

---

## 部署

```bash
# 使用 Cloudflare Tunnel 生产部署
make deploy

# 服务管理
make start      # 启动服务
make stop       # 停止服务
make restart    # 重启服务
make status     # 查看服务状态
make logs       # 查看日志
```

应用运行在 8501 端口，通过 Cloudflare Tunnel 暴露到 [rice.mayuanyuan.top](https://rice.mayuanyuan.top)。

---

## 版本历史

### v3.0.0 (2026年4月)
- 多页面 Streamlit 架构
- 多供应商 AI 智能功能
- Cloudflare Tunnel 生产部署

### v2.5.0 (2026年3月)
- UI/UX 全面升级，现代绿色主题
- 多页面应用结构
- 增强交互式可视化

### v2.0.0 (2026年1月)
- 参数校准模块（MCMC、PSO、PSO-MCMC 混合）
- Sobol 全局敏感性分析
- 多目标优化
- 核心模块重构

### v1.0.0 (2025年12月)
- CH4MOD 耦合，实现 CH₄ 排放预测
- 多品种比较（最多 8 个品种）
- 5 种水分管理模式
- 交互式 Plotly 可视化

### v0.5.0 (2025年11月)
- 初始 Streamlit Web 界面
- 基本模拟工作流
- 数据文件管理

### v0.1.0 (2025年9月)
- 项目启动
- RiceGrow 模型 Python 移植
- 核心模拟流程

---

## 参考文献

1. Tang, L., Zhu, Y., Hannaway, D., Meng, Q., Liu, L., Chen, W., & Cao, W. (2009). RiceGrow: A rice growth and productivity model. *NJAS - Wageningen Journal of Life Sciences*, 57(1), 83–92. [DOI: 10.1016/j.njas.2009.12.004](https://doi.org/10.1016/j.njas.2009.12.004)

2. Huang, Y., Sass, R.L., & Fisher, F.M. (1998). A semi-empirical model of methane emission from irrigated rice fields in China. *Global Change Biology*, 4(8), 809–821. [DOI: 10.1046/j.1365-2486.1998.00186.x](https://doi.org/10.1046/j.1365-2486.1998.00186.x)

3. Huang, Y., Zhang, W., Zheng, X., Li, J., & Yu, Y. (2004). Modeling methane emission from rice paddies with various agricultural practices. *Journal of Geophysical Research: Atmospheres*, 109(D8), D08113. [DOI: 10.1029/2003JD004401](https://doi.org/10.1029/2003JD004401)

---

## 许可证

本项目基于 MIT 许可证。详见 [LICENSE](LICENSE)。

---

## 联系方式

- **作者**: 马源源 (Yuanyuan Ma)
- **GitHub**: [https://github.com/YuanyuanMa03](https://github.com/YuanyuanMa03)
- **仓库**: [https://github.com/YuanyuanMa03/RiceGrowAI](https://github.com/YuanyuanMa03/RiceGrowAI)
- **在线演示**: [https://rice.mayuanyuan.top](https://rice.mayuanyuan.top)

---

## 致谢

### 科学模型

- **RiceGrow** — 由南京农业大学 Tang L.（汤亮）、Zhu Y.（朱艳）、Cao W.（曹卫星）等开发。参考文献：Tang et al. (2009), *NJAS - Wageningen Journal of Life Sciences*, 57(1), 83–92.

- **CH4MOD** — 由中国科学院大气物理研究所 Huang Y.（黄耀）等开发。参考文献：Huang et al. (1998), *Global Change Biology*, 4(8), 809–821; Huang et al. (2004), *Journal of Geophysical Research: Atmospheres*, 109(D8), D08113.

### 技术栈

- [Streamlit](https://streamlit.io/) — Web 应用框架
- [Plotly](https://plotly.com/python/) — 交互式数据可视化
- [PyMC](https://www.pymc.io/) — 贝叶斯统计建模与 MCMC 采样
- [SALib](https://salib.readthedocs.io/) — 敏感性分析库（Sobol 方法）
- [NumPy](https://numpy.org/) & [Pandas](https://pandas.pydata.org/) — 科学计算与数据分析
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) — 安全隧道生产部署
