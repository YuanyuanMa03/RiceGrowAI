"""
科研级别图表可视化模块

提供高质量的科研发表级别图表
"""
import plotly.graph_objects as go
import plotly.express as px
import plotly.subplots as sp
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple


# ==================== 科研级图表配置 ====================

# 科研期刊配色方案
PUBLICATION_COLORS = {
    'observed': '#1f77b4',      # 深蓝 - 观测值
    'simulated': '#2ca02c',     # 绿色 - 模拟值
    'before': '#7f7f7f',        # 灰色 - 校准前
    'after': '#d62728',         # 红色 - 校准后
    'confidence': '#ff7f0e',    # 橙色 - 置信区间
    'reference': '#9467bd',     # 紫色 - 参考线
}

# Nature期刊风格配色
NATURE_COLORS = {
    'observed': '#0173B2',      # Nature蓝
    'simulated': '#DE8F05',     # Nature橙
    'before': '#949494',        # 灰色
    'after': '#CC0203',         # Nature红
    'reference': '#949494',     # 灰色 - 参考线
}

# Science期刊风格配色
SCIENCE_COLORS = {
    'observed': '#0088AA',      # Science青
    'simulated': '#EECC44',     # Science黄
    'before': '#999999',        # 灰色
    'after': '#EE6666',         # Science红
    'reference': '#999999',     # 灰色 - 参考线
}

# 字体配置 - 科研论文标准
PUBLICATION_FONTS = dict(
    family='Arial, sans-serif',
    size=14,
    color='#212121'
)

TITLE_FONTS = dict(
    family='Arial, sans-serif',
    size=18,
    color='#000000'
)

AXIS_FONTS = dict(
    family='Arial, sans-serif',
    size=14,
    color='#424242'
)


# ==================== 时间序列对比图 ====================

