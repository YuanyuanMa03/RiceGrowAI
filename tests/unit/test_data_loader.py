"""
数据加载器单元测试

测试核心数据加载模块的各项功能。
"""
import pytest
from pathlib import Path
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from core.data.loader import (
    DataLoader,
    LoadResult,
    DataLoaderError,
    FileValidationError,
    ColumnMismatchError,
    get_data_loader,
)


# ==================== LoadResult测试 ====================

class TestLoadResult:
    """LoadResult数据类测试"""

    def test_create_result(self):
        """测试创建结果"""
        data = pd.DataFrame({"A": [1, 2, 3]})
        result = LoadResult(
            data=data,
            path=Path("test.csv"),
            encoding="gbk",
            rows=3,
            columns=["A"]
        )

        assert len(result.data) == 3
        assert result.path == Path("test.csv")
        assert result.encoding == "gbk"
        assert result.rows == 3
        assert result.columns == ["A"]

    def test_to_dict(self):
        """测试转换为字典"""
        data = pd.DataFrame({"A": [1, 2, 3]})
        result = LoadResult(
            data=data,
            path=Path("test.csv"),
            encoding="utf-8",
            rows=3,
            columns=["A"]
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "path" in result_dict
        assert "rows" in result_dict
        assert result_dict["rows"] == 3


# ==================== DataLoader类测试 ====================

class TestDataLoader:
    """DataLoader类测试套件"""

    def test_init_default(self):
        """测试默认初始化"""
        loader = DataLoader()
        assert loader.data_dir is not None
        assert isinstance(loader._cache, dict)

    def test_init_custom_dir(self, tmp_path):
        """测试自定义目录初始化"""
        loader = DataLoader(data_dir=tmp_path)
        assert loader.data_dir == tmp_path

    def test_encoding_fallback_success(self, tmp_path):
        """测试编码回退机制成功情况"""
        # 创建UTF-8文件
        test_file = tmp_path / "test.csv"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("列1,列2\n值1,值2\n")

        loader = DataLoader(data_dir=tmp_path)
        df, encoding = loader._try_read_csv(test_file)

        assert isinstance(df, pd.DataFrame)
        assert encoding == "utf-8"

    def test_encoding_fallback_gbk(self, tmp_path):
        """测试GBK编码读取"""
        # 创建GBK文件
        test_file = tmp_path / "test_gbk.csv"
        with open(test_file, "w", encoding="gbk") as f:
            f.write("中文列1,中文列2\n值1,值2\n")

        loader = DataLoader(data_dir=tmp_path)
        df, encoding = loader._try_read_csv(test_file)

        assert isinstance(df, pd.DataFrame)
        assert encoding == "gbk"

    def test_load_weather_success(self, tmp_path):
        """测试成功加载气象数据"""
        weather_data = pd.DataFrame({
            "Stationno": ["JSYX"],
            "Jour": ["1990/01/01"],
            "Tmax": [30],
            "Tmin": [20],
            "RAIN": [0],
            "SRAD": [15],
            "CO2": [350],
        })
        weather_file = tmp_path / "气象数据.csv"
        weather_data.to_csv(weather_file, index=False, encoding="gbk")

        loader = DataLoader(data_dir=tmp_path)
        result = loader.load_weather(path=weather_file)

        assert len(result.data) == 1
        assert "Tmax" in result.columns
        # 编码可能是gbk或utf-8，取决于系统
        assert result.encoding in ["gbk", "utf-8"]

    def test_load_observed_success(self, tmp_path):
        """测试成功加载观测数据"""
        obs_data = pd.DataFrame({
            "DAT": [0, 30, 60],
            "Biomass": [100, 500, 1500],
        })
        obs_file = tmp_path / "observed.csv"
        obs_data.to_csv(obs_file, index=False, encoding="gbk")

        loader = DataLoader(data_dir=tmp_path)
        result = loader.load_observed(path=obs_file)

        assert "Biomass" in result.columns
        assert len(result.data) == 3

    def test_load_soil_success(self, tmp_path):
        """测试加载土壤数据"""
        soil_data = pd.DataFrame({
            "pH": [6.5, 6.8],
            "depth": [0, 20],
            "thickness": [20, 40],
            "organicMatter": [15.0, 12.0],
        })
        soil_file = tmp_path / "土壤数据.csv"
        soil_data.to_csv(soil_file, index=False, encoding="gbk")

        loader = DataLoader(data_dir=tmp_path)
        result = loader.load_soil(path=soil_file)

        assert "pH" in result.columns

    def test_load_fertilizer_success(self, tmp_path):
        """测试加载施肥数据"""
        fert_data = pd.DataFrame({
            "type": ["尿素"],
            "methodName": ["撒施"],
            "DOY": [120],
            "nAmount": [50],
        })
        fert_file = tmp_path / "施肥数据.csv"
        fert_data.to_csv(fert_file, index=False, encoding="gbk")

        loader = DataLoader(data_dir=tmp_path)
        result = loader.load_fertilizer(path=fert_file)

        assert "nAmount" in result.columns


# ==================== 异常测试 ====================

class TestDataLoaderExceptions:
    """异常处理测试"""

    def test_file_validation_error_message(self):
        """测试FileValidationError消息"""
        error = FileValidationError("测试错误")
        assert "测试错误" in str(error)

    def test_column_mismatch_error(self):
        """测试ColumnMismatchError"""
        error = ColumnMismatchError(
            "test.csv",
            expected=["A", "B", "C"],
            actual=["A", "B"]
        )

        assert error.file_path == "test.csv"
        assert error.expected == ["A", "B", "C"]
        assert error.actual == ["A", "B"]


# ==================== 辅助函数测试 ====================

class TestHelperFunctions:
    """辅助函数测试"""

    def test_get_data_loader_singleton(self, tmp_path):
        """测试单例模式"""
        with patch("core.data.loader.DATA_DIR", tmp_path):
            loader1 = get_data_loader()
            loader2 = get_data_loader()

            assert loader1 is loader2
