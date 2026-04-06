"""
PSO-MCMC混合优化算法模块

基于论文《不确定条件下作物生育期模型品种参数自动校正框架》
实现两阶段优化：
1. PSO全局搜索 - 快速定位最优区域
2. MCMC精细采样 - 量化参数不确定性
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Callable, Optional, Any
import logging

logger = logging.getLogger('rice_app')

# 导入PSO优化器
from calibration.pso_optimizer import PSOOptimizer, create_pso_optimizer

# 尝试导入MCMC调参器
try:
    from calibration.pymc_calibrator import MCMCCalibrator, PYMC_AVAILABLE
except ImportError:
    PYMC_AVAILABLE = False
    logger.warning("PyMC未安装，混合优化功能将受限")


class PSOMCMCHybridOptimizer:
    """PSO-MCMC混合优化算法

    结合PSO的全局搜索能力和MCMC的贝叶斯推断能力
    """

    def __init__(self,
                 observed_data: pd.DataFrame,
                 model_runner: Callable,
                 param_bounds: Dict[str, Tuple[float, float]],
                 param_priors: Dict[str, Dict[str, Any]] = None,
                 target_columns: List[str] = None,
                 fixed_params: Dict[str, Any] = None):
        """初始化混合优化器

        Args:
            observed_data: 观测数据
            model_runner: 模型运行函数
            param_bounds: 参数边界
            param_priors: 参数先验分布（用于MCMC）
            target_columns: 目标列名
            fixed_params: 固定参数
        """
        self.observed_data = observed_data
        self.model_runner = model_runner
        self.param_bounds = param_bounds
        self.param_priors = param_priors or {}
        self.target_columns = target_columns or ['Biomass', 'CH4']
        self.fixed_params = fixed_params or {}

        # 参数名列表
        self.param_names = list(param_bounds.keys())

        # PSO配置
        self.pso_config = {
            'n_particles': 50,
            'max_iter': 200,
            'w': 0.9,
            'c1': 2.0,
            'c2': 2.0,
            'w_decay': True,
        }

        # MCMC配置
        self.mcmc_config = {
            'n_tunes': 1000,
            'n_draws': 5000,
            'n_chains': 4,
            'target_accept': 0.9,
        }

        # 结果存储
        self.pso_result = None
        self.mcmc_result = None
        self.adaptive_priors = None

        logger.info(f"混合优化器初始化: {len(self.param_names)}个参数")

    def _create_adaptive_priors(self, pso_result: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """根据PSO结果创建自适应先验

        策略：
        - 使用PSO最优解作为先验均值（μ）
        - 使用PSO粒子标准差调整先验方差（σ）

        Args:
            pso_result: PSO优化结果

        Returns:
            自适应先验字典
        """
        # 提取PSO粒子历史位置
        position_history = np.array(pso_result['position_history'])

        # 计算统计量
        best_position = pso_result['best_params']

        # 粒子标准差（作为先验标准差的参考）
        # 使用最后20%的粒子位置计算
        recent_positions = position_history[int(len(position_history) * 0.8):]
        particle_std = np.std(recent_positions, axis=0)

        # 自适应先验
        adaptive_priors = {}

        for i, param_name in enumerate(self.param_names):
            if param_name in self.param_priors:
                # 使用原配置的分布类型
                original_config = self.param_priors[param_name]
                dist_type = original_config.get('dist', 'TruncatedNormal')

                if dist_type == 'TruncatedNormal':
                    adaptive_priors[param_name] = {
                        'dist': 'TruncatedNormal',
                        'mu': best_position[param_name],
                        'sigma': max(particle_std[i] * 0.5, original_config.get('sigma', 0.1) * 0.5),
                        'lower': self.param_bounds[param_name][0],
                        'upper': self.param_bounds[param_name][1],
                        'description': original_config.get('description', param_name),
                    }
                else:
                    # 其他分布类型
                    adaptive_priors[param_name] = original_config.copy()
            else:
                # 默认使用截断正态分布
                adaptive_priors[param_name] = {
                    'dist': 'TruncatedNormal',
                    'mu': best_position[param_name],
                    'sigma': max(particle_std[i] * 0.5, 0.01),
                    'lower': self.param_bounds[param_name][0],
                    'upper': self.param_bounds[param_name][1],
                    'description': param_name,
                }

        logger.info(f"创建自适应先验: {len(adaptive_priors)}个参数")
        for param, config in adaptive_priors.items():
            logger.info(f"  {param}: N({config['mu']:.4f}, {config['sigma']:.4f})")

        return adaptive_priors

    def optimize(self,
                 pso_config: Dict[str, Any] = None,
                 mcmc_config: Dict[str, Any] = None,
                 run_pso: bool = True,
                 run_mcmc: bool = True,
                 verbose: bool = True) -> Dict[str, Any]:
        """运行混合优化

        Args:
            pso_config: PSO配置覆盖
            mcmc_config: MCMC配置覆盖
            run_pso: 是否运行PSO阶段
            run_mcmc: 是否运行MCMC阶段
            verbose: 是否打印详细信息

        Returns:
            优化结果字典
        """
        # 更新配置
        if pso_config:
            self.pso_config.update(pso_config)
        if mcmc_config:
            self.mcmc_config.update(mcmc_config)

        results = {}

        # ========== 阶段1: PSO全局搜索 ==========
        if run_pso:
            logger.info("=" * 60)
            logger.info("阶段1: PSO全局搜索")
            logger.info("=" * 60)

            # 创建PSO优化器
            pso = create_pso_optimizer(
                observed_data=self.observed_data,
                model_runner=self.model_runner,
                param_bounds=self.param_bounds,
                target_columns=self.target_columns,
                fixed_params=self.fixed_params,
                **self.pso_config
            )

            # 运行PSO
            self.pso_result = pso.optimize(verbose=verbose)

            results['pso'] = self.pso_result

            if verbose:
                logger.info(f"PSO最优适应度: {self.pso_result['best_fitness']:.6f}")
                logger.info(f"PSO迭代次数: {self.pso_result['n_iterations']}")

        # ========== 阶段2: 自适应先验调整 ==========
        if run_mcmc and self.pso_result:
            logger.info("=" * 60)
            logger.info("阶段2: 自适应先验调整")
            logger.info("=" * 60)

            # 创建自适应先验
            self.adaptive_priors = self._create_adaptive_priors(self.pso_result)

            results['adaptive_priors'] = self.adaptive_priors

        # ========== 阶段3: MCMC精细采样 ==========
        if run_mcmc:
            if not PYMC_AVAILABLE:
                logger.warning("PyMC未安装，跳过MCMC阶段")
            else:
                logger.info("=" * 60)
                logger.info("阶段3: MCMC精细采样")
                logger.info("=" * 60)

                # 创建MCMC调参器
                mcmc_calibrator = MCMCCalibrator(
                    observed_data=self.observed_data,
                    model_runner=self.model_runner,
                    param_priors=self.adaptive_priors,
                    target_columns=self.target_columns,
                    fixed_params=self.fixed_params
                )

                # 构建模型
                mcmc_calibrator.build_model(self.param_names)

                # 运行采样
                trace = mcmc_calibrator.sample(
                    n_tunes=self.mcmc_config['n_tunes'],
                    n_draws=self.mcmc_config['n_draws'],
                    n_chains=self.mcmc_config['n_chains'],
                    target_accept=self.mcmc_config['target_accept'],
                    cores=min(self.mcmc_config['n_chains'], 4)
                )

                # 获取结果
                ranges = mcmc_calibrator.get_parameter_ranges()
                converged, diagnostics = mcmc_calibrator.check_convergence()

                self.mcmc_result = {
                    'trace': trace,
                    'ranges': ranges,
                    'converged': converged,
                    'diagnostics': diagnostics,
                }

                results['mcmc'] = self.mcmc_result

                if verbose:
                    logger.info(f"MCMC收敛: {converged}")
                    for param in self.param_names:
                        if param in ranges:
                            stats = ranges[param]
                            logger.info(f"  {param}: {stats['mean']:.4f} ± {stats['sd']:.4f}")

        # ========== 结果汇总 ==========
        logger.info("=" * 60)
        logger.info("混合优化完成")
        logger.info("=" * 60)

        return results

    def get_best_params(self) -> Dict[str, float]:
        """获取最优参数

        优先使用MCMC后验均值，如果MCMC未运行则使用PSO最优解

        Returns:
            最优参数字典
        """
        if self.mcmc_result and 'ranges' in self.mcmc_result:
            # 使用MCMC后验均值
            ranges = self.mcmc_result['ranges']
            return {param: ranges[param]['mean'] for param in self.param_names if param in ranges}
        elif self.pso_result:
            # 使用PSO最优解
            return self.pso_result['best_params']
        else:
            raise ValueError("请先运行 optimize()")


def create_hybrid_optimizer(observed_data: pd.DataFrame,
                             model_runner: Callable,
                             param_bounds: Dict[str, Tuple[float, float]],
                             param_priors: Dict[str, Dict[str, Any]] = None,
                             **kwargs) -> PSOMCMCHybridOptimizer:
    """便捷函数：创建混合优化器

    Args:
        observed_data: 观测数据
        model_runner: 模型运行函数
        param_bounds: 参数边界
        param_priors: 参数先验
        **kwargs: 其他参数

    Returns:
        混合优化器实例
    """
    return PSOMCMCHybridOptimizer(
        observed_data=observed_data,
        model_runner=model_runner,
        param_bounds=param_bounds,
        param_priors=param_priors,
        **kwargs
    )


if __name__ == '__main__':
    # 测试代码
    print("PSO-MCMC混合优化器模块")

    # 测试混合优化器创建
    bounds = {
        'PS': (0.02, 0.08),
        'TS': (2.5, 3.2),
        'PHI': (0.43, 0.48),
    }

    priors = {
        'PS': {'dist': 'TruncatedNormal', 'mu': 0.05, 'sigma': 0.01, 'lower': 0.02, 'upper': 0.08},
        'TS': {'dist': 'TruncatedNormal', 'mu': 2.8, 'sigma': 0.2, 'lower': 2.5, 'upper': 3.2},
        'PHI': {'dist': 'TruncatedNormal', 'mu': 0.45, 'sigma': 0.02, 'lower': 0.43, 'upper': 0.48},
    }

    print(f'参数数量: {len(bounds)}')
    print(f'先验数量: {len(priors)}')

    # 创建混合优化器（不实际运行，因为需要完整的数据）
    optimizer = create_hybrid_optimizer(
        observed_data=pd.DataFrame({'test': [0]}),
        model_runner=lambda p: pd.DataFrame({'fitness': [0]}),
        param_bounds=bounds,
        param_priors=priors,
    )

    print('✅ 混合优化器创建成功')
    print(f'PSO配置: {optimizer.pso_config}')
    print(f'MCMC配置: {optimizer.mcmc_config}')
