"""
示例数据生成器

为测试提供标准化的示例数据。
"""
import pandas as pd
import numpy as np
from pathlib import Path


def create_sample_weather_csv(path: Path, days: int = 365) -> Path:
    """创建示例气象数据CSV文件

    Args:
        path: 保存路径
        days: 天数

    Returns:
        创建的文件路径
    """
    dates = pd.date_range("1990-01-01", periods=days, freq="D")

    data = pd.DataFrame({
        "Stationno": ["JSYX"] * days,
        "Jour": dates.strftime("%Y/%m/%d"),
        "Tmax": 25 + 5 * np.sin(np.arange(days) * 2 * np.pi / 365) + np.random.randn(days) * 2,
        "Tmin": 18 + 3 * np.sin(np.arange(days) * 2 * np.pi / 365) + np.random.randn(days) * 1.5,
        "RAIN": np.random.exponential(2, days),
        "SRAD": 15 + 5 * np.sin(np.arange(days) * 2 * np.pi / 365) + np.random.randn(days),
        "CO2": [350] * days,
    })

    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(path, index=False, encoding="gbk")
    return path


def create_sample_observed_csv(path: Path) -> Path:
    """创建示例观测数据CSV文件

    Args:
        path: 保存路径

    Returns:
        创建的文件路径
    """
    data = pd.DataFrame({
        "DAT": [0, 30, 60, 90, 120],
        "Biomass": [100, 500, 1500, 3000, 4500],
        "LAI": [0.1, 0.5, 2.0, 4.0, 3.5],
        "RootW": [10, 50, 150, 300, 450],
        "LN": [1.5, 2.0, 2.8, 3.2, 3.0],
        "ST": [0.5, 1.0, 1.5, 2.0, 2.5],
    })

    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(path, index=False, encoding="gbk")
    return path


def create_sample_cultivar_csv(path: Path) -> Path:
    """创建示例品种参数CSV文件

    Args:
        path: 保存路径

    Returns:
        创建的文件路径
    """
    data = pd.DataFrame({
        "PZ": ["Variety1", "Variety2", "Variety3"],
        "PS": [0.045, 0.050, 0.055],
        "TS": [2.7, 2.8, 2.9],
        "TO": [27.0, 28.0, 29.0],
        "IE": [0.14, 0.15, 0.16],
        "PHI": [0.44, 0.45, 0.46],
        "TGW": [25.0, 26.0, 27.0],
        "SLAc": [24.0, 25.0, 26.0],
        "PF": [0.48, 0.49, 0.50],
        "AMX": [45.0, 47.0, 49.0],
        "KF": [0.55, 0.56, 0.57],
        "RGC": [0.015, 0.016, 0.017],
        "LRS": [0.20, 0.21, 0.22],
        "TLN": [14, 15, 16],
        "EIN": [0.85, 0.86, 0.87],
        "TA": [28.0, 29.0, 30.0],
        "SGP": [0.0025, 0.0026, 0.0027],
        "PC": [0.14, 0.145, 0.15],
        "RAR": [0.35, 0.36, 0.37],
    })

    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(path, index=False, encoding="gbk")
    return path


def create_sample_soil_csv(path: Path) -> Path:
    """创建示例土壤数据CSV文件

    Args:
        path: 保存路径

    Returns:
        创建的文件路径
    """
    data = pd.DataFrame({
        "pH": [6.5, 6.6, 6.7],
        "depth": [0, 20, 40],
        "thickness": [20, 20, 40],
        "bulkWeight": [1.3, 1.4, 1.5],
        "clayParticle": [25, 28, 30],
        "actualWater": [0.25, 0.26, 0.27],
        "fieldCapacity": [0.35, 0.36, 0.38],
        "wiltingPoint": [0.15, 0.16, 0.17],
        "fieldSaturation": [0.45, 0.46, 0.48],
        "organicMatter": [15.0, 12.0, 8.0],
        "totalNitrogen": [1.2, 1.0, 0.6],
        "nitrateNitrogen": [20, 15, 10],
        "ammoniaNitrogen": [15, 12, 8],
        "fastAvailablePhosphorus": [15, 12, 8],
        "totalPhosphorus": [0.8, 0.6, 0.4],
        "fastAvailableK": [120, 100, 80],
        "slowAvailableK": [500, 400, 300],
        "caco3": [0.5, 0.6, 0.7],
        "soilTexture": ["中壤土", "中壤土", "重壤土"],
        "soilMineRate": [0.02, 0.02, 0.02],
        "soilNConcentration": [0.015, 0.012, 0.008],
    })

    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(path, index=False, encoding="gbk")
    return path


if __name__ == "__main__":
    # 生成所有示例数据
    fixtures_dir = Path(__file__).parent

    create_sample_weather_csv(fixtures_dir / "weather.csv")
    create_sample_observed_csv(fixtures_dir / "observed.csv")
    create_sample_cultivar_csv(fixtures_dir / "cultivar.csv")
    create_sample_soil_csv(fixtures_dir / "soil.csv")

    print("✅ 所有示例数据已生成")
