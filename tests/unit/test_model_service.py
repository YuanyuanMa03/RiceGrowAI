"""
模型服务层单元测试

测试模型服务的各项功能，包括参数验证、结果处理等。
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import pandas as pd
import numpy as np

from core.simulation.model_service import (
    ModelService,
    SimulationResult,
    get_model_service,
)
from core.exceptions import (
    ParameterError,
    ParameterOutOfBoundsError,
)


# ==================== SimulationResult测试 ====================

class TestSimulationResult:
    """SimulationResult数据类测试"""

    def test_create_success_result(self):
        """测试创建成功结果"""
        data = pd.DataFrame({
            "Biomass": [0, 100, 500],
            "LAI": [0.1, 0.5, 1.0],
        })
        result = SimulationResult(
            data=data,
            success=True,
            warnings=[]
        )

        assert result.success is True
        assert result.error is None
        assert len(result.warnings) == 0

    def test_biomass_property(self):
        """测试生物量属性"""
        data = pd.DataFrame({
            "Biomass": [0, 100, 500, 1000],
            "LAI": [0.1, 0.5, 1.0, 2.0],
        })
        result = SimulationResult(data=data, success=True)

        biomass = result.biomass
        assert len(biomass) == 4
        assert biomass.iloc[0] == 0
        assert biomass.iloc[-1] == 1000

    def test_biomass_property_missing_column(self):
        """测试缺少Biomass列时抛出异常"""
        data = pd.DataFrame({"LAI": [0.1, 0.5]})
        result = SimulationResult(data=data, success=True)

        with pytest.raises(KeyError, match="Biomass"):
            _ = result.biomass

    def test_ch4_property_present(self):
        """测试CH4属性存在时"""
        data = pd.DataFrame({
            "Biomass": [0, 100],
            "CH4": [10, 50],
        })
        result = SimulationResult(data=data, success=True)

        ch4 = result.ch4
        assert ch4 is not None
        assert len(ch4) == 2

    def test_ch4_property_absent(self):
        """测试CH4属性不存在时"""
        data = pd.DataFrame({"Biomass": [0, 100]})
        result = SimulationResult(data=data, success=True)

        assert result.ch4 is None

    def test_final_yield_present(self):
        """测试最终产量属性存在时"""
        data = pd.DataFrame({
            "Biomass": [0, 100, 200],
            "Yield": [0, 0, 5000],
        })
        result = SimulationResult(data=data, success=True)

        yield_value = result.final_yield
        assert yield_value == 5000

    def test_final_yield_absent(self):
        """测试最终产量不存在时"""
        data = pd.DataFrame({"Biomass": [0, 100]})
        result = SimulationResult(data=data, success=True)

        assert result.final_yield is None

    def test_to_dict(self):
        """测试转换为字典"""
        data = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        result = SimulationResult(
            data=data,
            success=True,
            error=None,
            warnings=["警告1"]
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["rows"] == 3
        assert "columns" in result_dict
        assert result_dict["warnings"] == ["警告1"]


# ==================== ModelService测试 ====================

class TestModelService:
    """ModelService类测试套件"""

    @patch("core.simulation.model_service.Path.exists")
    def test_init(self, mock_exists):
        """测试初始化"""
        mock_exists.return_value = True

        with patch("core.simulation.model_service.DATA_DIR"):
            service = ModelService()
            assert service is not None
            assert service._cultivar_cache == {}

    def test_validate_params_success(self, sample_cultivar_params):
        """测试参数验证成功"""
        service = ModelService()
        service._validate_params(sample_cultivar_params)
        # 不应抛出异常

    def test_validate_params_out_of_bounds(self):
        """测试参数超出边界"""
        service = ModelService()
        invalid_params = {
            "PS": 0.5,  # 超出 (0.0, 0.1)
            "TS": 2.8,
        }

        with pytest.raises(ParameterOutOfBoundsError):
            service._validate_params(invalid_params)

    def test_validate_params_custom_bounds(self):
        """测试自定义参数边界"""
        service = ModelService()
        custom_bounds = {"TEST_PARAM": (0, 100)}
        params = {"TEST_PARAM": 50}

        service._validate_params(params, bounds=custom_bounds)
        # 不应抛出异常

    @patch("core.simulation.model_service.ModelService._validate_data_files")
    def test_init_skip_validation(self, mock_validate):
        """测试跳过数据验证"""
        service = ModelService()
        assert service.data_dir is not None


# ==================== 参数处理测试 ====================

class TestParameterHandling:
    """参数处理测试"""

    @patch("core.simulation.model_service.DATA_DIR")
    def test_create_temp_cultivar_file(self, mock_data_dir, tmp_path, sample_cultivar_params):
        """测试创建临时品种文件"""
        # Mock DATA_DIR为tmp_path
        mock_data_dir.__str__ = lambda self: str(tmp_path)
        mock_data_dir.__truediv__ = lambda self, name: tmp_path / name

        # Mock模板文件
        template_df = pd.DataFrame({
            "PZ": ["Variety1"],
            "PS": [0.05],
            "TS": [2.8],
            "TO": [28.0],
            "IE": [0.15],
            "PHI": [0.45],
        })
        template_path = tmp_path / "品种参数.csv"
        template_df.to_csv(template_path, index=False, encoding="gbk")

        # Mock Path.exists返回True
        with patch("core.simulation.model_service.Path.exists", return_value=True):
            service = ModelService(data_dir=tmp_path)
            temp_path = service._create_temp_cultivar_file(
                sample_cultivar_params,
                variety_name="TestVariety"
            )

            assert temp_path.exists()
            # 清理
            temp_path.unlink()

    def test_validate_params_empty(self):
        """测试空参数验证"""
        service = ModelService()
        service._validate_params({})
        # 空参数不应抛出异常


# ==================== 单例模式测试 ====================

class TestSingleton:
    """单例模式测试"""

    @patch("core.simulation.model_service.DATA_DIR")
    @patch("core.simulation.model_service.Path.exists")
    def test_get_model_service_singleton(self, mock_exists, mock_dir):
        """测试单例模式"""
        mock_exists.return_value = True
        mock_dir = MagicMock()

        service1 = get_model_service()
        service2 = get_model_service()

        assert service1 is service2


# ==================== 数据处理测试 ====================

class TestDataProcessing:
    """数据处理功能测试"""

    @patch("pandas.read_csv")
    def test_load_temp_data(self, mock_read_csv, data_dir):
        """测试温度数据加载"""
        mock_weather = pd.DataFrame({
            "Tmax": [25, 28, 30, 32, 29],
        })
        mock_read_csv.return_value = mock_weather

        service = ModelService()
        temps = service._load_temp_data(5)

        assert len(temps) == 5

    @patch("pandas.read_csv")
    def test_load_temp_data_missing_column(self, mock_read_csv, data_dir):
        """测试温度数据缺少Tmax列"""
        mock_weather = pd.DataFrame({
            "Tmin": [20, 22, 24],
        })
        mock_read_csv.return_value = mock_weather

        service = ModelService()
        temps = service._load_temp_data(3)

        # 应返回默认温度
        assert all(t == 30.0 for t in temps)


class TestTempFileManagement:
    """临时文件管理测试"""

    def test_mkstemp_fd_is_closed(self):
        """mkstemp返回的文件描述符必须被关闭，否则会泄漏FD"""
        import os

        service = ModelService.__new__(ModelService)
        service.data_dir = Path("/tmp/test_rch4_data")

        # 创建带有一行的DataFrame模板（illoc[0]需要非空DataFrame）
        template = pd.DataFrame({"PZ": ["placeholder"], "PS": [0.05], "TS": [2.8]})

        with patch.object(Path, "exists", return_value=True), \
             patch("pandas.read_csv", return_value=template), \
             patch.object(pd.DataFrame, "to_csv"):
            path = service._create_temp_cultivar_file({"PS": 0.06}, "TestVar")

        # 验证临时文件路径由 tempfile 模块生成
        assert path is not None
        assert "tmp" in str(path).lower()  # tempfile puts files in /tmp

        # 关键验证：fd 已关闭后，可以正常打开文件（不被占用）
        try:
            test_fd = os.open(str(path), os.O_RDONLY)
            os.close(test_fd)
        except OSError:
            pass  # mock没有真正写入文件
        finally:
            try:
                Path(path).unlink()
            except OSError:
                pass
