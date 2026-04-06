"""
调参结果可视化模块

提供校准前后模拟结果与观测值的对比图表
"""
import plotly.graph_objects as go
import plotly.express as px
import plotly.subplots as sp
import pandas as pd
import numpy as np

from calibration.metrics import format_metric_value
from typing import Dict, List, Optional

# 导入 metrics 模块中的函数
from calibration.metrics import (
    calculate_r2,
    calculate_nse,
    calculate_all_metrics,
    get_model_rating,
    format_metric_value
)


def create_timeseries_comparison(
    observed_data: pd.DataFrame,
    simulated_after: pd.DataFrame,
    variables: List[str] = None,
    simulated_before: pd.DataFrame = None
) -> go.Figure:
    """创建时间序列对比图

    生成一个多子图，每个变量一个子图，显示：
    - 观测值（散点）
    - 校准前模拟值（虚线，可选）
    - 校准后模拟值（实线）

    Args:
        observed_data: 观测数据，包含 DAT 列和变量列
        simulated_after: 校准后模拟结果
        variables: 要显示的变量列表（如 ['Biomass', 'CH4']）
        simulated_before: 校准前模拟结果（可选）

    Returns:
        Plotly 图表对象
    """
    if variables is None:
        variables = ['Biomass', 'CH4']

    # 过滤存在的变量
    variables = [v for v in variables if v in observed_data.columns and v in simulated_after.columns]

    if not variables:
        # 如果没有变量，返回空图表
        fig = go.Figure()
        fig.update_layout(
            title="没有可显示的数据",
            template='plotly_white'
        )
        return fig

    # 创建子图
    n_vars = len(variables)
    fig = sp.make_subplots(
        rows=n_vars, cols=1,
        subplot_titles=variables,
        vertical_spacing=0.08,
        shared_xaxes=True
    )

    colors = {
        'observed': 'black',
        'before': 'gray',
        'after': '#10B981'  # 绿色
    }

    for i, var in enumerate(variables, start=1):
        # 获取观测值
        obs_dat = observed_data['DAT'].values
        obs_vals = observed_data[var].values

        # 获取校准后模拟值
        # 处理 DAT 不匹配的情况：创建统一的 x 轴
        sim_dat_after = simulated_after['DAT'].values
        sim_vals_after = simulated_after[var].values

        # 添加观测值（使用观测数据的 DAT）
        fig.add_trace(
            go.Scatter(
                x=obs_dat,
                y=obs_vals,
                mode='markers',
                name=f'{var} 观测' if i == 1 else None,
                marker=dict(size=8, color=colors['observed']),
                legendgroup='observed',
                showlegend=(i == 1),
            ),
            row=i, col=1
        )

        # 添加校准前模拟（如果有）
        if simulated_before is not None and var in simulated_before.columns:
            fig.add_trace(
                go.Scatter(
                    x=simulated_before['DAT'].values,
                    y=simulated_before[var].values,
                    mode='lines',
                    name=f'{var} 校准前' if i == 1 else None,
                    line=dict(dash='dash', color=colors['before'], width=2),
                    legendgroup='before',
                    showlegend=(i == 1),
                ),
                row=i, col=1
            )

        # 添加校准后模拟
        fig.add_trace(
            go.Scatter(
                x=sim_dat_after,
                y=sim_vals_after,
                mode='lines',
                name=f'{var} 校准后' if i == 1 else None,
                line=dict(color=colors['after'], width=3),
                legendgroup='after',
                showlegend=(i == 1),
            ),
            row=i, col=1
        )

    # 更新布局
    fig.update_layout(
        title={
            'text': '校准前后模拟结果对比',
            'x': 0.5,
            'xanchor': 'center'
        },
        height=300 * n_vars,
        template='plotly_white',
        hovermode='x unified'
    )

    # 配置x轴和y轴
    fig.update_xaxes(title_text="天数 (DAT)")
    for i, var in enumerate(variables, start=1):
        fig.update_yaxes(title_text=var, row=i, col=1)

    return fig


