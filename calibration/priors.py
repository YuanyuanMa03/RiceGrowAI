"""
先验分布定义模块

基于28个水稻品种的统计分析，定义各参数的先验分布。
用于贝叶斯参数校准（MCMC）。
"""
from typing import Dict, Any
import numpy as np

# ===== 品种参数先验分布 =====
# 基于 data/品种参数.csv 的统计特征（28个品种）

PARAMETER_PRIORS = {
    # 生育期参数（高度敏感）
    'PS': {
        'dist': 'TruncatedNormal',
        'mu': 0.046,      # 28个品种的均值
        'sigma': 0.018,   # 标准差
        'lower': 0.020,
        'upper': 0.078,
        'description': '光敏感性 (Photosensitivity)',
        'sensitivity': 'high',
    },
    'TS': {
        'dist': 'TruncatedNormal',
        'mu': 2.82,
        'sigma': 0.20,
        'lower': 2.55,
        'upper': 3.20,
        'description': '温度敏感性 (Temperature sensitivity)',
        'sensitivity': 'high',
    },
    'TO': {
        'dist': 'TruncatedNormal',
        'mu': 27.2,
        'sigma': 0.75,
        'lower': 25.8,
        'upper': 28.6,
        'description': '最适温度 (Optimum temperature, °C)',
        'sensitivity': 'high',
    },
    'IE': {
        'dist': 'Uniform',
        'lower': 0.10,
        'upper': 0.20,
        'description': '基本早熟性 (Index of earliness)',
        'sensitivity': 'high',
    },
    'HF': {
        'dist': 'TruncatedNormal',
        'mu': 0.0122,
        'sigma': 0.0012,
        'lower': 0.010,
        'upper': 0.015,
        'description': '高温因子 (High temperature factor)',
        'sensitivity': 'medium',
    },
    'FDF': {
        'dist': 'TruncatedNormal',
        'mu': 0.710,
        'sigma': 0.012,
        'lower': 0.688,
        'upper': 0.727,
        'description': '灌浆因子 (Filling duration factor)',
        'sensitivity': 'high',
    },

    # 收获相关（高度敏感）
    'PHI': {
        'dist': 'TruncatedNormal',
        'mu': 0.455,
        'sigma': 0.016,
        'lower': 0.427,
        'upper': 0.480,
        'description': '收获指数 (Harvest index)',
        'sensitivity': 'high',
    },
    'TGW': {
        'dist': 'TruncatedNormal',
        'mu': 26.5,
        'sigma': 1.2,
        'lower': 24.0,
        'upper': 28.0,
        'description': '千粒重 (Thousand grain weight, g)',
        'sensitivity': 'high',
    },

    # 光合参数（高度敏感）
    'SLAc': {
        'dist': 'TruncatedNormal',
        'mu': 196,
        'sigma': 7.0,
        'lower': 184,
        'upper': 207,
        'description': '比叶面积 (Specific leaf area, cm²/g)',
        'sensitivity': 'high',
    },
    'PF': {
        'dist': 'TruncatedNormal',
        'mu': 0.0149,
        'sigma': 0.0007,
        'lower': 0.0138,
        'upper': 0.0161,
        'description': '光合衰减因子 (Photosynthesis fading factor)',
        'sensitivity': 'high',
    },
    'AMX': {
        'dist': 'TruncatedNormal',
        'mu': 45.5,
        'sigma': 1.9,
        'lower': 41.0,
        'upper': 48.0,
        'description': '最大光合速率 (Maximum photosynthesis rate)',
        'sensitivity': 'high',
    },
    'KF': {
        'dist': 'TruncatedNormal',
        'mu': 0.0082,
        'sigma': 0.0005,
        'lower': 0.0072,
        'upper': 0.0090,
        'description': '消光系数因子 (Extinction coefficient factor)',
        'sensitivity': 'medium',
    },

    # 呼吸参数
    'RGC': {
        'dist': 'TruncatedNormal',
        'mu': 0.298,
        'sigma': 0.016,
        'lower': 0.27,
        'upper': 0.32,
        'description': '生长呼吸系数 (Growth respiration coefficient)',
        'sensitivity': 'high',
    },
    'LRS': {
        'dist': 'TruncatedNormal',
        'mu': 0.0067,
        'sigma': 0.0005,
        'lower': 0.0058,
        'upper': 0.0075,
        'description': '根系相对呼吸 (Leaf relative senescence)',
        'sensitivity': 'low',
    },

    # 形态参数（中度敏感）
    'TLN': {
        'dist': 'Uniform',
        'lower': 14.5,
        'upper': 18.3,
        'description': '总叶龄 (Total leaf number)',
        'sensitivity': 'medium',
    },
    'EIN': {
        'dist': 'TruncatedNormal',
        'mu': 5.0,
        'sigma': 0.25,
        'lower': 4.6,
        'upper': 5.5,
        'description': '伸长节间数 (Emerged leaf number at initiation)',
        'sensitivity': 'medium',
    },
    'TA': {
        'dist': 'TruncatedNormal',
        'mu': 0.47,
        'sigma': 0.03,
        'lower': 0.42,
        'upper': 0.52,
        'description': '分蘖能力 (Tillering ability)',
        'sensitivity': 'medium',
    },

    # 品质参数（低敏感）
    'SGP': {
        'dist': 'TruncatedNormal',
        'mu': 6.35,
        'sigma': 0.12,
        'lower': 6.15,
        'upper': 6.50,
        'description': '籽粒生长势 (Spikelet growth parameter)',
        'sensitivity': 'low',
    },
    'PC': {
        'dist': 'TruncatedNormal',
        'mu': 7.9,
        'sigma': 0.35,
        'lower': 7.4,
        'upper': 8.4,
        'description': '蛋白质含量 (Protein content, %)',
        'sensitivity': 'low',
    },
    'RAR': {
        'dist': 'TruncatedNormal',
        'mu': 2.12,
        'sigma': 0.14,
        'lower': 1.92,
        'upper': 2.36,
        'description': '根系吸收速率 (Root architecture ratio)',
        'sensitivity': 'low',
    },
}