def create_publication_timeseries(
    observed_data: pd.DataFrame,
    simulated_after: pd.DataFrame,
    variables: List[str] = None,
    simulated_before: pd.DataFrame = None,
    style: str = 'nature'
) -> go.Figure:
    """创建科研发表级别的时间序列对比图

    Args:
        observed_data: 观测数据
        simulated_after: 校准后模拟结果
        variables: 要显示的变量列表
        simulated_before: 校准前模拟结果（可选）
        style: 图表样式 ('nature', 'science', 'default')

    Returns:
        Plotly Figure对象
    """
    if variables is None:
        variables = ['Biomass']

    # 过滤存在的变量
    variables = [v for v in variables if v in observed_data.columns and v in simulated_after.columns]

    if not variables:
        fig = go.Figure()
        fig.add_annotation(text="无可用数据", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        return fig

    # 选择配色方案
    colors = PUBLICATION_COLORS if style == 'default' else (
        NATURE_COLORS if style == 'nature' else SCIENCE_COLORS
    )

    # 创建子图
    n_vars = len(variables)
    fig = sp.make_subplots(
        rows=n_vars, cols=1,
        subplot_titles=[f"<b>{var}</b>" for var in variables],
        vertical_spacing=0.12,
        shared_xaxes=True
    )

    # 添加数据 traces
    for i, var in enumerate(variables, start=1):
        # 观测值
        obs_dat = observed_data['DAT'].values
        obs_vals = observed_data[var].values

        fig.add_trace(
            go.Scatter(
                x=obs_dat,
                y=obs_vals,
                mode='markers',
                name='观测值' if i == 1 else None,
                marker=dict(
                    size=10,
                    color=colors['observed'],
                    symbol='circle',
                    line=dict(width=1, color='white')
                ),
                legendgroup='observed',
                showlegend=(i == 1),
                hovertemplate=f'<b>DAT</b>: %{{x}}<br><b>观测{var}</b>: %{{y:.2f}}<extra></extra>'
            ),
            row=i, col=1
        )

        # 校准前模拟
        if simulated_before is not None and var in simulated_before.columns:
            fig.add_trace(
                go.Scatter(
                    x=simulated_before['DAT'].values,
                    y=simulated_before[var].values,
                    mode='lines',
                    name='校准前' if i == 1 else None,
                    line=dict(dash='dash', color=colors['before'], width=2.5),
                    legendgroup='before',
                    showlegend=(i == 1),
                    hovertemplate=f'<b>DAT</b>: %{{x}}<br><b>校准前</b>: %{{y:.2f}}<extra></extra>'
                ),
                row=i, col=1
            )

        # 校准后模拟
        sim_dat = simulated_after['DAT'].values
        sim_vals = simulated_after[var].values

        fig.add_trace(
            go.Scatter(
                x=sim_dat,
                y=sim_vals,
                mode='lines',
                name='校准后' if i == 1 else None,
                line=dict(color=colors['after'], width=3),
                legendgroup='after',
                showlegend=(i == 1),
                hovertemplate=f'<b>DAT</b>: %{{x}}<br><b>校准后</b>: %{{y:.2f}}<extra></extra>'
            ),
            row=i, col=1
        )

    # 更新布局 - 科研论文风格
    # 计算生育期信息（使用第一个变量的数据）
    if len(simulated_after) > 0:
        max_day = simulated_after['DAT'].max()
        growth_period = f"生育期: 1-{int(max_day)} 天"
        obs_points = f"观测点: {len(observed_data)} 个"
        title_text = f'<b>模拟结果与观测值对比</b><br><sup>{growth_period} | {obs_points}</sup>'
    else:
        title_text = '<b>模拟结果与观测值对比</b>'

    fig.update_layout(
        title=dict(
            text=title_text,
            font=TITLE_FONTS,
            x=0.5,
            xanchor='center'
        ),
        height=400 * n_vars,
        template='plotly_white',
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            font=PUBLICATION_FONTS
        ),
        margin=dict(l=80, r=40, t=100, b=80)
    )

    # 配置坐标轴
    fig.update_xaxes(
        title_text='<b>天数 (DAT)</b>',
        title_font=AXIS_FONTS,
        tickfont=AXIS_FONTS,
        gridcolor='#E0E0E0',
        gridwidth=1,
        showgrid=True,
        zeroline=True,
        zerolinewidth=2,
        zerolinecolor='#424242'
    )

    for i, var in enumerate(variables, start=1):
        fig.update_yaxes(
            title_text=f'<b>{var}</b>',
            title_font=AXIS_FONTS,
            tickfont=AXIS_FONTS,
            gridcolor='#E0E0E0',
            gridwidth=1,
            showgrid=True,
            row=i, col=1
        )

    return fig


# ==================== 1:1散点图（科研级） ====================

