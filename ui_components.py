"""
UI组件模块 - 企业级水稻生长与CH4排放模拟系统

本模块包含可复用的Streamlit UI组件
"""
from typing import List, Tuple, Optional
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import (
    RECOMMENDED_VARIETIES,
    MAX_VARIETIES,
    WATER_REGIME_NAMES,
    WATER_REGIME_DESCRIPTIONS,
    SAND_CONTENT_MIN,
    SAND_CONTENT_MAX,
    OM_MIN,
    OM_MAX,
    ERROR_MESSAGES,
)


def render_sidebar_header() -> None:
    """渲染侧边栏头部"""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #10B981 0%, #3B82F6 100%);
        color: white;
        padding: 0.85rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        text-align: center;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
        position: relative;
        overflow: hidden;
    ">
        <div style="
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 100%;
            background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.15) 50%, transparent 70%);
            animation: shine 2.5s infinite;
        "></div>
        <h3 style="margin: 0; font-size: 1.1rem; font-weight: 700; letter-spacing: 0.5px; position: relative; z-index: 1;">
            ⚙️ 模拟控制台
        </h3>
        <p style="margin: 0.2rem 0 0 0; font-size: 0.75rem; opacity: 0.95; position: relative; z-index: 1;">
            配置参数并运行模拟
        </p>
    </div>

    <style>
        @keyframes shine {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
    </style>
    """, unsafe_allow_html=True)


def render_variety_selector(
    varieties: List[str],
    current_selection: List[str]
) -> List[str]:
    """渲染品种选择组件

    Args:
        varieties: 可选品种列表
        current_selection: 当前已选择的品种

    Returns:
        用户选择的品种列表
    """
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%);
        border: 2px solid #10B981;
        padding: 0.75rem;
        margin-bottom: 0.75rem;
        border-radius: 10px;
    ">
        <h4 style="
            color: #065F46;
            margin: 0 0 0.35rem 0;
            font-size: 0.95rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        ">
            🌱 <span>品种选择</span>
        </h4>
        <p style="
            color: #047857;
            margin: 0;
            font-size: 0.75rem;
            font-weight: 500;
            opacity: 0.9;
        ">
            选择2-5个品种进行对比分析
        </p>
    </div>
    """, unsafe_allow_html=True)

    selected_varieties = st.multiselect(
        "选择品种",
        varieties,
        default=current_selection,
        help="💡 提示：选择2-5个品种可获得最佳对比效果"
    )

    return selected_varieties


def render_variety_feedback(selected_count: int) -> None:
    """渲染品种选择反馈信息

    Args:
        selected_count: 已选择的品种数量
    """
    if selected_count == 0:
        return

    if selected_count <= RECOMMENDED_VARIETIES:
        bg_color = "#D1FAE5"
        text_color = "#065F46"
        icon = "✅"
        message = f"已选择 {selected_count} 个品种 - 完美！"
    elif selected_count <= MAX_VARIETIES:
        bg_color = "#FEF3C7"
        text_color = "#92400E"
        icon = "⚠️"
        message = f"已选择 {selected_count} 个品种 - 较多但可接受"
    else:
        bg_color = "#FEE2E2"
        text_color = "#991B1B"
        icon = "🔴"
        message = f"已选择 {selected_count} 个品种 - 建议减少到{MAX_VARIETIES}个以下"

    st.markdown(f"""
    <div style="
        background: {bg_color};
        border-left: 3px solid {text_color};
        padding: 0.5rem;
        border-radius: 6px;
        margin-top: 0.5rem;
    ">
        <div style="font-size: 0.8rem; color: {text_color}; font-weight: 600;">
            {icon} {message}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_water_regime_selector(current_value: int) -> int:
    """渲染水分管理选择器

    Args:
        current_value: 当前选择的水分管理值

    Returns:
        用户选择的水分管理值
    """
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        border: 2px solid #3B82F6;
        padding: 0.75rem;
        margin-bottom: 0.75rem;
        border-radius: 10px;
    ">
        <h4 style="
            color: #1E40AF;
            margin: 0 0 0.35rem 0;
            font-size: 0.95rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        ">
            💧 <span>水分管理</span>
        </h4>
        <p style="
            color: #1E3A8A;
            margin: 0;
            font-size: 0.75rem;
            font-weight: 500;
            opacity: 0.9;
        ">
            选择灌溉模式（影响CH4排放）
        </p>
    </div>
    """, unsafe_allow_html=True)

    water_regime = st.selectbox(
        "灌溉模式",
        options=list(WATER_REGIME_NAMES.keys()),
        format_func=lambda x: f"{x}. {WATER_REGIME_NAMES[x]}",
        index=current_value - 1,
        help="💡 不同灌溉模式对甲烷排放有显著影响"
    )

    # 显示选择模式的说明
    st.info(f"📝 {WATER_REGIME_DESCRIPTIONS[water_regime]}")

    return water_regime


