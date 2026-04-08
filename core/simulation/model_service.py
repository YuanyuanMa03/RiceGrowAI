"""
模型服务层

提供统一的模型调用接口，封装水稻生长模型和CH4排放模型的调用逻辑。
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger('rice_app')

# 导入配置和异常
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import DATA_DIR
from core.exceptions import (
    ModelRunError,
    ModelNotFoundError,
    ParameterError,
    ParameterOutOfBoundsError,
)


@dataclass
class SimulationResult:
    """模拟结果数据类"""
    data: pd.DataFrame
    success: bool
    error: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

    @property
    def biomass(self) -> pd.Series:
        """获取生物量序列"""
        if 'Biomass' in self.data.columns:
            return self.data['Biomass']
        raise KeyError("结果中不包含 Biomass 列")

    @property
    def ch4(self) -> Optional[pd.Series]:
        """获取CH4排放序列"""
        if 'CH4' in self.data.columns:
            return self.data['CH4']
        return None

    @property
    def final_yield(self) -> Optional[float]:
        """获取最终产量"""
        if 'Yield' in self.data.columns:
            return self.data['Yield'].iloc[-1]
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'error': self.error,
            'warnings': self.warnings,
            'rows': len(self.data),
            'columns': list(self.data.columns),
        }


class ModelService:
    """模型服务类

    统一管理水稻生长模型和CH4排放模型的调用。
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """初始化模型服务

        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = data_dir or DATA_DIR
        self._cultivar_cache: Dict[str, Path] = {}

        # 验证必需文件存在
        self._validate_data_files()

    def _validate_data_files(self) -> None:
        """验证数据文件完整性"""
        required_files = [
            '调参数据.csv',
            '气象数据.csv',
            '土壤数据.csv',
            '秸秆数据.csv',
            '管理数据_多种方案.csv',
            '施肥数据.csv',
        ]

        missing = []
        for file_name in required_files:
            path = self.data_dir / file_name
            if not path.exists():
                missing.append(file_name)

        if missing:
            raise ModelNotFoundError(
                self.data_dir / '数据文件缺失'
            )

    def _create_temp_cultivar_file(
        self,
        params: Dict[str, float],
        variety_name: str = "TempVariety"
    ) -> Path:
        """创建临时品种参数文件

        Args:
            params: 品种参数字典
            variety_name: 品种名称

        Returns:
            临时文件路径
        """
        import os
        import tempfile

        # 创建临时文件
        fd, temp_path = tempfile.mkstemp(suffix='.csv', text=True)
        os.close(fd)  # 关闭mkstemp返回的fd，pandas.to_csv会自己打开文件
        temp_path = Path(temp_path)

        try:
            # 读取原始品种参数文件作为模板
            template_path = self.data_dir / '品种参数.csv'

            if template_path.exists():
                # 读取模板获取列名
                template_df = pd.read_csv(template_path, encoding='gbk')

                # 创建新的参数行
                new_row = {'PZ': variety_name}
                new_row.update(params)

                # 更新第一行（或添加新行）
                template_df.iloc[0] = new_row

                # 保存
                template_df.to_csv(temp_path, index=False, encoding='gbk')
            else:
                raise FileNotFoundError(f"品种参数模板文件不存在: {template_path}")

            logger.debug(f"创建临时品种文件: {temp_path}")
            return temp_path

        except Exception as e:
            # 清理失败的临时文件
            try:
                temp_path.unlink()
            except Exception:
                pass
            raise ModelRunError(f"创建临时品种文件失败: {e}")

    def _validate_params(
        self,
        params: Dict[str, float],
        bounds: Dict[str, tuple] = None
    ) -> None:
        """验证参数

        Args:
            params: 参数字典
            bounds: 参数边界 {param_name: (lower, upper)}

        Raises:
            ParameterError: 参数无效
        """
        if bounds is None:
            # 默认边界
            bounds = {
                'PS': (0.0, 0.1),
                'TS': (2.0, 4.0),
                'TO': (20.0, 35.0),
                'IE': (0.0, 1.0),
                'PHI': (0.3, 0.6),
                'TGW': (15.0, 35.0),
                'Q10': (1.0, 5.0),
                'Eh0': (-200.0, 500.0),
                'WaterC': (0.3, 0.9),
            }

        for param_name, value in params.items():
            if param_name in bounds:
                lower, upper = bounds[param_name]
                if not (lower <= value <= upper):
                    raise ParameterOutOfBoundsError(param_name, value, lower, upper)

    def run_ricegrow(
        self,
        params: Dict[str, float],
        variety_name: str = "TempVariety",
        validate_params: bool = True
    ) -> SimulationResult:
        """运行水稻生长模型

        Args:
            params: 品种参数字典 (如 {'PS': 0.05, 'TS': 2.8, ...})
            variety_name: 临时品种名称
            validate_params: 是否验证参数边界

        Returns:
            SimulationResult 对象
        """
        try:
            # 验证参数
            if validate_params:
                self._validate_params(params)

            # 创建临时品种文件
            cultivar_path = self._create_temp_cultivar_file(params, variety_name)

            try:
                # 导入模型
                from models.Ricegrow_py_v1_0 import CalFun

                # 运行模型
                results = CalFun(
                    FieldPath=str(self.data_dir / '调参数据.csv'),
                    WeatherPath=str(self.data_dir / '气象数据.csv'),
                    SoilFieldPath=str(self.data_dir / '土壤数据.csv'),
                    ResiduePath=str(self.data_dir / '秸秆数据.csv'),
                    PlantingPath=str(self.data_dir / '管理数据_多种方案.csv'),
                    CultivarPath=str(cultivar_path),
                    FertilizerPath=str(self.data_dir / '施肥数据.csv')
                )

                # 提取结果 (results[4] 是地上部生物量)
                max_days = len(results[4])

                simulated = pd.DataFrame({
                    'DAT': range(1, max_days + 1),
                    'Biomass': results[4],
                    'LAI': results[1],
                    'RootW': results[0],
                    'LN': results[2] if len(results) > 2 else None,
                    'ST': results[3] if len(results) > 3 else None,
                })

                return SimulationResult(
                    data=simulated,
                    success=True,
                    warnings=[]
                )
            finally:
                # 确保临时文件在模型运行后（无论成功或失败）被清理
                try:
                    cultivar_path.unlink()
                except Exception:
                    pass

        except ParameterError as e:
            # 参数错误，不需要记录日志
            return SimulationResult(
                data=pd.DataFrame(),
                success=False,
                error=str(e)
            )

        except Exception as e:
            logger.error(f"Ricegrow 模型运行失败: {e}")
            return SimulationResult(
                data=pd.DataFrame(),
                success=False,
                error=f"Ricegrow 模型运行失败: {e}"
            )

    def run_ch4_model(
        self,
        rice_result: SimulationResult,
        params: Dict[str, float],
        ip: int = 1
    ) -> SimulationResult:
        """运行CH4排放模型

        Args:
            rice_result: 水稻模型结果
            params: CH4模型参数
            ip: 灌溉模式

        Returns:
            SimulationResult 对象 (添加 CH4 列)
        """
        if not rice_result.success:
            return rice_result

        try:
            # 导入CH4模型
            from models.RG2CH4 import CH4Flux_coupled

            # 提取参数
            ch4_params = {
                'Q10': params.get('Q10', 3.0),
                'Eh0': params.get('Eh0', 250.0),
                'EhBase': params.get('EhBase', -20.0),
                'WaterC': params.get('WaterC', 0.636),
                'IP': ip,
                'sand': params.get('Sand', 35.0),
                'OMS': params.get('OMS', 1300.0),
                'OMN': params.get('OMN', 1600.0),
            }

            max_days = len(rice_result.data)

            # 运行CH4模型
            ch4_result = CH4Flux_coupled(
                day_begin=1,
                day_end=max_days,
                IP=ch4_params['IP'],
                sand=ch4_params['sand'],
                Tmax=self._load_temp_data(max_days),
                OMS=ch4_params['OMS'],
                OMN=ch4_params['OMN'],
                ATOPWTSeq=rice_result.data['Biomass'].values,
                AROOTWTSeq=rice_result.data.get('RootW', pd.Series([0]*max_days)).values
            )

            # 添加CH4列到结果
            rice_result.data['CH4'] = ch4_result['E'].values[:max_days]

            return rice_result

        except Exception as e:
            logger.error(f"CH4 模型运行失败: {e}")
            # 添加警告但继续返回
            rice_result.warnings.append(f"CH4 模型运行失败: {e}")
            return rice_result

    def _load_temp_data(self, max_days: int) -> np.ndarray:
        """加载温度数据

        Args:
            max_days: 最大天数

        Returns:
            Tmax 数组
        """
        # 加载气象数据
        weather_path = self.data_dir / '气象数据.csv'
        weather_data = pd.read_csv(weather_path, encoding='gbk')

        if 'Tmax' in weather_data.columns:
            return weather_data['Tmax'].values[:max_days]
        else:
            # 使用默认温度
            return np.ones(max_days) * 30.0

    def run_coupled(
        self,
        params: Dict[str, float],
        run_ch4: bool = True,
        variety_name: str = "TempVariety",
        ip: int = 1
    ) -> SimulationResult:
        """运行耦合模型（水稻+CH4）

        Args:
            params: 完整参数字典（包含品种和CH4参数）
            run_ch4: 是否运行CH4模型
            variety_name: 品种名称
            ip: 灌溉模式

        Returns:
            SimulationResult 对象
        """
        # 分离品种参数和CH4参数
        cultivar_params = {k: v for k, v in params.items()
                           if k in ['PS', 'TS', 'TO', 'IE', 'PHI', 'TGW', 'SLAc', 'PF', 'AMX', 'KF', 'RGC', 'LRS', 'TLN', 'EIN', 'TA', 'SGP', 'PC', 'RAR']}

        # 运行水稻模型
        result = self.run_ricegrow(cultivar_params, variety_name)

        if not result.success:
            return result

        # 运行CH4模型
        if run_ch4:
            result = self.run_ch4_model(result, params, ip)

        return result

    def run_batch(
        self,
        params_list: List[Dict[str, float]],
        variety_names: Optional[List[str]] = None,
        run_ch4: bool = True
    ) -> List[SimulationResult]:
        """批量运行模型

        Args:
            params_list: 参数列表
            variety_names: 品种名称列表
            run_ch4: 是否运行CH4模型

        Returns:
            SimulationResult 列表
        """
        if variety_names is None:
            variety_names = [f"Variety_{i}" for i in range(len(params_list))]

        results = []
        for i, params in enumerate(params_list):
            result = self.run_coupled(
                params,
                run_ch4=run_ch4,
                variety_name=variety_names[i] if i < len(variety_names) else f"Variety_{i}"
            )
            results.append(result)

        return results


# 单例实例
_service_instance: Optional[ModelService] = None


def get_model_service() -> ModelService:
    """获取模型服务单例

    Returns:
        ModelService 实例
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = ModelService()
    return _service_instance


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)

    service = ModelService()

    # 测试运行模型
    print("=" * 60)
    print("测试模型服务")
    print("=" * 60)

    test_params = {
        'PS': 0.05,
        'TS': 2.8,
        'TO': 28.0,
        'IE': 0.15,
        'PHI': 0.45,
        'TGW': 26.0,
    }

    result = service.run_coupled(test_params, run_ch4=False)

    print(f"成功: {result.success}")
    if result.success:
        print(f"行数: {len(result.data)}")
        print(f"列名: {list(result.data.columns)}")
        print(f"生物量范围: {result.biomass.min():.1f} - {result.biomass.max():.1f}")
    else:
        print(f"错误: {result.error}")
