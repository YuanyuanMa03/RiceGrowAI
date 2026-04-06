# 校准系统参考内容速查表

## 📖 论文核心要点总结

---

## 论文1: 《RiceGrow系统安装与操作》

### 系统架构
```
RiceGrow/
├── RiceGrow.exe           # 主程序
├── 数据库/
│   ├── Weather/          # 气象数据 (.csv)
│   ├── Cultivar/         # 品种参数 (cultivar.csv)
│   ├── Soil/             # 土壤数据 (soil.csv)
│   ├── Management/       # 管理措施 (management.csv)
│   ├── Fertilizer/       # 施肥数据 (fertilizer.csv)
│   └── Residue/          # 秸秆数据 (residue.csv)
└── 输出/
    ├── 生育期.txt
    ├── 生物量.txt
    ├── LAI.txt
    ├── 产量.txt
    └── CH4.txt
```

### 24个品种参数完整列表

| 代码 | 含义 | 单位 | 范围 | 敏感性 |
|------|------|------|------|--------|
| **生育期参数** |
| PS | 光敏感性 | - | 0.02-0.08 | 高 |
| TS | 感温性 | °C⁻¹ | 2.5-3.2 | 高 |
| TO | 最适温度 | °C | 26-28 | 高 |
| IE | 基本早熟性 | - | 0.10-0.20 | 高 |
| HF | 高温因子 | - | 0.010-0.015 | 中 |
| FDF | 灌浆因子 | - | 0.688-0.727 | 高 |
| **光合参数** |
| SLAc | 比叶面积 | cm²/g | 184-207 | 高 |
| PF | 光合转化效率 | - | 0.0138-0.0161 | 高 |
| AMX | 最大光合速率 | - | 41-48 | 高 |
| KF | 消光系数 | - | 0.0072-0.0090 | 中 |
| **呼吸参数** |
| RGC | 生长呼吸系数 | - | 0.27-0.32 | 高 |
| LRS | 根系相对呼吸 | - | 0.0058-0.0075 | 低 |
| **形态参数** |
| TLN | 总叶龄 | - | 14.5-18.3 | 中 |
| EIN | 伸长节间数 | - | 4.6-5.5 | 中 |
| TA | 分蘖能力 | - | 0.42-0.52 | 中 |
| **产量参数** |
| PHI | 收获指数 | - | 0.427-0.480 | 高 |
| TGW | 千粒重 | g | 24.0-28.0 | 高 |
| SGP | 籽粒生长势 | - | 6.15-6.50 | 低 |
| **品质参数** |
| PC | 蛋白质含量 | % | 7.4-8.4 | 低 |
| **根系参数** |
| RAR | 根系吸收速率 | - | 1.92-2.36 | 低 |

---

## 论文2: 《RiceGrow模型品种参数不确定性研究》

### Sobol敏感性分析结果（ST总效应指数）

#### 高敏感参数 (ST > 0.1) - 8个
| 参数 | ST值 | 物理意义 |
|------|------|----------|
| PHI | 0.47 | 收获指数，最敏感 |
| TGW | 0.35 | 千粒重 |
| FDF | 0.28 | 灌浆因子 |
| SLAc | 0.22 | 比叶面积 |
| RGC | 0.18 | 生长呼吸系数 |
| PF | 0.15 | 光合转化效率 |
| AMX | 0.12 | 最大光合速率 |
| TS | 0.11 | 感温性 |

#### 中敏感参数 (0.01 < ST < 0.1) - 10个
PS, TO, IE, KF, TA, TLN, EIN, HF, HPC, PARC

#### 低敏感参数 (ST < 0.01) - 6个
LRS, SGP, PC, RAR, SLAT, PH

### 响应曲面方程

**1. PHI响应曲面**
```
PHI = 0.42 + 0.01×TLN + 0.3×PS + 0.05×TS
```
- 长生育期(TLN↑) + 高感光性(PS↑) → 高收获指数(PHI↑)
- 应用场景: 参数约束、先验调整

**2. TGW响应曲面**
```
TGW = 30 - 10×PHI
```
- 高收获指数 → 小粒重
- 负相关关系

### 分层校准策略

| 层次 | 参数 | 敏感性 | 校准方法 | MCMC采样数 |
|------|------|--------|----------|------------|
| 第一层 | 8个 | 高 | MCMC | 5000 |
| 第二层 | 10个 | 中 | MCMC | 2000 |
| 第三层 | 6个 | 低 | 固定文献值 | - |

---

## 论文3: 《不确定条件下作物生育期模型品种参数自动校正框架》

### PSO-MCMC混合算法流程

```
输入: 观测数据、模型runner、参数边界

┌─────────────────────────────────────┐
│  第一阶段: PSO全局搜索              │
├─────────────────────────────────────┤
│  粒子数: 50                         │
│  迭代次数: 200                      │
│  惯性权重: w = 0.9 → 0.4           │
│  学习因子: c1 = c2 = 2.0            │
│  收敛判定: 连续20代无改进           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  第二阶段: 自适应先验调整           │
├─────────────────────────────────────┤
│  μ = PSO最优解                      │
│  σ = PSO粒子标准差 × 0.1            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  第三阶段: MCMC精细采样             │
├─────────────────────────────────────┤
│  采样方法: NUTS                     │
│  样本数: 2000-5000                  │
│  Burn-in: 1000                      │
│  链数: 4                            │
│  目标接受率: 0.65                   │
└─────────────────────────────────────┘

输出: 参数后验分布、预测置信区间
```

