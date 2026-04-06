"""
参数约束模块

定义水稻模型参数的硬约束和软约束规则
"""
from typing import Dict, List, Tuple, Optional, Callable
import numpy as np


# ===== 参数相关性约束 =====

class ParameterCorrelation:
    """参数相关性约束"""

    # PS × TS 权衡关系（粳稻 vs 籼稻）
    @staticmethod
    def ps_ts_balance(params: Dict[str, float]) -> Tuple[bool, str]:
        """检查 PS 和 TS 的平衡关系

        粳稻: 低PS + 高TS
        籼稻: 高PS + 低TS
        """
        ps = params.get('PS', 0.05)
        ts = params.get('TS', 2.8)

        # 粳稻类型
        if ps < 0.035 and ts > 2.85:
            return True, "japonica"
        # 籼稻类型
        elif ps > 0.05 and ts < 2.85:
            return True, "indica"
        # 中间类型
        elif 0.035 <= ps <= 0.05 and 2.7 <= ts <= 2.85:
            return True, "intermediate"
        else:
            return False, f"PS×TS 不匹配: PS={ps:.3f}, TS={ts:.2f}"

    # PHI × TLN 关联（生育期长可以支持更高的收获指数）
    @staticmethod
    def phi_tln_consistency(params: Dict[str, float]) -> Tuple[bool, str]:
        """检查 PHI 和 TLN 的一致性"""
        phi = params.get('PHI', 0.45)
        tln = params.get('TLN', 17.0)

        # 长生育期品种可以支持更高的收获指数
        if tln > 17.5:
            if phi > 0.46:
                return True, "valid"
            else:
                return False, f"长生育期品种 (TLN={tln:.1f}) 的收获指数偏低"
        # 短生育期品种收获指数受限
        elif tln < 15.5:
            if phi < 0.46:
                return True, "valid"
            else:
                return False, f"短生育期品种 (TLN={tln:.1f}) 的收获指数偏高"
        else:
            return True, "valid"

    # AMX × RGC 平衡（光合强需要呼吸强）
    @staticmethod
    def amx_rgc_balance(params: Dict[str, float]) -> Tuple[bool, str]:
        """检查 AMX 和 RGC 的平衡"""
        amx = params.get('AMX', 45)
        rgc = params.get('RGC', 0.3)

        # 高光合需要高呼吸
        if amx > 46 and rgc < 0.29:
            return False, f"高光合品种 (AMX={amx:.1f}) 需要更高的呼吸系数"
        # 低光合可以低呼吸
        elif amx < 43 and rgc > 0.31:
            return False, f"低光合品种 (AMX={amx:.1f}) 的呼吸系数过高"
        else:
            return True, "valid"


# ===== 生物学边界约束 =====

class BiologicalBounds:
    """生物学边界约束"""

    # 必须满足的边界
    HARD_BOUNDS = {
        'PS': (0.0, 0.1),           # 光敏感性 0-10%
        'TS': (2.0, 4.0),           # 温度敏感性
        'TO': (20.0, 35.0),         # 最适温度范围
        'IE': (0.0, 0.3),           # 基本早熟性
        'HF': (0.005, 0.02),        # 高温因子
        'FDF': (0.5, 0.9),          # 灌浆因子
        'PHI': (0.30, 0.55),        # 收获指数 30%-55%
        'TGW': (15.0, 40.0),        # 千粒重 15-40g
        'SLAc': (150, 250),         # 比叶面积
        'PF': (0.01, 0.02),         # 光合衰减因子
        'AMX': (30, 60),            # 最大光合速率
        'KF': (0.005, 0.015),       # 消光系数因子
        'RGC': (0.20, 0.40),        # 生长呼吸系数
        'LRS': (0.003, 0.01),       # 根系相对呼吸
        'TLN': (10, 22),            # 总叶龄
        'EIN': (3, 7),              # 伸长节间数
        'TA': (0.2, 0.7),           # 分蘖能力
        'SGP': (5, 8),              # 籽粒生长势
        'PC': (5, 12),              # 蛋白质含量
        'RAR': (1.5, 3.0),          # 根系吸收速率
    }

    @classmethod
    def check_bounds(cls, params: Dict[str, float]) -> Tuple[bool, List[str]]:
        """检查所有参数是否在生物学边界内

        Returns:
            (is_valid, violations)
        """
        violations = []

        for param, value in params.items():
            if param in cls.HARD_BOUNDS:
                lower, upper = cls.HARD_BOUNDS[param]
                if not (lower <= value <= upper):
                    violations.append(
                        f"{param}={value:.3f} 超出边界 [{lower}, {upper}]"
                    )

        return len(violations) == 0, violations


# ===== 优先级约束 =====

class PriorityConstraints:
    """优先级约束：根据敏感度确定调参优先级"""

    # 高敏感度参数（优先校准）
    HIGH_PRIORITY = [
        'PS', 'TS', 'TO',      # 生育期驱动
        'PHI', 'TGW',          # 产量形成
        'AMX', 'RGC',          # 光合呼吸平衡
        'FDF',                 # 灌浆进程
    ]

    # 中敏感度参数
    MEDIUM_PRIORITY = [
        'IE', 'HF',
        'SLAc', 'PF', 'KF',
        'TLN', 'EIN', 'TA',
    ]

    # 低敏感度参数（可固定）
    LOW_PRIORITY = [
        'LRS', 'SGP', 'PC', 'RAR',
    ]

    @classmethod
    def get_priority(cls, param: str) -> str:
        """获取参数优先级"""
        if param in cls.HIGH_PRIORITY:
            return 'high'
        elif param in cls.MEDIUM_PRIORITY:
            return 'medium'
        elif param in cls.LOW_PRIORITY:
            return 'low'
        return 'unknown'

    @classmethod
    def get_param_groups(cls) -> Dict[str, List[str]]:
        """获取按优先级分组的参数"""
        return {
            'high': cls.HIGH_PRIORITY,
            'medium': cls.MEDIUM_PRIORITY,
            'low': cls.LOW_PRIORITY,
        }


