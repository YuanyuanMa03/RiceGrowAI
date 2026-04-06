"""
统计指标计算模块

提供模型拟合质量评估的各种统计指标
"""
import numpy as np
from typing import Dict, Tuple, Optional
import pandas as pd


def calculate_r2(observed: np.ndarray, simulated: np.ndarray) -> float:
    """计算决定系数 R²

    R² = 1 - SS_res / SS_tot
    其中:
    - SS_res = Σ(y_obs - y_sim)²  (残差平方和)
    - SS_tot = Σ(y_obs - ȳ)²      (总平方和)

    Args:
        observed: 观测值数组
        simulated: 模拟值数组

    Returns:
        R² 值 (0-1, 越接近1拟合越好)
    """
    # 移除NaN
    mask = ~(np.isnan(observed) | np.isnan(simulated))
    obs = observed[mask]
    sim = simulated[mask]

    if len(obs) == 0:
        return np.nan

    ss_res = np.sum((obs - sim) ** 2)
    ss_tot = np.sum((obs - np.mean(obs)) ** 2)

    if ss_tot == 0:
        return 1.0 if ss_res == 0 else 0.0

    r2 = 1 - (ss_res / ss_tot)
    return r2


def calculate_rmse(observed: np.ndarray, simulated: np.ndarray) -> float:
    """计算均方根误差 RMSE

    RMSE = √(Σ(y_obs - y_sim)² / n)

    Args:
        observed: 观测值数组
        simulated: 模拟值数组

    Returns:
        RMSE 值（与观测值同单位）
    """
    mask = ~(np.isnan(observed) | np.isnan(simulated))
    obs = observed[mask]
    sim = simulated[mask]

    if len(obs) == 0:
        return np.nan

    return np.sqrt(np.mean((obs - sim) ** 2))


def calculate_mae(observed: np.ndarray, simulated: np.ndarray) -> float:
    """计算平均绝对误差 MAE

    MAE = Σ|y_obs - y_sim| / n

    Args:
        observed: 观测值数组
        simulated: 模拟值数组

    Returns:
        MAE 值（与观测值同单位）
    """
    mask = ~(np.isnan(observed) | np.isnan(simulated))
    obs = observed[mask]
    sim = simulated[mask]

    if len(obs) == 0:
        return np.nan

    return np.mean(np.abs(obs - sim))


def calculate_nse(observed: np.ndarray, simulated: np.ndarray) -> float:
    """计算 Nash-Sutcliffe 效率系数 NSE

    NSE = 1 - Σ(y_obs - y_sim)² / Σ(y_obs - ȳ)²

    NSE 取值范围 (-∞, 1]:
    - NSE = 1: 完美拟合
    - NSE = 0: 模拟等于观测均值
    - NSE < 0: 模拟比用均值还差

    Args:
        observed: 观测值数组
        simulated: 模拟值数组

    Returns:
        NSE 值
    """
    mask = ~(np.isnan(observed) | np.isnan(simulated))
    obs = observed[mask]
    sim = simulated[mask]

    if len(obs) == 0:
        return np.nan

    numerator = np.sum((obs - sim) ** 2)
    denominator = np.sum((obs - np.mean(obs)) ** 2)

    if denominator == 0:
        return 1.0 if numerator == 0 else np.nan

    return 1 - (numerator / denominator)


def calculate_pbias(observed: np.ndarray, simulated: np.ndarray) -> float:
    """计算百分比偏差 PBIAS

    PBIAS = Σ(y_sim - y_obs) / Σ(y_obs) × 100%

    PBIAS 取值范围 (-∞, +∞):
    - PBIAS = 0: 无偏差
    - PBIAS > 0: 高估（模拟值偏高）
    - PBIAS < 0: 低估（模拟值偏低）

    Args:
        observed: 观测值数组
        simulated: 模拟值数组

    Returns:
        PBIAS 值（百分比）
    """
    mask = ~(np.isnan(observed) | np.isnan(simulated))
    obs = observed[mask]
    sim = simulated[mask]

    if len(obs) == 0 or np.sum(obs) == 0:
        return np.nan

    return np.sum(sim - obs) / np.sum(obs) * 100


