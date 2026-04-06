"""
参数校准页面

支持多种优化算法：
- 随机搜索（简单稳定）
- 差分进化（高效）
- MCMC 贝叶斯推断（带不确定性量化）
- PSO 粒子群优化（全局搜索）
- PSO-MCMC 混合优化（两阶段优化）
- 多目标优化（多变量同时优化）
- Sobol 敏感性分析
"""
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import time
import json
import traceback
import plotly.graph_objects as go
import plotly.express as px

from simple_optimizer import (
    SimpleParameterOptimizer,
    load_observed_data_simple,
    load_weather_data_simple,
    run_simple_optimization
)
from config import UPLOADS_DIR, DATA_DIR, PARAMETER_SPACE_CULTIVAR, PARAMETER_SPACE_CH4

# 导入新的优化模块
# 尝试导入 MCMC 模块
try:
    from calibration.pymc_calibrator import MCMCCalibrator, PYMC_AVAILABLE
    from calibration.priors import PARAMETER_PRIORS, CH4_PARAMETER_PRIORS
except ImportError:
    PYMC_AVAILABLE = False
    PARAMETER_PRIORS = {}
    CH4_PARAMETER_PRIORS = {}

# 尝试导入 PSO 模块
try:
    from calibration.pso_optimizer import PSOOptimizer, AdaptivePSOOptimizer, create_pso_optimizer
    PSO_AVAILABLE = True
except ImportError:
    PSO_AVAILABLE = False

# 尝试导入混合优化模块
try:
    from calibration.hybrid_optimizer import PSOMCMCHybridOptimizer, create_hybrid_optimizer
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False

# 尝试导入多目标优化模块
try:
    from calibration.multi_objective import (
        MultiObjectiveOptimizer,
        EpsilonConstraintOptimizer,
        create_multi_objective_optimizer
    )
    MULTI_OBJECTIVE_AVAILABLE = True
except ImportError:
    MULTI_OBJECTIVE_AVAILABLE = False

# 尝试导入敏感性分析模块
try:
    from calibration.sensitivity import (
        get_default_parameter_bounds,
        create_sobol_problem,
        generate_sobol_samples,
        run_sobol_analysis,
        classify_sensitivity,
        SALIB_AVAILABLE
    )
except ImportError:
    SALIB_AVAILABLE = False

# 尝试导入可视化和指标模块
try:
    from calibration.metrics import (
        calculate_all_metrics,
        get_model_rating,
        align_and_calculate_metrics
    )
    from calibration.visualization import (
        create_timeseries_comparison,
        create_scatter_plot,
        create_residual_plot,
        create_metrics_cards,
        create_evaluation_section
    )
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

# 导入科研级图表模块
try:
    from calibration.publication_charts import (
        create_publication_timeseries,
        create_publication_scatter,
        create_publication_residual,
        create_metrics_summary,
        display_publication_figure
    )
    PUBLICATION_CHARTS_AVAILABLE = True
except ImportError:
    PUBLICATION_CHARTS_AVAILABLE = False


def run_simulation_with_params(observed_data, calibrated_params, fixed_params):
    """使用校准后的参数运行模型

    Args:
        observed_data: 观测数据
        calibrated_params: 校准后的参数
        fixed_params: 固定参数

    Returns:
        模拟结果 DataFrame
    """
    weather_data = load_weather_data_simple()

    # 合并固定参数
    full_params = fixed_params.copy()
    full_params.update(calibrated_params)

    # 创建临时优化器用于运行模型（根据 use_custom_files 选择文件）
    use_custom = st.session_state.get('calibration_use_custom_files', False)
    temp_optimizer = SimpleParameterOptimizer(
        observed_data=observed_data,
        weather_data=weather_data,
        parameter_bounds={},  # 不需要边界
        fixed_params=fixed_params,
        algorithm='random',
        n_iterations=1,
        use_custom_files=use_custom
    )

    return temp_optimizer._run_model(full_params)


def show_calibration_results(observed_data, calibrated_params, fixed_params,
                               algorithm_name='优化'):
    """展示校准结果对比

    Args:
        observed_data: 观测数据
        calibrated_params: 校准后的参数
        fixed_params: 固定参数
        algorithm_name: 算法名称
    """
    if not VISUALIZATION_AVAILABLE:
        st.warning("⚠️ 可视化模块不可用，跳过结果展示")
        return

    st.markdown("---")
    st.markdown("### 📊 校准结果评估")

    # 1. 运行校准后模拟
    with st.spinner("运行校准后模拟..."):
        simulated_after = run_simulation_with_params(
            observed_data, calibrated_params, fixed_params
        )

    if simulated_after is None or len(simulated_after) == 0:
        st.error("❌ 校准后模拟失败")
        return

    # 调试：显示数据信息
    with st.expander("🔍 数据调试信息"):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**观测数据**")
            st.dataframe(observed_data.head())
        with col2:
            st.write("**模拟数据**")
            st.dataframe(simulated_after.head())

    # 2. 确定要评估的变量
    variables = [v for v in ['Biomass', 'CH4']
                 if v in observed_data.columns and v in simulated_after.columns]

    if not variables:
        st.warning("⚠️ 观测数据和模拟数据没有共同变量")
        return

    # 3. 数据对齐：使用重采样而不是 DAT merge
    # 因为模拟数据的 DAT 可能从 1 开始，而观测数据可能从 0 开始或步长不同
    def align_series(obs_series, sim_series):
        """对齐观测和模拟序列（按长度截取）"""
        min_len = min(len(obs_series), len(sim_series))
        return obs_series.iloc[:min_len].values, sim_series.iloc[:min_len].values

    # 4. 显示指标卡片
    st.markdown("#### 📈 统计指标")

    for var in variables:
        # 使用对齐后的数据计算指标
        obs_vals, sim_vals = align_series(observed_data[var], simulated_after[var])

        # 直接使用 metrics 模块计算
        from calibration.metrics import calculate_all_metrics, get_model_rating

        var_metrics = calculate_all_metrics(obs_vals, sim_vals)
        rating = get_model_rating(
            var_metrics.get('R²', float('nan')),
            var_metrics.get('NSE', float('nan'))
        )

        # 显示指标卡片
        st.markdown(f"**{var}**")
        from calibration.visualization import create_metrics_cards
        st.markdown(create_metrics_cards(var_metrics, rating), unsafe_allow_html=True)

    # 5. 显示时间序列对比图（科研级别）
    st.markdown("#### 📉 时间序列对比")

    # 使用科研级图表（优先）或原始图表
    if PUBLICATION_CHARTS_AVAILABLE:
        fig = create_publication_timeseries(
            observed_data,
            simulated_after,
            variables=variables,
            simulated_before=None,
            style='nature'  # Nature 期刊风格
        )
        display_publication_figure(fig, use_container_width=True)
    else:
        from calibration.visualization import create_timeseries_comparison
        fig = create_timeseries_comparison(
            observed_data,
            simulated_after,
            variables=variables,
            simulated_before=None
        )
        st.plotly_chart(fig, use_container_width=True)

    # 6. 显示1:1散点图（科研级别）
    st.markdown("#### 🔍 模拟值 vs 观测值")

    for var in variables:
        # 直接使用对齐的序列，不依赖 DAT merge
        obs_vals, sim_vals = align_series(observed_data[var], simulated_after[var])

        # 移除 NaN
        mask = ~(np.isnan(obs_vals) | np.isnan(sim_vals))
        obs_clean = obs_vals[mask]
        sim_clean = sim_vals[mask]

        if len(obs_clean) > 0:
            # 使用科研级图表（优先）或原始图表
            if PUBLICATION_CHARTS_AVAILABLE:
                fig = create_publication_scatter(
                    obs_clean,
                    sim_clean,
                    var_name=var,
                    style='nature'
                )
                display_publication_figure(fig, use_container_width=True)
            else:
                from calibration.visualization import create_scatter_plot
                fig = create_scatter_plot(
                    obs_clean,
                    sim_clean,
                    var
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"⚠️ {var}: 没有有效数据用于散点图")

    # 7. 显示残差图（科研级别）
    st.markdown("#### 📊 残差分布")

    for var in variables:
        # 直接使用对齐的序列
        obs_vals, sim_vals = align_series(observed_data[var], simulated_after[var])

        # 移除 NaN
        mask = ~(np.isnan(obs_vals) | np.isnan(sim_vals))
        obs_clean = obs_vals[mask]
        sim_clean = sim_vals[mask]

        if len(obs_clean) > 0:
            # 使用科研级图表（优先）或原始图表
            if PUBLICATION_CHARTS_AVAILABLE:
                fig = create_publication_residual(
                    obs_clean,
                    sim_clean,
                    var_name=var,
                    style='nature'
                )
                display_publication_figure(fig, use_container_width=True)
            else:
                from calibration.visualization import create_residual_plot
                fig = create_residual_plot(
                    obs_clean,
                    sim_clean,
                    var
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"⚠️ {var}: 没有有效数据用于残差图")


