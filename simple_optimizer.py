"""
简化的水稻模型参数校准系统
支持多种优化算法：随机采样、遗传算法、差分进化、贝叶斯优化
"""
import sys
import os
import tempfile
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Callable, Optional, Any
import logging
from datetime import datetime
import time
import json

logger = logging.getLogger('rice_app')

PROJECT_ROOT = Path(__file__).parent


class SimpleParameterOptimizer:
    """简化的参数优化器 - 专注于稳定性"""

    def __init__(self,
                 observed_data: pd.DataFrame,
                 weather_data: pd.DataFrame,
                 parameter_bounds: Dict[str, Tuple[float, float]],
                 fixed_params: Dict[str, Any],
                 algorithm: str = 'random',
                 n_iterations: int = 100,
                 target_columns: List[str] = None,
                 use_custom_files: bool = False):
        """
        Args:
            observed_data: 观测数据（必须包含DAT列）
            weather_data: 气象数据
            parameter_bounds: 参数边界 {参数名: (最小值, 最大值)}
            fixed_params: 固定参数
            algorithm: 优化算法 ('random', 'differential_evolution', 'genetic', 'bayes')
            n_iterations: 迭代次数
            target_columns: 目标列（如 ['Biomass', 'CH4']）
            use_custom_files: 是否使用上传的自定义文件
        """
        self.observed_data = observed_data
        self.weather_data = weather_data
        self.parameter_bounds = parameter_bounds
        self.fixed_params = fixed_params
        self.algorithm = algorithm
        self.n_iterations = n_iterations
        self.target_columns = target_columns or ['Biomass', 'CH4']
        self.use_custom_files = use_custom_files

        # 过滤掉观测数据中不存在的目标列
        self.target_columns = [col for col in self.target_columns if col in observed_data.columns]

        # 结果存储
        self.best_params = None
        self.best_error = float('inf')
        self.history = []
        self.start_time = None

        # 验证数据
        self._validate_data()

    def _get_data_path(self, filename: str) -> Path:
        """获取数据文件路径（根据 use_custom_files 选择）"""
        from config import DATA_DIR, UPLOADS_DIR

        # 如果启用自定义文件且上传的文件存在，使用上传的文件
        if self.use_custom_files:
            custom_path = UPLOADS_DIR / filename
            if custom_path.exists():
                return custom_path

        return DATA_DIR / filename

    def _validate_data(self):
        """验证输入数据"""
        if 'DAT' not in self.observed_data.columns:
            raise ValueError("观测数据必须包含 DAT 列")

        if not self.target_columns:
            raise ValueError("观测数据必须包含至少一个目标列 (Biomass 或 CH4)")

        if self.weather_data is None or len(self.weather_data) == 0:
            raise ValueError("气象数据不能为空")

        logger.info(f"数据验证通过: {len(self.observed_data)} 条观测, "
                   f"目标列: {self.target_columns}")

    def _create_test_cultivar_file(self, params: Dict[str, float]) -> Path:
        """创建临时品种参数文件"""
        # 默认品种参数（从配置中获取）
        default_params = {
            'PZ': 'Calibrated',
            'PS': params.get('PS', 0.065),
            'TS': params.get('TS', 2.75),
            'TO': params.get('TO', 27.5),
            'IE': params.get('IE', 0.16),
            'HF': params.get('HF', 0.012),
            'FDF': params.get('FDF', 0.715),
            'PHI': params.get('PHI', 0.45),  # ✅ 修正：原为 200
            'SLAc': params.get('SLAc', 198),
            'PF': params.get('PF', 0.015),
            'AMX': params.get('AMX', 45),
            'KF': params.get('KF', 0.0085),
            'TGW': params.get('TGW', 27),
            'RGC': params.get('RGC', 0.3),
            'LRS': params.get('LRS', 0.007),
            'TLN': params.get('TLN', 17.5),
            'EIN': params.get('EIN', 5),
            'TA': params.get('TA', 6.5),
            'SGP': params.get('SGP', 0.47),
            'PC': params.get('PC', 0.08),
            'RAR': params.get('RAR', 2.1),
        }

        df = pd.DataFrame([default_params])
        fd, tmp = tempfile.mkstemp(suffix='_cultivar.csv', prefix='rch4_opt_')
        os.close(fd)
        temp_path = Path(tmp)
        df.to_csv(temp_path, index=False, encoding='gbk')
        return temp_path

    def _run_model(self, params: Dict[str, float]) -> Optional[pd.DataFrame]:
        """运行模型并返回结果"""
        try:
            # 动态导入（避免循环依赖）
            sys.path.append(str(PROJECT_ROOT))

            from models.Ricegrow_py_v1_0 import CalFun
            from models.RG2CH4 import CH4Flux_coupled

            # 创建品种参数文件
            cultivar_path = self._create_test_cultivar_file(params)

            # 获取数据文件路径（支持自定义文件）
            field_path = self._get_data_path('调参数据.csv')
            weather_path = self._get_data_path('气象数据.csv')
            soil_path = self._get_data_path('土壤数据.csv')
            residue_path = self._get_data_path('秸秆数据.csv')
            planting_path = self._get_data_path('管理数据_多种方案.csv')
            fertilizer_path = self._get_data_path('施肥数据.csv')

            # 运行 Ricegrow 模型
            results = CalFun(
                FieldPath=str(field_path),
                WeatherPath=str(weather_path),
                SoilFieldPath=str(soil_path),
                ResiduePath=str(residue_path),
                PlantingPath=str(planting_path),
                CultivarPath=str(cultivar_path),
                FertilizerPath=str(fertilizer_path)
            )

            # 构造结果 - 运行整个生育期
            # 获取调参数据中的生育期长度
            try:
                field_df = pd.read_csv(field_path, encoding='gbk')
                maturity_days = field_df['maturity'].iloc[0]  # 成熟期天数
                max_days = min(len(results[4]), maturity_days)  # 使用完整生育期
            except Exception:
                max_days = len(results[4])  # 默认使用所有可用天数

            simulated = pd.DataFrame({
                'DAT': range(1, max_days + 1),
                'Biomass': results[4][:max_days],  # 地上部生物量
            })

            # 运行 CH4 模型（如果需要）
            if 'CH4' in self.target_columns:
                ch4_params = {
                    'Q10': params.get('Q10', 3.0),
                    'Eh0': params.get('Eh0', 250),
                    'EhBase': params.get('EhBase', -20),
                    'WaterC': params.get('WaterC', 0.636),
                    'IP': self.fixed_params.get('IP', 1),
                    'sand': self.fixed_params.get('Sand', 35.0),
                    'OMS': self.fixed_params.get('OMS', 1300.0),
                    'OMN': self.fixed_params.get('OMN', 1600.0),
                }

                ch4_result = CH4Flux_coupled(
                    day_begin=1,
                    day_end=max_days,
                    IP=ch4_params['IP'],
                    sand=ch4_params['sand'],
                    Tair=self.weather_data['Tmax'].values[:max_days],
                    OMS=ch4_params['OMS'],
                    OMN=ch4_params['OMN'],
                    ATOPWTSeq=results[4][:max_days],
                    AROOTWTSeq=results[0][:max_days]
                )

                simulated['CH4'] = ch4_result['E'].values[:max_days]

            return simulated

        except Exception as e:
            logger.debug(f"模型运行失败: {type(e).__name__}: {e}")
            return None

    def _calculate_error(self, simulated: pd.DataFrame) -> float:
        """计算模拟与观测的误差"""
        if simulated is None:
            return 1e6

        total_error = 0
        count = 0

        for target_col in self.target_columns:
            if target_col not in simulated.columns:
                continue

            # 合并观测和模拟数据
            merged = pd.merge(
                self.observed_data[['DAT', target_col]],
                simulated[['DAT', target_col]],
                on='DAT',
                how='inner',
                suffixes=('_obs', '_sim')
            )

            if len(merged) == 0:
                continue

            # 计算 RMSE
            y_true = merged[f'{target_col}_obs'].values
            y_pred = merged[f'{target_col}_sim'].values

            # 移除NaN
            mask = ~(np.isnan(y_true) | np.isnan(y_pred))
            y_true = y_true[mask]
            y_pred = y_pred[mask]

            if len(y_true) == 0:
                continue

            rmse = np.sqrt(np.mean((y_pred - y_true) ** 2))

            # 归一化误差
            y_range = y_true.max() - y_true.min()
            if y_range > 0:
                normalized_rmse = rmse / y_range
            else:
                normalized_rmse = rmse

            total_error += normalized_rmse
            count += 1

        if count == 0:
            return 1e6

        return total_error / count

    def _random_search(self) -> Dict[str, Any]:
        """随机搜索算法"""
        logger.info("使用随机搜索算法")

        for i in range(self.n_iterations):
            # 随机采样参数
            params = {}
            for param_name, (min_val, max_val) in self.parameter_bounds.items():
                params[param_name] = np.random.uniform(min_val, max_val)

            # 运行模型
            simulated = self._run_model(params)
            error = self._calculate_error(simulated)

            # 记录历史
            self.history.append({
                'iteration': i,
                'params': params.copy(),
                'error': error,
                'timestamp': datetime.now().isoformat()
            })

            # 更新最佳参数
            if error < self.best_error:
                self.best_error = error
                self.best_params = params.copy()
                logger.info(f"迭代 {i}: 新最佳误差 = {error:.6f}")

            # 进度报告
            if (i + 1) % 10 == 0 or i == 0:
                elapsed = time.time() - self.start_time
                logger.info(f"进度: {i + 1}/{self.n_iterations} | "
                           f"当前误差: {error:.6f} | 最佳误差: {self.best_error:.6f} | "
                           f"耗时: {elapsed:.1f}s")

        return {
            'best_params': self.best_params,
            'best_error': self.best_error,
            'history': self.history
        }

    def _differential_evolution(self) -> Dict[str, Any]:
        """差分进化算法（使用scipy）"""
        from scipy.optimize import differential_evolution
        import sys

        logger.info("使用差分进化算法")

        # 准备边界
        bounds = [self.parameter_bounds[k] for k in sorted(self.parameter_bounds.keys())]
        param_names = sorted(self.parameter_bounds.keys())

        def objective_function(x):
            params = dict(zip(param_names, x))
            simulated = self._run_model(params)
            error = self._calculate_error(simulated)

            # 记录
            self.history.append({
                'iteration': len(self.history),
                'params': params.copy(),
                'error': error,
                'timestamp': datetime.now().isoformat()
            })

            if error < self.best_error:
                self.best_error = error
                self.best_params = params.copy()

            return error

        # 运行优化
        result = differential_evolution(
            objective_function,
            bounds,
            maxiter=self.n_iterations,
            seed=42,
            disp=True
        )

        return {
            'best_params': dict(zip(param_names, result.x)),
            'best_error': result.fun,
            'history': self.history
        }

    def optimize(self) -> Dict[str, Any]:
        """执行优化"""
        self.start_time = time.time()
        logger.info("=" * 60)
        logger.info("开始参数优化")
        logger.info(f"  算法: {self.algorithm}")
        logger.info(f"  迭代次数: {self.n_iterations}")
        logger.info(f"  参数数量: {len(self.parameter_bounds)}")
        logger.info(f"  目标列: {self.target_columns}")
        logger.info("=" * 60)

        try:
            if self.algorithm == 'random':
                result = self._random_search()
            elif self.algorithm == 'differential_evolution':
                result = self._differential_evolution()
            else:
                logger.warning(f"未知算法 {self.algorithm}，使用随机搜索")
                result = self._random_search()

            elapsed = time.time() - self.start_time
            logger.info("=" * 60)
            logger.info("优化完成")
            logger.info(f"  最佳误差: {result['best_error']:.6f}")
            logger.info(f"  总耗时: {elapsed:.2f}s")
            logger.info(f"  成功评估: {len([h for h in self.history if h['error'] < 1e6])}")
            logger.info("=" * 60)

            result['elapsed_time'] = elapsed
            return result

        except Exception as e:
            logger.error(f"优化失败: {type(e).__name__}: {e}")
            raise