def create_publication_scatter(
    observed: np.ndarray,
    simulated: np.ndarray,
    var_name: str = "Biomass",
    unit: str = "kg/ha",
    style: str = 'nature'
) -> go.Figure:
    """创建科研发表级别的1:1散点图

    Args:
        observed: 观测值数组
        simulated: 模拟值数组
        var_name: 变量名称
        unit: 单位
        style: 图表样式

    Returns:
        Plotly Figure对象
    """
    # 移除NaN
    mask = ~(np.isnan(observed) | np.isnan(simulated))
    obs = observed[mask]
    sim = simulated[mask]

    if len(obs) == 0:
        fig = go.Figure()
        fig.add_annotation(text=f"{var_name}: 无数据", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=16))
        return fig

    # 计算统计指标
    from calibration.metrics import calculate_r2, calculate_nse, calculate_rmse, calculate_mae

    r2 = calculate_r2(obs, sim)
    nse = calculate_nse(obs, sim)
    rmse = calculate_rmse(obs, sim)
    mae = calculate_mae(obs, sim)

    # 选择配色
    colors = NATURE_COLORS if style == 'nature' else SCIENCE_COLORS

    # 创建图表
    fig = go.Figure()

    # 添加数据点
    fig.add_trace(
        go.Scatter(
            x=obs,
            y=sim,
            mode='markers',
            name='数据点',
            marker=dict(
                size=12,
                color=colors['observed'],
                symbol='circle',
                line=dict(width=1, color='white'),
                opacity=0.8
            ),
            hovertemplate=f'<b>观测值</b>: %{{x:.2f}} {unit}<br><b>模拟值</b>: %{{y:.2f}} {unit}<extra></extra>'
        )
    )

    # 添加1:1参考线
    max_val = max(obs.max(), sim.max()) * 1.05
    min_val = min(obs.min(), sim.min()) * 0.95

    fig.add_trace(
        go.Scatter(
            x=[min_val, max_val],
            y=[min_val, max_val],
            mode='lines',
            name='1:1 参考线',
            line=dict(color=colors['reference'], dash='solid', width=2),
            hovertemplate='1:1 线<extra></extra>'
        )
    )

    # 添加拟合线
    if len(obs) > 2:
        from scipy import stats
        slope, intercept, r_value, p_value, std_err = stats.linregress(obs, sim)
        line_x = np.array([min_val, max_val])
        line_y = slope * line_x + intercept

        fig.add_trace(
            go.Scatter(
                x=line_x,
                y=line_y,
                mode='lines',
                name='拟合线',
                line=dict(color=colors['simulated'], dash='dash', width=2),
                hovertemplate=f'拟合线: y={slope:.3f}x+{intercept:.3f}<extra></extra>'
            )
        )

    # 更新布局 - 科研论文风格
    stats_text = (
        f'<b>R²</b> = {r2:.4f}<br>'
        f'<b>NSE</b> = {nse:.4f}<br>'
        f'<b>RMSE</b> = {rmse:.2f} {unit}<br>'
        f'<b>MAE</b> = {mae:.2f} {unit}'
    )

    fig.update_layout(
        title=dict(
            text=f'<b>{var_name}</b>: 模拟值 vs 观测值',
            font=TITLE_FONTS,
            x=0.5,
            xanchor='center'
        ),
        xaxis_title=f'<b>观测值 ({unit})</b>',
        yaxis_title=f'<b>模拟值 ({unit})</b>',
        template='plotly_white',
        height=550,
        width=600,
        font=PUBLICATION_FONTS,
        legend=dict(
            x=0.02,
            y=0.98,
            xanchor='left',
            yanchor='top',
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#CCCCCC',
            borderwidth=1,
            font=dict(size=12)
        ),
        margin=dict(l=80, r=40, t=80, b=80),
        annotations=[
            dict(
                text=stats_text,
                xref='paper',
                yref='paper',
                x=0.98,
                y=0.98,
                xanchor='right',
                yanchor='top',
                showarrow=False,
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='#CCCCCC',
                borderwidth=1,
                font=dict(size=12)
            )
        ]
    )

    # 配置坐标轴
    fig.update_xaxes(
        title_font=AXIS_FONTS,
        tickfont=AXIS_FONTS,
        gridcolor='#E0E0E0',
        gridwidth=1,
        showgrid=True,
        zeroline=True,
        zerolinewidth=2,
        zerolinecolor='#424242',
        range=[min_val, max_val]
    )

    fig.update_yaxes(
        title_font=AXIS_FONTS,
        tickfont=AXIS_FONTS,
        gridcolor='#E0E0E0',
        gridwidth=1,
        showgrid=True,
        zeroline=True,
        zerolinewidth=2,
        zerolinecolor='#424242',
        range=[min_val, max_val]
    )

    return fig


# ==================== 残差图（科研级） ====================

