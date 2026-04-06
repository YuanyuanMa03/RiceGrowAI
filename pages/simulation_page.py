"""
模拟运行页面

提供水稻生长与CH4排放模拟的主页面。
当前阶段为薄包装层。
"""
import streamlit as st
import os
import time
import pandas as pd
from pathlib import Path

from config import (
    PROJECT_ROOT, DATA_DIR, UPLOADS_DIR, PROGRESS_UPDATE_DELAY,
    PANDAS_ILON_FIRST_ROW,
)


def show_simulation_page(cultivar_df, openai_available=False):
    """显示模拟运行页面

    薄包装层，调用 app.py 中现有的模拟逻辑。
    后续迭代将把模拟循环迁移至此处。

    Args:
        cultivar_df: 品种参数DataFrame
        openai_available: AI功能是否可用
    """
    # 延迟导入避免循环依赖
    from app import (
        show_sidebar_content,
        display_simulation_results,
        run_single_variety_simulation,
        safe_read_csv,
    )
    from models.Ricegrow_py_v1_0 import GetCultivarParams

    try:
        from ai.ui.recommendation_panel import render_recommendation_panel
    except ImportError:
        render_recommendation_panel = None

    base_dir = PROJECT_ROOT

    # 检查必需文件
    required_files = [
        "调参数据.csv", "气象数据.csv", "土壤数据.csv",
        "秸秆数据.csv", "管理数据_多种方案.csv", "施肥数据.csv"
    ]
    missing_files = [f for f in required_files if not (DATA_DIR / f).exists()]

    if missing_files:
        st.error(f"❌ 缺少必需的数据文件: {', '.join(missing_files)}")
        st.stop()

    # 显示侧边栏
    with st.sidebar:
        show_sidebar_content(cultivar_df)

    # 获取用户配置
    selected_varieties = st.session_state.get('selected_varieties', [])
    water_regime = st.session_state.get('water_regime', 1)
    sand_value = st.session_state.get('sand_value', 35)
    oms = st.session_state.get('oms', 1300)
    omn = st.session_state.get('omn', 1600)
    run_simulation = st.session_state.get('run_simulation', False)

    # AI 参数推荐面板
    if openai_available and render_recommendation_panel:
        render_recommendation_panel(cultivar_df=cultivar_df)

    # 运行模拟
    if run_simulation and selected_varieties:
        use_custom = st.session_state.get('use_custom_files', True)
        upload_dir = str(UPLOADS_DIR)
        has_custom = use_custom and Path(upload_dir).exists() and list(Path(upload_dir).iterdir())

        if has_custom:
            custom_count = len([f for f in Path(upload_dir).iterdir() if f.name.endswith('.csv')])
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%);
                border: 2px solid #3B82F6;
                padding: 0.75rem;
                border-radius: 8px;
                margin-bottom: 1rem;
            ">
                <div style="font-size: 0.8rem; color: #1E40AF; font-weight: 600;">
                    ✨ 使用 {custom_count} 个自定义文件进行模拟
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #E0E7FF 0%, #C7D2FE 100%);
                border: 2px solid #6366F1;
                padding: 0.75rem;
                border-radius: 8px;
                margin-bottom: 1rem;
            ">
                <div style="font-size: 0.8rem; color: #3730A3; font-weight: 600;">
                    📁 使用默认数据文件进行模拟
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #F59E0B 0%, #EF4444 100%);
            color: white;
            padding: 1rem;
            border-radius: 12px;
            margin: 1rem 0;
            text-align: center;
            box-shadow: 0 8px 20px rgba(245, 158, 11, 0.3), 0 4px 10px rgba(239, 68, 68, 0.2);
            animation: pulse 2s infinite;
        ">
            <h3 style="margin: 0; font-size: 1.2rem; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                <span>🔄</span>模拟进行中...
            </h3>
            <p style="margin: 0.35rem 0 0 0; font-size: 0.8rem; opacity: 0.95;">
                正在运行Ricegrow模型和CH4排放耦合模型
            </p>
        </div>
        """, unsafe_allow_html=True)

        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

        results = []
        total_varieties = len(selected_varieties)
        status_container = st.container()

        for i, variety in enumerate(selected_varieties):
            progress_percent = i / total_varieties
            progress_bar.progress(progress_percent)
            status_text.text(f"🌱 正在模拟: {variety} ({i+1}/{total_varieties})")

            with status_container:
                st.info(f"🔄 开始模拟品种: **{variety}** ({i+1}/{total_varieties})")

            cultivar_row = cultivar_df[cultivar_df['PZ'] == variety].iloc[PANDAS_ILON_FIRST_ROW]
            cultivar_temp_df = pd.DataFrame([cultivar_row])
            cultivar_temp_path = str(PROJECT_ROOT / f"temp_{variety}_cultivar.csv")

            for col in cultivar_temp_df.columns:
                if pd.api.types.is_numeric_dtype(cultivar_temp_df[col]):
                    cultivar_temp_df[col] = cultivar_temp_df[col].astype(float)

            try:
                cultivar_temp_df.to_csv(cultivar_temp_path, index=False, encoding='gbk', errors='replace')
            except UnicodeEncodeError:
                with status_container:
                    st.warning(f"⚠️ GBK编码警告，尝试清理数据")
                for col in cultivar_temp_df.columns:
                    if cultivar_temp_df[col].dtype == 'object':
                        cultivar_temp_df[col] = cultivar_temp_df[col].astype(str).str.encode(
                            'gbk', errors='replace'
                        ).str.decode('gbk')
                cultivar_temp_df.to_csv(cultivar_temp_path, index=False, encoding='gbk')

            try:
                cultivar_params_tuple = GetCultivarParams(cultivar_temp_path)
                cultivar_params = cultivar_params_tuple[1:]

                use_custom = st.session_state.get('use_custom_files', True)
                result = run_single_variety_simulation(
                    cultivar_params, variety, base_dir, water_regime, sand_value, oms, omn, use_custom
                )
                results.append(result)

                if result:
                    with status_container:
                        st.success(f"✅ **{variety}** 模拟完成 - 产量: **{result['final_yield']:.1f} kg/ha**")

            except Exception as e:
                with status_container:
                    st.error(f"❌ **{variety}** 模拟失败: {e}")
                results.append(None)
            finally:
                if Path(cultivar_temp_path).exists():
                    Path(cultivar_temp_path).unlink()

            time.sleep(PROGRESS_UPDATE_DELAY)

        progress_bar.progress(1.0)
        status_text.text("🎉 模拟完成!")

        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #10B981 0%, #059669 100%);
            color: white;
            padding: 1rem;
            border-radius: 12px;
            margin: 1rem 0;
            text-align: center;
            box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3), 0 4px 10px rgba(5, 150, 105, 0.2);
            animation: fadeInUp 0.8s ease-out;
        ">
            <h3 style="margin: 0; font-size: 1.2rem; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                <span>🎉</span>模拟完成！
            </h3>
            <p style="margin: 0.35rem 0 0 0; font-size: 0.8rem; opacity: 0.95;">
                所有品种模拟成功，正在生成分析报告...
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.session_state['simulation_results_cache'] = results
        display_simulation_results(results)
        st.session_state['run_simulation'] = False

    elif not run_simulation and st.session_state.get('simulation_results_cache'):
        cached_results = st.session_state['simulation_results_cache']
        if any(r is not None for r in cached_results):
            display_simulation_results(cached_results)

    # 页脚
    st.markdown("""
    <div style="
        background: #FFFFFF;
        border: 2px solid #E5E7EB;
        padding: 1.5rem;
        border-radius: 12px;
        margin-top: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    ">
        <h3 style="margin: 0 0 1rem 0; font-size: 1.2rem; font-weight: 700; color: #1E293B;">
            <span>ℹ️</span>系统信息
        </h3>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1rem; max-width: 600px; margin-left: auto; margin-right: auto;">
            <div style="text-align: left; padding: 0.85rem; background: #F8FAFC; border-radius: 8px; border: 1px solid #E5E7EB;">
                <h4 style="color: #10B981; margin: 0 0 0.4rem 0; font-size: 0.95rem; font-weight: 700;">🌾 模型架构</h4>
                <p style="margin: 0; font-size: 0.8rem; color: #475569; line-height: 1.4;">Ricegrow + CH4排放耦合模型</p>
            </div>
            <div style="text-align: left; padding: 0.85rem; background: #F8FAFC; border-radius: 8px; border: 1px solid #E5E7EB;">
                <h4 style="color: #10B981; margin: 0 0 0.4rem 0; font-size: 0.95rem; font-weight: 700;">🎯 核心功能</h4>
                <p style="margin: 0; font-size: 0.8rem; color: #475569; line-height: 1.4;">水稻生长模拟与甲烷排放预测</p>
            </div>
            <div style="text-align: left; padding: 0.85rem; background: #F8FAFC; border-radius: 8px; border: 1px solid #E5E7EB;">
                <h4 style="color: #10B981; margin: 0 0 0.4rem 0; font-size: 0.95rem; font-weight: 700;">📊 数据基础</h4>
                <p style="margin: 0; font-size: 0.8rem; color: #475569; line-height: 1.4;">基于实测气象、土壤和管理数据</p>
            </div>
            <div style="text-align: left; padding: 0.85rem; background: #F8FAFC; border-radius: 8px; border: 1px solid #E5E7EB;">
                <h4 style="color: #10B981; margin: 0 0 0.4rem 0; font-size: 0.95rem; font-weight: 700;">📈 输出结果</h4>
                <p style="margin: 0; font-size: 0.8rem; color: #475569; line-height: 1.4;">产量预测、CH4排放通量、生长过程数据</p>
            </div>
        </div>
        <div style="border-top: 2px solid #E5E7EB; padding-top: 1rem; margin-top: 1rem;">
            <p style="margin: 0; font-size: 0.8rem; color: #64748B; font-weight: 500; line-height: 1.5;">
                🚀 基于现代前端技术构建 | 致力于可持续农业发展 | 精准农业决策支持系统
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
