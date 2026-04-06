"""
结果展示模块 - 模拟结果可视化

提供模拟结果展示的统一入口。当前阶段为薄包装层，
实际实现仍在 app.py 的 display_simulation_results() 中。
后续迭代将逐步将逻辑迁移至此模块。
"""
from typing import List, Dict, Any, Optional


def display_simulation_results(results: List[Optional[Dict[str, Any]]]) -> None:
    """显示模拟结果

    薄包装层，委托给 app.py 中的 display_simulation_results()。

    Args:
        results: 模拟结果列表
    """
    # 延迟导入避免循环依赖
    from app import display_simulation_results as _display
    _display(results)
