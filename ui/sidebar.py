"""
侧边栏模块 - 模拟参数配置界面

提供侧边栏渲染的统一入口。当前阶段为薄包装层，
实际实现仍在 app.py 的 show_sidebar_content() 中。
后续迭代将逐步将逻辑迁移至此模块。
"""
import pandas as pd


def render_sidebar(cultivar_df: pd.DataFrame) -> None:
    """渲染模拟控制侧边栏

    薄包装层，委托给 app.py 中的 show_sidebar_content()。

    Args:
        cultivar_df: 品种参数DataFrame
    """
    # 延迟导入避免循环依赖
    from app import show_sidebar_content
    show_sidebar_content(cultivar_df)