def create_publication_residual(
    observed: np.ndarray,
    simulated: np.ndarray,
    var_name: str = "Biomass",
    unit: str = "kg/ha",
    style: str = 'nature'
) -> go.Figure:
    """创建科研发表级别的残差图

    Args:
        observed: 观测值数组
        simulated: 模拟值数组
        var_name: 变量名称
        unit: 单位
        style: 图表样式

    Returns:
        Plotly Figure对象
    """
    # 计算残差
    mask = ~(np.isnan(observed) | np.isnan(simulated))
    obs = observed[mask]
    sim = simulated[mask]
    residuals = sim - obs
    dat = np.arange(len(residuals))

    if len(residuals) == 0:
        fig = go.Figure()
        fig.add_annotation(text=f"{var_name}: 无数据", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        return fig

    # 计算统计
    mean_res = np.mean(residuals)
    std_res = np.std(residuals)

    # 选择配色
    colors = NATURE_COLORS if style == 'nature' else SCIENCE_COLORS

    # 创建图表
    fig = go.Figure()

    # 添加零线
    fig.add_hline(
        y=0,
        line_dash='solid',
        line_color='red',
        line_width=2,
        annotation_text='零线',
        annotation_position='right'
    )

    # 添加均值线
    fig.add_hline(
        y=mean_res,
        line_dash='dash',
        line_color=colors['reference'],
        line_width=2,
        annotation_text=f'均值: {mean_res:.2f}',
        annotation_position='left'
    )

    # 添加残差柱状图
    colors_res = ['#d62728' if r < 0 else '#2ca02c' for r in residuals]

    fig.add_trace(
        go.Bar(
            x=dat,
            y=residuals,
            name='残差',
            marker=dict(color=colors_res),
            hovertemplate=f'<b>样本</b>: %{{x}}<br><b>残差</b>: %{{y:.2f}} {unit}<extra></extra>'
        )
    )

    # 更新布局
    fig.update_layout(
        title=dict(
            text=f'<b>{var_name}</b>: 残差分布',
            font=TITLE_FONTS,
            x=0.5,
            xanchor='center'
        ),
        xaxis_title='<b>样本编号</b>',
        yaxis_title=f'<b>残差 ({unit})</b>',
        template='plotly_white',
        height=400,
        font=PUBLICATION_FONTS,
        showlegend=False,
        margin=dict(l=80, r=40, t=80, b=80),
        annotations=[
            dict(
                text=f'<b>均值</b>: {mean_res:.2f}<br><b>标准差</b>: {std_res:.2f}',
                xref='paper',
                yref='paper',
                x=0.98,
                y=0.95,
                xanchor='right',
                yanchor='top',
                showarrow=False,
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='#CCCCCC',
                borderwidth=1,
                font=dict(size=12)
            )
        ]
    )

    fig.update_xaxes(title_font=AXIS_FONTS, tickfont=AXIS_FONTS, showgrid=False)
    fig.update_yaxes(
        title_font=AXIS_FONTS,
        tickfont=AXIS_FONTS,
        gridcolor='#E0E0E0',
        gridwidth=1,
        showgrid=True,
        zeroline=True,
        zerolinewidth=2,
        zerolinecolor='#424242'
    )

    return fig


# ==================== 箱线图（科研级） ====================

def create_publication_boxplot(
    data: List[np.ndarray],
    labels: List[str],
    var_name: str = "Biomass",
    unit: str = "kg/ha"
) -> go.Figure:
    """创建科研发表级别的箱线图

    Args:
        data: 数据数组列表
        labels: 标签列表
        var_name: 变量名称
        unit: 单位

    Returns:
        Plotly Figure对象
    """
    fig = go.Figure()

    for i, (d, label) in enumerate(zip(data, labels)):
        fig.add_trace(
            go.Box(
                y=d,
                name=label,
                marker_color=NATURE_COLORS['observed'],
                boxpoints='outliers',
                jitter=0.3,
                pointpos=-1.8 + 0.3 * i,
                hovertemplate=f'<b>{label}</b><br>中位数: %{{median:.2f}} {unit}<extra></extra>'
            )
        )

    fig.update_layout(
        title=dict(
            text=f'<b>{var_name}</b>: 数据分布对比',
            font=TITLE_FONTS,
            x=0.5,
            xanchor='center'
        ),
        yaxis_title=f'<b>{var_name} ({unit})</b>',
        template='plotly_white',
        height=500,
        font=PUBLICATION_FONTS,
        showlegend=True,
        margin=dict(l=80, r=40, t=80, b=80)
    )

    fig.update_yaxes(
        title_font=AXIS_FONTS,
        tickfont=AXIS_FONTS,
        gridcolor='#E0E0E0',
        gridwidth=1
    )

    return fig


# ==================== Streamlit 显示函数 ====================

def display_publication_figure(
    fig: go.Figure,
    use_container_width: bool = True,
    height: int = None
):
    """在Streamlit中显示科研级图表

    Args:
        fig: Plotly Figure对象
        use_container_width: 是否使用容器宽度
        height: 图表高度
    """
    import streamlit as st

    config = {
        'displayModeBar': True,
        'displaylogo': False,
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'chart_export',
            'height': height or 600,
            'width': 1000,
            'scale': 2  # 高分辨率导出
        },
        'staticPlot': False,  # 保持交互性
    }

    st.plotly_chart(
        fig,
        use_container_width=use_container_width,
        height=height,
        config=config
    )