def run_mcmc_optimization(observed_data, parameter_bounds, params_to_calibrate,
                          fixed_params, n_tunes, n_draws, n_chains, cultivar_type):
    """运行 MCMC 贝叶斯优化"""
    if not PYMC_AVAILABLE:
        st.error("❌ PyMC 未安装，无法使用 MCMC 优化。请运行: pip install pymc arviz")
        return

    from calibration.priors import get_default_priors

    # 创建进度显示
    progress_bar = st.progress(0)
    status_text = st.empty()
    result_container = st.container()

    try:
        status_text.text("🔨 构建 PyMC 模型...")

        # 准备先验分布
        all_priors = get_default_priors(cultivar_type)
        selected_priors = {k: all_priors[k] for k in params_to_calibrate if k in all_priors}

        # 对于 CH4 参数，添加其先验
        for param in params_to_calibrate:
            if param in ['Q10', 'Eh0', 'EhBase', 'WaterC']:
                from calibration.priors import CH4_PARAMETER_PRIORS
                if param in CH4_PARAMETER_PRIORS:
                    selected_priors[param] = CH4_PARAMETER_PRIORS[param]

        # 创建模型运行器包装器
        def model_runner(params):
            from simple_optimizer import SimpleParameterOptimizer
            from simple_optimizer import load_weather_data_simple

            weather_data = load_weather_data_simple()

            # 合并固定参数
            full_params = fixed_params.copy()
            full_params.update(params)

            # 创建临时优化器用于运行模型（自动使用上传的文件）
            use_custom = st.session_state.get('calibration_use_custom_files', False)
            temp_optimizer = SimpleParameterOptimizer(
                observed_data=observed_data,
                weather_data=weather_data,
                parameter_bounds=parameter_bounds,
                fixed_params=fixed_params,
                algorithm='random',
                n_iterations=1,
                use_custom_files=use_custom
            )

            return temp_optimizer._run_model(full_params)

        # 创建 MCMC 调参器
        calibrator = MCMCCalibrator(
            observed_data=observed_data,
            model_runner=model_runner,
            param_priors=selected_priors,
            target_columns=['Biomass', 'CH4'],
            fixed_params=fixed_params
        )

        progress_bar.progress(0.1)
        status_text.text("🏗️ 构建贝叶斯模型...")

        # 构建模型
        calibrator.build_model(params_to_calibrate)

        progress_bar.progress(0.2)
        status_text.text("🔥 运行 MCMC 采样...")

        # 运行采样
        trace = calibrator.sample(
            n_tunes=n_tunes,
            n_draws=n_draws,
            n_chains=n_chains,
            target_accept=0.9,
            cores=min(n_chains, 4)
        )

        progress_bar.progress(0.8)
        status_text.text("📊 分析后验分布...")

        # 获取结果
        summary = calibrator.get_posterior_summary()
        ranges = calibrator.get_parameter_ranges()
        converged, diagnostics = calibrator.check_convergence()

        progress_bar.progress(1.0)
        status_text.text("✅ MCMC 采样完成！")

        # 显示结果
        with result_container:
            st.markdown("### 🏆 MCMC 贝叶斯推断结果")

            # 收敛性检查
            if converged:
                st.success("✅ 模型已收敛 (R-hat < 1.05, ESS > 400)")
            else:
                st.warning("⚠️ 模型可能未完全收敛，建议增加采样数")

            # 参数后验统计
            st.markdown("#### 📋 参数后验分布")

            for param in params_to_calibrate:
                if param in ranges:
                    with st.expander(f"**{param}** - {selected_priors.get(param, {}).get('description', param)}"):
                        stats = ranges[param]
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("后验均值", f"{stats['mean']:.4f}")
                        col2.metric("标准差", f"{stats['sd']:.4f}")
                        col3.metric("95% HDI 下限", f"{stats['hdi_lower']:.4f}")
                        col4.metric("95% HDI 上限", f"{stats['hdi_upper']:.4f}")

                        st.metric("R-hat", f"{stats['r_hat']:.4f}",
                                 help="R-hat < 1.05 表示收敛")
                        st.metric("有效样本量", f"{int(stats['ess_bulk'])}",
                                 help="ESS > 400 表示样本充足")

            # 完整摘要表
            st.markdown("#### 📊 完整统计摘要")
            st.dataframe(summary, use_container_width=True)

            # 下载结果
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_data = {
                'method': 'MCMC',
                'converged': converged,
                'parameter_ranges': ranges,
                'diagnostics': diagnostics,
                'settings': {
                    'n_tunes': n_tunes,
                    'n_draws': n_draws,
                    'n_chains': n_chains,
                    'cultivar_type': cultivar_type,
                },
                'timestamp': datetime.now().isoformat()
            }

            st.download_button(
                "📥 下载 MCMC 结果 (JSON)",
                data=json.dumps(result_data, ensure_ascii=False, indent=2, default=str),
                file_name=f"mcmc_result_{timestamp}.json",
                mime="application/json",
                use_container_width=True
            )

            # 显示校准结果评估（R²、图表等）
            # 使用后验均值作为校准参数
            calibrated_params = {k: v['mean'] for k, v in ranges.items()}
            show_calibration_results(observed_data, calibrated_params, fixed_params, 'MCMC')

    except Exception as e:
        st.error(f"❌ MCMC 优化失败: {type(e).__name__}: {e}")
        st.code(traceback.format_exc())


def run_traditional_optimization(observed_data, parameter_bounds, fixed_params,
                                 algorithm, n_iterations):
    """运行传统优化算法（随机搜索、差分进化）"""
    # 创建进度显示
    progress_bar = st.progress(0)
    status_text = st.empty()
    result_container = st.container()

    try:
        # 加载气象数据
        weather_data = load_weather_data_simple()

        # 创建优化器（根据 use_custom_files 选择文件）
        use_custom = st.session_state.get('calibration_use_custom_files', False)
        optimizer = SimpleParameterOptimizer(
            observed_data=observed_data,
            weather_data=weather_data,
            parameter_bounds=parameter_bounds,
            fixed_params=fixed_params,
            algorithm=algorithm,
            n_iterations=n_iterations,
            use_custom_files=use_custom
        )

        # 自定义进度回调
        original_history = []
        for i in range(n_iterations):
            # 运行一次迭代

            # 随机采样
            params = {}
            for param_name, (min_val, max_val) in parameter_bounds.items():
                params[param_name] = np.random.uniform(min_val, max_val)

            # 运行模型
            simulated = optimizer._run_model(params)
            error = optimizer._calculate_error(simulated)

            # 记录
            original_history.append({
                'iteration': i,
                'params': params,
                'error': error
            })

            # 更新最佳
            if error < optimizer.best_error:
                optimizer.best_error = error
                optimizer.best_params = params.copy()

            # 更新进度
            progress = (i + 1) / n_iterations
            progress_bar.progress(progress)
            status_text.text(
                f"迭代 {i+1}/{n_iterations} | "
                f"当前误差: {error:.4f} | "
                f"最佳误差: {optimizer.best_error:.4f}"
            )

            # 每5次更新一次结果显示
            if (i + 1) % 5 == 0:
                with result_container:
                    st.markdown("#### 📊 实时结果")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("最佳误差", f"{optimizer.best_error:.4f}")
                    with col2:
                        st.metric("当前误差", f"{error:.4f}")

        # 最终结果
        progress_bar.progress(1.0)
        status_text.text("✅ 优化完成！")

        with result_container:
            st.markdown("### 🏆 最终结果")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("最佳误差", f"{optimizer.best_error:.4f}")
            with col2:
                st.metric("迭代次数", n_iterations)
            with col3:
                successful = sum(1 for h in original_history if h['error'] < 1e6)
                st.metric("成功率", f"{successful/n_iterations*100:.1f}%")

            # 最佳参数
            st.markdown("#### 📋 最佳参数")
            if optimizer.best_params:
                params_df = pd.DataFrame([
                    {'参数': k, '优化值': f"{v:.4f}"}
                    for k, v in optimizer.best_params.items()
                ])
                st.dataframe(params_df, use_container_width=True)

            # 下载结果
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_data = {
                'best_params': {k: float(v) for k, v in optimizer.best_params.items()},
                'best_error': float(optimizer.best_error),
                'algorithm': algorithm,
                'n_iterations': n_iterations,
                'timestamp': datetime.now().isoformat()
            }

            st.download_button(
                "📥 下载结果 (JSON)",
                data=json.dumps(result_data, ensure_ascii=False, indent=2),
                file_name=f"optimization_{timestamp}.json",
                mime="application/json",
                use_container_width=True
            )

            # 显示校准结果评估（R²、图表等）
            calibrated_params = optimizer.best_params
            show_calibration_results(observed_data, calibrated_params, fixed_params, algorithm)

    except Exception as e:
        st.error(f"❌ 优化失败: {type(e).__name__}: {e}")
        st.code(traceback.format_exc())