# ===== CH4 模型参数先验 =====

CH4_PARAMETER_PRIORS = {
    'Q10': {
        'dist': 'TruncatedNormal',
        'mu': 2.8,
        'sigma': 0.5,
        'lower': 2.0,
        'upper': 4.0,
        'description': '温度敏感性系数 (Q10 temperature coefficient)',
    },
    'Eh0': {
        'dist': 'Uniform',
        'lower': 200.0,
        'upper': 300.0,
        'description': '初始氧化还原电位 (Initial redox potential, mV)',
    },
    'EhBase': {
        'dist': 'Uniform',
        'lower': -50.0,
        'upper': 50.0,
        'description': '基础氧化还原电位 (Base redox potential, mV)',
    },
    'WaterC': {
        'dist': 'TruncatedNormal',
        'mu': 0.65,
        'sigma': 0.06,
        'lower': 0.5,
        'upper': 0.8,
        'description': '水分含量系数 (Water content coefficient)',
    },
}

# ===== 管理参数先验（按地区调整）=====

MANAGEMENT_PARAMETER_PRIORS = {
    'OMS': {
        'dist': 'TruncatedNormal',
        'mu': 1500,
        'sigma': 500,
        'lower': 500,
        'upper': 3000,
        'description': '慢速分解有机质 (Slow decomposition OM, kg/ha)',
    },
    'OMN': {
        'dist': 'TruncatedNormal',
        'mu': 1500,
        'sigma': 500,
        'lower': 500,
        'upper': 3000,
        'description': '快速分解有机质 (Fast decomposition OM, kg/ha)',
    },
    'SoilSand': {
        'dist': 'TruncatedNormal',
        'mu': 35,
        'sigma': 10,
        'lower': 10,
        'upper': 60,
        'description': '土壤砂粒含量 (Soil sand content, %)',
    },
}


# ===== 参数软约束（品种类型建议）=====

SOFT_CONSTRAINTS = {
    'japonica': {
        'name': '粳稻 (Japonica)',
        'description': '适应北方低温短光环境',
        'typical_values': {
            'PS': (0.020, 0.030),
            'TS': (2.9, 3.2),
            'TO': (25.8, 26.8),
            'TLN': (14.5, 16.0),
        },
    },
    'indica': {
        'name': '籼稻 (Indica)',
        'description': '适应南方高温长光环境',
        'typical_values': {
            'PS': (0.055, 0.078),
            'TS': (2.55, 2.80),
            'TO': (27.0, 28.6),
            'TLN': (17.0, 18.3),
        },
    },
    'hybrid': {
        'name': '杂交稻 (Hybrid)',
        'description': '高产杂交组合',
        'typical_values': {
            'PS': (0.065, 0.075),
            'TS': (2.68, 2.78),
            'TO': (27.0, 28.0),
            'PHI': (0.46, 0.48),
        },
    },
}


