"""
PSO粒子群优化算法模块

基于论文《不确定条件下作物生育期模型品种参数自动校正框架》
实现标准PSO和自适应PSO算法
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Callable, Optional, Any
import logging

logger = logging.getLogger('rice_app')


class PSOOptimizer:
    """粒子群优化算法（Particle Swarm Optimization）"""

    def __init__(self,
                 observed_data: pd.DataFrame,
                 model_runner: Callable,
                 param_bounds: Dict[str, Tuple[float, float]],
                 n_particles: int = 50,
                 max_iter: int = 200,
                 w: float = 0.9,
                 c1: float = 2.0,
                 c2: float = 2.0,
                 w_decay: bool = True,
                 target_columns: List[str] = None,
                 fixed_params: Dict[str, Any] = None):
        """初始化PSO优化器

        Args:
            observed_data: 观测数据
            model_runner: 模型运行函数，接受参数字典，返回模拟结果
            param_bounds: 参数边界 {param_name: (lower, upper)}
            n_particles: 粒子数量
            max_iter: 最大迭代次数
            w: 惯性权重
            c1: 个体学习因子
            c2: 社会学习因子
            w_decay: 是否使用惯性权重衰减
            target_columns: 目标列名（如 ['Biomass', 'CH4']）
            fixed_params: 固定参数
        """
        self.observed_data = observed_data
        self.model_runner = model_runner
        self.param_bounds = param_bounds
        self.n_particles = n_particles
        self.max_iter = max_iter
        self.w_init = w
        self.c1 = c1
        self.c2 = c2
        self.w_decay = w_decay
        self.target_columns = target_columns or ['Biomass', 'CH4']
        self.fixed_params = fixed_params or {}

        # 参数名列表
        self.param_names = list(param_bounds.keys())
        self.n_dim = len(self.param_names)

        # 边界数组
        self.lower_bounds = np.array([param_bounds[p][0] for p in self.param_names])
        self.upper_bounds = np.array([param_bounds[p][1] for p in self.param_names])

        # 优化结果
        self.best_position = None
        self.best_fitness = float('inf')
        self.fitness_history = []
        self.position_history = []

        logger.info(f"PSO优化器初始化: {self.n_dim}个参数, {n_particles}个粒子, {max_iter}次迭代")

    def _evaluate_fitness(self, position: np.ndarray) -> float:
        """计算适应度（误差函数）

        Args:
            position: 粒子位置向量

        Returns:
            适应度值（越小越好）
        """
        # 转换为参数字典
        params = {self.param_names[i]: position[i] for i in range(self.n_dim)}

        # 合并固定参数
        full_params = self.fixed_params.copy()
        full_params.update(params)

        # 运行模型
        try:
            simulated = self.model_runner(full_params)

            if simulated is None or len(simulated) == 0:
                return 1e10  # 模型失败惩罚

            # 计算误差
            error = 0.0
            n_valid = 0

            for target in self.target_columns:
                if target not in self.observed_data.columns:
                    continue

                if target not in simulated.columns:
                    continue

                # 对齐数据
                obs = self.observed_data[target].values
                sim = simulated[target].values

                # 只计算共同部分
                valid = ~(np.isnan(obs) | np.isnan(sim))
                if valid.sum() > 0:
                    obs_valid = obs[valid]
                    sim_valid = sim[valid]

                    # RMSE
                    rmse = np.sqrt(np.mean((obs_valid - sim_valid) ** 2))

                    # 归一化（相对于数据范围）
                    data_range = obs_valid.max() - obs_valid.min()
                    if data_range > 0:
                        normalized_error = rmse / data_range
                    else:
                        normalized_error = rmse

                    error += normalized_error
                    n_valid += 1

            if n_valid > 0:
                return error / n_valid
            else:
                return 1e10

        except Exception as e:
            logger.warning(f"模型运行失败: {e}")
            return 1e10

    def _initialize_particles(self) -> Tuple[np.ndarray, np.ndarray]:
        """初始化粒子位置和速度

        Returns:
            (positions, velocities)
        """
        # 位置：随机采样
        positions = np.random.uniform(
            low=self.lower_bounds,
            high=self.upper_bounds,
            size=(self.n_particles, self.n_dim)
        )

        # 速度：初始化为0
        velocities = np.zeros((self.n_particles, self.n_dim))

        return positions, velocities

    def _update_velocity(self,
                         positions: np.ndarray,
                         velocities: np.ndarray,
                         pbest_positions: np.ndarray,
                         pbest_fitness: np.ndarray,
                         gbest_position: np.ndarray,
                         w: float) -> np.ndarray:
        """更新粒子速度

        Args:
            positions: 当前位置
            velocities: 当前速度
            pbest_positions: 个体历史最优位置
            pbest_fitness: 个体历史最优适应度
            gbest_position: 全局最优位置
            w: 惯性权重

        Returns:
            更新后的速度
        """
        r1 = np.random.random((self.n_particles, self.n_dim))
        r2 = np.random.random((self.n_particles, self.n_dim))

        # 认知部分
        cognitive = self.c1 * r1 * (pbest_positions - positions)

        # 社会部分
        social = self.c2 * r2 * (gbest_position - positions)

        # 速度更新
        new_velocities = w * velocities + cognitive + social

        return new_velocities

    def _apply_constraints(self, positions: np.ndarray) -> np.ndarray:
        """应用边界约束

        Args:
            positions: 粒子位置

        Returns:
            约束后的位置
        """
        # 裁剪到边界
        constrained = np.clip(positions, self.lower_bounds, self.upper_bounds)

        return constrained

    def optimize(self,
                 callback: Optional[Callable] = None,
                 verbose: bool = True) -> Dict[str, Any]:
        """运行PSO优化

        Args:
            callback: 迭代回调函数，参数为 (iter, best_fitness, positions)
            verbose: 是否打印进度

        Returns:
            优化结果字典
        """
        # 初始化粒子
        positions, velocities = self._initialize_particles()

        # 个体历史最优
        pbest_positions = positions.copy()
        pbest_fitness = np.array([self._evaluate_fitness(p) for p in positions])

        # 全局最优
        gbest_idx = np.argmin(pbest_fitness)
        gbest_position = pbest_positions[gbest_idx].copy()
        gbest_fitness = pbest_fitness[gbest_idx]

        logger.info("开始PSO优化...")

        # 主循环
        no_improve_count = 0
        for iteration in range(self.max_iter):
            # 惯性权重衰减
            if self.w_decay:
                w = self.w_init - (self.w_init - 0.4) * (iteration / self.max_iter)
            else:
                w = self.w_init

            # 更新速度
            velocities = self._update_velocity(
                positions, velocities,
                pbest_positions, pbest_fitness,
                gbest_position, w
            )

            # 更新位置
            positions = positions + velocities
            positions = self._apply_constraints(positions)

            # 评估适应度
            fitness = np.array([self._evaluate_fitness(p) for p in positions])

            # 更新个体最优
            improved = fitness < pbest_fitness
            pbest_positions[improved] = positions[improved]
            pbest_fitness[improved] = fitness[improved]

            # 更新全局最优
            current_best_idx = np.argmin(pbest_fitness)
            current_best_fitness = pbest_fitness[current_best_idx]

            if current_best_fitness < gbest_fitness:
                gbest_position = pbest_positions[current_best_idx].copy()
                gbest_fitness = current_best_fitness
                no_improve_count = 0

                if verbose:
                    logger.info(f"迭代 {iteration+1}: 新最优适应度 = {gbest_fitness:.6f}")
            else:
                no_improve_count += 1

            # 记录历史
            self.fitness_history.append(gbest_fitness)
            self.position_history.append(gbest_position.copy())

            # 回调
            if callback:
                callback(iteration, gbest_fitness, positions)

            # 早停：连续50代无改进
            if no_improve_count >= 50:
                logger.info(f"早停触发：连续50代无改进")
                break

        # 保存结果
        self.best_position = gbest_position
        self.best_fitness = gbest_fitness

        # 转换为参数字典
        best_params = {self.param_names[i]: gbest_position[i] for i in range(self.n_dim)}

        logger.info(f"PSO优化完成: 最优适应度 = {gbest_fitness:.6f}")

        return {
            'best_params': best_params,
            'best_fitness': float(gbest_fitness),
            'fitness_history': self.fitness_history,
            'position_history': self.position_history,
            'n_iterations': len(self.fitness_history),
        }

    def get_best_params(self) -> Dict[str, float]:
        """获取最优参数"""
        if self.best_position is None:
            raise ValueError("请先运行 optimize()")
        return {self.param_names[i]: self.best_position[i] for i in range(self.n_dim)}


class AdaptivePSOOptimizer(PSOOptimizer):
    """自适应PSO优化器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.adaptive_params = {
            'w': self.w_init,
            'c1': self.c1,
            'c2': self.c2,
        }

    def _update_velocity(self,
                         positions: np.ndarray,
                         velocities: np.ndarray,
                         pbest_positions: np.ndarray,
                         pbest_fitness: np.ndarray,
                         gbest_position: np.ndarray,
                         w: float) -> np.ndarray:
        """更新粒子速度（自适应）"""
        # 根据收敛状态自适应调整参数
        diversity = np.mean(np.std(positions, axis=0))

        if diversity < 0.1:  # 种群多样性低，增加探索
            w = min(w * 1.05, 0.95)
            self.c1 = min(self.c1 * 1.02, 2.5)
            self.c2 = max(self.c2 * 0.98, 1.5)
        else:  # 种群多样性高，增加开发
            w = max(w * 0.98, 0.4)
            self.c1 = max(self.c1 * 0.98, 1.5)
            self.c2 = min(self.c2 * 1.02, 2.5)

        return super()._update_velocity(
            positions, velocities,
            pbest_positions, pbest_fitness,
            gbest_position, w
        )