def show_simple_calibration_page():
    """显示参数校准页面"""

    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #10B981 0%, #3B82F6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: center;
        box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3);
    ">
        <h2 style="margin: 0; font-size: 1.5rem; font-weight: 700;">
            🎯 水稻模型参数校准
        </h2>
        <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; opacity: 0.95;">
            支持随机搜索、差分进化、MCMC、PSO、混合优化、多目标优化
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ========== 模式选择 ==========
    st.markdown("### 🔧 选择优化模式")

    # 初始化 session state
    if 'calibration_mode' not in st.session_state:
        st.session_state.calibration_mode = 'basic'

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button(
            "🎲 基础模式",
            type="primary" if st.session_state.calibration_mode == 'basic' else "secondary",
            use_container_width=True
        ):
            st.session_state.calibration_mode = 'basic'
            st.rerun()

    with col2:
        if st.button(
            "⚡ 高级模式",
            type="primary" if st.session_state.calibration_mode == 'advanced' else "secondary",
            use_container_width=True,
            disabled=not PSO_AVAILABLE
        ):
            st.session_state.calibration_mode = 'advanced'
            st.rerun()

    with col3:
        if st.button(
            "🎯 多目标",
            type="primary" if st.session_state.calibration_mode == 'multi' else "secondary",
            use_container_width=True,
            disabled=not MULTI_OBJECTIVE_AVAILABLE
        ):
            st.session_state.calibration_mode = 'multi'
            st.rerun()

    with col4:
        if st.button(
            "📊 敏感性",
            type="primary" if st.session_state.calibration_mode == 'sensitivity' else "secondary",
            use_container_width=True,
            disabled=not SALIB_AVAILABLE
        ):
            st.session_state.calibration_mode = 'sensitivity'
            st.rerun()

    st.markdown("---")

    # ========== 根据模式显示不同内容 ==========
    if st.session_state.calibration_mode == 'basic':
        _show_basic_calibration_page()
    elif st.session_state.calibration_mode == 'advanced':
        _show_advanced_calibration_page()
    elif st.session_state.calibration_mode == 'multi':
        _show_multi_objective_page()
    elif st.session_state.calibration_mode == 'sensitivity':
        _show_sensitivity_analysis_page()


