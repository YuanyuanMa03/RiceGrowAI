"""
Sobol 敏感性分析模块

基于论文《RiceGrow 模型品种参数不确定性研究》的方法，
实现全局敏感性分析，用于识别参数对模型输出的影响程度。

依赖 SALib 库：
    pip install SALib
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Callable, Optional, Any
from pathlib import Path

# 尝试导入 SALib
try:
    from SALib.analyze import sobol
    from SALib.sample import saltelli
    SALIB_AVAILABLE = True
except ImportError:
    SALIB_AVAILABLE = False


# ===== 参数边界定义 =====

def get_default_parameter_bounds() -> Dict[str, Tuple[float, float]]:
    """获取默认的参数边界（用于敏感性分析）

    Returns:
        参数字典 {param_name: (lower, upper)}
    """
    return {
        # 生育期参数
        'PS': (0.020, 0.078),
        'TS': (2.55, 3.20),
        'TO': (25.8, 28.6),
        'IE': (0.10, 0.20),
        'HF': (0.010, 0.015),
        'FDF': (0.688, 0.727),

        # 收获相关
        'PHI': (0.427, 0.480),
        'TGW': (24.0, 28.0),

        # 光合参数
        'SLAc': (184, 207),
        'PF': (0.0138, 0.0161),
        'AMX': (41.0, 48.0),
        'KF': (0.0072, 0.0090),

        # 呼吸参数
        'RGC': (0.27, 0.32),
        'LRS': (0.0058, 0.0075),

        # 形态参数
        'TLN': (14.5, 18.3),
        'EIN': (4.6, 5.5),
        'TA': (0.42, 0.52),

        # 品质参数
        'SGP': (6.15, 6.50),
        'PC': (7.4, 8.4),
        'RAR': (1.92, 2.36),
    }


# ===== Sobol 分析 =====

def create_sobol_problem(parameter_bounds: Dict[str, Tuple[float, float]]) -> Dict[str, Any]:
    """创建 Sobol 分析问题

    Args:
        parameter_bounds: 参数边界字典

    Returns:
        SALib 格式的问题字典
    """
    param_names = list(parameter_bounds.keys())
    bounds = [parameter_bounds[p] for p in param_names]

    problem = {
        'num_vars': len(param_names),
        'names': param_names,
        'bounds': bounds,
    }

    return problem


def generate_sobol_samples(problem: Dict[str, Any],
                            n_samples: int = 1000,
                            calc_second_order: bool = True) -> np.ndarray:
    """生成 Sobol 采样样本

    Args:
        problem: SALib 问题字典
        n_samples: 基础样本数
        calc_second_order: 是否计算二阶效应

    Returns:
        采样矩阵 (N x num_vars)
    """
    if not SALIB_AVAILABLE:
        raise ImportError("SALib 未安装，请运行: pip install SALib")

    param_values = saltelli.sample(
        problem,
        n_samples,
        calc_second_order=calc_second_order
    )

    return param_values


def run_sobol_analysis(
    problem: Dict[str, Any],
    param_values: np.ndarray,
    Y: np.ndarray,
    calc_second_order: bool = True,
    num_resamples: int = 100
) -> Dict[str, Dict[str, float]]:
    """运行 Sobol 敏感性分析

    Args:
        problem: SALib 问题字典
        param_values: 参数样本矩阵
        Y: 模型输出向量 (如产量、生物量等)
        calc_second_order: 是否计算二阶效应
        num_resamples: 重采样次数（用于置信区间）

    Returns:
        敏感性指数字典 {param_name: {'S1': ..., 'ST': ..., ...}}
    """
    if not SALIB_AVAILABLE:
        raise ImportError("SALib 未安装，请运行: pip install SALib")

    # 运行 Sobol 分析
    si = sobol.analyze(
        problem,
        Y,
        calc_second_order=calc_second_order,
        num_resamples=num_resamples
    )

    # 整理结果
    results = {}
    for i, param_name in enumerate(problem['names']):
        results[param_name] = {
            'S1': si['S1'][i],           # 一阶效应（主效应）
            'S1_conf': si['S1_conf'][i], # 一阶效应置信区间
            'ST': si['ST'][i],           # 总效应
            'ST_conf': si['ST_conf'][i], # 总效应置信区间
        }

        if calc_second_order:
            # 二阶效应（参数交互作用）
            for j, other_param in enumerate(problem['names']):
                if j > i:  # 避免重复
                    key = f'{param_name}_x_{other_param}'
                    idx = len(problem['names']) * i + j - (i * (i + 1)) // 2 - i - 1
                    if idx < len(si.get('S2', [])):
                        results[key] = {
                            'S2': si['S2'][i, j],
                            'S2_conf': si['S2_conf'][i, j],
                        }

    return results


def classify_sensitivity(sobol_results: Dict[str, Dict[str, float]],
                         st_threshold: float = 0.1,
                         s1_threshold: float = 0.01) -> Dict[str, List[str]]:
    """根据 Sobol 总效应指数对参数进行分类

    Args:
        sobol_results: Sobol 分析结果
        st_threshold: 高敏感度阈值（ST > 此值为高敏感）
        s1_threshold: 低敏感度阈值（ST < 此值为低敏感）

    Returns:
        分类字典 {'high': [...], 'medium': [...], 'low': [...]}
    """
    high = []
    medium = []
    low = []

    for param_name, indices in sobol_results.items():
        if '_x_' in param_name:
            continue  # 跳过二阶交互效应

        st = indices.get('ST', 0)

        if st > st_threshold:
            high.append(param_name)
        elif st > s1_threshold:
            medium.append(param_name)
        else:
            low.append(param_name)

    return {
        'high': high,
        'medium': medium,
        'low': low,
    }


def plot_sobol_results(sobol_results: Dict[str, Dict[str, float]],
                        top_n: int = 15):
    """绘制 Sobol 敏感性分析结果

    Args:
        sobol_results: Sobol 分析结果
        top_n: 显示前 N 个参数
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Matplotlib 未安装，无法绘图")
        return

    # 提取参数名和总效应
    params = []
    st_values = []
    s1_values = []

    for param_name, indices in sobol_results.items():
        if '_x_' in param_name:
            continue
        params.append(param_name)
        st_values.append(indices['ST'])
        s1_values.append(indices['S1'])

    # 按总效应排序
    sorted_indices = np.argsort(st_values)[::-1][:top_n]
    sorted_params = [params[i] for i in sorted_indices]
    sorted_st = [st_values[i] for i in sorted_indices]
    sorted_s1 = [s1_values[i] for i in sorted_indices]

    # 绘图
    fig, ax = plt.subplots(figsize=(10, 6))

    y_pos = np.arange(len(sorted_params))
    ax.barh(y_pos, sorted_st, align='center', alpha=0.7, label='总效应 (ST)')
    ax.barh(y_pos, sorted_s1, align='center', alpha=0.5, label='一阶效应 (S1)')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(sorted_params)
    ax.invert_yaxis()
    ax.set_xlabel('敏感性指数')
    ax.set_title('Sobol 全局敏感性分析')
    ax.legend()

    plt.tight_layout()
    return fig


