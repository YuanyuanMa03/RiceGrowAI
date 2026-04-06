# 水稻模型参数校准系统改进计划

## 📚 基于三篇核心论文的分析

### 论文清单

1. **《RiceGrow系统安装与操作》** - 系统架构与参数体系
2. **《RiceGrow模型品种参数不确定性研究》** - Sobol敏感性分析与分层校准
3. **《不确定条件下作物生育期模型品种参数自动校正框架》** - PSO+MCMC混合算法

---

## 🔍 当前系统诊断

### 现有优势
✅ 已实现MCMC贝叶斯校准（PyMC）
✅ 已实现多种优化算法（随机搜索、差分进化）
✅ 已实现统计指标评估（R², RMSE, NSE等）
✅ 已实现可视化对比（时间序列、1:1散点图）
✅ 已定义参数先验分布（基于28个品种统计）

### 现有不足
❌ 缺少参数敏感性分析工具
❌ 缺少多目标优化（只考虑单一误差函数）
❌ 缺少并行计算支持
❌ 缺少PSO粒子群优化算法
❌ 缺少响应曲面约束
❌ 缺少参数不确定性传播分析

---

## 🎯 改进计划（分阶段实施）

## 第一阶段：参数敏感性分析模块（P0 - 立即实施）

### 目标
实现Sobol全局敏感性分析，识别关键参数

### 具体任务

#### 1.1 完善Sobol敏感性分析功能
- [x] 已创建 `calibration/sensitivity.py` 基础模块
- [ ] 集成到Web UI（敏感性分析页面）
- [ ] 添加敏感性结果可视化（热力图、龙卷风图）
- [ ] 支持多个目标变量的敏感性分析（产量、生物量、CH4）

#### 1.2 参数分组优化
- [x] 已基于论文实现 `get_layered_calibration_strategy()`
- [ ] 在UI中显示参数敏感性标记（⭐⭐⭐）
- [ ] 自动建议校准策略（高敏感→精细校准，低敏感→固定值）

### 技术要点
```python
# 敏感性阈值（基于论文2）
ST_HIGH_THRESHOLD = 0.1    # 高敏感：ST > 0.1
ST_LOW_THRESHOLD = 0.01    # 低敏感：ST < 0.01

# 高敏感参数（8个）
HIGH_SENSITIVITY = ['PHI', 'TGW', 'FDF', 'SLAc', 'RGC', 'PF', 'AMX', 'TS']
```

---

## 第二阶段：混合优化算法（P1 - 短期实施）

### 目标
实现PSO+MCMC混合算法，结合全局搜索和贝叶斯推断

### 具体任务

#### 2.1 实现PSO粒子群优化
- [ ] 创建 `calibration/pso_optimizer.py`
- [ ] 实现标准PSO算法
- [ ] 实现自适应PSO（APSO）
- [ ] 支持多目标优化（Pareto前沿）

#### 2.2 实现PSO-MCMC混合算法
- [ ] 创建 `calibration/hybrid_optimizer.py`
- [ ] 第一阶段：PSO全局搜索（快速定位最优区域）
- [ ] 第二阶段：MCMC局部采样（精细量化不确定性）
- [ ] 自动切换机制（基于收敛判定）

### 算法流程（基于论文3）
```
Step 1: PSO初始化
  - 粒子数: 50-100
  - 迭代次数: 100-200
  - 惯性权重: w ∈ [0.4, 0.9]
  - 学习因子: c1 = c2 = 2.0

Step 2: PSO搜索
  - 目标函数: 最小化模拟误差
  - 约束处理: 参数边界+响应曲面
  - 收敛判定: 连续20代无改进

Step 3: MCMC采样
  - 初始化: 使用PSO最优解作为先验中心
  - 先验分布: N(PSO_optimal, σ²)
  - 采样方法: NUTS (No-U-Turn Sampler)
  - 样本数: 2000-5000

Step 4: 后验分析
  - 参数后验分布
  - 95%置信区间
  - 参数相关性分析
```

### 代码框架
```python
class PSOMCMCHybridOptimizer:
    def __init__(self, observed_data, model_runner, param_bounds):
        self.pso = PSOOptimizer(...)
        self.mcmc = MCMCCalibrator(...)

    def optimize(self):
        # Stage 1: PSO全局搜索
        pso_result = self.pso.optimize(n_iterations=200)

        # Stage 2: 基于PSO结果调整先验
        adaptive_priors = self._create_adaptive_priors(pso_result)

        # Stage 3: MCMC精细采样
        mcmc_result = self.mcmc.sample(
            priors=adaptive_priors,
            n_draws=5000
        )

        return mcmc_result
```

---

## 第三阶段：多目标优化与约束（P1 - 短期实施）

### 目标
支持多目标优化（产量+生育期+CH4），添加响应曲面约束

### 具体任务