def calculate_kge(observed: np.ndarray, simulated: np.ndarray) -> float:
    """计算 Kling-Gupta 效率 KGE

    KGE = 1 - √((r-1)² + (α-1)² + (β-1)²)

    其中:
    - r: 相关系数
    - α: 标准差比率
    - β: 均值比率

    KGE 取值范围 (-∞, 1]：
    - KGE = 1: 完美拟合
    - KGE > 0.8: 很好
    - KGE 0.5-0.8: 好

    Args:
        observed: 观测值数组
        simulated: 模拟值数组

    Returns:
        KGE 值
    """
    mask = ~(np.isnan(observed) | np.isnan(simulated))
    obs = observed[mask]
    sim = simulated[mask]

    if len(obs) == 0:
        return np.nan

    # 相关系数
    r = np.corrcoef(obs, sim)[0, 1]

    # 标准差比率
    alpha = np.std(sim) / (np.std(obs) + 1e-10)

    # 均值比率
    beta = np.mean(sim) / (np.mean(obs) + 1e-10)

    kge = 1 - np.sqrt((r - 1)**2 + (alpha - 1)**2 + (beta - 1)**2)
    return kge


def calculate_all_metrics(observed: np.ndarray,
                           simulated: np.ndarray) -> Dict[str, float]:
    """计算所有统计指标

    Args:
        observed: 观测值数组
        simulated: 模拟值数组

    Returns:
        包含所有指标的字典
    """
    return {
        'R²': calculate_r2(observed, simulated),
        'RMSE': calculate_rmse(observed, simulated),
        'MAE': calculate_mae(observed, simulated),
        'NSE': calculate_nse(observed, simulated),
        'PBIAS': calculate_pbias(observed, simulated),
        'KGE': calculate_kge(observed, simulated),
    }


def get_model_rating(r2: float, nse: float) -> str:
    """根据R²和NSE值给出模型评级

    Args:
        r2: 决定系数
        nse: Nash-Sutcliffe效率

    Returns:
        评级字符串
    """
    if np.isnan(r2) or np.isnan(nse):
        return "无法评估"

    if r2 >= 0.85 and nse >= 0.85:
        return "优秀 ⭐⭐⭐⭐⭐"
    elif r2 >= 0.75 and nse >= 0.75:
        return "良好 ⭐⭐⭐⭐"
    elif r2 >= 0.60 and nse >= 0.65:
        return "中等 ⭐⭐⭐"
    elif r2 >= 0.40 and nse >= 0.50:
        return "及格 ⭐⭐"
    else:
        return "较差 ⭐"


def format_metric_value(value: float, metric_name: str) -> str:
    """格式化指标值用于显示

    Args:
        value: 指标值
        metric_name: 指标名称

    Returns:
        格式化后的字符串
    """
    if np.isnan(value):
        return "N/A"

    if metric_name == 'R²' or metric_name == 'NSE' or metric_name == 'KGE':
        return f"{value:.4f}"
    elif metric_name == 'RMSE' or metric_name == 'MAE':
        return f"{value:.2f}"
    elif metric_name == 'PBIAS':
        return f"{value:.2f}%"
    else:
        return f"{value:.4f}"


def align_and_calculate_metrics(observed_data: pd.DataFrame,
                                  simulated_data: pd.DataFrame,
                                  variables: list) -> Dict[str, Dict[str, float]]:
    """对齐数据并计算所有变量的统计指标

    Args:
        observed_data: 观测数据，包含 DAT 列和变量列
        simulated_data: 模拟数据，包含 DAT 列和变量列
        variables: 要计算的变量列表（如 ['Biomass', 'CH4']）

    Returns:
        字典，key为变量名，value为该变量的指标字典
    """
    results = {}

    for var in variables:
        if var not in observed_data.columns or var not in simulated_data.columns:
            continue

        # 按 DAT 合并数据（内连接，只保留共同的时间点）
        merged = pd.merge(
            observed_data[['DAT', var]],
            simulated_data[['DAT', var]],
            on='DAT',
            how='inner'
        ).dropna()

        if len(merged) < 2:
            results[var] = {k: np.nan for k in ['R²', 'RMSE', 'MAE', 'NSE', 'PBIAS', 'KGE']}
            continue

        # 计算指标
        obs = merged[f'{var}_x'].values  # 观测值
        sim = merged[f'{var}_y'].values  # 模拟值

        results[var] = calculate_all_metrics(obs, sim)

    return results


if __name__ == '__main__':
    # 测试
    obs = np.array([1, 2, 3, 4, 5])
    sim = np.array([1.1, 2.2, 2.9, 4.1, 4.9])

    metrics = calculate_all_metrics(obs, sim)
    print("统计指标:")
    for name, value in metrics.items():
        print(f"  {name}: {format_metric_value(value, name)}")

    rating = get_model_rating(metrics['R²'], metrics['NSE'])
    print(f"\n模型评级: {rating}")
