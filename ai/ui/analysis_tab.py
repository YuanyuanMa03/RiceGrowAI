"""
AI 结果分析标签页 UI

在模拟结果中渲染 AI 分析报告标签页。
"""
import streamlit as st

from ai.client import get_ai_client, OPENAI_AVAILABLE
from ai.features.results_analysis import generate_results_analysis


def render_ai_analysis_tab(results, simulation_params):
    """渲染 AI 分析标签页

    Args:
        results: 模拟结果列表
        simulation_params: 模拟参数字典
    """
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        padding: 1rem;
        border-radius: 12px;
        border-left: 4px solid #3B82F6;
        margin-bottom: 1rem;
    ">
        <div style="font-weight:600; color:#1E40AF;">AI 智能分析</div>
        <div style="font-size:0.8rem; color:#1E40AF; opacity:0.8;">
            基于 AI 分析模拟结果，生成产量与 CH4 排放的深度分析报告
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not OPENAI_AVAILABLE:
        st.warning("AI 功能需要安装 openai 包。请运行：`pip install openai`")
        return

    if not st.session_state.get("ai_api_key"):
        st.info("请在侧边栏「AI 助手设置」中输入 API Key 以启用 AI 分析。")
        return

    if not results:
        st.info("暂无模拟结果。请先运行模拟。")
        return

    # 生成/重新生成按钮
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("生成 AI 分析报告", key="btn_gen_analysis", use_container_width=True, type="primary"):
            _generate_analysis(results, simulation_params)
    with col2:
        if st.session_state.get("ai_analysis_report"):
            if st.button("重新生成", key="btn_regen_analysis", use_container_width=True):
                _generate_analysis(results, simulation_params)

    # 显示分析报告
    report = st.session_state.get("ai_analysis_report")
    if report:
        st.markdown("---")
        st.markdown(report)


def _generate_analysis(results, simulation_params):
    """执行分析生成"""
    ai_client = get_ai_client()
    if ai_client is None:
        st.error("AI 客户端不可用，请检查 API Key。")
        return

    with st.spinner("AI 正在分析模拟结果，生成深度报告..."):
        report = generate_results_analysis(
            ai_client=ai_client,
            results=results,
            simulation_params=simulation_params,
        )

    if report:
        if report.startswith("抱歉") or report.startswith("API"):
            st.error(report)
        else:
            st.session_state["ai_analysis_report"] = report
            st.success("分析报告生成完成！")
    else:
        st.error("生成分析报告失败，请稍后重试。")