# ===== 便捷函数 =====

def load_observed_data_simple(file_path: Path) -> pd.DataFrame:
    """简化版观测数据加载"""
    encodings = ['utf-8', 'gbk', 'gb2312']

    for encoding in encodings:
        try:
            df = pd.read_csv(file_path, encoding=encoding)

            # 清理列名（移除空格和特殊字符）
            df.columns = df.columns.str.strip()

            # 检查必需列
            if 'DAT' not in df.columns:
                # 可能是中文列名
                if '天数' in df.columns or 'dat' in df.columns:
                    df.rename(columns={'天数': 'DAT', 'dat': 'DAT'}, inplace=True)
                else:
                    raise ValueError(f"找不到 DAT 列，现有列: {df.columns.tolist()}")

            logger.info(f"成功加载观测数据: {len(df)} 行, 编码: {encoding}")
            return df

        except (UnicodeDecodeError, UnicodeError):
            continue

    raise ValueError(f"无法读取文件: {file_path}")


def load_weather_data_simple() -> pd.DataFrame:
    """简化版气象数据加载"""
    from config import DATA_DIR
    weather_path = DATA_DIR / '气象数据.csv'

    encodings = ['utf-8', 'gbk', 'gb2312']

    for encoding in encodings:
        try:
            df = pd.read_csv(weather_path, encoding=encoding)
            logger.info(f"成功加载气象数据: {len(df)} 行, 编码: {encoding}")
            return df
        except (UnicodeDecodeError, UnicodeError):
            continue

    raise ValueError(f"无法读取气象数据: {weather_path}")


