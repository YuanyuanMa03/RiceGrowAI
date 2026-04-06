# 校准系统改进任务清单

## 📋 已完成 ✅

1. **敏感性分析模块** (`calibration/sensitivity.py`)
   - Sobol全局敏感性分析
   - 参数自动分类（高/中/低敏感）
   - 论文验证的敏感性分组

2. **响应曲面约束** (`calibration/priors.py`)
   - `get_phi_constraint()` - PHI = f(TLN, PS, TS)
   - `get_tgw_constraint()` - TGW = g(PHI)
   - `get_maturity_type()` - 品种熟性分类
   - `get_layered_calibration_strategy()` - 分层校准策略

3. **统计指标评估** (`calibration/metrics.py`)
   - R², RMSE, MAE, NSE, PBIAS, KGE
   - 模型评级（5星制）
   - 数据对齐功能

4. **可视化模块** (`calibration/visualization.py`)
   - 时间序列对比图
   - 1:1散点图
   - 残差分布图
   - 指标卡片

---

## 🚀 待实施任务

### 阶段1: PSO优化算法 (1-2天)

**文件**: 新建 `calibration/pso_optimizer.py`

**功能点**:
```python
class PSOOptimizer:
    """粒子群优化算法"""
    def __init__(self, observed_data, model_runner, param_bounds,
                 n_particles=50, max_iter=200, w=0.9, c1=2.0, c2=2.0):
        pass

    def optimize(self):
        """运行PSO优化"""
        pass

    def get_best_params(self):
        """获取最优参数"""
        pass
```

**关键参数**:
- 粒子数: 50-100
- 最大迭代: 200
- 惯性权重: w ∈ [0.4, 0.9]
- 学习因子: c1 = c2 = 2.0

---

### 阶段2: PSO-MCMC混合算法 (2-3天)

**文件**: 新建 `calibration/hybrid_optimizer.py`

**功能点**:
```python
class PSOMCMCHybridOptimizer:
    """PSO+MCMC混合优化算法"""
    def __init__(self, observed_data, model_runner, param_bounds):
        self.pso = PSOOptimizer(...)
        self.mcmc = MCMCCalibrator(...)

    def optimize(self):
        """两阶段优化"""
        # Stage 1: PSO全局搜索
        pso_result = self.pso.optimize()

        # Stage 2: 基于PSO结果调整MCMC先验
        adaptive_priors = self._create_adaptive_priors(pso_result)

        # Stage 3: MCMC精细采样
        mcmc_result = self.mcmc.sample(priors=adaptive_priors)

        return mcmc_result

    def _create_adaptive_priors(self, pso_result):
        """根据PSO结果创建自适应先验"""
        # 使用PSO最优解作为先验中心
        # 使用PSO粒子方差调整先验方差
        pass
```

**流程图**:
```
┌─────────────┐
│  PSO搜索    │ → 快速定位最优区域
│  (200代)    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 调整先验    │ → μ = PSO_optimal, σ = PSO_std × 0.1
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  MCMC采样   │ → 精细量化不确定性
│  (5000样本) │
└─────────────┘
```

---

### 阶段3: 多目标优化 (2-3天)

**文件**: 新建 `calibration/multi_objective.py`

**功能点**:
```python
def multi_objective_error(simulated, observed, weights):
    """
    多目标误差函数

    目标: 生育期 + 生物量 + 产量 + CH4
    权重: 可调节
    """
    errors = {
        'dat': calculate_error(simulated['DAT'], observed['DAT']),
        'biomass': calculate_error(simulated['Biomass'], observed['Biomass']),
        'yield': calculate_error(simulated['Yield'], observed['Yield']),
        'ch4': calculate_error(simulated['CH4'], observed['CH4']),
    }

    weighted = sum(weights[k] * errors[k] for k in weights)
    return weighted, errors
```

**UI集成**:
```python
# 在 calibration_page.py 中添加权重调节
with st.expander("🎯 多目标权重设置"):
    weights = {
        'dat': st.slider("生育期权重", 0.0, 1.0, 0.2),
        'biomass': st.slider("生物量权重", 0.0, 1.0, 0.3),
        'yield': st.slider("产量权重", 0.0, 1.0, 0.3),
        'ch4': st.slider("CH4权重", 0.0, 1.0, 0.2),
    }
```

---

### 阶段4: Web UI集成 (3-4天)

**文件**: 修改 `calibration_page.py`

**新增页面**:

#### 4.1 敏感性分析页面
```python
def show_sensitivity_analysis_page():
    """敏感性分析页面"""
    st.markdown("### 📊 参数敏感性分析")

    # 选择目标变量
    target = st.selectbox("分析目标", ["产量", "生物量", "CH4排放"])

    # 运行Sobol分析
    if st.button("开始分析"):
        sobol_results, classification = perform_sensitivity_analysis(...)

        # 显示结果
        st.write("#### 参数敏感性排序")
        # 柱状图

        st.write("#### 敏感性分组")
        # 高/中/低敏感参数列表
```

#### 4.2 混合优化页面
```python
def show_hybrid_optimization_page():
    """混合优化页面"""
    st.markdown("### 🚀 PSO-MCMC混合优化")

    # 算法配置
    col1, col2 = st.columns(2)
    with col1:
        pso_iterations = st.slider("PSO迭代数", 100, 500, 200)
        pso_particles = st.slider("PSO粒子数", 20, 100, 50)

    with col2:
        mcmc_draws = st.slider("MCMC采样数", 1000, 10000, 5000)
        mcmc_chains = st.slider("MCMC链数", 1, 8, 4)

    # 运行优化
    if st.button("开始混合优化"):
        optimizer = PSOMCMCHybridOptimizer(...)
        result = optimizer.optimize()

        # 显示结果
        show_calibration_results(...)
```

---

### 阶段5: 并行计算优化 (2-3天)

**文件**: 修改 `calibration/pymc_calibrator.py`

**功能点**:
```python
from multiprocessing import Pool
import os

def parallel_mcmc_sampling(n_chains=4, n_draws=2000):
    """并行MCMC采样"""
    # 设置多进程启动方法
    os.environ['OMP_NUM_THREADS'] = '1'

    with Pool(n_chains) as pool:
        results = pool.map(
            _run_single_chain,
            [(chain_id, n_draws) for chain_id in range(n_chains)]
        )

    return merge_chains(results)
```

**性能提升预期**:
- 4核并行: 3.5x 加速
- 8核并行: 6.5x 加速

---

### 阶段6: 不确定性传播 (2-3天)

**文件**: 新建 `calibration/uncertainty.py`

**功能点**:
```python
def uncertainty_propagation(mcmc_result, n_samples=1000):
    """不确定性传播分析"""
    # 1. 从后验分布采样
    param_samples = mcmc_result.posterior.sample(n_samples)

    # 2. 运行模型
    predictions = []
    for params in param_samples:
        sim = model_runner(params)
        predictions.append(sim)

    # 3. 计算置信区间
    ci_lower = np.percentile(predictions, 2.5, axis=0)
    ci_upper = np.percentile(predictions, 97.5, axis=0)

    return {
        'mean': np.mean(predictions, axis=0),
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
    }
```

**UI展示**:
```python
def show_uncertainty_band(observed, simulated, ci_lower, ci_upper):
    """显示不确定性带"""
    fig = go.Figure()

    # 观测值
    fig.add_trace(go.Scatter(...))

    # 模拟均值
    fig.add_trace(go.Scatter(...))

    # 95%置信区间
    fig.add_trace(go.Scatter(
        x=dat,
        y=ci_upper,
        mode='lines',
        line=dict(width=0),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=dat,
        y=ci_lower,
        mode='lines',
        line=dict(width=0),
        fillcolor='rgba(0,100,80,0.2)',
        fill='tonexty',
        name='95% CI',
    ))
```

---

## 📊 依赖安装

```bash
# PSO优化
pip install pyswarms

# 并行计算
pip install dask[complete]

# 已有依赖
pip install pymc arviz salib numpy pandas plotly streamlit
```

---

## ⏱️ 预计时间线

| 阶段 | 任务 | 预计时间 |
|------|------|----------|
| 1 | PSO优化算法 | 1-2天 |
| 2 | PSO-MCMC混合 | 2-3天 |
| 3 | 多目标优化 | 2-3天 |
| 4 | Web UI集成 | 3-4天 |
| 5 | 并行计算优化 | 2-3天 |
| 6 | 不确定性传播 | 2-3天 |
| **总计** | | **12-18天** |

---

## 🎯 优先级建议

### 第一批（必须做）
1. ✅ 敏感性分析模块（已完成）
2. PSO优化算法
3. PSO-MCMC混合算法
4. Web UI集成

### 第二批（重要）
5. 多目标优化
6. 并行计算优化

### 第三批（可选）
7. 不确定性传播分析
8. 高级可视化
