"""
MCMC 贝叶斯参数校准器

使用 PyMC 库实现基于马尔可夫链蒙特卡洛 (MCMC) 的贝叶斯参数推断。
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Callable
import warnings

import numpy as np
import pandas as pd

logger = logging.getLogger('rice_app')

# PyMC/pytensor 会产生大量 UserWarning，仅在需要时局部抑制
_PMC_WARNING_CATEGORIES = (UserWarning, FutureWarning)

# 尝试导入 PyMC 和 ArviZ
try:
    import pymc as pm
    import arviz as az
    import pytensor.tensor as pt
    from pytensor.graph.op import Op
    PYMC_AVAILABLE = True
except ImportError:
    PYMC_AVAILABLE = False
    pm = None
    az = None
    pt = None
    Op = None
    logger.warning("PyMC 或 ArviZ 未安装。MCMC 调参功能将不可用。"
                   "请运行: pip install pymc arviz")


if PYMC_AVAILABLE:
    class _BlackBoxLogLikelihoodOp(Op):
        """PyTensor Op wrapping a black-box log-likelihood function.

        This allows PyMC's NUTS sampler to call a pure-Python model
        (which pytensor cannot trace symbolically) during sampling.
        """
        itypes = [pt.dvector]
        otypes = [pt.dscalar]

        def __init__(self, logp_fn: Callable):
            self._logp_fn = logp_fn

        def perform(self, node, inputs, output_storage):
            param_values = inputs[0]
            result = self._logp_fn(param_values)
            output_storage[0][0] = np.asarray(result, dtype=np.float64)


class MCMCCalibrator:
    """MCMC 贝叶斯参数校准器

    使用 NUTS (No-U-Turn Sampler) 进行参数后验分布推断
    """

    def __init__(self,
                 observed_data: pd.DataFrame,
                 model_runner: Callable,
                 param_priors: Dict[str, Dict[str, Any]],
                 target_columns: List[str] = None,
                 fixed_params: Dict[str, Any] = None):
        """初始化 MCMC 调参器

        Args:
            observed_data: 观测数据，必须包含 DAT 列
            model_runner: 模型运行函数，接受参数字典，返回模拟结果 DataFrame
            param_priors: 参数先验配置（从 priors.py 导入）
            target_columns: 目标列名列表，如 ['Biomass', 'CH4']
            fixed_params: 固定参数字典
        """
        if not PYMC_AVAILABLE:
            raise ImportError("PyMC/ArviZ 未安装，无法使用 MCMC 调参功能")

        self.observed_data = observed_data
        self.model_runner = model_runner
        self.param_priors = param_priors
        self.target_columns = target_columns or ['Biomass', 'CH4']
        self.fixed_params = fixed_params or {}

        # 过滤掉观测数据中不存在的目标列
        self.target_columns = [col for col in self.target_columns
                              if col in observed_data.columns]

        # 结果存储
        self.trace = None
        self.model = None
        self.param_names = []

        # 验证数据
        self._validate_data()

        logger.info(f"MCMC 调参器初始化完成: {len(self.target_columns)} 个目标变量")

    def _validate_data(self):
        """验证输入数据"""
        if 'DAT' not in self.observed_data.columns:
            raise ValueError("观测数据必须包含 DAT 列")

        if not self.target_columns:
            raise ValueError("观测数据必须包含至少一个目标列")

    def _prepare_data_for_model(self, params: Dict[str, float]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """准备模型输入数据

        将观测数据插值到模型输出的时间点上
        """
        # 运行模型获取模拟数据
        simulated = self.model_runner(params)

        if simulated is None or len(simulated) == 0:
            return None, None

        # 合并观测和模拟数据
        merged = []
        for target in self.target_columns:
            if target not in simulated.columns:
                continue

            # 按 DAT 合并
            obs_col = f'{target}_obs'
            sim_col = f'{target}_sim'

            temp = pd.merge(
                self.observed_data[['DAT', target]].rename(columns={target: obs_col}),
                simulated[['DAT', target]].rename(columns={target: sim_col}),
                on='DAT',
                how='inner'
            )

            # 移除 NaN
            temp = temp.dropna(subset=[obs_col, sim_col])
            merged.append(temp)

        if not merged:
            return None, None

        # 合并所有目标变量
        result = merged[0]
        for df in merged[1:]:
            result = pd.merge(result, df, on='DAT', how='inner')

        # 提取观测值和模拟值数组
        obs_arrays = {}
        sim_arrays = {}

        for target in self.target_columns:
            obs_col = f'{target}_obs'
            sim_col = f'{target}_sim'

            if obs_col in result.columns and sim_col in result.columns:
                obs_arrays[target] = result[obs_col].values
                sim_arrays[target] = result[sim_col].values

        return obs_arrays, sim_arrays

    def _build_likelihood(self, obs_arrays: Dict[str, np.ndarray],
                         sim_arrays: Dict[str, np.ndarray]):
        """构建似然函数

        为每个目标变量添加观测误差模型和似然
        """
        # 观测误差先验（heteroscedastic）
        sigma_priors = {}
        for target in self.target_columns:
            # 根据数据范围设置误差先验
            if target in obs_arrays:
                data_range = obs_arrays[target].max() - obs_arrays[target].min()
                sigma_priors[target] = pm.HalfNormal(
                    f'sigma_{target}',
                    sigma=data_range * 0.1  # 误差约为数据范围的10%
                )

        # 似然函数
        for target in self.target_columns:
            if target in obs_arrays:
                pm.Normal(
                    f'likelihood_{target}',
                    mu=sim_arrays[target],
                    sigma=sigma_priors[target],
                    observed=obs_arrays[target]
                )

    def build_model(self, params_to_calibrate: List[str]):
        """构建 PyMC 贝叶斯模型

        Args:
            params_to_calibrate: 要校准的参数名列表
        """
        self.param_names = params_to_calibrate

        logger.info(f"构建 PyMC 模型，校准参数: {params_to_calibrate}")

        # 创建模型上下文
        model_context = pm.Model()

        # 局部抑制 PyMC 构建时的警告，不影响全局
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=_PMC_WARNING_CATEGORIES)

            with model_context:
                # 1. 添加参数先验
                priors = {}
                for param in params_to_calibrate:
                    if param not in self.param_priors:
                        logger.warning(f"参数 {param} 没有定义先验，使用默认 Uniform(0,1)")
                        priors[param] = pm.Uniform(param, lower=0, upper=1)
                        continue

                    config = self.param_priors[param]
                    dist_type = config['dist']

                    if dist_type == 'TruncatedNormal':
                        priors[param] = pm.TruncatedNormal(
                            param,
                            mu=config['mu'],
                            sigma=config['sigma'],
                            lower=config['lower'],
                            upper=config['upper']
                        )
                    elif dist_type == 'Uniform':
                        priors[param] = pm.Uniform(
                            param,
                            lower=config['lower'],
                            upper=config['upper']
                        )
                    elif dist_type == 'HalfNormal':
                        priors[param] = pm.HalfNormal(
                            param,
                            sigma=config.get('sigma', 1.0)
                        )
                    else:
                        priors[param] = pm.Uniform(
                            param,
                            lower=config.get('lower', 0),
                            upper=config.get('upper', 1)
                        )

                # 2. 保存先验引用供似然函数使用
                self._priors = priors

                # 3. 用先验均值运行一次模型，获取观测数据格式
                test_params = {}
                for k in params_to_calibrate:
                    config = self.param_priors.get(k, {})
                    if 'mu' in config:
                        test_params[k] = config['mu']
                    elif 'lower' in config and 'upper' in config:
                        test_params[k] = (config['lower'] + config['upper']) / 2
                    else:
                        test_params[k] = 0.5
                test_params.update(self.fixed_params)

                obs_arrays, _ = self._prepare_data_for_model(test_params)

                if obs_arrays is None:
                    raise ValueError("无法使用先验均值运行模型，请检查模型配置")

                # 4. 通过 pm.Potential + 自定义 Op 注册似然
                self._build_custom_likelihood(obs_arrays)

        self.model = model_context
        logger.info("PyMC 模型构建完成")

        return model_context

    def _build_custom_likelihood(self, obs_arrays: Dict[str, np.ndarray]):
        """构建自定义似然函数

        使用 pm.Potential + 自定义 PyTensor Op 添加黑箱 log-likelihood，
        将纯 Python 模型与 PyMC 计算图耦合。
        """
        target_columns = self.target_columns
        fixed_params = self.fixed_params
        param_names = self.param_names

        # 定义 log-likelihood 函数（接收参数向量）
        def logp_fn(param_vector: np.ndarray) -> float:
            params = dict(fixed_params)
            params.update(dict(zip(param_names, param_vector)))

            _, sim_arrays = self._prepare_data_for_model(params)

            if sim_arrays is None:
                return -1e10  # 模型失败时返回极小值

            log_likelihood = 0.0
            for target in target_columns:
                if target in obs_arrays and target in sim_arrays:
                    obs = obs_arrays[target]
                    sim = sim_arrays[target]
                    sigma = (obs.max() - obs.min()) * 0.05
                    if sigma > 0:
                        log_likelihood += -0.5 * np.sum(((obs - sim) / sigma) ** 2)
                        log_likelihood -= len(obs) * np.log(sigma * np.sqrt(2 * np.pi))

            return log_likelihood

        # 将先验参数堆叠为向量，传入自定义 Op
        param_vector = pm.math.stack([self._priors[p] for p in param_names])
        logl_op = _BlackBoxLogLikelihoodOp(logp_fn)
        logl = logl_op(param_vector)
        pm.Potential('log_likelihood', logl)

    def sample(self,
               n_tunes: int = 1000,
               n_draws: int = 2000,
               n_chains: int = 4,
               target_accept: float = 0.9,
               cores: int = 4) -> Any:
        """运行 MCMC 采样

        Args:
            n_tunes: Burn-in 采样数（调谐阶段）
            n_draws: 正式采样数
            n_chains: 并行链数
            target_accept: 目标接受率
            cores: 使用的 CPU 核心数

        Returns:
            ArviZ InferenceData 对象
        """
        if self.model is None:
            raise ValueError("请先调用 build_model() 构建模型")

        logger.info("=" * 60)
        logger.info("开始 MCMC 采样")
        logger.info(f"  调谐样本: {n_tunes}")
        logger.info(f"  采样数: {n_draws}")
        logger.info(f"  链数: {n_chains}")
        logger.info(f"  目标接受率: {target_accept}")
        logger.info("=" * 60)

        start_time = time.time()

        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=_PMC_WARNING_CATEGORIES)
            with self.model:
                self.trace = pm.sample(
                    tune=n_tunes,
                    draws=n_draws,
                    chains=n_chains,
                    cores=cores,
                    target_accept=target_accept,
                    return_inferencedata=True,
                    progressbar=True,
                    random_seed=42,
                )

        elapsed = time.time() - start_time

        logger.info("=" * 60)
        logger.info("MCMC 采样完成")
        logger.info(f"  总耗时: {elapsed:.1f} 秒")
        logger.info(f"  每个样本: {elapsed / (n_chains * n_draws):.3f} 秒")
        logger.info("=" * 60)

        return self.trace

    def get_posterior_summary(self, hdi_prob: float = 0.95) -> pd.DataFrame:
        """获取后验分布摘要

        Args:
            hdi_prob: 最高密度区间概率

        Returns:
            包含后验统计量的 DataFrame
        """
        if self.trace is None:
            raise ValueError("请先运行 sample() 获取采样结果")

        summary = az.summary(self.trace, hdi_prob=hdi_prob)
        return summary

    def get_parameter_ranges(self, hdi_prob: float = 0.95) -> Dict[str, Dict[str, float]]:
        """获取参数的可信区间

        Args:
            hdi_prob: 最高密度区间概率

        Returns:
            参数统计量字典
        """
        import arviz as az

        # 使用 ArviZ API 直接获取 HDI
        hdi = az.hdi(self.trace, hdi_prob=hdi_prob)

        summary = self.get_posterior_summary(hdi_prob)

        ranges = {}
        for param in self.param_names:
            if param in summary.index:
                # 从 HDI 结果中提取值
                if param in hdi:
                    hdi_values = hdi[param].values
                    # hdi 返回的格式可能是 (chain, draw) 或带有坐标的格式
                    if hasattr(hdi_values, 'flatten'):
                        hdi_lower = float(hdi_values.flatten()[0])
                        hdi_upper = float(hdi_values.flatten()[1])
                    else:
                        hdi_lower = float(hdi_values[0])
                        hdi_upper = float(hdi_values[1])
                else:
                    hdi_lower = 0.0
                    hdi_upper = 1.0

                ranges[param] = {
                    'mean': float(summary.loc[param, 'mean']),
                    'sd': float(summary.loc[param, 'sd']),
                    'hdi_lower': hdi_lower,
                    'hdi_upper': hdi_upper,
                    'mcse_mean': float(summary.loc[param, 'mcse_mean']),
                    'ess_bulk': float(summary.loc[param, 'ess_bulk']),
                    'ess_tail': float(summary.loc[param, 'ess_tail']),
                    'r_hat': float(summary.loc[param, 'r_hat']),
                }

        return ranges

    def check_convergence(self, rhat_threshold: float = 1.05,
                         ess_threshold: int = 400) -> Tuple[bool, Dict[str, Any]]:
        """检查收敛性

        Args:
            rhat_threshold: R-hat 阈值
            ess_threshold: 有效样本量阈值

        Returns:
            (是否收敛, 诊断信息)
        """
        if self.trace is None:
            raise ValueError("请先运行 sample() 获取采样结果")

        # 计算 R-hat
        rhat = az.rhat(self.trace)

        # 计算 ESS
        ess = az.ess(self.trace)

        # 检查收敛
        converged = True
        diagnostics = {}

        for param in self.param_names:
            param_rhat = float(rhat[param])
            param_ess = float(ess[param])

            param_converged = param_rhat < rhat_threshold and param_ess > ess_threshold
            converged &= param_converged

            diagnostics[param] = {
                'r_hat': param_rhat,
                'ess': param_ess,
                'converged': param_converged,
            }

        return converged, diagnostics

    def get_best_params(self) -> Dict[str, float]:
        """获取最佳参数（后验均值）"""
        ranges = self.get_parameter_ranges()

        best_params = {}
        for param, stats in ranges.items():
            best_params[param] = stats['mean']

        return best_params


# ===== 便捷函数 =====

def create_mcmc_calibrator(observed_data: pd.DataFrame,
                           model_runner: Callable,
                           param_priors: Dict[str, Dict[str, Any]],
                           target_columns: List[str] = None,
                           fixed_params: Dict[str, Any] = None) -> MCMCCalibrator:
    """创建 MCMC 调参器

    Args:
        observed_data: 观测数据
        model_runner: 模型运行函数
        param_priors: 参数先验配置
        target_columns: 目标列名列表
        fixed_params: 固定参数

    Returns:
        MCMCCalibrator 实例
    """
    return MCMCCalibrator(
        observed_data=observed_data,
        model_runner=model_runner,
        param_priors=param_priors,
        target_columns=target_columns,
        fixed_params=fixed_params,
    )


if __name__ == '__main__':
    # 测试代码
    if PYMC_AVAILABLE:
        print("PyMC 可用，MCMC 调参器已就绪")
    else:
        print("PyMC 不可用，请安装: pip install pymc arviz")