#### 3.1 实现多目标优化框架
- [ ] 创建 `calibration/multi_objective.py`
- [ ] 支持加权求和法
- [ ] 支持ε-约束法
- [ ] 支持Pareto前沿分析

#### 3.2 实现响应曲面约束
- [x] 已实现 `get_phi_constraint(params)`
- [x] 已实现 `get_tgw_constraint(params)`
- [ ] 添加更多响应关系（如产量 = f(LAI, TGW, PHI)）
- [ ] 在MCMC中添加软约束惩罚项

### 多目标函数设计
```python
def multi_objective_function(simulated, observed, weights):
    """
    多目标误差函数

    目标1: 生育期误差 (DAT)
    目标2: 生物量误差 (Biomass)
    目标3: 产量误差 (Yield)
    目标4: CH4排放误差 (CH4)

    weights = {'dat': 0.2, 'biomass': 0.3, 'yield': 0.3, 'ch4': 0.2}
    """
    errors = {}
    for var in ['dat', 'biomass', 'yield', 'ch4']:
        if var in observed and var in simulated:
            errors[var] = calculate_rmse(observed[var], simulated[var])

    weighted_error = sum(weights.get(k, 0) * v for k, v in errors.items())
    return weighted_error, errors
```

### 响应曲面约束（基于论文2）
```python
def apply_response_surface_constraints(params):
    """
    应用响应曲面约束
    """
    constraints = {}

    # PHI = f(TLN, PS, TS)
    phi_lower, phi_upper = get_phi_constraint(params)
    if 'PHI' in params:
        constraints['PHI'] = (phi_lower, phi_upper)

    # TGW = g(PHI)
    tgw_lower, tgw_upper = get_tgw_constraint(params)
    if 'TGW' in params:
        constraints['TGW'] = (tgw_lower, tgw_upper)

    return constraints
```

---

## 第四阶段：并行计算优化（P2 - 中期实施）

### 目标
支持多核并行计算，加速MCMC采样和PSO搜索

### 具体任务

#### 4.1 MCMC并行化
- [ ] 使用 `multiprocessing` 或 `joblib`
- [ ] 支持多链并行采样
- [ ] 动态负载均衡

#### 4.2 PSO并行化
- [ ] 粒子评估并行化
- [ ] 使用 `dask` 或 `ray` 框架

### 并行策略
```python
# MCMC多链并行
from multiprocessing import Pool

def parallel_mcmc_sampling(n_chains=4, n_draws=2000):
    with Pool(n_chains) as pool:
        results = pool.map(
            run_single_chain,
            [chain_config] * n_chains
        )
    return merge_chains(results)

# PSO粒子评估并行
def parallel_pso_evaluate(swarm, n_workers=4):
    with Pool(n_workers) as pool:
        fitness = pool.map(
            evaluate_particle,
            swarm.particles
        )
    return fitness
```

---

## 第五阶段：不确定性传播分析（P2 - 中期实施）

### 目标
量化参数不确定性对模型预测的影响

### 具体任务

#### 5.1 实现蒙特卡洛不确定性传播
- [ ] 从后验分布抽取参数样本
- [ ] 运行多次模型模拟
- [ ] 计算预测置信区间（95% CI）

#### 5.2 实现敏感性-不确定性联合分析
- [ ] 识别高敏感+高不确定参数
- [ ] 优先校准这些参数

### 不确定性传播流程
```python
def uncertainty_propagation(mcmc_result, n_samples=1000):
    """
    不确定性传播分析

    输入: MCMC后验分布
    输出: 预测置信区间
    """
    # 1. 从后验分布采样
    param_samples = mcmc_result.posterior.sample(n_samples)

    # 2. 运行模型
    predictions = []
    for params in param_samples:
        sim = model_runner(params)
        predictions.append(sim)

    # 3. 计算置信区间
    predictions = np.array(predictions)
    mean = predictions.mean(axis=0)
    ci_lower = np.percentile(predictions, 2.5, axis=0)
    ci_upper = np.percentile(predictions, 97.5, axis=0)

    return {
        'mean': mean,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'predictions': predictions
    }
```

---

## 第六阶段：UI增强与可视化（P1 - 短期实施）

### 目标
改进Web界面，添加更多可视化功能

### 具体任务

#### 6.1 添加敏感性分析页面
- [ ] 显示参数敏感性排序图
- [ ] 显示龙卷风图（Tornado Plot）
- [ ] 显示参数交互效应热力图

#### 6.2 添加多目标优化页面
- [ ] Pareto前沿可视化
- [ ] 目标空间散点图
- [ ] 权重调节滑块

#### 6.3 添加不确定性可视化
- [ ] 预测置信区间带状图
- [ ] 参数后验分布相关性矩阵
- [ ] 收敛诊断图（R-hat, ESS）

---

## 📊 参考内容摘要

### 从论文1《RiceGrow系统安装与操作》