# ===== 参数硬约束（生物学边界）=====

def check_hard_constraints(params: Dict[str, float]) -> tuple[bool, list[str]]:
    """检查参数是否违反硬约束

    Args:
        params: 参数字典

    Returns:
        (is_valid, violations): (是否有效, 违反的约束列表)
    """
    violations = []

    # 1. 收获指数不可能超过0.5
    if 'PHI' in params and params['PHI'] > 0.50:
        violations.append(f"PHI ({params['PHI']:.3f}) 超过生物学上限 0.50")

    # 2. 千粒重合理范围
    if 'TGW' in params and not (20 <= params['TGW'] <= 35):
        violations.append(f"TGW ({params['TGW']:.1f}) 超出合理范围 [20, 35] g")

    # 3. 光敏感性必须在0-1之间
    if 'PS' in params and not (0 <= params['PS'] <= 0.1):
        violations.append(f"PS ({params['PS']:.3f}) 超出合理范围 [0, 0.1]")

    # 4. 温度敏感性合理范围
    if 'TS' in params and not (2.0 <= params['TS'] <= 4.0):
        violations.append(f"TS ({params['TS']:.2f}) 超出合理范围 [2.0, 4.0]")

    # 5. 总叶龄合理范围
    if 'TLN' in params and not (12 <= params['TLN'] <= 22):
        violations.append(f"TLN ({params['TLN']:.1f}) 超出合理范围 [12, 22]")

    # 6. 分蘖能力合理范围
    if 'TA' in params and not (0.3 <= params['TA'] <= 0.7):
        violations.append(f"TA ({params['TA']:.2f}) 超出合理范围 [0.3, 0.7]")

    is_valid = len(violations) == 0
    return is_valid, violations


def get_parameter_prior(param_name: str) -> Dict[str, Any]:
    """获取单个参数的先验配置

    Args:
        param_name: 参数名称

    Returns:
        先验配置字典，如果参数不存在则返回 None
    """
    if param_name in PARAMETER_PRIORS:
        return PARAMETER_PRIORS[param_name]
    elif param_name in CH4_PARAMETER_PRIORS:
        return CH4_PARAMETER_PRIORS[param_name]
    elif param_name in MANAGEMENT_PARAMETER_PRIORS:
        return MANAGEMENT_PARAMETER_PRIORS[param_name]
    return None


def get_all_prior_names() -> list[str]:
    """获取所有定义了先验的参数名称"""
    return (
        list(PARAMETER_PRIORS.keys()) +
        list(CH4_PARAMETER_PRIORS.keys()) +
        list(MANAGEMENT_PARAMETER_PRIORS.keys())
    )


def get_high_sensitivity_params() -> list[str]:
    """获取高敏感度参数列表（基于Sobol敏感性分析，总效应指数 > 0.1）"""
    return [
        'PS', 'TS', 'TO', 'IE', 'FDF',  # 生育期驱动参数
        'PHI', 'TGW',  # 产量形成参数
        'SLAc', 'PF', 'AMX',  # 光合作用参数
        'RGC',  # 呼吸参数
    ]


def get_medium_sensitivity_params() -> list[str]:
    """获取中敏感度参数列表（基于Sobol敏感性分析，0.01 < 总效应 < 0.1）"""
    return ['HF', 'KF', 'TLN', 'EIN', 'TA']


def get_low_sensitivity_params() -> list[str]:
    """获取低敏感度参数列表（基于Sobol敏感性分析，总效应 < 0.01）"""
    return ['LRS', 'SGP', 'PC', 'RAR']


def get_sensitivity_group(param_name: str) -> str:
    """获取参数的敏感度分组"""
    if param_name in get_high_sensitivity_params():
        return 'high'
    elif param_name in get_medium_sensitivity_params():
        return 'medium'
    elif param_name in get_low_sensitivity_params():
        return 'low'
    return 'unknown'


# ===== 响应曲面关系（基于PDF论文）=====

