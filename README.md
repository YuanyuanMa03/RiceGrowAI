# RiceGrow-CH4: Rice Growth & Methane Emission Simulation System

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A web-based simulation system coupling the **RiceGrow** process-based rice growth model (Tang et al., 2009) with the **CH4MOD** methane emission model (Huang et al., 1998, 2004). It enables interactive multi-variety comparison, water management assessment, and advanced parameter calibration for rice paddy CH₄ emission research.

**Live Demo**: [rice.mayuanyuan.top](https://rice.mayuanyuan.top)

**[中文文档](README_CN.md)**

---

## Overview

This system couples two well-established models to simulate rice growth dynamics and predict methane emissions from paddy fields:

- **RiceGrow** (Tang et al., 2009) — A process-based rice growth model that simulates phenological development, biomass accumulation, leaf area index (LAI), tillering, and yield formation as functions of cultivar genetics, weather, soil, and management practices.

- **CH4MOD** (Huang et al., 1998, 2004) — A semi-empirical methane emission model that predicts daily CH₄ fluxes from rice paddies, driven by rice growth outputs (biomass, root exudates), soil redox potential, organic matter decomposition, temperature, and water management regime.

### Key Features

| Module | Description |
|--------|-------------|
| **Multi-Variety Comparison** | Simulate up to 8 rice cultivars simultaneously with side-by-side growth and emission analysis |
| **Water Management Assessment** | 5 irrigation regimes (continuous flooding, intermittent, wet, controlled, alternate wet-dry) with CH₄ impact evaluation |
| **Parameter Calibration** | MCMC Bayesian inference, PSO swarm optimization, PSO-MCMC hybrid, and multi-objective optimization |
| **Sensitivity Analysis** | Sobol global sensitivity analysis to identify key cultivar parameters |
| **AI-Powered Assistance** | Multi-provider AI integration for simulation guidance and parameter recommendations |
| **Interactive Visualization** | Dynamic Plotly charts for growth curves, CH₄ emission trends, and comparative analysis |

---

## Quick Start

### Prerequisites

- Python 3.9+ (Anaconda/Miniconda recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/YuanyuanMa03/RiceGrowAI.git
cd RiceGrowAI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Data Preparation

Place the following CSV files (GBK-encoded) in the `data/` directory:

```
data/
├── 气象数据.csv            # Weather data (Tmax, Tmin, radiation, precipitation)
├── 调参数据.csv            # Field parameters (latitude, sowing/transplant dates)
├── 品种参数.csv            # Cultivar parameters (PS, TS, IE, PHI, PF, etc.)
├── 土壤数据.csv            # Soil properties (pH, organic matter, texture)
├── 施肥数据.csv            # Fertilizer application data
├── 秸秆数据.csv            # Crop residue inputs
└── 管理数据_多种方案.csv    # Management practices (planting density, dates)
```

Users can also upload custom data files via the web interface.

### Run the Application

```bash
streamlit run app.py
```

Visit [http://localhost:8501](http://localhost:8501) to access the application.

---

## Project Structure

```
RiceGrowAI/
├── app.py                      # Streamlit main application
├── config.py                   # Configuration management
├── session_manager.py          # Session state management
├── ui_components.py            # Shared UI components
│
├── models/                     # Core scientific models
│   ├── Ricegrow_py_v1_0.py     # RiceGrow rice growth model
│   └── RG2CH4.py               # CH4MOD-based CH₄ emission coupling model
│
├── calibration/                # Parameter calibration algorithms
│   ├── pymc_calibrator.py      # MCMC Bayesian inference
│   ├── pso_optimizer.py        # PSO particle swarm optimization
│   ├── hybrid_optimizer.py     # PSO-MCMC hybrid optimization
│   ├── multi_objective.py      # Multi-objective optimization
│   ├── sensitivity.py          # Sobol global sensitivity analysis
│   ├── priors.py               # Bayesian prior distributions
│   └── constraints.py          # Parameter constraints
│
├── ai/                         # AI-powered features
│   ├── client.py               # Multi-provider AI client
│   ├── features/               # AI feature modules
│   ├── prompts/                # AI prompt templates
│   └── ui/                     # AI UI components
│
├── core/                       # Core business logic
│   ├── data/loader.py          # Data loading & encoding
│   ├── simulation/             # Simulation service layer
│   └── exceptions.py           # Unified exception handling
│
├── pages/                      # Streamlit multi-page app
│   ├── simulation_page.py      # Simulation page
│   ├── calibration_page.py     # Calibration page
│   └── ai_page.py              # AI assistant page
│
├── ui/                         # UI components
│   ├── sidebar.py              # Sidebar navigation
│   ├── results.py              # Result display
│   └── styles.py               # CSS styling
│
├── data/                       # Data files (GBK-encoded CSVs)
├── docs/                       # Documentation
├── tests/                      # Unit tests
└── scripts/                    # Deployment scripts
```

---

## Calibration Algorithms

| Algorithm | Type | Description | Use Case |
|-----------|------|-------------|----------|
| **Random Search** | Baseline | Simple, stable, no external dependencies | Quick testing |
| **Differential Evolution** | Evolutionary | Fast convergence, high precision | Precise calibration |
| **MCMC (PyMC)** | Bayesian | Uncertainty quantification, posterior distributions | Scientific research |
| **PSO** | Swarm Intelligence | Strong global search capability | Complex optimization |
| **PSO-MCMC** | Hybrid | Two-stage: PSO global search → MCMC refinement | High-precision + uncertainty |
| **Multi-Objective** | Multi-objective | Simultaneous optimization of multiple variables | Comprehensive decision-making |
| **Sobol** | Sensitivity | Global sensitivity analysis (SALib) | Parameter importance ranking |

---

## Water Management Regimes

The system supports 5 irrigation regimes, each with distinct effects on CH₄ emissions:

| Mode | Regime | CH₄ Level | Description |
|------|--------|-----------|-------------|
| 1 | Continuous Flooding | Highest | Fields kept flooded throughout the season |
| 2 | Intermittent Irrigation | Medium-High | Alternating flooded and drained periods |
| 3 | Wet Irrigation | Medium-Low | Maintaining moist but not flooded soil |
| 4 | Controlled Irrigation | Medium | Water-saving irrigation with controlled depth |
| 5 | Alternate Wet-Dry | Lowest | Regular drying cycles, most CH₄ reduction |

---

## Deployment

```bash
# Production deployment with Cloudflare Tunnel
make deploy

# Service management
make start      # Start services
make stop       # Stop services
make restart    # Restart services
make status     # Check service status
make logs       # View logs
```

The application runs on port 8501 and is exposed via Cloudflare Tunnel to [rice.mayuanyuan.top](https://rice.mayuanyuan.top).

---

## Version History

### v3.0.0 (Apr 2026)
- Multi-page Streamlit architecture
- AI-powered features with multi-provider support
- Production deployment with Cloudflare Tunnel

### v2.5.0 (Mar 2026)
- UI/UX overhaul with modern green theme
- Multi-page application structure
- Enhanced interactive visualizations

### v2.0.0 (Jan 2026)
- Parameter calibration module (MCMC, PSO, PSO-MCMC hybrid)
- Sobol global sensitivity analysis
- Multi-objective optimization
- Core module refactoring

### v1.0.0 (Dec 2025)
- CH4MOD coupling for CH₄ emission prediction
- Multi-variety comparison (up to 8 cultivars)
- 5 water management regimes
- Interactive Plotly visualizations

### v0.5.0 (Nov 2025)
- Initial Streamlit web interface
- Basic simulation workflow
- Data file management

### v0.1.0 (Sep 2025)
- Project initiation
- RiceGrow model ported to Python
- Core simulation pipeline

---

## References

1. Tang, L., Zhu, Y., Hannaway, D., Meng, Q., Liu, L., Chen, W., & Cao, W. (2009). RiceGrow: A rice growth and productivity model. *NJAS - Wageningen Journal of Life Sciences*, 57(1), 83–92. [DOI: 10.1016/j.njas.2009.12.004](https://doi.org/10.1016/j.njas.2009.12.004)

2. Huang, Y., Sass, R.L., & Fisher, F.M. (1998). A semi-empirical model of methane emission from irrigated rice fields in China. *Global Change Biology*, 4(8), 809–821. [DOI: 10.1046/j.1365-2486.1998.00186.x](https://doi.org/10.1046/j.1365-2486.1998.00186.x)

3. Huang, Y., Zhang, W., Zheng, X., Li, J., & Yu, Y. (2004). Modeling methane emission from rice paddies with various agricultural practices. *Journal of Geophysical Research: Atmospheres*, 109(D8), D08113. [DOI: 10.1029/2003JD004401](https://doi.org/10.1029/2003JD004401)

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Contact

- **Author**: Yuanyuan Ma
- **GitHub**: [https://github.com/YuanyuanMa03](https://github.com/YuanyuanMa03)
- **Repository**: [https://github.com/YuanyuanMa03/RiceGrowAI](https://github.com/YuanyuanMa03/RiceGrowAI)
- **Live Demo**: [https://rice.mayuanyuan.top](https://rice.mayuanyuan.top)

---

## Acknowledgments

### Scientific Models

- **RiceGrow** — Developed by Tang L., Zhu Y., Cao W. et al. at Nanjing Agricultural University. Reference: Tang et al. (2009), *NJAS - Wageningen Journal of Life Sciences*, 57(1), 83–92.

- **CH4MOD** — Developed by Huang Y. et al. at the Institute of Atmospheric Physics, Chinese Academy of Sciences. References: Huang et al. (1998), *Global Change Biology*, 4(8), 809–821; Huang et al. (2004), *Journal of Geophysical Research: Atmospheres*, 109(D8), D08113.

### Technologies

- [Streamlit](https://streamlit.io/) — Web application framework
- [Plotly](https://plotly.com/python/) — Interactive data visualization
- [PyMC](https://www.pymc.io/) — Bayesian statistical modeling and MCMC sampling
- [SALib](https://salib.readthedocs.io/) — Sensitivity analysis library (Sobol method)
- [NumPy](https://numpy.org/) & [Pandas](https://pandas.pydata.org/) — Scientific computing and data analysis
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) — Secure tunnel for production deployment