def create_pso_optimizer(observed_data: pd.DataFrame,
                         model_runner: Callable,
                         param_bounds: Dict[str, Tuple[float, float]],
                         n_particles: int = 50,
                         max_iter: int = 200,
                         adaptive: bool = False,
                         **kwargs) -> PSOOptimizer:
    """便捷函数：创建PSO优化器

    Args:
        observed_data: 观测数据
        model_runner: 模型运行函数
        param_bounds: 参数边界
        n_particles: 粒子数
        max_iter: 最大迭代
        adaptive: 是否使用自适应PSO
        **kwargs: 其他参数

    Returns:
        PSO优化器实例
    """
    if adaptive:
        return AdaptivePSOOptimizer(
            observed_data=observed_data,
            model_runner=model_runner,
            param_bounds=param_bounds,
            n_particles=n_particles,
            max_iter=max_iter,
            **kwargs
        )
    else:
        return PSOOptimizer(
            observed_data=observed_data,
            model_runner=model_runner,
            param_bounds=param_bounds,
            n_particles=n_particles,
            max_iter=max_iter,
            **kwargs
        )


if __name__ == '__main__':
    # 测试代码
    print("PSO优化器模块")

    # 创建测试问题（Rastrigin函数）
    def rastrigin(x):
        """Rastrigin函数 - 多模态优化测试"""
        n = len(x)
        return 10 * n + sum([(xi ** 2 - 10 * np.cos(2 * np.pi * xi)) for xi in x])

    class TestRunner:
        def __init__(self):
            pass

        def __call__(self, params):
            # 简单返回适应度
            result = pd.DataFrame({'fitness': [rastrigin(list(params.values()))]})
            return result

    # 测试优化器
    bounds = {f'x{i}': (-5.12, 5.12) for i in range(5)}

    optimizer = create_pso_optimizer(
        observed_data=pd.DataFrame({'test': [0]}),
        model_runner=TestRunner(),
        param_bounds=bounds,
        n_particles=30,
        max_iter=50,
    )

    result = optimizer.optimize(verbose=True)

    print(f"\n最优适应度: {result['best_fitness']:.4f}")
    print(f"最优位置: {[f'{v:.4f}' for v in result['best_params'].values()]}")