def get_phi_constraint(params: Dict[str, float]) -> tuple[float, float]:
    """根据其他参数推断 PHI 的合理范围

    基于PDF论文中的参数化关系：
    PHI 与 TLN（总叶龄）、PS（感光性）、TS（感温性）相关

    Args:
        params: 当前参数字典

    Returns:
        (lower, upper): PHI的推荐范围
    """
    tln = params.get('TLN', 17.0)
    ps = params.get('PS', 0.046)

    # 长生育期 + 高感光性 → 高收获指数
    if tln > 17.5 and ps > 0.05:
        return 0.46, 0.48
    # 短生育期 + 低感光性 → 中等收获指数
    elif tln < 15.5 and ps < 0.035:
        return 0.42, 0.45
    else:
        return 0.43, 0.47


def get_tgw_constraint(params: Dict[str, float]) -> tuple[float, float]:
    """根据收获指数推断 TGW 的合理范围

    基于PDF论文：TGW 与 PHI 负相关

    Args:
        params: 当前参数字典

    Returns:
        (lower, upper): TGW的推荐范围
    """
    phi = params.get('PHI', 0.45)

    # 高收获指数通常对应较小粒重
    if phi > 0.47:
        return 24.0, 26.5
    # 中等收获指数
    elif phi > 0.44:
        return 25.5, 27.5
    else:
        return 26.5, 28.5


def get_maturity_type(params: Dict[str, float]) -> str:
    """根据生育期参数推断品种熟性类型

    基于 PDF 论文的品种聚类方法

    Args:
        params: 参数字典（至少包含 TLN, PS, TS）

    Returns:
        'early' (早熟), 'mid' (中熟), 'late' (晚熟)
    """
    tln = params.get('TLN', 17.0)
    ps = params.get('PS', 0.046)
    ts = params.get('TS', 2.82)

    # 综合评分
    score = (tln / 18.0) * 0.5 + (ps / 0.078) * 0.3 + ((ts - 2.5) / 1.5) * 0.2

    if score < 0.85:
        return 'early'
    elif score < 0.95:
        return 'mid'
    else:
        return 'late'


def get_layered_calibration_strategy() -> Dict[str, Dict[str, Any]]:
    """获取分层校准策略（基于PDF论文）

    第一层：高敏感参数 → 精细校准（先验分布窄，MCMC采样数多）
    第二层：中敏感参数 → 适度校准
    第三层：低敏感参数 → 固定为文献值

    Returns:
        分层策略配置
    """
    return {
        'layer_1_high': {
            'description': '高敏感参数 - 精细校准',
            'params': get_high_sensitivity_params(),
            'calibration_method': 'mcmc',
            'prior_width': 'narrow',  # sigma 缩小20%
            'mcmc_draws': 5000,
            'mcmc_tunes': 2000,
        },
        'layer_2_medium': {
            'description': '中敏感参数 - 适度校准',
            'params': get_medium_sensitivity_params(),
            'calibration_method': 'mcmc',
            'prior_width': 'medium',
            'mcmc_draws': 2000,
            'mcmc_tunes': 1000,
        },
        'layer_3_low': {
            'description': '低敏感参数 - 固定文献值',
            'params': get_low_sensitivity_params(),
            'calibration_method': 'fixed',
            'fixed_values': {
                'LRS': 0.0067,
                'SGP': 6.35,
                'PC': 7.9,
                'RAR': 2.12,
            }
        }
    }


# ===== 便捷函数 =====

def get_default_priors(cultivar_type: str = 'hybrid') -> Dict[str, Dict[str, Any]]:
    """根据品种类型获取默认先验

    Args:
        cultivar_type: 品种类型 ('japonica', 'indica', 'hybrid')

    Returns:
        参数先验字典
    """
    priors = PARAMETER_PRIORS.copy()

    # 根据品种类型调整先验
    if cultivar_type in SOFT_CONSTRAINTS:
        typical = SOFT_CONSTRAINTS[cultivar_type]['typical_values']
        for param, (lower, upper) in typical.items():
            if param in priors:
                # 调整分布以匹配品种类型的典型值
                priors[param]['mu'] = (lower + upper) / 2
                priors[param]['lower'] = lower
                priors[param]['upper'] = upper

    return priors


if __name__ == '__main__':
    # 测试代码
    print("=== 品种参数先验分布 ===")
    for param, config in PARAMETER_PRIORS.items():
        print(f"{param}: {config['description']}")

    print("\n=== 软约束检查 ===")
    test_params = {'PHI': 0.52, 'TGW': 40}
    valid, violations = check_hard_constraints(test_params)
    print(f"有效性: {valid}")
    for v in violations:
        print(f"  - {v}")