def run_simple_optimization(observed_file: Path,
                           parameter_bounds: Dict[str, Tuple[float, float]],
                           fixed_params: Dict[str, Any],
                           algorithm: str = 'random',
                           n_iterations: int = 50) -> Dict[str, Any]:
    """运行简化的优化流程

    Args:
        observed_file: 观测数据文件路径
        parameter_bounds: 参数边界
        fixed_params: 固定参数
        algorithm: 优化算法
        n_iterations: 迭代次数

    Returns:
        优化结果字典
    """
    # 加载数据
    observed_data = load_observed_data_simple(observed_file)
    weather_data = load_weather_data_simple()

    # 创建优化器
    optimizer = SimpleParameterOptimizer(
        observed_data=observed_data,
        weather_data=weather_data,
        parameter_bounds=parameter_bounds,
        fixed_params=fixed_params,
        algorithm=algorithm,
        n_iterations=n_iterations
    )

    # 执行优化
    result = optimizer.optimize()

    # 保存结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_path = PROJECT_ROOT / 'uploads' / f'optimization_{timestamp}.json'

    save_data = {
        'best_params': result['best_params'],
        'best_error': float(result['best_error']),
        'elapsed_time': result['elapsed_time'],
        'algorithm': algorithm,
        'n_iterations': n_iterations,
        'timestamp': datetime.now().isoformat()
    }

    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    logger.info(f"结果已保存: {result_path}")

    return result
