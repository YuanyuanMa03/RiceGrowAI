"""
目标函数包装器
将模型运行包装为优化器可调用的函数
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path
import sys
import logging

logger = logging.getLogger('rice_app')

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

from models.Ricegrow_py_v1_0 import CalFun
from models.RG2CH4 import CH4Flux_coupled
from config import DATA_DIR, ENCODING_FALLBACK


class ObjectiveWrapper:
    """目标函数包装器 - 连接优化器和模型"""

    def __init__(self,
                 observed_data: pd.DataFrame,
                 weather_data: pd.DataFrame,
                 fixed_params: Dict[str, Any],
                 optimize_target: str = 'both'):
        """
        Args:
            observed_data: 观测数据（包含生物量、CH4排放等）
            weather_data: 气象数据
            fixed_params: 固定参数（不参与优化的参数）
            optimize_target: 优化目标 ('cultivar', 'ch4', 'both')
        """
        self.observed_data = observed_data
        self.weather_data = weather_data
        self.fixed_params = fixed_params
        self.optimize_target = optimize_target

        # 验证观测数据
        self._validate_observed_data()

        # 缓存结果以提高性能
        self._cache = {}

    def _validate_observed_data(self):
        """增强的观测数据验证"""
        # 1. 检查必需列
        required_columns = ['DAT']
        for col in required_columns:
            if col not in self.observed_data.columns:
                raise ValueError(f"观测数据缺少必需列: {col}")

        # 2. 检查是否有观测值
        value_columns = ['Biomass', 'CH4']
        has_values = any(col in self.observed_data.columns for col in value_columns)

        if not has_values:
            raise ValueError("观测数据必须包含 Biomass 或 CH4 列")

        # 3. 检查DAT列的唯一性
        if self.observed_data['DAT'].duplicated().any():
            dupes = self.observed_data['DAT'].duplicated().sum()
            raise ValueError(f"DAT列包含 {dupes} 个重复值，每个DAT必须是唯一的")

        # 4. 检查数值范围
        if 'DAT' in self.observed_data.columns:
            dat_min = self.observed_data['DAT'].min()
            dat_max = self.observed_data['DAT'].max()
            if dat_min < 1 or dat_max > 365:
                logger.warning(f"DAT值范围异常 [{dat_min}, {dat_max}]，通常应在1-365之间")

        # 5. 检查生物量数据（如果存在）
        if 'Biomass' in self.observed_data.columns:
            if (self.observed_data['Biomass'] < 0).any():
                raise ValueError("生物量数据不能包含负值")
            if (self.observed_data['Biomass'] > 50000).any():  # kg/ha
                logger.warning("生物量数据包含异常高值（>50000 kg/ha），请检查单位是否正确")

        # 6. 检查CH4数据（如果存在）
        if 'CH4' in self.observed_data.columns:
            if (self.observed_data['CH4'] < 0).any():
                raise ValueError("CH4排放数据不能包含负值")
            if (self.observed_data['CH4'] > 100).any():  # g/m²/day
                logger.warning("CH4排放数据包含异常高值（>100 g/m²/day），请检查单位是否正确")

        # 7. 检查缺失值比例
        total_cells = len(self.observed_data) * len(self.observed_data.columns)
        missing_cells = self.observed_data.isna().sum().sum()
        missing_ratio = missing_cells / total_cells if total_cells > 0 else 0

        if missing_ratio > 0.5:
            logger.warning(f"观测数据缺失值比例较高: {missing_ratio:.1%}")

        # 8. 检查观测点数量
        n_observations = len(self.observed_data)
        if n_observations < 3:
            raise ValueError(f"观测数据点过少（{n_observations}个），建议至少3个观测点")
        elif n_observations < 10:
            logger.warning(f"观测数据点较少（{n_observations}个），建议增加观测点以提高拟合精度")

        logger.info(f"观测数据验证通过: {n_observations} 条记录")

    def __call__(self, optimized_params: Dict[str, float]) -> pd.DataFrame:
        """
        运行模型并返回结果 - 增强错误处理

        Args:
            optimized_params: 优化后的参数

        Returns:
            包含模拟值和观测值的数据框

        Raises:
            RuntimeError: 当模型运行失败时
        """
        # 合并参数
        all_params = {**self.fixed_params, **optimized_params}

        # 生成缓存键
        cache_key = tuple(sorted(all_params.items()))

        # 检查缓存
        if cache_key in self._cache:
            logger.debug("Using cached result")
            return self._cache[cache_key]

        try:
            # 运行模型
            if self.optimize_target in ['cultivar', 'both']:
                ricegrow_results = self._run_ricegrow(all_params)
            else:
                # 如果不优化品种参数，使用默认生物量
                logger.warning("未优化品种参数，使用默认生物量数据")
                ricegrow_results = self._generate_default_biomass()

            if self.optimize_target in ['ch4', 'both']:
                ch4_results = self._run_ch4_model(all_params, ricegrow_results)
            else:
                # 如果不优化CH4参数，使用默认CH4排放
                logger.warning("未优化CH4参数，使用默认CH4排放数据")
                ch4_results = self._generate_default_ch4()

            # 合并结果并与观测数据对齐
            combined_results = self._align_with_observed(
                ricegrow_results,
                ch4_results
            )

            # 缓存结果
            self._cache[cache_key] = combined_results

            return combined_results

        except RuntimeError as e:
            # 已经包装过的错误，直接传递
            raise
        except Exception as e:
            # 未预期的错误，包装并提供更多信息
            params_str = ", ".join([f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
                                   for k, v in optimized_params.items()])
            logger.error(f"模型运行失败，参数: {params_str}, 错误: {type(e).__name__}: {e}")
            raise RuntimeError(
                f"模型运行失败，参数组合可能不合理。"
                f"参数: {params_str}, 错误: {str(e)}"
            ) from e

    def _run_ricegrow(self, params: Dict[str, Any]) -> pd.DataFrame:
        """运行Ricegrow模型 - 增强错误处理"""
        try:
            # 提取品种参数
            cultivar_params = {
                'PS': params.get('PS', 0.065),
                'TS': params.get('TS', 2.75),
                'TO': params.get('TO', 27.5),
                'IE': params.get('IE', 0.16),
                'HF': params.get('HF', 0.012),
                'FDF': params.get('FDF', 0.47),
                'PHI': params.get('PHI', 200),
                'SLAc': params.get('SLAc', 0.015),
                'PF': params.get('PF', 46),
                'AMX': params.get('AMX', 45),
                'KF': params.get('KF', 0.0085),
                'TGW': params.get('TGW', 27),
                'RGC': params.get('RGC', 0.3),
                'LRS': params.get('LRS', 0.007),
                'TLN': params.get('TLN', 17.5),
                'EIN': params.get('EIN', 5),
                'TA': params.get('TA', 6.5),
                'SGP': params.get('SGP', 0.5),
                'PC': params.get('PC', 0.08),
                'RAR': params.get('RAR', 2),
            }

            # 构造品种参数DataFrame（模拟品种参数文件）
            cultivar_df = pd.DataFrame([cultivar_params])
            cultivar_df.insert(0, 'PZ', 'Optimized_Variety')

            # 保存临时品种参数文件
            temp_cultivar_path = PROJECT_ROOT / 'uploads' / 'temp_cultivar.csv'
            cultivar_df.to_csv(temp_cultivar_path, index=False, encoding='gbk')

            # 调用Ricegrow模型
            results = CalFun(
                FieldPath=str(DATA_DIR / '调参数据.csv'),
                WeatherPath=str(DATA_DIR / '气象数据.csv'),
                SoilFieldPath=str(DATA_DIR / '土壤数据.csv'),
                ResiduePath=str(DATA_DIR / '秸秆数据.csv'),
                PlantingPath=str(DATA_DIR / '管理数据_多种方案.csv'),
                CultivarPath=str(temp_cultivar_path),
                FertilizerPath=str(DATA_DIR / '施肥数据.csv')
            )

            # 验证结果
            if results is None or len(results) < 8:
                raise ValueError(f"Ricegrow模型返回结果异常: results={results}")

            # 检查结果长度
            expected_length = len(results[4]) if hasattr(results[4], '__len__') else 0
            if expected_length == 0:
                raise ValueError("Ricegrow模型返回空结果，可能是参数不合理导致模拟失败")

            # 构造结果DataFrame
            ricegrow_df = pd.DataFrame({
                'DAT': range(1, len(results[4]) + 1),
                'W': results[4],      # ATOPWTSeq - 地上部生物量
                'Wroot': results[0],  # AROOTWTSeq - 根系生物量
                'LAI': results[5],    # LAISeq - 叶面积指数
                'YIELD': results[7],  # YIELDSeq - 产量
            })

            logger.debug(f"Ricegrow模型运行完成: {len(ricegrow_df)} 天")
            return ricegrow_df

        except FileNotFoundError as e:
            logger.error(f"数据文件未找到: {e}")
            raise ValueError(f"缺少必需的数据文件: {e.filename}")
        except pd.errors.EmptyDataError as e:
            logger.error(f"数据文件为空: {e}")
            raise ValueError("数据文件格式错误或为空")
        except Exception as e:
            logger.error(f"Ricegrow模型运行失败: {type(e).__name__}: {e}")
            # 提供更详细的错误信息
            raise RuntimeError(f"模型运行失败: {type(e).__name__} - {str(e)}") from e

    def _run_ch4_model(self,
                      params: Dict[str, Any],
                      ricegrow_results: pd.DataFrame) -> pd.DataFrame:
        """运行CH4模型"""
        try:
            # 提取CH4模型参数
            ch4_params = {
                'Q10': params.get('Q10', 3.0),
                'Eh0': params.get('Eh0', 250),
                'EhBase': params.get('EhBase', -20),
                'WaterC': params.get('WaterC', 0.636),
                'Sand': params.get('Sand', 35.0),
                'OMS': params.get('OMS', 1300.0),
                'OMN': params.get('OMN', 1600.0),
                'IP': params.get('IP', 1),
            }

            # 确保气象数据长度匹配
            max_days = min(len(self.weather_data), len(ricegrow_results))

            # 调用CH4模型
            results = CH4Flux_coupled(
                day_begin=1,
                day_end=max_days,
                IP=ch4_params['IP'],
                sand=ch4_params['Sand'],
                Tair=self.weather_data['Tmax'].values[:max_days],
                OMS=ch4_params['OMS'],
                OMN=ch4_params['OMN'],
                ATOPWTSeq=ricegrow_results['W'].values[:max_days],
                AROOTWTSeq=ricegrow_results['Wroot'].values[:max_days]
            )

            logger.debug(f"CH4模型运行完成: {len(results)} 天")
            return results

        except Exception as e:
            logger.error(f"CH4模型运行失败: {e}")
            # 返回默认值
            return self._generate_default_ch4(len(ricegrow_results))

    def _generate_default_biomass(self) -> pd.DataFrame:
        """生成默认生物量数据（当模型运行失败时使用）"""
        max_days = len(self.observed_data)

        # 简单的S形曲线
        days = np.arange(1, max_days + 1)
        biomass = 150 * (1 / (1 + np.exp(-0.05 * (days - 50))))

        return pd.DataFrame({
            'DAT': days,
            'W': biomass,
            'Wroot': biomass * 0.15,
            'LAI': biomass * 0.04,
            'YIELD': 0
        })

    def _generate_default_ch4(self, n_days: Optional[int] = None) -> pd.DataFrame:
        """生成默认CH4数据（当模型运行失败时使用）"""
        if n_days is None:
            n_days = len(self.observed_data)

        days = np.arange(1, n_days + 1)
        # 简单的钟形曲线
        ch4 = 1.0 * np.exp(-0.001 * (days - 40) ** 2)

        return pd.DataFrame({
            'DAT': days,
            'E': ch4,
            'P': ch4 * 0.8,
            'Ebl': ch4 * 0.3,
            'Ep': ch4 * 0.5,
        })

    def _align_with_observed(self,
                            ricegrow_results: pd.DataFrame,
                            ch4_results: pd.DataFrame) -> pd.DataFrame:
        """将模拟结果与观测数据对齐"""
        # 合并模拟结果
        simulated = pd.merge(
            ricegrow_results[['DAT', 'W', 'Wroot', 'LAI', 'YIELD']],
            ch4_results[['DAT', 'E', 'P', 'Ebl', 'Ep']],
            on='DAT',
            how='outer'
        )

        # 与观测数据合并
        combined = pd.merge(
            simulated,
            self.observed_data,
            on='DAT',
            how='outer',
            suffixes=('_simulated', '_observed')
        )

        # 计算误差列
        if 'Biomass_observed' in combined.columns and 'W' in combined.columns:
            combined['Biomass_simulated'] = combined['W']

        if 'CH4_observed' in combined.columns and 'E' in combined.columns:
            combined['CH4_simulated'] = combined['E']

        # 创建通用的simulated和observed列用于误差计算
        if 'Biomass_observed' in combined.columns and 'Biomass_simulated' in combined.columns:
            combined['simulated'] = combined['Biomass_simulated']
            combined['observed'] = combined['Biomass_observed']
        elif 'CH4_observed' in combined.columns and 'CH4_simulated' in combined.columns:
            combined['simulated'] = combined['CH4_simulated']
            combined['observed'] = combined['CH4_observed']
        else:
            combined['simulated'] = np.nan
            combined['observed'] = np.nan

        return combined

    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
        logger.debug("Cache cleared")


def load_weather_data(weather_path: Optional[Path] = None) -> pd.DataFrame:
    """加载气象数据"""
    if weather_path is None:
        weather_path = DATA_DIR / '气象数据.csv'

    for encoding in ENCODING_FALLBACK:
        try:
            weather_data = pd.read_csv(weather_path, encoding=encoding)
            logger.info(f"成功加载气象数据: {len(weather_data)} 条记录 (编码: {encoding})")
            return weather_data
        except (UnicodeDecodeError, UnicodeError):
            continue

    raise ValueError(f"无法读取气象数据文件: {weather_path}")


def load_observed_data(observed_path: Path) -> pd.DataFrame:
    """加载观测数据"""
    for encoding in ENCODING_FALLBACK:
        try:
            observed_data = pd.read_csv(observed_path, encoding=encoding)
            logger.info(f"成功加载观测数据: {len(observed_data)} 条记录 (编码: {encoding})")
            return observed_data
        except (UnicodeDecodeError, UnicodeError):
            continue

    raise ValueError(f"无法读取观测数据文件: {observed_path}")