def _show_data_file_management():
    """显示数据文件管理区域（通用组件）"""
    # 初始化 session state
    if 'calibration_use_custom_files' not in st.session_state:
        st.session_state['calibration_use_custom_files'] = False

    st.markdown("### 📁 数据文件管理")

    # 文件上传区域
    with st.expander("📂 数据文件管理（可选）", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**上传自定义文件**")
            uploaded_field = st.file_uploader(
                "🌾 调参数据.csv",
                type=['csv'],
                help="替换默认调参数据",
                key="cal_field_upload"
            )

            uploaded_weather = st.file_uploader(
                "🌤️ 气象数据.csv",
                type=['csv'],
                help="替换默认气象数据",
                key="cal_weather_upload"
            )

            uploaded_soil = st.file_uploader(
                "🏜️ 土壤数据.csv",
                type=['csv'],
                help="替换默认土壤数据",
                key="cal_soil_upload"
            )

        with col2:
            uploaded_residue = st.file_uploader(
                "🌾 秸秆数据.csv",
                type=['csv'],
                help="替换默认秸秆数据",
                key="cal_residue_upload"
            )

            uploaded_management = st.file_uploader(
                "📋 管理数据.csv",
                type=['csv'],
                help="替换默认管理数据",
                key="cal_management_upload"
            )

            uploaded_fertilizer = st.file_uploader(
                "🧪 施肥数据.csv",
                type=['csv'],
                help="替换默认施肥数据",
                key="cal_fertilizer_upload"
            )

        # 处理上传的文件
        uploaded_files = {
            '调参数据.csv': uploaded_field,
            '气象数据.csv': uploaded_weather,
            '土壤数据.csv': uploaded_soil,
            '秸秆数据.csv': uploaded_residue,
            '管理数据_多种方案.csv': uploaded_management,
            '施肥数据.csv': uploaded_fertilizer,
        }

        saved_count = 0
        for filename, uploaded_file in uploaded_files.items():
            if uploaded_file is not None:
                file_path = UPLOADS_DIR / filename
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                    df.to_csv(file_path, index=False, encoding='gbk')
                    saved_count += 1
                except Exception:
                    try:
                        df = pd.read_csv(uploaded_file, encoding='gbk')
                        df.to_csv(file_path, index=False, encoding='gbk')
                        saved_count += 1
                    except Exception:
                        pass

        if saved_count > 0:
            st.success(f"✅ 已保存 {saved_count} 个文件")
            if hasattr(st, 'cache_data'):
                st.cache_data.clear()

    # 是否使用自定义文件开关
    use_custom = st.checkbox(
        "✨ 使用上传的自定义文件进行校准",
        value=False,
        help="启用后将使用上传的自定义文件，否则使用系统默认文件"
    )
    st.session_state['calibration_use_custom_files'] = use_custom

    # 显示当前使用的文件状态
    st.markdown("**当前数据文件状态：**")
    required_files = [
        ("调参数据.csv", "🌾 调参数据", "播种期、生育期"),
        ("气象数据.csv", "🌤️ 气象数据", "Tmax、Tmin、辐射"),
        ("土壤数据.csv", "🏜️ 土壤数据", "pH、有机质"),
        ("秸秆数据.csv", "🌾 秸秆数据", "残茬输入"),
        ("管理数据_多种方案.csv", "📋 管理数据", "种植管理"),
        ("施肥数据.csv", "🧪 施肥数据", "肥料施用")
    ]

    for file, name, desc in required_files:
        uploaded_exists = (UPLOADS_DIR / file).exists()
        default_exists = (DATA_DIR / file).exists()

        if use_custom and uploaded_exists:
            status = "✅ 自定义"
        elif default_exists:
            status = "📦 默认"
        else:
            status = "❌ 缺失"

        st.markdown(f"{status} **{name}** - {desc}")

    st.markdown("---")

    return use_custom


def _show_basic_calibration_page():
    """基础校准页面 - 按照模拟控制台模式设计"""
    st.info("🎲 **基础模式**: 随机搜索、差分进化、MCMC 贝叶斯推断")

    # 使用通用的数据文件管理组件
    use_custom = _show_data_file_management()

    # ========== 步骤1: 上传观测数据 ==========
    st.markdown("### 📊 步骤1: 上传观测数据")

    uploaded_file = st.file_uploader(
        "选择观测数据文件 (ObservedData.csv) *",
        type=['csv'],
        help="必填。必须包含 DAT 列，可选 Biomass、CH4 列"
    )

    if uploaded_file:
        # 保存文件
        upload_path = UPLOADS_DIR / uploaded_file.name
        with open(upload_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())

        try:
            # 加载数据
            observed_data = load_observed_data_simple(upload_path)

            st.success(f"✅ 成功加载 {len(observed_data)} 条观测数据")

            # 显示数据预览
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("观测点数", len(observed_data))
            with col2:
                days = observed_data['DAT'].max() - observed_data['DAT'].min()
                st.metric("观测天数", f"{days} 天")
            with col3:
                targets = [c for c in ['Biomass', 'CH4'] if c in observed_data.columns]
                st.metric("目标列", ", ".join(targets) if targets else "无")

            st.dataframe(observed_data, use_container_width=True)

            # 显示数据文件信息
            # 根据是否使用自定义文件选择路径
            if use_custom and (UPLOADS_DIR / '调参数据.csv').exists():
                field_path = UPLOADS_DIR / '调参数据.csv'
            else:
                field_path = DATA_DIR / '调参数据.csv'

            if field_path.exists():
                try:
                    field_df = pd.read_csv(field_path, encoding='gbk')
                    field_info = field_df.iloc[0]

                    st.markdown("#### 📋 当前使用的数据信息")
                    info_col1, info_col2, info_col3, info_col4 = st.columns(4)
                    with info_col1:
                        st.metric("播种期", field_info.get('SowingDate', '-'))
                    with info_col2:
                        st.metric("移栽期", field_info.get('TransplantDate', '-'))
                    with info_col3:
                        st.metric("生育期天数", f"{int(field_info.get('maturity', 0))} 天")
                    with info_col4:
                        st.metric("纬度", f"{field_info.get('Latitude', 0)}°N")
                except Exception as e:
                    st.warning(f"⚠️ 无法读取调参数据信息: {e}")

            # 步骤2: 配置参数
            st.markdown("### ⚙️ 步骤2: 配置优化参数")

            col1, col2 = st.columns(2)

            with col1:
                # 算法选择
                algorithm_options = ['random', 'differential_evolution']
                if PYMC_AVAILABLE:
                    algorithm_options.append('mcmc')

                algorithm = st.selectbox(
                    "优化算法",
                    options=algorithm_options,
                    format_func=lambda x: {
                        'random': '🎲 随机搜索（简单稳定）',
                        'differential_evolution': '🧬 差分进化（高效）',
                        'mcmc': '🔮 MCMC 贝叶斯（带不确定性）'
                    }[x],
                    help="MCMC 可提供参数可信区间，但耗时较长"
                )

                # 根据算法显示不同选项
                if algorithm == 'mcmc':
                    st.info("ℹ️ MCMC 贝叶斯推断提供参数后验分布和不确定性量化")

                    n_tunes = st.slider(
                        "Burn-in 样本数",
                        min_value=500,
                        max_value=3000,
                        value=1000,
                        step=100,
                        help="调谐阶段样本数"
                    )

                    n_draws = st.slider(
                        "MCMC 采样数",
                        min_value=500,
                        max_value=5000,
                        value=2000,
                        step=500,
                        help="采样数越多，结果越稳定"
                    )

                    n_chains = st.slider(
                        "MCMC 链数",
                        min_value=1,
                        max_value=8,
                        value=4,
                        help="多链并行可检查收敛性"
                    )

                    n_iterations = n_draws  # 兼容后续代码

                else:
                    n_iterations = st.slider(
                        "迭代次数",
                        min_value=10,
                        max_value=200,
                        value=50,
                        step=10,
                        help="迭代次数越多，结果越精确，但耗时越长"
                    )

            with col2:
                sand_value = st.slider(
                    "土壤砂粒含量 (%)",
                    min_value=0,
                    max_value=100,
                    value=35
                )

                ip_value = st.selectbox(
                    "水管理模式",
                    options=[1, 2, 3, 4, 5],
                    format_func=lambda x: ['淹水', '间歇', '湿润', '控制', '干湿交替'][x-1]
                )

                if algorithm == 'mcmc':
                    st.markdown("**品种类型**（软约束）")
                    cultivar_type = st.selectbox(
                        "选择品种类型",
                        options=['hybrid', 'japonica', 'indica'],
                        format_func=lambda x: {
                            'hybrid': '杂交稻（默认）',
                            'japonica': '粳稻（北方）',
                            'indica': '籼稻（南方）'
                        }[x]
                    )

            # 参数选择
            st.markdown("#### 选择要优化的参数")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**品种参数**")
                optimize_ps = st.checkbox("感光性 (PS)", value=True)
                optimize_ts = st.checkbox("感温性 (TS)", value=True)
                optimize_to = st.checkbox("最适温度 (TO)", value=True)
                optimize_ie = st.checkbox("基本早熟性 (IE)")
                optimize_phi = st.checkbox("收获指数 (PHI)")

            with col2:
                st.markdown("**CH4模型参数**")
                optimize_q10 = st.checkbox("Q10系数", value=True)
                optimize_waterc = st.checkbox("水分含量 (WaterC)", value=True)
                optimize_eh0 = st.checkbox("初始氧化还原电位 (Eh0)")

            # 步骤3: 开始优化
            st.markdown("### 🚀 步骤3: 开始优化")

            if st.button("开始优化", type="primary", use_container_width=True):
                # 构建参数边界（使用 config.py 中定义的正确范围）
                parameter_bounds = {}
                params_to_calibrate = []

                if optimize_ps:
                    parameter_bounds['PS'] = PARAMETER_SPACE_CULTIVAR['PS']
                    params_to_calibrate.append('PS')
                if optimize_ts:
                    parameter_bounds['TS'] = PARAMETER_SPACE_CULTIVAR['TS']
                    params_to_calibrate.append('TS')
                if optimize_to:
                    parameter_bounds['TO'] = PARAMETER_SPACE_CULTIVAR['TO']
                    params_to_calibrate.append('TO')
                if optimize_ie:
                    parameter_bounds['IE'] = PARAMETER_SPACE_CULTIVAR['IE']
                    params_to_calibrate.append('IE')
                if optimize_phi:
                    parameter_bounds['PHI'] = PARAMETER_SPACE_CULTIVAR['PHI']  # ✅ 使用正确范围 (0.427, 0.480)
                    params_to_calibrate.append('PHI')
                if optimize_q10:
                    parameter_bounds['Q10'] = PARAMETER_SPACE_CH4['Q10']
                    params_to_calibrate.append('Q10')
                if optimize_waterc:
                    parameter_bounds['WaterC'] = PARAMETER_SPACE_CH4['WaterC']
                    params_to_calibrate.append('WaterC')
                if optimize_eh0:
                    parameter_bounds['Eh0'] = PARAMETER_SPACE_CH4['Eh0']
                    params_to_calibrate.append('Eh0')

                if not parameter_bounds:
                    st.error("❌ 请至少选择一个参数")
                    return

                # 固定参数
                fixed_params = {
                    'Sand': float(sand_value),
                    'IP': ip_value,
                    'OMS': 1300.0,
                    'OMN': 1600.0,
                }

                # 根据算法选择执行不同的优化流程
                if algorithm == 'mcmc':
                    # MCMC 贝叶斯推断
                    run_mcmc_optimization(
                        observed_data, parameter_bounds, params_to_calibrate,
                        fixed_params, n_tunes, n_draws, n_chains, cultivar_type
                    )
                else:
                    # 传统优化算法（随机搜索、差分进化）
                    run_traditional_optimization(
                        observed_data, parameter_bounds, fixed_params,
                        algorithm, n_iterations
                    )

        except Exception as e:
            st.error(f"❌ 数据加载失败: {type(e).__name__}: {e}")
            st.code(traceback.format_exc())


# ============================================================
# ⚡ 高级模式页面 (PSO, 混合优化)
# ============================================================

def _show_advanced_calibration_page():
    """高级校准页面（PSO、PSO-MCMC混合优化）"""
    if not PSO_AVAILABLE:
        st.error("❌ PSO 模块不可用")
        return

    st.info("⚡ **高级模式**: PSO 粒子群优化、PSO-MCMC 混合优化")

    # 使用通用的数据文件管理组件
    use_custom = _show_data_file_management()

    # 步骤1: 上传观测数据
    st.markdown("### 📊 步骤1: 上传观测数据")

    uploaded_file = st.file_uploader(
        "选择CSV文件",
        type=['csv'],
        help="必须包含 DAT 列，可选 Biomass、CH4 列",
        key="adv_upload"
    )

    if uploaded_file:
        # 保存文件
        upload_path = UPLOADS_DIR / uploaded_file.name
        with open(upload_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())

        try:
            # 加载数据
            observed_data = load_observed_data_simple(upload_path)

            st.success(f"✅ 成功加载 {len(observed_data)} 条观测数据")

            # 显示数据预览
            col1, col2 = st.columns(2)
            with col1:
                st.metric("观测点数", len(observed_data))
            with col2:
                targets = [c for c in ['Biomass', 'CH4'] if c in observed_data.columns]
                st.metric("目标列", ", ".join(targets) if targets else "无")

            st.dataframe(observed_data, use_container_width=True)

            # 步骤2: 选择优化算法
            st.markdown("### ⚙️ 步骤2: 选择优化算法")

            col1, col2 = st.columns(2)

            with col1:
                adv_algorithm = st.radio(
                    "高级算法",
                    options=['pso', 'hybrid'],
                    format_func=lambda x: {
                        'pso': '🐝 PSO 粒子群优化（全局搜索）',
                        'hybrid': '🔬 PSO-MCMC 混合优化（两阶段）'
                    }[x],
                    help="混合优化结合PSO的全局搜索和MCMC的不确定性量化"
                )

                if adv_algorithm == 'pso':
                    st.info("💡 PSO 通过粒子群体协作进行全局搜索，适合多模态优化问题")

                    pso_type = st.selectbox(
                        "PSO 类型",
                        ['standard', 'adaptive'],
                        format_func=lambda x: {
                            'standard': '标准 PSO（固定惯性权重）',
                            'adaptive': '自适应 PSO（动态调整参数）'
                        }[x]
                    )

                    n_particles = st.slider(
                        "粒子数量",
                        min_value=20,
                        max_value=100,
                        value=50,
                        step=10,
                        help="粒子数量越多，搜索能力越强，但耗时越长"
                    )

                    pso_max_iter = st.slider(
                        "最大迭代次数",
                        min_value=50,
                        max_value=500,
                        value=200,
                        step=50
                    )

                    w_init = st.slider(
                        "初始惯性权重 (w)",
                        min_value=0.5,
                        max_value=1.2,
                        value=0.9,
                        step=0.1,
                        help="控制粒子探索能力"
                    )

                    use_w_decay = st.checkbox("使用惯性权重衰减", value=True)

                else:  # hybrid
                    st.info("💡 混合优化先用PSO快速定位最优区域，再用MCMC进行精细采样")

                    pso_max_iter = st.slider(
                        "PSO 迭代次数",
                        min_value=50,
                        max_value=300,
                        value=150,
                        step=50
                    )

                    mcmc_n_tunes = st.slider(
                        "MCMC Burn-in 样本数",
                        min_value=500,
                        max_value=3000,
                        value=1000,
                        step=100
                    )

                    mcmc_n_draws = st.slider(
                        "MCMC 采样数",
                        min_value=500,
                        max_value=5000,
                        value=2000,
                        step=500
                    )

                    mcmc_n_chains = st.slider(
                        "MCMC 链数",
                        min_value=2,
                        max_value=4,
                        value=3
                    )

            with col2:
                sand_value = st.slider(
                    "土壤砂粒含量 (%)",
                    min_value=0,
                    max_value=100,
                    value=35,
                    key="adv_sand"
                )

                ip_value = st.selectbox(
                    "水管理模式",
                    options=[1, 2, 3, 4, 5],
                    format_func=lambda x: ['淹水', '间歇', '湿润', '控制', '干湿交替'][x-1],
                    key="adv_ip"
                )

            # 参数选择
            st.markdown("#### 选择要优化的参数")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**品种参数**")
                opt_ps = st.checkbox("感光性 (PS)", value=True, key="adv_ps")
                opt_ts = st.checkbox("感温性 (TS)", value=True, key="adv_ts")
                opt_to = st.checkbox("最适温度 (TO)", value=True, key="adv_to")
                opt_ie = st.checkbox("基本早熟性 (IE)", key="adv_ie")
                opt_phi = st.checkbox("收获指数 (PHI)", key="adv_phi")

            with col2:
                st.markdown("**CH4模型参数**")
                opt_q10 = st.checkbox("Q10系数", value=True, key="adv_q10")
                opt_waterc = st.checkbox("水分含量 (WaterC)", value=True, key="adv_waterc")
                opt_eh0 = st.checkbox("初始氧化还原电位 (Eh0)", key="adv_eh0")

            # 步骤3: 开始优化
            st.markdown("### 🚀 步骤3: 开始优化")

            if st.button("⚡ 开始高级优化", type="primary", use_container_width=True):
                # 构建参数边界
                parameter_bounds = {}
                params_to_calibrate = []

                if opt_ps:
                    parameter_bounds['PS'] = PARAMETER_SPACE_CULTIVAR['PS']
                    params_to_calibrate.append('PS')
                if opt_ts:
                    parameter_bounds['TS'] = PARAMETER_SPACE_CULTIVAR['TS']
                    params_to_calibrate.append('TS')
                if opt_to:
                    parameter_bounds['TO'] = PARAMETER_SPACE_CULTIVAR['TO']
                    params_to_calibrate.append('TO')
                if opt_ie:
                    parameter_bounds['IE'] = PARAMETER_SPACE_CULTIVAR['IE']
                    params_to_calibrate.append('IE')
                if opt_phi:
                    parameter_bounds['PHI'] = PARAMETER_SPACE_CULTIVAR['PHI']
                    params_to_calibrate.append('PHI')
                if opt_q10:
                    parameter_bounds['Q10'] = PARAMETER_SPACE_CH4['Q10']
                    params_to_calibrate.append('Q10')
                if opt_waterc:
                    parameter_bounds['WaterC'] = PARAMETER_SPACE_CH4['WaterC']
                    params_to_calibrate.append('WaterC')
                if opt_eh0:
                    parameter_bounds['Eh0'] = PARAMETER_SPACE_CH4['Eh0']
                    params_to_calibrate.append('Eh0')

                if not parameter_bounds:
                    st.error("❌ 请至少选择一个参数")
                    return

                # 固定参数
                fixed_params = {
                    'Sand': float(sand_value),
                    'IP': ip_value,
                    'OMS': 1300.0,
                    'OMN': 1600.0,
                }

                # 执行优化
                if adv_algorithm == 'pso':
                    _run_pso_optimization(
                        observed_data, parameter_bounds, params_to_calibrate,
                        fixed_params, n_particles, pso_max_iter,
                        w_init, use_w_decay, pso_type
                    )
                else:  # hybrid
                    _run_hybrid_optimization(
                        observed_data, parameter_bounds, params_to_calibrate,
                        fixed_params, pso_max_iter, mcmc_n_tunes,
                        mcmc_n_draws, mcmc_n_chains
                    )

        except Exception as e:
            st.error(f"❌ 数据加载失败: {type(e).__name__}: {e}")
            st.code(traceback.format_exc())


def _run_pso_optimization(observed_data, parameter_bounds, params_to_calibrate,
                          fixed_params, n_particles, max_iter,
                          w_init, use_w_decay, pso_type):
    """运行 PSO 优化"""
    if not PSO_AVAILABLE:
        st.error("❌ PSO 模块不可用")
        return

    # 创建进度显示
    progress_bar = st.progress(0)
    status_text = st.empty()
    result_container = st.container()

    try:
        status_text.text("🔨 创建 PSO 优化器...")

        # 创建模型运行器
        def model_runner(params):
            weather_data = load_weather_data_simple()

            full_params = fixed_params.copy()
            full_params.update(params)

            use_custom = st.session_state.get('calibration_use_custom_files', False)
            temp_optimizer = SimpleParameterOptimizer(
                observed_data=observed_data,
                weather_data=weather_data,
                parameter_bounds={},
                fixed_params=fixed_params,
                algorithm='random',
                n_iterations=1,
                use_custom_files=use_custom
            )

            return temp_optimizer._run_model(full_params)

        # 创建 PSO 优化器
        if pso_type == 'adaptive':
            pso = AdaptivePSOOptimizer(
                observed_data=observed_data,
                model_runner=model_runner,
                param_bounds=parameter_bounds,
                n_particles=n_particles,
                max_iter=max_iter,
                w=w_init,
                w_decay=use_w_decay,
                target_columns=['Biomass', 'CH4'],
                fixed_params=fixed_params
            )
        else:
            pso = PSOOptimizer(
                observed_data=observed_data,
                model_runner=model_runner,
                param_bounds=parameter_bounds,
                n_particles=n_particles,
                max_iter=max_iter,
                w=w_init,
                w_decay=use_w_decay,
                target_columns=['Biomass', 'CH4'],
                fixed_params=fixed_params
            )

        progress_bar.progress(0.1)
        status_text.text("🐝 运行 PSO 优化...")

        # 运行优化（带进度回调）
        def progress_callback(iteration, best_fitness, positions):
            progress = min(0.1 + 0.8 * (iteration + 1) / max_iter, 0.9)
            progress_bar.progress(progress)
            status_text.text(
                f"迭代 {iteration+1}/{max_iter} | 最佳适应度: {best_fitness:.6f}"
            )

        result = pso.optimize(callback=progress_callback, verbose=False)

        progress_bar.progress(1.0)
        status_text.text("✅ PSO 优化完成！")

        # 显示结果
        with result_container:
            st.markdown("### 🏆 PSO 优化结果")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("最优适应度", f"{result['best_fitness']:.6f}")
            with col2:
                st.metric("迭代次数", result['n_iterations'])
            with col3:
                st.metric("粒子数量", n_particles)

            # 最优参数
            st.markdown("#### 📋 最优参数")
            params_df = pd.DataFrame([
                {'参数': k, '优化值': f"{v:.4f}"}
                for k, v in result['best_params'].items()
            ])
            st.dataframe(params_df, use_container_width=True)

            # 收敛曲线
            st.markdown("#### 📈 收敛曲线")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=result['fitness_history'],
                mode='lines',
                name='适应度',
                line=dict(color='#10B981', width=2)
            ))
            fig.update_layout(
                title="PSO 优化收敛过程",
                xaxis_title="迭代次数",
                yaxis_title="适应度",
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)

            # 下载结果
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_data = {
                'method': 'PSO',
                'pso_type': pso_type,
                'best_params': {k: float(v) for k, v in result['best_params'].items()},
                'best_fitness': float(result['best_fitness']),
                'n_iterations': result['n_iterations'],
                'n_particles': n_particles,
                'timestamp': datetime.now().isoformat()
            }

            st.download_button(
                "📥 下载 PSO 结果 (JSON)",
                data=json.dumps(result_data, ensure_ascii=False, indent=2),
                file_name=f"pso_result_{timestamp}.json",
                mime="application/json",
                use_container_width=True
            )

            # 显示校准结果评估
            show_calibration_results(
                observed_data, result['best_params'], fixed_params, 'PSO'
            )

    except Exception as e:
        st.error(f"❌ PSO 优化失败: {type(e).__name__}: {e}")
        st.code(traceback.format_exc())