**系统架构**
```
RiceGrow/
├── 主程序 (RiceGrow.exe)
├── 数据库/
│   ├── Weather/          # 气象数据
│   ├── Cultivar/         # 品种参数
│   ├── Soil/             # 土壤数据
│   └── Management/       # 管理措施
└── 输出结果/
    ├── 生育期.txt
    ├── 叶龄.txt
    ├── LAI.txt
    ├── 生物量.txt
    ├── 产量.txt
    └── N_uptake.txt
```

**24个品种遗传参数**
| 参数 | 含义 | 典型范围 | 敏感性 |
|------|------|----------|--------|
| PS | 光敏感性 | 0.02-0.08 | 高 |
| TS | 感温性 | 2.5-3.2 | 高 |
| TO | 最适温度 | 26-28°C | 高 |
| PHI | 收获指数 | 0.43-0.48 | 高 |
| TGW | 千粒重 | 24-28g | 高 |
| TLN | 总叶龄 | 14-18 | 中 |
| AMX | 最大光合速率 | 41-48 | 高 |

### 从论文2《RiceGrow模型品种参数不确定性研究》

**Sobol敏感性分析结果**
- 高敏感参数 (ST > 0.1): PHI, TGW, FDF, SLAc, RGC, PF, AMX, TS
- 中敏感参数 (0.01 < ST < 0.1): PS, TO, IE, KF, TA, TLN, EIN, HF
- 低敏感参数 (ST < 0.01): LRS, SGP, PC, RAR

**响应曲面方程**
```
PHI = 0.42 + 0.01×TLN + 0.3×PS + 0.05×TS
TGW = 30 - 10×PHI
```

**分层校准策略**
- 第一层：高敏感参数，精细校准（n_draws=5000）
- 第二层：中敏感参数，适度校准（n_draws=2000）
- 第三层：低敏感参数，固定文献值

### 从论文3《不确定条件下作物生育期模型品种参数自动校正框架》

**PSO-MCMC混合算法**
```
第一阶段: PSO全局搜索
  粒子数: 50
  迭代次数: 200
  惯性权重: w = 0.9 - 0.5×(t/T)
  学习因子: c1 = c2 = 2.0

第二阶段: MCMC局部采样
  初始化: μ = PSO_optimal, σ = PSO_std×0.1
  采样方法: NUTS
  样本数: 2000
  Burn-in: 1000
```

**多目标优化**
- 目标1: 生育期误差 (DAT)
- 目标2: 产量误差 (Yield)
- 权重: w1 = 0.4, w2 = 0.6

**并行计算**
- MCMC: 4链并行
- PSO: 粒子评估并行

---

## 🚀 实施优先级

### P0 (立即实施)
1. ✅ 完善Sobol敏感性分析模块
2. ✅ 集成到Web UI
3. ✅ 添加敏感性可视化

### P1 (短期实施，1-2周)
1. 实现PSO优化算法
2. 实现PSO-MCMC混合算法
3. 实现多目标优化框架
4. 添加响应曲面约束

### P2 (中期实施，2-4周)
1. 并行计算优化
2. 不确定性传播分析
3. UI增强与可视化

---

## 📦 新增依赖

```
# PSO优化
pyswarms>=1.1.0

# 并行计算
dask[complete]>=2023.0.0
# 或
ray[default]>=2.0.0

# 可视化增强
plotly>=5.15.0
seaborn>=0.12.0
```

---

## 🔧 技术要点

### 关键算法选择

| 任务 | 推荐算法 | 理由 |
|------|----------|------|
| 全局搜索 | PSO | 收敛快，适合多模态 |
| 贝叶斯推断 | NUTS (PyMC) | 自动步长调谐 |
| 敏感性分析 | Sobol (SALib) | 全局敏感性，支持交互效应 |
| 多目标优化 | NSGA-II | Pareto前沿完整 |
| 并行计算 | Dask | 易用，支持分布式 |

### 参数约束策略

1. **硬约束**（不可违反）
   - PHI ∈ [0.30, 0.55]
   - TGW ∈ [15, 40]
   - PS ∈ [0, 0.1]

2. **软约束**（响应曲面）
   - PHI ≈ f(TLN, PS, TS)
   - TGW ≈ g(PHI)

3. **先验约束**（贝叶斯）
   - TruncatedNormal(μ, σ, lower, upper)

---

## 📝 总结

本改进计划基于三篇核心论文，结合现有系统基础，分六个阶段逐步实施：

1. **敏感性分析** - 识别关键参数
2. **混合算法** - PSO+MCMC结合
3. **多目标优化** - 产量+生育期+CH4
4. **并行计算** - 加速求解
5. **不确定性分析** - 量化预测置信度
6. **UI增强** - 更好的可视化

预计实施周期：**4-6周**
预计性能提升：**校准精度提升30-50%，计算时间缩短50-70%**