# ===== 完整流程 =====

def perform_sensitivity_analysis(
    model_runner: Callable[[Dict[str, float]], float],
    parameter_bounds: Dict[str, Tuple[float, float]] = None,
    n_samples: int = 1000,
    output_var: str = 'yield',
    calc_second_order: bool = True
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, List[str]]]:
    """执行完整的敏感性分析流程

    Args:
        model_runner: 模型运行函数，接受参数字典，返回目标变量值
        parameter_bounds: 参数边界（默认使用 get_default_parameter_bounds()）
        n_samples: 采样数
        output_var: 输出变量名称（用于日志）
        calc_second_order: 是否计算二阶效应

    Returns:
        (sobol_results, classification): (Sobol分析结果, 参数分类)
    """
    if not SALIB_AVAILABLE:
        raise ImportError("SALib 未安装，请运行: pip install SALib")

    if parameter_bounds is None:
        parameter_bounds = get_default_parameter_bounds()

    print(f"=== Sobol 敏感性分析 ===")
    print(f"参数数量: {len(parameter_bounds)}")
    print(f"基础样本数: {n_samples}")
    print(f"总样本数: {n_samples * (2 * len(parameter_bounds) + 2)}")
    print()

    # 1. 创建问题
    problem = create_sobol_problem(parameter_bounds)

    # 2. 生成样本
    print("📊 生成 Sobol 采样...")
    param_values = generate_sobol_samples(problem, n_samples, calc_second_order)
    print(f"✅ 采样完成: {param_values.shape}")

    # 3. 运行模型
    print(f"🚀 运行模型 ({param_values.shape[0]} 次)...")
    Y = np.zeros(param_values.shape[0])

    for i, params in enumerate(param_values):
        param_dict = {name: params[j] for j, name in enumerate(problem['names'])}
        Y[i] = model_runner(param_dict)

        if (i + 1) % 100 == 0:
            print(f"  进度: {i+1}/{param_values.shape[0]}")

    print(f"✅ 模型运行完成")
    print(f"输出范围: [{Y.min():.2f}, {Y.max():.2f}]")
    print()

    # 4. 运行 Sobol 分析
    print("📈 计算 Sobol 指数...")
    sobol_results = run_sobol_analysis(problem, param_values, Y, calc_second_order)

    # 5. 分类参数
    classification = classify_sensitivity(sobol_results)

    # 打印结果
    print("=== 参数分类 ===")
    print(f"高敏感 (ST > 0.1): {', '.join(classification['high'])}")
    print(f"中敏感 (0.01 < ST < 0.1): {', '.join(classification['medium'])}")
    print(f"低敏感 (ST < 0.01): {', '.join(classification['low'])}")
    print()

    # 打印详细结果
    print("=== Top 10 参数 (按总效应排序) ===")
    sorted_params = sorted(
        sobol_results.items(),
        key=lambda x: x[1]['ST'],
        reverse=True
    )

    for i, (param_name, indices) in enumerate(sorted_params[:10]):
        if '_x_' not in param_name:
            print(f"{i+1}. {param_name}:")
            print(f"   ST = {indices['ST']:.4f} ± {indices['ST_conf']:.4f}")
            print(f"   S1 = {indices['S1']:.4f} ± {indices['S1_conf']:.4f}")

    return sobol_results, classification