def _run_hybrid_optimization(observed_data, parameter_bounds, params_to_calibrate,
                             fixed_params, pso_max_iter, mcmc_n_tunes,
                             mcmc_n_draws, mcmc_n_chains):
    """运行 PSO-MCMC 混合优化"""
    if not HYBRID_AVAILABLE or not PYMC_AVAILABLE:
        st.error("❌ 混合优化需要 PyMC 模块")
        return

    # 创建进度显示
    progress_bar = st.progress(0)
    status_text = st.empty()
    result_container = st.container()

    try:
        status_text.text("🔨 创建混合优化器...")

        # 创建模型运行器
        def model_runner(params):
            weather_data = load_weather_data_simple()

            full_params = fixed_params.copy()
            full_params.update(params)

            use_custom = st.session_state.get('calibration_use_custom_files', False)
            temp_optimizer = SimpleParameterOptimizer(
                observed_data=observed_data,
                weather_data=weather_data,
                parameter_bounds={},
                fixed_params=fixed_params,
                algorithm='random',
                n_iterations=1,
                use_custom_files=use_custom
            )

            return temp_optimizer._run_model(full_params)

        # 准备先验分布（使用简化版本，基于参数边界）
        param_priors = {}
        for param_name, (lower, upper) in parameter_bounds.items():
            param_priors[param_name] = {
                'dist': 'TruncatedNormal',
                'mu': (lower + upper) / 2,  # 中点作为均值
                'sigma': (upper - lower) / 6,  # 6-sigma规则
                'lower': lower,
                'upper': upper,
                'description': param_name
            }

        # 创建混合优化器
        hybrid = create_hybrid_optimizer(
            observed_data=observed_data,
            model_runner=model_runner,
            param_bounds=parameter_bounds,
            param_priors=param_priors,
            target_columns=['Biomass', 'CH4'],
            fixed_params=fixed_params
        )

        progress_bar.progress(0.05)

        # 运行混合优化
        result = hybrid.optimize(
            pso_config={'max_iter': pso_max_iter},
            mcmc_config={
                'n_tunes': mcmc_n_tunes,
                'n_draws': mcmc_n_draws,
                'n_chains': mcmc_n_chains
            },
            verbose=True
        )

        progress_bar.progress(1.0)
        status_text.text("✅ 混合优化完成！")

        # 显示结果
        with result_container:
            st.markdown("### 🏆 混合优化结果")

            # PSO 结果
            if 'pso' in result:
                st.markdown("#### 🐝 阶段1: PSO 全局搜索")
                pso_result = result['pso']
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("PSO 最优适应度", f"{pso_result['best_fitness']:.6f}")
                with col2:
                    st.metric("PSO 迭代次数", pso_result['n_iterations'])

            # MCMC 结果
            if 'mcmc' in result:
                st.markdown("#### 🔮 阶段2: MCMC 精细采样")
                mcmc_result = result['mcmc']

                if mcmc_result.get('converged'):
                    st.success("✅ MCMC 已收敛")
                else:
                    st.warning("⚠️ MCMC 可能未完全收敛")

                ranges = mcmc_result['ranges']
                for param in params_to_calibrate:
                    if param in ranges:
                        with st.expander(f"**{param}** 后验分布"):
                            stats = ranges[param]
                            c1, c2, c3 = st.columns(3)
                            c1.metric("后验均值", f"{stats['mean']:.4f}")
                            c2.metric("标准差", f"{stats['sd']:.4f}")
                            c3.metric("95% HDI", f"[{stats['hdi_lower']:.4f}, {stats['hdi_upper']:.4f}]")

            # 最优参数（使用MCMC后验均值）
            best_params = hybrid.get_best_params()

            st.markdown("#### 📋 最优参数（后验均值）")
            params_df = pd.DataFrame([
                {'参数': k, '优化值': f"{v:.4f}"}
                for k, v in best_params.items()
            ])
            st.dataframe(params_df, use_container_width=True)

            # 下载结果
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_data = {
                'method': 'PSO-MCMC-Hybrid',
                'pso_result': result.get('pso', {}),
                'mcmc_result': {
                    'converged': result.get('mcmc', {}).get('converged'),
                    'ranges': result.get('mcmc', {}).get('ranges', {})
                },
                'best_params': {k: float(v) for k, v in best_params.items()},
                'timestamp': datetime.now().isoformat()
            }

            st.download_button(
                "📥 下载混合优化结果 (JSON)",
                data=json.dumps(result_data, ensure_ascii=False, indent=2, default=str),
                file_name=f"hybrid_result_{timestamp}.json",
                mime="application/json",
                use_container_width=True
            )

            # 显示校准结果评估
            show_calibration_results(
                observed_data, best_params, fixed_params, '混合优化'
            )

    except Exception as e:
        st.error(f"❌ 混合优化失败: {type(e).__name__}: {e}")
        st.code(traceback.format_exc())


