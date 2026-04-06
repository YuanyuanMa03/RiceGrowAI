"""
AI 参数推荐面板 UI

在模拟页面中渲染 AI 推荐卡片。
"""
import streamlit as st

from ai.client import get_ai_client, OPENAI_AVAILABLE
from ai.features.parameter_recommendation import get_parameter_recommendation


WATER_REGIME_NAMES = {
    1: "淹水灌溉",
    2: "间歇灌溉",
    3: "湿润灌溉",
    4: "控制灌溉",
    5: "干湿交替",
}


def render_recommendation_panel(cultivar_df=None):
    """渲染 AI 参数推荐面板"""
    if not OPENAI_AVAILABLE:
        return

    if not st.session_state.get("ai_api_key"):
        return

    with st.expander("AI 参数推荐", expanded=False):
        selected = st.session_state.get("selected_varieties", [])
        if not selected:
            st.info("请先在侧边栏选择品种，AI 将根据品种特性推荐最优参数。")
            return

        if st.button("获取 AI 推荐", key="btn_ai_recommend", use_container_width=True):
            ai_client = get_ai_client()
            if ai_client is None:
                st.error("AI 客户端不可用，请检查 API Key。")
                return

            current_params = {
                "water_regime": st.session_state.get("water_regime", 1),
                "sand_value": st.session_state.get("sand_value", 35.0),
                "oms": st.session_state.get("oms", 1300.0),
                "omn": st.session_state.get("omn", 1600.0),
            }

            with st.spinner("AI 正在分析品种特性并生成推荐..."):
                rec = get_parameter_recommendation(
                    ai_client=ai_client,
                    selected_varieties=selected,
                    current_params=current_params,
                    cultivar_df=cultivar_df,
                )

            if rec is None:
                st.error("获取推荐失败，请检查 API Key 或稍后重试。")
                return

            st.session_state["ai_recommendation"] = rec

        # 显示推荐结果
        rec = st.session_state.get("ai_recommendation")
        if rec is not None:
            _display_recommendation(rec)


def _display_recommendation(rec):
    """展示推荐卡片"""
    if rec.summary:
        st.markdown(f"**{rec.summary}**")
        st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
            padding: 1rem;
            border-radius: 12px;
            border-left: 4px solid #F59E0B;
            margin-bottom: 0.5rem;
        ">
            <div style="font-size:0.75rem; color:#92400E; font-weight:600;">水管理模式</div>
            <div style="font-size:1.1rem; font-weight:700; color:#78350F;">模式 {rec.water_regime} - {WATER_REGIME_NAMES.get(rec.water_regime, '')}</div>
            <div style="font-size:0.8rem; color:#92400E; margin-top:0.3rem;">{rec.water_regime_reason}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
            padding: 1rem;
            border-radius: 12px;
            border-left: 4px solid #F59E0B;
            margin-bottom: 0.5rem;
        ">
            <div style="font-size:0.75rem; color:#92400E; font-weight:600;">土壤砂粒含量</div>
            <div style="font-size:1.1rem; font-weight:700; color:#78350F;">{rec.sand_value:.1f}%</div>
            <div style="font-size:0.8rem; color:#92400E; margin-top:0.3rem;">{rec.sand_reason}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
            padding: 1rem;
            border-radius: 12px;
            border-left: 4px solid #F59E0B;
            margin-bottom: 0.5rem;
        ">
            <div style="font-size:0.75rem; color:#92400E; font-weight:600;">慢速有机质 (OMS)</div>
            <div style="font-size:1.1rem; font-weight:700; color:#78350F;">{rec.oms:.0f} kg/ha</div>
            <div style="font-size:0.8rem; color:#92400E; margin-top:0.3rem;">{rec.oms_reason}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
            padding: 1rem;
            border-radius: 12px;
            border-left: 4px solid #F59E0B;
            margin-bottom: 0.5rem;
        ">
            <div style="font-size:0.75rem; color:#92400E; font-weight:600;">快速有机质 (OMN)</div>
            <div style="font-size:1.1rem; font-weight:700; color:#78350F;">{rec.omn:.0f} kg/ha</div>
            <div style="font-size:0.8rem; color:#92400E; margin-top:0.3rem;">{rec.omn_reason}</div>
        </div>
        """, unsafe_allow_html=True)

    # 一键应用按钮
    if st.button("应用推荐参数", key="btn_apply_recommend", use_container_width=True, type="primary"):
        st.session_state["water_regime"] = rec.water_regime
        st.session_state["water_mode_index"] = rec.water_regime - 1
        st.session_state["sand_value"] = rec.sand_value
        st.session_state["oms"] = rec.oms
        st.session_state["omn"] = rec.omn
        st.success("推荐参数已应用！参数将在下次运行模拟时生效。")
