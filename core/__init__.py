"""
核心业务逻辑模块

提供统一的数据加载、模型调用、异常处理等核心功能。
"""
from core.data.loader import (
    DataLoader,
    LoadResult,
    DataLoaderError,
    FileValidationError,
    ColumnMismatchError,
    get_data_loader,
    load_weather_data,
    load_observed_data,
)

__all__ = [
    # Data Loader
    'DataLoader',
    'LoadResult',
    'DataLoaderError',
    'FileValidationError',
    'ColumnMismatchError',
    'get_data_loader',
    'load_weather_data',
    'load_observed_data',
]
