"""
pytest配置和共享fixtures

提供全局测试配置和共享的测试fixtures。
"""
import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
from typing import Dict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ==================== 路径Fixtures ====================

@pytest.fixture
def data_dir():
    """获取数据目录路径"""
    return project_root / "data"


@pytest.fixture
def tests_dir():
    """获取测试目录路径"""
    return project_root / "tests"


@pytest.fixture
def fixtures_dir(tests_dir):
    """获取fixtures目录路径"""
    return tests_dir / "fixtures"


# ==================== 数据Fixtures ====================

@pytest.fixture
def sample_weather_data():
    """生成示例气象数据"""
    dates = pd.date_range("1990-01-01", periods=120, freq="D")
    return pd.DataFrame({
        "Stationno": ["JSYX"] * 120,
        "Jour": dates.strftime("%Y/%m/%d"),
        "Tmax": np.random.uniform(25, 35, 120),
        "Tmin": np.random.uniform(18, 25, 120),
        "RAIN": np.random.uniform(0, 10, 120),
        "SRAD": np.random.uniform(10, 25, 120),
        "CO2": [350] * 120,
    })


@pytest.fixture
def sample_observed_data():
    """生成示例观测数据"""
    return pd.DataFrame({
        "DAT": [0, 30, 60, 90, 120],
        "Biomass": [100, 500, 1500, 3000, 4500],
        "LAI": [0.1, 0.5, 2.0, 4.0, 3.5],
        "Yield": [0, 0, 0, 0, 8000],
    })


@pytest.fixture
def sample_cultivar_params():
    """生成示例品种参数"""
    return {
        "PS": 0.05,
        "TS": 2.8,
        "TO": 28.0,
        "IE": 0.15,
        "PHI": 0.45,
        "TGW": 26.0,
        "SLAc": 25.0,
    }


@pytest.fixture
def sample_ch4_params():
    """生成示例CH4参数"""
    return {
        "Q10": 3.0,
        "Eh0": 250.0,
        "EhBase": -20.0,
        "WaterC": 0.636,
        "Sand": 35.0,
        "OMS": 1300.0,
        "OMN": 1600.0,
    }


# ==================== 文件Fixtures ====================

@pytest.fixture
def temp_csv_file(tmp_path, sample_weather_data):
    """创建临时CSV文件"""
    file_path = tmp_path / "weather.csv"
    sample_weather_data.to_csv(file_path, index=False, encoding="gbk")
    return file_path


@pytest.fixture
def temp_gbk_file(tmp_path):
    """创建GBK编码的临时文件"""
    file_path = tmp_path / "gbk_file.csv"
    with open(file_path, "w", encoding="gbk") as f:
        f.write("列1,列2,列3\n")
        f.write("值1,值2,值3\n")
    return file_path


# ==================== 模拟结果Fixtures ====================

@pytest.fixture
def sample_simulation_result():
    """生成示例模拟结果"""
    data = pd.DataFrame({
        "DAT": range(1, 121),
        "Biomass": np.linspace(0, 5000, 120),
        "LAI": np.concatenate([np.linspace(0, 5, 80), np.linspace(5, 3, 40)]),
        "RootW": np.linspace(0, 500, 120),
        "CH4": np.random.uniform(0, 500, 120),
    })
    from core.simulation.model_service import SimulationResult
    return SimulationResult(
        data=data,
        success=True,
        error=None,
        warnings=[]
    )


# ==================== 参数边界Fixtures ====================

@pytest.fixture
def parameter_bounds():
    """标准参数边界"""
    return {
        "PS": (0.0, 0.1),
        "TS": (2.0, 4.0),
        "TO": (20.0, 35.0),
        "IE": (0.0, 1.0),
        "PHI": (0.3, 0.6),
        "TGW": (15.0, 35.0),
        "Q10": (1.0, 5.0),
        "Eh0": (-200.0, 500.0),
        "WaterC": (0.3, 0.9),
    }


# ==================== pytest配置 ====================

def pytest_configure(config):
    """pytest配置钩子"""
    config.addinivalue_line(
        "markers", "slow: 标记测试运行较慢"
    )
    config.addinivalue_line(
        "markers", "integration: 标记集成测试"
    )
    config.addinivalue_line(
        "markers", "unit: 标记单元测试"
    )


@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return {
        "max_file_size": 10 * 1024 * 1024,  # 10MB
        "allowed_encodings": ["utf-8", "gbk", "gb2312", "gb18030"],
        "timeout": 30,  # seconds
    }
