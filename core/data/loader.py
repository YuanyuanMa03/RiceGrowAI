"""
统一数据加载模块

提供所有数据文件的加载功能，支持：
- 自动编码检测
- 统一错误处理
- 类型验证
- 缓存支持
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger('rice_app')

# 导入配置和异常
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import DATA_DIR, ENCODING_FALLBACK
from core.exceptions import FileReadError


@dataclass
class LoadResult:
    """数据加载结果"""
    data: pd.DataFrame
    path: Path
    encoding: str
    rows: int
    columns: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'path': str(self.path),
            'encoding': self.encoding,
            'rows': self.rows,
            'columns': self.columns,
        }


class DataLoaderError(Exception):
    """数据加载错误基类"""
    pass


class FileValidationError(DataLoaderError):
    """文件验证失败"""
    pass


class ColumnMismatchError(DataLoaderError):
    """列不匹配错误"""
    def __init__(self, file_path: str, expected: List[str], actual: List[str]):
        self.file_path = file_path
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"文件 {file_path} 列不匹配.\n"
            f"期望: {expected}\n"
            f"实际: {actual}"
        )


class DataLoader:
    """统一数据加载器

    提供类型安全的数据加载接口，支持自动编码检测和验证。
    """

    # 默认编码列表（按优先级）
    DEFAULT_ENCODINGS = ENCODING_FALLBACK

    # 必需列定义
    REQUIRED_COLUMNS = {
        'weather': ['Jour', 'Tmax', 'Tmin', 'SRAD'],
        'field_params': ['PanelCode', 'Latitude', 'SowingDate', 'TransplantDate'],
        'cultivar': ['PZ'],
        'soil': ['pH', 'depth'],
        'fertilizer': ['DOY'],
        'residue': ['previousCropType'],
        'management': ['VI', 'SoilSand', 'WaterRegime'],
    }

    def __init__(self, data_dir: Optional[Path] = None):
        """初始化数据加载器

        Args:
            data_dir: 数据目录路径，默认使用配置中的 DATA_DIR
        """
        self.data_dir = data_dir or DATA_DIR
        self._cache: Dict[str, pd.DataFrame] = {}

    def _try_read_csv(
        self,
        path: Path,
        encodings: Optional[List[str]] = None
    ) -> tuple[pd.DataFrame, str]:
        """尝试用多种编码读取CSV

        Args:
            path: 文件路径
            encodings: 编码列表，默认使用 DEFAULT_ENCODINGS

        Returns:
            (DataFrame, 使用的编码)

        Raises:
            DataLoaderError: 所有编码都失败
        """
        encodings = encodings or self.DEFAULT_ENCODINGS

        last_error = None
        for encoding in encodings:
            try:
                df = pd.read_csv(path, encoding=encoding)
                logger.debug(f"成功用编码 {encoding} 读取: {path}")
                return df, encoding
            except (UnicodeDecodeError, UnicodeError) as e:
                last_error = e
                continue
            except Exception as e:
                last_error = e
                logger.warning(f"用编码 {encoding} 读取失败: {e}")
                continue

        raise DataLoaderError(
            f"无法读取文件 {path}，尝试了 {len(encodings)} 种编码。"
            f"最后错误: {last_error}"
        )

    def _validate_columns(
        self,
        df: pd.DataFrame,
        required: List[str],
        file_type: str
    ) -> None:
        """验证DataFrame是否包含必需列

        Args:
            df: 数据框
            required: 必需列名列表
            file_type: 文件类型（用于错误信息）

        Raises:
            ColumnMismatchError: 缺少必需列
        """
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ColumnMismatchError(
                file_type,
                required,
                list(df.columns)
            )

    def load_weather(
        self,
        path: Optional[Path] = None,
        validate: bool = True
    ) -> LoadResult:
        """加载气象数据

        Args:
            path: 文件路径，默认为 DATA_DIR / '气象数据.csv'
            validate: 是否验证列

        Returns:
            LoadResult 对象
        """
        if path is None:
            path = self.data_dir / '气象数据.csv'

        path = Path(path)
        if not path.exists():
            raise FileReadError(f"气象数据文件不存在: {path}")

        data, encoding = self._try_read_csv(path)

        if validate:
            self._validate_columns(data, self.REQUIRED_COLUMNS['weather'], '气象数据')

        return LoadResult(
            data=data,
            path=path,
            encoding=encoding,
            rows=len(data),
            columns=list(data.columns)
        )

    def load_field_params(
        self,
        path: Optional[Path] = None,
        validate: bool = True
    ) -> LoadResult:
        """加载田间参数数据

        Args:
            path: 文件路径，默认为 DATA_DIR / '调参数据.csv'
            validate: 是否验证列

        Returns:
            LoadResult 对象
        """
        if path is None:
            path = self.data_dir / '调参数据.csv'

        path = Path(path)
        if not path.exists():
            raise FileReadError(f"田间参数文件不存在: {path}")

        data, encoding = self._try_read_csv(path)

        if validate:
            self._validate_columns(data, self.REQUIRED_COLUMNS['field_params'], '田间参数')

        return LoadResult(
            data=data,
            path=path,
            encoding=encoding,
            rows=len(data),
            columns=list(data.columns)
        )

    def load_cultivar(
        self,
        path: Optional[Path] = None,
        validate: bool = True
    ) -> LoadResult:
        """加载品种参数数据

        Args:
            path: 文件路径，默认为 DATA_DIR / '品种参数.csv'
            validate: 是否验证列

        Returns:
            LoadResult 对象
        """
        if path is None:
            path = self.data_dir / '品种参数.csv'

        path = Path(path)
        if not path.exists():
            raise FileReadError(f"品种参数文件不存在: {path}")

        data, encoding = self._try_read_csv(path)

        if validate:
            self._validate_columns(data, self.REQUIRED_COLUMNS['cultivar'], '品种参数')

        return LoadResult(
            data=data,
            path=path,
            encoding=encoding,
            rows=len(data),
            columns=list(data.columns)
        )

    def load_soil(
        self,
        path: Optional[Path] = None,
        validate: bool = True
    ) -> LoadResult:
        """加载土壤数据

        Args:
            path: 文件路径，默认为 DATA_DIR / '土壤数据.csv'
            validate: 是否验证列

        Returns:
            LoadResult 对象
        """
        if path is None:
            path = self.data_dir / '土壤数据.csv'

        path = Path(path)
        if not path.exists():
            raise FileReadError(f"土壤数据文件不存在: {path}")

        data, encoding = self._try_read_csv(path)

        if validate:
            self._validate_columns(data, self.REQUIRED_COLUMNS['soil'], '土壤数据')

        return LoadResult(
            data=data,
            path=path,
            encoding=encoding,
            rows=len(data),
            columns=list(data.columns)
        )

    def load_fertilizer(
        self,
        path: Optional[Path] = None,
        validate: bool = True
    ) -> LoadResult:
        """加载施肥数据

        Args:
            path: 文件路径，默认为 DATA_DIR / '施肥数据.csv'
            validate: 是否验证列

        Returns:
            LoadResult 对象
        """
        if path is None:
            path = self.data_dir / '施肥数据.csv'

        path = Path(path)
        if not path.exists():
            raise FileReadError(f"施肥数据文件不存在: {path}")

        data, encoding = self._try_read_csv(path)

        if validate:
            self._validate_columns(data, self.REQUIRED_COLUMNS['fertilizer'], '施肥数据')

        return LoadResult(
            data=data,
            path=path,
            encoding=encoding,
            rows=len(data),
            columns=list(data.columns)
        )

    def load_residue(
        self,
        path: Optional[Path] = None,
        validate: bool = True
    ) -> LoadResult:
        """加载秸秆/残留物数据

        Args:
            path: 文件路径，默认为 DATA_DIR / '秸秆数据.csv'
            validate: 是否验证列

        Returns:
            LoadResult 对象
        """
        if path is None:
            path = self.data_dir / '秸秆数据.csv'

        path = Path(path)
        if not path.exists():
            raise FileReadError(f"秸秆数据文件不存在: {path}")

        data, encoding = self._try_read_csv(path)

        if validate:
            self._validate_columns(data, self.REQUIRED_COLUMNS['residue'], '秸秆数据')

        return LoadResult(
            data=data,
            path=path,
            encoding=encoding,
            rows=len(data),
            columns=list(data.columns)
        )

    def load_management(
        self,
        path: Optional[Path] = None,
        validate: bool = True
    ) -> LoadResult:
        """加载管理数据

        Args:
            path: 文件路径，默认为 DATA_DIR / '管理数据_多种方案.csv'
            validate: 是否验证列

        Returns:
            LoadResult 对象
        """
        if path is None:
            path = self.data_dir / '管理数据_多种方案.csv'

        path = Path(path)
        if not path.exists():
            raise FileReadError(f"管理数据文件不存在: {path}")

        data, encoding = self._try_read_csv(path)

        if validate:
            self._validate_columns(data, self.REQUIRED_COLUMNS['management'], '管理数据')

        return LoadResult(
            data=data,
            path=path,
            encoding=encoding,
            rows=len(data),
            columns=list(data.columns)
        )

    def load_observed(
        self,
        path: Path,
        required_columns: Optional[List[str]] = None
    ) -> LoadResult:
        """加载观测数据（用户上传）

        Args:
            path: 文件路径
            required_columns: 必需列，默认为 ['DAT']

        Returns:
            LoadResult 对象
        """
        path = Path(path)
        if not path.exists():
            raise FileReadError(f"观测数据文件不存在: {path}")

        data, encoding = self._try_read_csv(path)

        if required_columns is None:
            required_columns = ['DAT']

        self._validate_columns(data, required_columns, '观测数据')

        return LoadResult(
            data=data,
            path=path,
            encoding=encoding,
            rows=len(data),
            columns=list(data.columns)
        )

    def load_all(self, validate: bool = True) -> Dict[str, LoadResult]:
        """加载所有核心数据文件

        Args:
            validate: 是否验证列

        Returns:
            字典 {文件类型: LoadResult}
        """
        results = {}

        try:
            results['weather'] = self.load_weather(validate=validate)
        except DataLoaderError as e:
            logger.warning(f"气象数据加载失败: {e}")

        try:
            results['field_params'] = self.load_field_params(validate=validate)
        except DataLoaderError as e:
            logger.warning(f"田间参数加载失败: {e}")

        try:
            results['cultivar'] = self.load_cultivar(validate=validate)
        except DataLoaderError as e:
            logger.warning(f"品种参数加载失败: {e}")

        try:
            results['soil'] = self.load_soil(validate=validate)
        except DataLoaderError as e:
            logger.warning(f"土壤数据加载失败: {e}")

        try:
            results['fertilizer'] = self.load_fertilizer(validate=validate)
        except DataLoaderError as e:
            logger.warning(f"施肥数据加载失败: {e}")

        try:
            results['residue'] = self.load_residue(validate=validate)
        except DataLoaderError as e:
            logger.warning(f"秸秆数据加载失败: {e}")

        try:
            results['management'] = self.load_management(validate=validate)
        except DataLoaderError as e:
            logger.warning(f"管理数据加载失败: {e}")

        return results

    def get_cached(self, data_type: str) -> Optional[pd.DataFrame]:
        """获取缓存的数据

        Args:
            data_type: 数据类型 ('weather', 'cultivar', etc.)

        Returns:
            DataFrame 或 None
        """
        return self._cache.get(data_type)

    def cache(self, data_type: str, df: pd.DataFrame) -> None:
        """缓存数据

        Args:
            data_type: 数据类型
            df: 数据框
        """
        self._cache[data_type] = df


# 单例实例（全局使用）
_loader_instance: Optional[DataLoader] = None


def get_data_loader() -> DataLoader:
    """获取数据加载器单例

    Returns:
        DataLoader 实例
    """
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = DataLoader()
    return _loader_instance


# 便捷函数（向后兼容）
def load_weather_data(path: Optional[Path] = None) -> pd.DataFrame:
    """加载气象数据（便捷函数）

    Args:
        path: 文件路径

    Returns:
        DataFrame
    """
    loader = get_data_loader()
    result = loader.load_weather(path)
    # 缓存结果
    loader.cache('weather', result.data)
    return result.data


def load_observed_data(path: Path, required_columns: Optional[List[str]] = None) -> pd.DataFrame:
    """加载观测数据（便捷函数）

    Args:
        path: 文件路径
        required_columns: 必需列

    Returns:
        DataFrame
    """
    loader = get_data_loader()
    result = loader.load_observed(path, required_columns)
    return result.data


if __name__ == '__main__':
    # 测试代码
    import logging
    logging.basicConfig(level=logging.DEBUG)

    loader = DataLoader()

    # 测试加载所有数据
    print("=" * 60)
    print("测试数据加载器")
    print("=" * 60)

    results = loader.load_all(validate=True)

    for name, result in results.items():
        print(f"\n{name}:")
        print(f"  路径: {result.path}")
        print(f"  编码: {result.encoding}")
        print(f"  行数: {result.rows}")
        print(f"  列数: {len(result.columns)}")
        print(f"  列名: {', '.join(result.columns[:5])}...")