def create_metrics_summary(
    metrics: Dict[str, float],
    var_name: str = ""
) -> str:
    """生成科研级指标摘要HTML

    Args:
        metrics: 指标字典
        var_name: 变量名称

    Returns:
        HTML字符串
    """
    # 定义指标信息
    metric_info = {
        'R²': {'icon': 'R²', 'label': '决定系数', 'format': '{:.4f}'},
        'RMSE': {'icon': 'RMSE', 'label': '均方根误差', 'format': '{:.2f}'},
        'MAE': {'icon': 'MAE', 'label': '平均绝对误差', 'format': '{:.2f}'},
        'NSE': {'icon': 'NSE', 'label': '纳什效率', 'format': '{:.4f}'},
        'PBIAS': {'icon': 'PBIAS', 'label': '偏差百分比', 'format': '{:.2f}%'},
        'KGE': {'icon': 'KGE', 'label': 'Kling-Gupta效率', 'format': '{:.4f}'},
    }

    html = '<div style="display: flex; gap: 0.75rem; flex-wrap: wrap; margin: 1rem 0;">'

    for key, value in metrics.items():
        if key not in metric_info:
            continue

        info = metric_info[key]
        formatted_value = info['format'].format(value)

        # 根据指标值确定颜色
        if key in ['R²', 'NSE', 'KGE']:
            if value >= 0.75:
                bg_color = '#10B981'  # 绿色 - 优秀
                status = '优秀'
            elif value >= 0.5:
                bg_color = '#F59E0B'  # 橙色 - 良好
                status = '良好'
            else:
                bg_color = '#EF4444'  # 红色 - 较差
                status = '较差'
        elif key == 'PBIAS':
            abs_val = abs(value)
            if abs_val <= 10:
                bg_color = '#10B981'
                status = '优秀'
            elif abs_val <= 20:
                bg_color = '#F59E0B'
                status = '良好'
            else:
                bg_color = '#EF4444'
                status = '较差'
        else:
            bg_color = '#6366F1'
            status = '常规'

        html += f"""
        <div style="
            background: {bg_color};
            color: white;
            padding: 0.85rem;
            border-radius: 8px;
            min-width: 140px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            text-align: center;
        ">
            <div style="font-size: 0.75rem; opacity: 0.9;">{info['label']}</div>
            <div style="font-size: 1.5rem; font-weight: 700; margin: 0.25rem 0;">{formatted_value}</div>
            <div style="font-size: 0.65rem; opacity: 0.8;">{status}</div>
        </div>
        """

    html += '</div>'
    return html


if __name__ == '__main__':
    # 测试代码
    import pandas as pd

    # 创建测试数据
    np.random.seed(42)
    dat = np.arange(0, 120, 10)
    obs = np.array([100, 500, 1500, 3500, 6000, 8500, 11000, 13000, 14500, 15000, 15500, 15700])
    sim = obs * np.random.uniform(0.95, 1.05, len(obs))

    # 测试时间序列图
    observed_data = pd.DataFrame({'DAT': dat[:len(obs)], 'Biomass': obs})
    simulated_data = pd.DataFrame({'DAT': dat[:len(sim)], 'Biomass': sim})

    fig = create_publication_timeseries(observed_data, simulated_data, style='nature')
    fig.show()

    # 测试散点图
    fig2 = create_publication_scatter(obs, sim, "Biomass", "kg/ha", style='nature')
    fig2.show()

    # 测试残差图
    fig3 = create_publication_residual(obs, sim, "Biomass", "kg/ha", style='nature')
    fig3.show()