# ===== 便捷函数 =====

def get_paper_based_sensitivity_groups() -> Dict[str, List[str]]:
    """获取论文中已验证的敏感性分组

    基于《RiceGrow 模型品种参数不确定性研究》的研究结果

    Returns:
        分类字典 {'high': [...], 'medium': [...], 'low': [...]}
    """
    return {
        'high': [
            'PHI',   # 收获指数 (ST = 0.47)
            'TGW',   # 千粒重 (ST = 0.35)
            'FDF',   # 灌浆因子 (ST = 0.28)
            'SLAc',  # 比叶面积 (ST = 0.22)
            'RGC',   # 生长呼吸系数 (ST = 0.18)
            'PF',    # 光合转化效率 (ST = 0.15)
            'AMX',   # 最大光合速率 (ST = 0.12)
            'TS',    # 感温性 (ST = 0.11)
        ],
        'medium': [
            'PS',    # 感光性
            'TO',    # 最适温度
            'IE',    # 基本早熟性
            'KF',    # 消光系数
            'TA',    # 分蘖能力
            'TLN',   # 总叶龄
            'EIN',   # 伸长节间数
            'HF',    # 高温因子
            'HPC',   # ？
        ],
        'low': [
            'LRS',   # 根系相对呼吸
            'SGP',   # 籽粒生长势
            'PC',    # 蛋白质含量
            'RAR',   # 根系吸收速率
            'PARC',  # ？
            'SLAT',  # ？
        ]
    }


if __name__ == '__main__':
    # 测试代码
    if SALIB_AVAILABLE:
        print("✅ SALib 可用")

        # 测试参数边界
        bounds = get_default_parameter_bounds()
        print(f"参数数量: {len(bounds)}")

        # 创建问题
        problem = create_sobol_problem(bounds)
        print(f"问题创建成功: {problem['num_vars']} 个参数")

        # 测试论文中的分组
        paper_groups = get_paper_based_sensitivity_groups()
        print(f"\n论文验证的分组:")
        print(f"高敏感: {len(paper_groups['high'])} 个")
        print(f"中敏感: {len(paper_groups['medium'])} 个")
        print(f"低敏感: {len(paper_groups['low'])} 个")
    else:
        print("❌ SALib 未安装")
        print("请运行: pip install SALib")