# ===== 参数建议系统 =====

class ParameterSuggestions:
    """参数建议系统"""

    # 根据其他参数的建议
    @staticmethod
    def suggest_phi(params: Dict[str, float]) -> Tuple[float, float]:
        """根据生育期参数建议 PHI 范围"""
        tln = params.get('TLN', 17.0)
        ps = params.get('PS', 0.05)

        # 长生育期 + 籼稻类型 → 高收获指数
        if tln > 17.5 and ps > 0.05:
            return 0.46, 0.48
        # 短生育期 + 粳稻类型 → 中等收获指数
        elif tln < 15.5 and ps < 0.035:
            return 0.42, 0.45
        else:
            return 0.44, 0.47

    @staticmethod
    def suggest_tgw(params: Dict[str, float]) -> Tuple[float, float]:
        """根据其他参数建议 TGW 范围"""
        phi = params.get('PHI', 0.45)

        # 高收获指数通常对应较小粒重
        if phi > 0.47:
            return 24.0, 26.5
        # 中等收获指数
        elif phi > 0.44:
            return 25.5, 27.5
        else:
            return 26.5, 28.5


# ===== 综合约束检查器 =====

class ConstraintChecker:
    """综合约束检查器"""

    def __init__(self):
        self.correlation = ParameterCorrelation()
        self.bounds = BiologicalBounds()
        self.priority = PriorityConstraints()
        self.suggestions = ParameterSuggestions()

    def check_all(self, params: Dict[str, float],
                  check_correlations: bool = True) -> Dict[str, any]:
        """执行所有约束检查

        Args:
            params: 参数字典
            check_correlations: 是否检查参数相关性

        Returns:
            检查结果字典
        """
        result = {
            'is_valid': True,
            'violations': [],
            'warnings': [],
            'suggestions': {},
            'variety_type': None,
        }

        # 1. 硬边界检查
        valid, violations = self.bounds.check_bounds(params)
        result['is_valid'] &= valid
        result['violations'].extend(violations)

        # 2. 相关性检查
        if check_correlations:
            # PS × TS
            valid, msg = self.correlation.ps_ts_balance(params)
            if 'invalid' in msg.lower() or '不匹配' in msg:
                result['warnings'].append(msg)
            else:
                result['variety_type'] = msg

            # PHI × TLN
            valid, msg = self.correlation.phi_tln_consistency(params)
            if not valid:
                result['warnings'].append(msg)

            # AMX × RGC
            valid, msg = self.correlation.amx_rgc_balance(params)
            if not valid:
                result['warnings'].append(msg)

        # 3. 生成建议
        if 'PHI' not in params or params['PHI'] == 0:
            phi_range = self.suggestions.suggest_phi(params)
            result['suggestions']['PHI'] = phi_range

        if 'TGW' not in params or params['TGW'] == 0:
            tgw_range = self.suggestions.suggest_tgw(params)
            result['suggestions']['TGW'] = tgw_range

        return result

    def get_recommended_bounds(self, params: Dict[str, float]) -> Dict[str, Tuple[float, float]]:
        """根据当前参数值获取推荐的参数边界

        考虑品种类型和相关性约束
        """
        bounds = {}

        # 确定品种类型
        _, variety_type = self.correlation.ps_ts_balance(params)

        # 根据品种类型调整边界
        if variety_type == 'japonica':
            bounds['PS'] = (0.020, 0.035)
            bounds['TS'] = (2.85, 3.20)
            bounds['TO'] = (25.5, 27.0)
        elif variety_type == 'indica':
            bounds['PS'] = (0.050, 0.078)
            bounds['TS'] = (2.55, 2.80)
            bounds['TO'] = (27.0, 28.6)
        else:
            # 中间类型使用默认边界
            bounds['PS'] = (0.030, 0.060)
            bounds['TS'] = (2.70, 2.90)
            bounds['TO'] = (26.5, 27.5)

        # PHI 建议根据 TLN
        phi_range = self.suggestions.suggest_phi(params)
        bounds['PHI'] = phi_range

        return bounds


# ===== 便捷函数 =====

def validate_params(params: Dict[str, float],
                    strict: bool = False) -> Tuple[bool, List[str], List[str]]:
    """验证参数

    Args:
        params: 参数字典
        strict: 是否使用严格模式（警告视为错误）

    Returns:
        (is_valid, errors, warnings)
    """
    checker = ConstraintChecker()
    result = checker.check_all(params, check_correlations=True)

    errors = result['violations']
    warnings = result['warnings']

    if strict:
        errors.extend(warnings)
        warnings = []

    is_valid = len(errors) == 0

    return is_valid, errors, warnings


def get_variety_type(params: Dict[str, float]) -> str:
    """推断品种类型"""
    checker = ConstraintChecker()
    _, variety_type = checker.correlation.ps_ts_balance(params)
    return variety_type


if __name__ == '__main__':
    # 测试
    test_params = {
        'PS': 0.025, 'TS': 3.1, 'TO': 26.5,
        'PHI': 0.45, 'TGW': 26,
        'TLN': 15.5, 'AMX': 45, 'RGC': 0.3,
    }

    valid, errors, warnings = validate_params(test_params)
    print(f"有效性: {valid}")
    print(f"错误: {errors}")
    print(f"警告: {warnings}")
    print(f"品种类型: {get_variety_type(test_params)}")