def render_soil_parameter_sliders(
    current_sand: float,
    current_oms: float,
    current_omn: float
) -> Tuple[float, float, float]:
    """渲染土壤参数滑块

    Args:
        current_sand: 当前砂粒含量
        current_oms: 当前慢速分解有机质
        current_omn: 当前快速分解有机质

    Returns:
        (sand_value, oms, omn) 元组
    """
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #FAF5FF 0%, #F3E8FF 100%);
        border: 2px solid #8B5CF6;
        padding: 0.75rem;
        margin-bottom: 0.75rem;
        border-radius: 10px;
    ">
        <h4 style="
            color: #5B21B6;
            margin: 0 0 0.35rem 0;
            font-size: 0.95rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        ">
            🏜️ <span>土壤参数</span>
        </h4>
        <p style="
            color: #6D28D9;
            margin: 0;
            font-size: 0.75rem;
            font-weight: 500;
            opacity: 0.9;
        ">
            配置土壤特性
        </p>
    </div>
    """, unsafe_allow_html=True)

    sand_value = st.slider(
        "砂粒含量 (%)",
        min_value=SAND_CONTENT_MIN,
        max_value=SAND_CONTENT_MAX,
        value=current_sand,
        step=1,
        help="💡 土壤砂粒百分比影响甲烷排放"
    )

    col1, col2 = st.columns(2)

    with col1:
        oms = st.slider(
            "慢速分解有机质 (OMS, kg/ha)",
            min_value=OM_MIN,
            max_value=OM_MAX,
            value=current_oms,
            step=50,
            help="💡 秸秆等有机物输入"
        )

    with col2:
        omn = st.slider(
            "快速分解有机质 (OMN, kg/ha)",
            min_value=OM_MIN,
            max_value=OM_MAX,
            value=current_omn,
            step=50,
            help="💡 绿肥等有机物输入"
        )

    return sand_value, oms, omn


def render_run_button(variety_count: int) -> bool:
    """渲染运行模拟按钮

    Args:
        variety_count: 已选择的品种数量

    Returns:
        是否点击运行按钮
    """
    if variety_count == 0:
        st.warning(ERROR_MESSAGES['no_variety_selected'])
        return False

    return st.button(
        "🚀 运行模拟",
        type="primary",
        use_container_width=True,
        help="开始运行水稻生长和CH4排放模拟"
    )


def render_results_header(results_count: int) -> None:
    """渲染结果展示头部

    Args:
        results_count: 成功的模拟结果数量
    """
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #10B981 0%, #3B82F6 50%, #8B5CF6 100%);
        color: white;
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        text-align: center;
        box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3), 0 4px 10px rgba(59, 130, 246, 0.2);
    ">
        <h2 style="margin: 0; font-size: 1.5rem; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">
            <span>📈</span>模拟结果总览
        </h2>
        <p style="margin: 0.3rem 0 0 0; font-size: 0.8rem; opacity: 0.95;">
            成功完成 {results_count} 个品种的模拟
        </p>
    </div>
    """, unsafe_allow_html=True)


def create_comparison_chart(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    color_col: str = None,
    height: int = 400
) -> go.Figure:
    """创建对比图表

    Args:
        data: 数据框
        x_col: X轴列名
        y_col: Y轴列名
        title: 图表标题
        color_col: 颜色列名（可选）
        height: 图表高度

    Returns:
        Plotly Figure对象
    """
    if color_col:
        fig = px.bar(
            data,
            x=x_col,
            y=y_col,
            color=color_col,
            title=title,
            height=height,
            color_continuous_scale='Viridis'
        )
    else:
        fig = px.bar(
            data,
            x=x_col,
            y=y_col,
            title=title,
            height=height,
            color_discrete_sequence=['#10B981']
        )

    fig.update_layout(
        font=dict(size=12),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    fig.update_xaxes(tickangle=-45)
    fig.update_yaxes(gridcolor='rgba(0,0,0,0.1)')

    return fig


def create_timeseries_chart(
    data: pd.DataFrame,
    x_col: str,
    y_cols: List[str],
    title: str,
    color_col: str = None
) -> go.Figure:
    """创建时间序列图表

    Args:
        data: 数据框
        x_col: X轴列名（通常是日期或天数）
        y_cols: Y轴列名列表
        title: 图表标题
        color_col: 颜色分组列名（可选）

    Returns:
        Plotly Figure对象
    """
    fig = go.Figure()

    colors = ['#10B981', '#3B82F6', '#8B5CF6', '#F59E0B', '#EF4444',
              '#EC4899', '#6366F1', '#14B8A6']

    if color_col and color_col in data.columns:
        # 按品种分组绘制
        for i, (name, group) in enumerate(data.groupby(color_col)):
            for j, y_col in enumerate(y_cols):
                if y_col in group.columns:
                    fig.add_trace(go.Scatter(
                        x=group[x_col],
                        y=group[y_col],
                        mode='lines',
                        name=f'{name} - {y_col}',
                        line=dict(color=colors[i % len(colors)], width=2)
                    ))
    else:
        # 简单绘制所有Y列
        for i, y_col in enumerate(y_cols):
            if y_col in data.columns:
                fig.add_trace(go.Scatter(
                    x=data[x_col],
                    y=data[y_col],
                    mode='lines',
                    name=y_col,
                    line=dict(color=colors[i % len(colors)], width=2)
                ))

    fig.update_layout(
        title=title,
        xaxis_title=x_col,
        yaxis_title='值',
        hovermode='x unified',
        template='plotly_white',
        height=400
    )

    return fig