def create_scatter_plot(
    observed: np.ndarray,
    simulated: np.ndarray,
    var_name: str = "变量"
) -> go.Figure:
    """创建 1:1 散点对比图

    显示观测值 vs 模拟值，带1:1参考线和R²标注

    Args:
        observed: 观测值数组
        simulated: 模拟值数组
        var_name: 变量名称（用于标题）

    Returns:
        Plotly 图表对象
    """
    # 移除NaN
    mask = ~(np.isnan(observed) | np.isnan(simulated))
    obs = observed[mask]
    sim = simulated[mask]

    if len(obs) == 0:
        # 返回空图表
        fig = go.Figure()
        fig.update_layout(
            title=f"{var_name}: 无数据",
            template='plotly_white'
        )
        return fig

    # 计算R²和NSE
    r2 = calculate_r2(obs, sim)
    nse = calculate_nse(obs, sim)

    # 创建散点图
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=obs,
            y=sim,
            mode='markers',
            name='数据点',
            marker=dict(
                size=10,
                color=sim,
                colorscale='Viridis',
                showscale=False,
                opacity=0.7
            ),
        )
    )

    # 添加1:1参考线
    max_val = max(obs.max(), sim.max())
    min_val = min(obs.min(), sim.min())

    fig.add_trace(
        go.Scatter(
            x=[min_val, max_val],
            y=[min_val, max_val],
            mode='lines',
            name='1:1 线',
            line=dict(color='red', dash='dash', width=2),
        )
    )

    # 更新布局
    fig.update_layout(
        title=f'{var_name}: 模拟值 vs 观测值<br><sub>R² = {r2:.4f}, NSE = {nse:.4f}</sub>',
        xaxis_title='观测值',
        yaxis_title='模拟值',
        template='plotly_white',
        height=500,
    )

    return fig


def create_residual_plot(
    observed: np.ndarray,
    simulated: np.ndarray,
    var_name: str = "残差"
) -> go.Figure:
    """创建残差分布图

    Args:
        observed: 观测值数组
        simulated: 模拟值数组
        var_name: 变量名称

    Returns:
        Plotly 图表对象（直方图）
    """
    # 计算残差
    mask = ~(np.isnan(observed) | np.isnan(simulated))
    obs = observed[mask]
    sim = simulated[mask]
    residuals = sim - obs

    if len(residuals) == 0:
        # 返回空图表
        fig = go.Figure()
        fig.update_layout(
            title=f"{var_name}: 无数据",
            template='plotly_white'
        )
        return fig

    # 创建直方图
    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=residuals,
            nbinsx=20,
            name='残差分布',
            marker_color='skyblue',
        )
    )

    # 添加零线
    fig.add_vline(x=0, line_dash="dash", line_color="red")

    # 计算统计
    mean_res = np.mean(residuals)
    std_res = np.std(residuals)

    fig.update_layout(
        title=f'{var_name} 残差分布<br><sub>均值={mean_res:.2f}, 标准差={std_res:.2f}</sub>',
        xaxis_title='残差 (模拟 - 观测)',
        yaxis_title='频数',
        template='plotly_white',
        height=400,
    )

    return fig


def create_metrics_cards(
    metrics: Dict[str, float],
    rating: str = ""
) -> str:
    """生成统计指标卡片的HTML

    Args:
        metrics: 指标字典 {name: value}
        rating: 模型评级

    Returns:
        HTML字符串
    """
    cards_html = """
    <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem;">
    """

    # 定义每个指标的颜色和图标
    metric_info = {
        'R²': {'icon': '🎯', 'color': '#10B981', 'format': '{:.4f}'},
        'RMSE': {'icon': '📏', 'color': '#F59E0B', 'format': '{:.2f}'},
        'MAE': {'icon': '📐', 'color': '#3B82F6', 'format': '{:.2f}'},
        'NSE': {'icon': '💧', 'color': '#6366F1', 'format': '{:.4f}'},
        'PBIAS': {'icon': '📊', 'color': '#8B5CF6', 'format': '{:.2f}%'},
        'KGE': {'icon': '⭐', 'color': '#EC4899', 'format': '{:.4f}'},
    }

    for name, value in metrics.items():
        if name in metric_info:
            info = metric_info[name]
            formatted_value = format_metric_value(value, name)

            # 根据值设定颜色深浅
            bg_color = info['color']
            if name == 'R²' or name == 'NSE' or name == 'KGE':
                if value < 0.5:
                    bg_color = '#EF4444'  # 红色
                elif value < 0.75:
                    bg_color = '#F59E0B'  # 橙色
                else:
                    bg_color = '#10B981'  # 绿色

            cards_html += f"""
        <div style="
            background: {bg_color};
            color: white;
            padding: 1rem;
            border-radius: 12px;
            min-width: 140px;
            flex: 1;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        ">
            <div style="font-size: 1.5rem;">{info['icon']}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">{name}</div>
            <div style="font-size: 1.5rem; font-weight: 700;">{formatted_value}</div>
        </div>
    """

    # 添加评级卡片
    if rating:
        cards_html += f"""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            border-radius: 12px;
            min-width: 200px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        ">
            <div style="font-size: 0.9rem; opacity: 0.9;">模型评级</div>
            <div style="font-size: 1.2rem; font-weight: 700;">{rating}</div>
        </div>
    """

    cards_html += "</div>"
    return cards_html