# ============================================================
# 🎯 多目标优化页面
# ============================================================

def _show_multi_objective_page():
    """多目标优化页面"""
    if not MULTI_OBJECTIVE_AVAILABLE:
        st.error("❌ 多目标优化模块不可用")
        return

    st.info("🎯 **多目标优化**: 同时优化多个目标变量")

    # 使用通用的数据文件管理组件
    use_custom = _show_data_file_management()

    # 步骤1: 上传观测数据
    st.markdown("### 📊 步骤1: 上传观测数据")

    uploaded_file = st.file_uploader(
        "选择CSV文件",
        type=['csv'],
        help="必须包含 DAT 列，可选 Biomass、CH4、Yield 列",
        key="multi_upload"
    )

    if uploaded_file:
        upload_path = UPLOADS_DIR / uploaded_file.name
        with open(upload_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())

        try:
            observed_data = load_observed_data_simple(upload_path)
            st.success(f"✅ 成功加载 {len(observed_data)} 条观测数据")

            # 显示可用目标变量
            available_targets = [c for c in ['Biomass', 'CH4', 'Yield', 'LAI']
                                if c in observed_data.columns]

            if len(available_targets) < 2:
                st.warning("⚠️ 多目标优化需要至少2个目标变量")
                return

            st.info(f"📊 可用目标变量: {', '.join(available_targets)}")

            # 步骤2: 配置多目标优化
            st.markdown("### ⚙️ 步骤2: 配置多目标优化")

            col1, col2 = st.columns(2)

            with col1:
                # 选择目标变量
                st.markdown("**选择目标变量**")
                selected_targets = []
                weights = {}

                for target in available_targets:
                    if st.checkbox(target, value=True, key=f"multi_{target}"):
                        selected_targets.append(target)
                        weights[target] = st.slider(
                            f"{target} 权重",
                            min_value=0.0,
                            max_value=1.0,
                            value=1.0/len(available_targets),
                            step=0.1,
                            key=f"weight_{target}"
                        )

                if len(selected_targets) < 2:
                    st.warning("⚠️ 请至少选择2个目标变量")
                    return

                # 优化方法
                opt_method = st.radio(
                    "优化方法",
                    options=['weighted', 'epsilon'],
                    format_func=lambda x: {
                        'weighted': '加权求和法',
                        'epsilon': 'ε-约束法'
                    }[x]
                )

                if opt_method == 'epsilon':
                    primary_target = st.selectbox(
                        "主要优化目标",
                        options=selected_targets
                    )

                    epsilon_constraints = {}
                    for target in selected_targets:
                        if target != primary_target:
                            epsilon_constraints[target] = st.slider(
                                f"{target} 最大允许误差",
                                min_value=0.01,
                                max_value=1.0,
                                value=0.2,
                                step=0.05,
                                key=f"epsilon_{target}"
                            )

            with col2:
                sand_value = st.slider(
                    "土壤砂粒含量 (%)",
                    min_value=0,
                    max_value=100,
                    value=35,
                    key="multi_sand"
                )

                ip_value = st.selectbox(
                    "水管理模式",
                    options=[1, 2, 3, 4, 5],
                    format_func=lambda x: ['淹水', '间歇', '湿润', '控制', '干湿交替'][x-1],
                    key="multi_ip"
                )

                # 优化算法
                base_algorithm = st.selectbox(
                    "基础算法",
                    options=['pso', 'random'],
                    format_func=lambda x: {
                        'pso': 'PSO 粒子群优化',
                        'random': '随机搜索（简单）'
                    }[x]
                )

                if base_algorithm == 'pso':
                    max_iter = st.slider(
                        "最大迭代次数",
                        min_value=50,
                        max_value=300,
                        value=150,
                        step=50,
                        key="multi_iter"
                    )
                else:
                    max_iter = st.slider(
                        "采样次数",
                        min_value=20,
                        max_value=200,
                        value=50,
                        step=10,
                        key="multi_iter"
                    )

            # 步骤3: 开始优化
            st.markdown("### 🚀 步骤3: 开始多目标优化")

            if st.button("🎯 开始多目标优化", type="primary", use_container_width=True):
                # 固定参数
                fixed_params = {
                    'Sand': float(sand_value),
                    'IP': ip_value,
                    'OMS': 1300.0,
                    'OMN': 1600.0,
                }

                _run_multi_objective_optimization(
                    observed_data, selected_targets, weights,
                    fixed_params, opt_method, base_algorithm, max_iter,
                    primary_target if opt_method == 'epsilon' else None,
                    epsilon_constraints if opt_method == 'epsilon' else None
                )

        except Exception as e:
            st.error(f"❌ 数据加载失败: {type(e).__name__}: {e}")
            st.code(traceback.format_exc())