### PSO算法关键公式

**速度更新**:
```
v_i(t+1) = w×v_i(t) + c1×r1×(pbest_i - x_i(t)) + c2×r2×(gbest - x_i(t))
```

**位置更新**:
```
x_i(t+1) = x_i(t) + v_i(t+1)
```

**参数说明**:
- `w`: 惯性权重 (0.4-0.9)，控制探索能力
- `c1, c2`: 学习因子 (通常=2.0)
- `r1, r2`: 随机数 [0,1]
- `pbest`: 粒子历史最优
- `gbest`: 全局最优

### 多目标优化

**目标函数**:
```
min: F = w1×E_dat + w2×E_yield + w3×E_biomass + w4×E_ch4

约束:
- E_dat < 5天
- E_yield < 15%
- 参数边界约束
- 响应曲面约束
```

**权重建议**:
```python
weights = {
    'dat': 0.2,      # 生育期
    'biomass': 0.3,  # 生物量
    'yield': 0.3,    # 产量
    'ch4': 0.2,      # CH4排放
}
```

### 并行计算策略

**MCMC并行**:
```python
# 方法1: 多链并行（推荐）
from multiprocessing import Pool

with Pool(4) as p:
    results = p.map(run_single_chain, [config]*4)

# 方法2: 粒子评估并行
for iteration in range(max_iter):
    with Pool(os.cpu_count()) as p:
        fitness = p.map(evaluate_particle, swarm)
```

**性能提升**:
- 4核: ~3.5x 加速
- 8核: ~6.5x 加速

---

## 🔧 技术实现要点

### 1. 参数约束优先级

**硬约束**（不可违反）:
```python
HARD_CONSTRAINTS = {
    'PHI': (0.30, 0.55),
    'TGW': (15, 40),
    'PS': (0, 0.1),
    'TS': (2.0, 4.0),
}
```

**软约束**（响应曲面）:
```python
def apply_soft_constraints(params):
    # PHI约束
    phi_range = get_phi_constraint(params)
    if 'PHI' in params:
        params['PHI'] = np.clip(params['PHI'], *phi_range)

    # TGW约束
    tgw_range = get_tgw_constraint(params)
    if 'TGW' in params:
        params['TGW'] = np.clip(params['TGW'], *tgw_range)

    return params
```

**先验约束**（贝叶斯）:
```python
PRIORS = {
    'PHI': TruncatedNormal(mu=0.455, sigma=0.016, lower=0.427, upper=0.480),
    'TGW': TruncatedNormal(mu=26.5, sigma=1.2, lower=24.0, upper=28.0),
}
```

### 2. MCMC采样建议

| 参数类型 | 建议采样数 | 建议链数 | 说明 |
|----------|------------|----------|------|
| 高敏感 | 5000 | 4 | 精细量化 |
| 中敏感 | 2000 | 4 | 适度量化 |
| 低敏感 | 固定值 | - | 文献值 |

### 3. 收敛诊断标准

```python
def check_convergence(trace):
    """检查MCMC收敛"""
    rhat = az.rhat(trace)
    ess = az.ess(trace)

    converged = all([
        rhat[param] < 1.05 for param in rhat
    ]) and all([
        ess[param] > 400 for param in ess
    ])

    return converged, {'rhat': rhat, 'ess': ess}
```

**标准**:
- R-hat < 1.05 (接近1)
- ESS > 400 (有效样本量)

### 4. 不确定性传播

```python
def monte_carlo_propagation(posterior, n_samples=1000):
    """蒙特卡洛不确定性传播"""

    # 1. 从后验采样
    param_samples = posterior.sample(n_samples)

    # 2. 运行模型
    predictions = [model_runner(p) for p in param_samples]

    # 3. 计算统计量
    mean = np.mean(predictions, axis=0)
    std = np.std(predictions, axis=0)
    ci_95 = np.percentile(predictions, [2.5, 97.5], axis=0)

    return {
        'mean': mean,
        'std': std,
        'ci_95': ci_95,
    }
```

---

## 📦 Python库依赖

```bash
# 必需
pip install numpy pandas pymc arviz salib plotly streamlit

# PSO优化
pip install pyswarms

# 并行计算
pip install dask[complete]  # 或 ray[default]

# 可视化
pip install seaborn matplotlib
```

---

## 🎯 快速参考

### 敏感性阈值
- **高敏感**: ST > 0.1
- **中敏感**: 0.01 < ST < 0.1
- **低敏感**: ST < 0.01

### MCMC采样建议
- **高敏感**: n_draws=5000, n_chains=4
- **中敏感**: n_draws=2000, n_chains=4
- **低敏感**: 固定文献值

### PSO参数
- **粒子数**: 50-100
- **迭代数**: 200
- **惯性权重**: w = 0.9 → 0.4
- **学习因子**: c1 = c2 = 2.0

### 收敛标准
- **R-hat** < 1.05
- **ESS** > 400

### 响应曲面
- **PHI** = f(TLN, PS, TS)
- **TGW** = g(PHI)

### 分层策略
- **第一层**: 高敏感参数，精细校准
- **第二层**: 中敏感参数，适度校准
- **第三层**: 低敏感参数，固定文献值
