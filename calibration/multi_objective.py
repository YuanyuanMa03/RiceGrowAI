"""
多目标优化模块

支持同时优化多个目标：
- 生育期 (DAT)
- 生物量 (Biomass)
- 产量 (Yield)
- CH4排放 (CH4)

方法：
- 加权求和法
- ε-约束法
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Callable, Optional, Any, Union
import logging

logger = logging.getLogger('rice_app')

# 导入统计指标
from calibration.metrics import (
    calculate_rmse,
    calculate_mae,
    calculate_nse,
    calculate_r2
)


class MultiObjectiveOptimizer:
    """多目标优化器

    支持多个目标变量的同时优化
    """

    def __init__(self,
                 observed_data: pd.DataFrame,
                 model_runner: Callable,
                 target_variables: List[str],
                 weights: Dict[str, float] = None,
                 fixed_params: Dict[str, Any] = None):
        """初始化多目标优化器

        Args:
            observed_data: 观测数据
            model_runner: 模型运行函数
            target_variables: 目标变量列表（如 ['DAT', 'Biomass', 'Yield', 'CH4']）
            weights: 各目标权重（默认均等权重）
            fixed_params: 固定参数
        """
        self.observed_data = observed_data
        self.model_runner = model_runner
        self.target_variables = target_variables
        self.fixed_params = fixed_params or {}

        # 设置默认权重（均等权重）
        if weights is None:
            self.weights = {v: 1.0 / len(target_variables) for v in target_variables}
        else:
            self.weights = weights

        # 归一化权重
        total_weight = sum(self.weights.values())
        self.weights = {k: v / total_weight for k, v in self.weights.items()}

        logger.info(f"多目标优化器初始化: {len(target_variables)}个目标")
        logger.info(f"目标变量: {target_variables}")
        logger.info(f"权重: {self.weights}")

    def _align_data(self, simulated: pd.DataFrame, target: str) -> Tuple[np.ndarray, np.ndarray]:
        """对齐观测数据和模拟数据

        Args:
            simulated: 模拟结果
            target: 目标变量名

        Returns:
            (观测值, 模拟值) 对齐后的数组
        """
        if target not in self.observed_data.columns:
            return None, None

        if target not in simulated.columns:
            return None, None

        obs = self.observed_data[target].values
        sim = simulated[target].values

        # 移除NaN
        valid = ~(np.isnan(obs) | np.isnan(sim))

        return obs[valid], sim[valid]

    def _calculate_single_error(self,
                                  obs: np.ndarray,
                                  sim: np.ndarray,
                                  method: str = 'rmse') -> float:
        """计算单个目标的误差

        Args:
            obs: 观测值
            sim: 模拟值
            method: 误差计算方法

        Returns:
            误差值
        """
        if len(obs) == 0:
            return 1e10  # 无效数据惩罚

        if method == 'rmse':
            return calculate_rmse(obs, sim)
        elif method == 'mae':
            return calculate_mae(obs, sim)
        elif method == 'nse':
            return 1.0 - calculate_nse(obs, sim)  # 转换为误差（越小越好）
        elif method == 'r2':
            return 1.0 - calculate_r2(obs, sim)  # 转换为误差
        else:
            return calculate_rmse(obs, sim)

    def calculate_weighted_error(self,
                                   simulated: pd.DataFrame,
                                   method: str = 'rmse') -> Tuple[float, Dict[str, float]]:
        """计算加权总误差

        Args:
            simulated: 模拟结果
            method: 误差计算方法

        Returns:
            (加权总误差, 各目标误差字典)
        """
        errors = {}
        total_error = 0.0

        for target in self.target_variables:
            # 对齐数据
            obs, sim = self._align_data(simulated, target)

            if obs is None:
                continue

            # 计算误差
            error = self._calculate_single_error(obs, sim, method)

            # 归一化（相对于数据范围）
            data_range = obs.max() - obs.min()
            if data_range > 0:
                normalized_error = error / data_range
            else:
                normalized_error = error

            errors[target] = {
                'raw': error,
                'normalized': normalized_error,
            }

            # 加权累加
            total_error += self.weights.get(target, 0) * normalized_error

        return total_error, errors

    def evaluate_fitness(self,
                         params: Dict[str, float],
                         method: str = 'rmse') -> Tuple[float, Dict[str, Any]]:
        """评估参数的适应度（用于优化算法）

        Args:
            params: 参数字典
            method: 误差计算方法

        Returns:
            (适应度值, 详细信息字典)
        """
        # 合并固定参数
        full_params = self.fixed_params.copy()
        full_params.update(params)

        # 运行模型
        try:
            simulated = self.model_runner(full_params)

            if simulated is None or len(simulated) == 0:
                return 1e10, {'error': '模型运行失败', 'errors': {}}

            # 计算加权误差
            total_error, errors = self.calculate_weighted_error(simulated, method)

            details = {
                'total_error': total_error,
                'errors': errors,
                'method': method,
            }

            return total_error, details

        except Exception as e:
            logger.warning(f"模型运行失败: {e}")
            return 1e10, {'error': str(e), 'errors': {}}


class EpsilonConstraintOptimizer(MultiObjectiveOptimizer):
    """ε-约束法多目标优化器

    将主要目标优化，其他目标作为约束
    """

    def __init__(self,
                 observed_data: pd.DataFrame,
                 model_runner: Callable,
                 target_variables: List[str],
                 primary_target: str,
                 epsilon_constraints: Dict[str, float] = None,
                 fixed_params: Dict[str, Any] = None):
        """初始化ε-约束优化器

        Args:
            observed_data: 观测数据
            model_runner: 模型运行函数
            target_variables: 目标变量列表
            primary_target: 主要优化目标
            epsilon_constraints: 其他目标的约束 (如 {'Biomass': 0.1, 'CH4': 0.2})
            fixed_params: 固定参数
        """
        super().__init__(
            observed_data=observed_data,
            model_runner=model_runner,
            target_variables=target_variables,
            fixed_params=fixed_params
        )

        self.primary_target = primary_target
        self.epsilon_constraints = epsilon_constraints or {}

        logger.info(f"ε-约束优化器: 主要目标={primary_target}")
        logger.info(f"约束: {self.epsilon_constraints}")

    def evaluate_fitness(self,
                         params: Dict[str, float],
                         method: str = 'rmse') -> Tuple[float, Dict[str, Any]]:
        """评估适应度（带约束）

        如果违反约束，返回极大惩罚值
        """
        # 调用父类方法
        total_error, details = super().evaluate_fitness(params, method)

        # 检查约束
        constraint_penalty = 0.0
        violated_constraints = []

        for target, epsilon in self.epsilon_constraints.items():
            if target == self.primary_target:
                continue

            if target in details['errors']:
                error = details['errors'][target]['normalized']

                if error > epsilon:
                    # 违反约束，施加惩罚
                    penalty = (error - epsilon) * 1000  # 惩罚系数
                    constraint_penalty += penalty
                    violated_constraints.append(target)

        details['constraint_penalty'] = constraint_penalty
        details['violated_constraints'] = violated_constraints

        if violated_constraints:
            details['status'] = 'constraint_violated'
            return total_error + constraint_penalty, details
        else:
            details['status'] = 'feasible'
            return total_error, details


def create_multi_objective_optimizer(observed_data: pd.DataFrame,
                                      model_runner: Callable,
                                      target_variables: List[str],
                                      method: str = 'weighted',
                                      **kwargs) -> MultiObjectiveOptimizer:
    """便捷函数：创建多目标优化器

    Args:
        observed_data: 观测数据
        model_runner: 模型运行函数
        target_variables: 目标变量列表
        method: 优化方法 ('weighted' 或 'epsilon')
        **kwargs: 其他参数

    Returns:
        多目标优化器实例
    """
    if method == 'epsilon':
        return EpsilonConstraintOptimizer(
            observed_data=observed_data,
            model_runner=model_runner,
            target_variables=target_variables,
            **kwargs
        )
    else:
        return MultiObjectiveOptimizer(
            observed_data=observed_data,
            model_runner=model_runner,
            target_variables=target_variables,
            **kwargs
        )


if __name__ == '__main__':
    # 测试代码
    print("多目标优化模块")

    # 创建测试数据
    observed = pd.DataFrame({
        'DAT': [0, 30, 60, 90, 120],
        'Biomass': [0, 3000, 8000, 12000, 15000],
        'CH4': [0, 0.1, 0.3, 0.5, 0.4],
    })

    # 创建测试模型
    def test_model(params):
        return pd.DataFrame({
            'DAT': observed['DAT'],
            'Biomass': observed['Biomass'] * params.get('scale', 1.0),
            'CH4': observed['CH4'] * params.get('scale', 1.0),
        })

    # 测试多目标优化器
    optimizer = create_multi_objective_optimizer(
        observed_data=observed,
        model_runner=test_model,
        target_variables=['Biomass', 'CH4'],
        weights={'Biomass': 0.6, 'CH4': 0.4},
    )

    print('✅ 多目标优化器创建成功')
    print(f'目标变量: {optimizer.target_variables}')
    print(f'权重: {optimizer.weights}')

    # 测试适应度评估
    test_params = {'scale': 0.9}
    fitness, details = optimizer.evaluate_fitness(test_params)

    print(f'\\n测试适应度评估:')
    print(f'总误差: {fitness:.4f}')
    print(f'各目标误差: {details}')

    # 测试ε-约束优化器
    epsilon_optimizer = create_multi_objective_optimizer(
        observed_data=observed,
        model_runner=test_model,
        target_variables=['Biomass', 'CH4'],
        method='epsilon',
        primary_target='Biomass',
        epsilon_constraints={'CH4': 0.1},
    )

    print('\\n✅ ε-约束优化器创建成功')

    fitness2, details2 = epsilon_optimizer.evaluate_fitness(test_params)
    print(f'ε-约束适应度: {fitness2:.4f}')
    print(f'状态: {details2.get("status", "unknown")}')

    print('\\n✅ 多目标优化模块测试通过！')
