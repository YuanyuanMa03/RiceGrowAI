"""
调参模块

提供水稻模型参数校准功能，包括：
- 先验分布定义 (priors.py)
- 参数约束检查 (constraints.py)
- MCMC 贝叶斯调参器 (pymc_calibrator.py)
- 统计指标计算 (metrics.py)
- 结果可视化 (visualization.py)
"""

from calibration.priors import (
    PARAMETER_PRIORS,
    CH4_PARAMETER_PRIORS,
    MANAGEMENT_PARAMETER_PRIORS,
    SOFT_CONSTRAINTS,
    check_hard_constraints,
    get_parameter_prior,
    get_high_sensitivity_params,
    get_medium_sensitivity_params,
    get_low_sensitivity_params,
    get_sensitivity_group,
    get_default_priors,
    get_phi_constraint,
    get_tgw_constraint,
    get_maturity_type,
    get_layered_calibration_strategy,
)

from calibration.constraints import (
    ParameterCorrelation,
    BiologicalBounds,
    PriorityConstraints,
    ParameterSuggestions,
    ConstraintChecker,
    validate_params,
    get_variety_type,
)

from calibration.metrics import (
    calculate_r2,
    calculate_rmse,
    calculate_mae,
    calculate_nse,
    calculate_pbias,
    calculate_kge,
    calculate_all_metrics,
    get_model_rating,
    format_metric_value,
    align_and_calculate_metrics,
)

from calibration.visualization import (
    create_timeseries_comparison,
    create_scatter_plot,
    create_residual_plot,
    create_metrics_cards,
    create_evaluation_section,
)

# 尝试导入敏感性分析模块
try:
    from calibration.sensitivity import (
        get_default_parameter_bounds,
        create_sobol_problem,
        generate_sobol_samples,
        run_sobol_analysis,
        classify_sensitivity,
        plot_sobol_results,
        perform_sensitivity_analysis,
        get_paper_based_sensitivity_groups,
        SALIB_AVAILABLE,
    )
except ImportError:
    SALIB_AVAILABLE = False

# 尝试导入 PSO 优化模块
try:
    from calibration.pso_optimizer import (
        PSOOptimizer,
        AdaptivePSOOptimizer,
        create_pso_optimizer
    )
    PSO_AVAILABLE = True
except ImportError:
    PSO_AVAILABLE = False

# 尝试导入混合优化模块
try:
    from calibration.hybrid_optimizer import (
        PSOMCMCHybridOptimizer,
        create_hybrid_optimizer
    )
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

__all__ = [
    # Priors
    'PARAMETER_PRIORS',
    'CH4_PARAMETER_PRIORS',
    'MANAGEMENT_PARAMETER_PRIORS',
    'SOFT_CONSTRAINTS',
    'check_hard_constraints',
    'get_parameter_prior',
    'get_high_sensitivity_params',
    'get_medium_sensitivity_params',
    'get_low_sensitivity_params',
    'get_sensitivity_group',
    'get_default_priors',
    'get_phi_constraint',
    'get_tgw_constraint',
    'get_maturity_type',
    'get_layered_calibration_strategy',

    # Constraints
    'ParameterCorrelation',
    'BiologicalBounds',
    'PriorityConstraints',
    'ParameterSuggestions',
    'ConstraintChecker',
    'validate_params',
    'get_variety_type',

    # Metrics
    'calculate_r2',
    'calculate_rmse',
    'calculate_mae',
    'calculate_nse',
    'calculate_pbias',
    'calculate_kge',
    'calculate_all_metrics',
    'get_model_rating',
    'format_metric_value',
    'align_and_calculate_metrics',

    # Visualization
    'create_timeseries_comparison',
    'create_scatter_plot',
    'create_residual_plot',
    'create_metrics_cards',
    'create_evaluation_section',

    # Sensitivity (optional, SALib-dependent)
    'get_default_parameter_bounds',
    'create_sobol_problem',
    'generate_sobol_samples',
    'run_sobol_analysis',
    'classify_sensitivity',
    'plot_sobol_results',
    'perform_sensitivity_analysis',
    'get_paper_based_sensitivity_groups',
    'SALIB_AVAILABLE',

    # PSO Optimization
    'PSOOptimizer',
    'AdaptivePSOOptimizer',
    'create_pso_optimizer',
    'PSO_AVAILABLE',

    # Hybrid Optimization (PSO-MCMC)
    'PSOMCMCHybridOptimizer',
    'create_hybrid_optimizer',
    'HYBRID_AVAILABLE',

    # Multi-Objective Optimization
    'MultiObjectiveOptimizer',
    'EpsilonConstraintOptimizer',
    'create_multi_objective_optimizer',
    'MULTI_OBJECTIVE_AVAILABLE',
]