def _run_multi_objective_optimization(observed_data, selected_targets, weights,
                                      fixed_params, opt_method, base_algorithm,
                                      max_iter, primary_target=None,
                                      epsilon_constraints=None):
    """运行多目标优化"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    result_container = st.container()

    try:
        status_text.text("🔨 创建多目标优化器...")

        # 创建模型运行器
        def model_runner(params):
            weather_data = load_weather_data_simple()
            full_params = fixed_params.copy()
            full_params.update(params)

            use_custom = st.session_state.get('calibration_use_custom_files', False)
            temp_optimizer = SimpleParameterOptimizer(
                observed_data=observed_data,
                weather_data=weather_data,
                parameter_bounds={},
                fixed_params=fixed_params,
                algorithm='random',
                n_iterations=1,
                use_custom_files=use_custom
            )

            return temp_optimizer._run_model(full_params)

        # 创建多目标优化器
        if opt_method == 'epsilon':
            multi_opt = EpsilonConstraintOptimizer(
                observed_data=observed_data,
                model_runner=model_runner,
                target_variables=selected_targets,
                primary_target=primary_target,
                epsilon_constraints=epsilon_constraints,
                fixed_params=fixed_params
            )
        else:
            multi_opt = MultiObjectiveOptimizer(
                observed_data=observed_data,
                model_runner=model_runner,
                target_variables=selected_targets,
                weights=weights,
                fixed_params=fixed_params
            )

        progress_bar.progress(0.1)
        status_text.text("🎯 运行多目标优化...")

        # 定义参数空间（使用一些默认参数进行示例）
        param_bounds = {
            'PS': PARAMETER_SPACE_CULTIVAR['PS'],
            'TS': PARAMETER_SPACE_CULTIVAR['TS'],
            'PHI': PARAMETER_SPACE_CULTIVAR['PHI'],
        }

        best_error = float('inf')
        best_params = None
        error_history = []

        for i in range(max_iter):
            # 随机采样参数
            params = {}
            for param_name, (min_val, max_val) in param_bounds.items():
                params[param_name] = np.random.uniform(min_val, max_val)

            # 评估适应度
            error, details = multi_opt.evaluate_fitness(params)

            error_history.append(error)

            if error < best_error:
                best_error = error
                best_params = params.copy()

            # 更新进度
            progress = min(0.1 + 0.8 * (i + 1) / max_iter, 0.9)
            progress_bar.progress(progress)
            status_text.text(
                f"迭代 {i+1}/{max_iter} | 当前误差: {error:.4f} | 最佳误差: {best_error:.4f}"
            )

        progress_bar.progress(1.0)
        status_text.text("✅ 多目标优化完成！")

        # 显示结果
        with result_container:
            st.markdown("### 🏆 多目标优化结果")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("总误差", f"{best_error:.6f}")
            with col2:
                st.metric("迭代次数", max_iter)

            # 最优参数
            st.markdown("#### 📋 最优参数")
            if best_params:
                params_df = pd.DataFrame([
                    {'参数': k, '优化值': f"{v:.4f}"}
                    for k, v in best_params.items()
                ])
                st.dataframe(params_df, use_container_width=True)

            # 收敛曲线
            st.markdown("#### 📈 优化收敛过程")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=error_history,
                mode='lines',
                name='总误差',
                line=dict(color='#8B5CF6', width=2)
            ))
            fig.update_layout(
                title="多目标优化收敛过程",
                xaxis_title="迭代次数",
                yaxis_title="总误差",
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)

            # 显示校准结果评估
            show_calibration_results(
                observed_data, best_params, fixed_params, '多目标优化'
            )

    except Exception as e:
        st.error(f"❌ 多目标优化失败: {type(e).__name__}: {e}")
        st.code(traceback.format_exc())


# ============================================================
# 📊 敏感性分析页面
# ============================================================

def _show_sensitivity_analysis_page():
    """敏感性分析页面"""
    if not SALIB_AVAILABLE:
        st.error("❌ SALib 模块不可用，请运行: pip install SALib")
        return

    st.info("📊 **Sobol 全局敏感性分析**: 识别参数对模型输出的影响程度")

    # 使用通用的数据文件管理组件
    use_custom = _show_data_file_management()

    # 步骤1: 配置分析
    st.markdown("### ⚙️ 步骤1: 配置敏感性分析")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**选择参数组**")

        use_default_bounds = st.checkbox(
            "使用默认参数边界",
            value=True,
            help="使用论文中验证的参数边界"
        )

        if not use_default_bounds:
            st.warning("⚠️ 自定义边界需要手动输入所有参数范围")

        n_samples = st.slider(
            "基础样本数",
            min_value=100,
            max_value=5000,
            value=1000,
            step=100,
            help="样本数越多，结果越准确，但耗时越长"
        )

        calc_second_order = st.checkbox(
            "计算二阶效应（参数交互作用）",
            value=True,
            help="计算参数之间的交互效应"
        )

    with col2:
        st.markdown("**输出变量**")

        output_var = st.selectbox(
            "分析目标变量",
            options=['Yield', 'Biomass', 'CH4', 'LAI'],
            help="选择要分析敏感性的输出变量"
        )

        sand_value = st.slider(
            "土壤砂粒含量 (%)",
            min_value=0,
            max_value=100,
            value=35,
            key="sens_sand"
        )

        ip_value = st.selectbox(
            "水管理模式",
            options=[1, 2, 3, 4, 5],
            format_func=lambda x: ['淹水', '间歇', '湿润', '控制', '干湿交替'][x-1],
            key="sens_ip"
        )

    # 步骤2: 开始分析
    st.markdown("### 🚀 步骤2: 开始敏感性分析")

    if st.button("📊 开始敏感性分析", type="primary", use_container_width=True):
        _run_sensitivity_analysis(
            n_samples, calc_second_order, output_var,
            sand_value, ip_value, use_default_bounds
        )


def _run_sensitivity_analysis(n_samples, calc_second_order, output_var,
                             sand_value, ip_value, use_default_bounds):
    """运行 Sobol 敏感性分析"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    result_container = st.container()

    try:
        # 获取参数边界
        if use_default_bounds:
            parameter_bounds = get_default_parameter_bounds()
        else:
            # 使用示例边界
            parameter_bounds = {
                'PS': PARAMETER_SPACE_CULTIVAR['PS'],
                'TS': PARAMETER_SPACE_CULTIVAR['TS'],
                'PHI': PARAMETER_SPACE_CULTIVAR['PHI'],
            }

        # 创建问题
        problem = create_sobol_problem(parameter_bounds)
        n_params = len(parameter_bounds)
        total_samples = n_samples * (2 * n_params + 2)

        status_text.text(f"📊 生成 Sobol 采样序列 (约 {total_samples} 个样本)...")

        # 生成样本
        param_values = generate_sobol_samples(
            problem, n_samples, calc_second_order
        )

        progress_bar.progress(0.1)
        status_text.text(f"🚀 运行模型 ({param_values.shape[0]} 次)...")

        # 创建模型运行器
        fixed_params = {
            'Sand': float(sand_value),
            'IP': ip_value,
            'OMS': 1300.0,
            'OMN': 1600.0,
        }

        def model_runner(params):
            weather_data = load_weather_data_simple()
            full_params = fixed_params.copy()
            full_params.update(params)

            temp_optimizer = SimpleParameterOptimizer(
                observed_data=pd.DataFrame({'DAT': [0]}),  # 占位
                weather_data=weather_data,
                parameter_bounds={},
                fixed_params=fixed_params,
                algorithm='random',
                n_iterations=1
            )

            result = temp_optimizer._run_model(full_params)

            if result is not None and output_var in result.columns:
                return result[output_var].iloc[-1] if len(result) > 0 else 0
            return 0

        # 运行模型
        Y = np.zeros(param_values.shape[0])

        for i, params in enumerate(param_values):
            param_dict = {name: params[j] for j, name in enumerate(problem['names'])}
            Y[i] = model_runner(param_dict)

            if (i + 1) % 100 == 0:
                progress = min(0.1 + 0.7 * (i + 1) / param_values.shape[0], 0.8)
                progress_bar.progress(progress)
                status_text.text(f"运行模型: {i+1}/{param_values.shape[0]}")

        progress_bar.progress(0.85)
        status_text.text("📈 计算 Sobol 指数...")

        # 运行 Sobol 分析
        sobol_results = run_sobol_analysis(
            problem, param_values, Y, calc_second_order
        )

        # 分类参数
        classification = classify_sensitivity(sobol_results)

        progress_bar.progress(1.0)
        status_text.text("✅ 敏感性分析完成！")

        # 显示结果
        with result_container:
            st.markdown("### 🏆 Sobol 敏感性分析结果")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("高敏感参数", len(classification['high']))
            with col2:
                st.metric("中敏感参数", len(classification['medium']))
            with col3:
                st.metric("低敏感参数", len(classification['low']))

            # 参数分类
            st.markdown("#### 📋 参数分类")

            tab1, tab2, tab3 = st.tabs(["高敏感", "中敏感", "低敏感"])

            with tab1:
                if classification['high']:
                    for param in classification['high']:
                        if param in sobol_results:
                            st.markdown(f"**{param}**")
                            col1, col2 = st.columns(2)
                            col1.metric("总效应 (ST)", f"{sobol_results[param]['ST']:.4f}")
                            col2.metric("一阶效应 (S1)", f"{sobol_results[param]['S1']:.4f}")
                            st.markdown("---")
                else:
                    st.info("无高敏感参数")

            with tab2:
                if classification['medium']:
                    for param in classification['medium']:
                        if param in sobol_results:
                            st.markdown(f"**{param}**")
                            col1, col2 = st.columns(2)
                            col1.metric("总效应 (ST)", f"{sobol_results[param]['ST']:.4f}")
                            col2.metric("一阶效应 (S1)", f"{sobol_results[param]['S1']:.4f}")
                            st.markdown("---")
                else:
                    st.info("无中敏感参数")

            with tab3:
                if classification['low']:
                    for param in classification['low']:
                        if param in sobol_results:
                            st.markdown(f"**{param}**")
                            col1, col2 = st.columns(2)
                            col1.metric("总效应 (ST)", f"{sobol_results[param]['ST']:.4f}")
                            col2.metric("一阶效应 (S1)", f"{sobol_results[param]['S1']:.4f}")
                            st.markdown("---")
                else:
                    st.info("无低敏感参数")

            # 可视化
            st.markdown("#### 📊 敏感性指数图")

            # 提取数据
            params = []
            st_values = []
            s1_values = []

            for param_name, indices in sobol_results.items():
                if '_x_' not in param_name:
                    params.append(param_name)
                    st_values.append(indices['ST'])
                    s1_values.append(indices['S1'])

            # 排序
            sorted_indices = np.argsort(st_values)[::-1]
            sorted_params = [params[i] for i in sorted_indices]
            sorted_st = [st_values[i] for i in sorted_indices]
            sorted_s1 = [s1_values[i] for i in sorted_indices]

            # 创建图表
            fig = go.Figure()

            fig.add_trace(go.Bar(
                y=sorted_params[:15],
                x=sorted_st[:15],
                orientation='h',
                name='总效应 (ST)',
                marker_color='#10B981'
            ))

            fig.add_trace(go.Bar(
                y=sorted_params[:15],
                x=sorted_s1[:15],
                orientation='h',
                name='一阶效应 (S1)',
                marker_color='#3B82F6'
            ))

            fig.update_layout(
                title=f"Sobol 敏感性指数 (Top 15) - {output_var}",
                xaxis_title="敏感性指数",
                yaxis_title="参数",
                barmode='overlay',
                height=500
            )

            st.plotly_chart(fig, use_container_width=True)

            # 下载结果
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_data = {
                'output_var': output_var,
                'n_samples': n_samples,
                'sobol_results': sobol_results,
                'classification': classification,
                'settings': {
                    'sand_value': sand_value,
                    'ip_value': ip_value,
                    'calc_second_order': calc_second_order
                },
                'timestamp': datetime.now().isoformat()
            }

            st.download_button(
                "📥 下载敏感性分析结果 (JSON)",
                data=json.dumps(result_data, ensure_ascii=False, indent=2, default=str),
                file_name=f"sobol_result_{timestamp}.json",
                mime="application/json",
                use_container_width=True
            )

    except Exception as e:
        st.error(f"❌ 敏感性分析失败: {type(e).__name__}: {e}")
        st.code(traceback.format_exc())