def create_evaluation_section(
    observed_data: pd.DataFrame,
    simulated_data: pd.DataFrame,
    variables: List[str] = None
) -> tuple:
    """创建完整的评估部分（指标卡片 + 图表）

    Args:
        observed_data: 观测数据，包含 DAT 列和变量列
        simulated_data: 模拟数据，包含 DAT 列和变量列
        variables: 要评估的变量列表

    Returns:
        (指标卡片HTML, 图表列表)
    """
    from calibration.metrics import align_and_calculate_metrics

    if variables is None:
        variables = ['Biomass', 'CH4']

    # 过滤存在的变量
    variables = [v for v in variables if v in observed_data.columns and v in simulated_data.columns]

    if not variables:
        return "<p>没有可显示的数据</p>", []

    # 计算所有指标的HTML
    metrics_html = ""
    figures = []

    for var in variables:
        # 对齐数据并计算指标
        var_metrics = align_and_calculate_metrics(observed_data, simulated_data, [var])

        if var not in var_metrics:
            continue

        # 获取指标
        metrics = var_metrics[var]
        rating = get_model_rating(metrics.get('R²', np.nan), metrics.get('NSE', np.nan))

        # 生成指标卡片
        metrics_html += f"""
        <h4 style="margin-top: 1.5rem; margin-bottom: 0.5rem;">{var}</h4>
        {create_metrics_cards(metrics, rating)}
        """

        # 创建1:1散点图
        obs_vals = observed_data[var].values
        sim_vals = simulated_data[var].values

        # 对齐数据
        merged = pd.merge(
            observed_data[['DAT', var]],
            simulated_data[['DAT', var]],
            on='DAT',
            how='inner'
        ).dropna()

        if len(merged) > 0:
            scatter_fig = create_scatter_plot(
                merged[f'{var}_x'].values,
                merged[f'{var}_y'].values,
                var
            )
            figures.append(('scatter', var, scatter_fig))

            # 创建残差图
            residual_fig = create_residual_plot(
                merged[f'{var}_x'].values,
                merged[f'{var}_y'].values,
                var
            )
            figures.append(('residual', var, residual_fig))

    return metrics_html, figures


if __name__ == '__main__':
    # 测试
    import pandas as pd

    # 创建测试数据
    dat = np.arange(0, 130, 10)
    obs = np.array([200, 500, 1500, 3500, 6000, 8500, 11000, 13000, 14500, 15400, 16000, 16500, 16800])
    sim = obs * np.random.uniform(0.9, 1.1, len(obs))

    observed_data = pd.DataFrame({'DAT': dat[:len(obs)], 'Biomass': obs})
    simulated_data = pd.DataFrame({'DAT': dat[:len(sim)], 'Biomass': sim})

    # 测试散点图
    fig = create_scatter_plot(obs, sim, "Biomass")
    fig.show()

    # 测试指标卡片
    from calibration.metrics import calculate_all_metrics
    metrics = calculate_all_metrics(obs, sim)
    rating = get_model_rating(metrics['R²'], metrics['NSE'])
    html = create_metrics_cards(metrics, rating)
    print(html)
