"""
AI 上下文构建模块

将模拟系统的状态（品种、参数、结果）转换为 AI 提示词上下文。
"""
from typing import Any, Dict, List, Optional

import pandas as pd


WATER_REGIME_NAMES = {
    1: "淹水灌溉 (Continuous Flooding)",
    2: "间歇灌溉 (Intermittent Irrigation)",
    3: "湿润灌溉 (Wet Irrigation)",
    4: "控制灌溉 (Controlled Irrigation)",
    5: "干湿交替 (Alternate Wet-Dry)",
}


def build_simulation_context(
    selected_varieties: List[str],
    water_regime: int,
    sand_value: float,
    oms: float,
    omn: float,
    cultivar_df: Optional[pd.DataFrame] = None,
) -> str:
    """构建当前模拟参数的上下文文本"""
    lines = ["## 当前模拟参数\n"]
    lines.append(f"- 选中品种: {', '.join(selected_varieties) if selected_varieties else '未选择'}")
    lines.append(f"- 水管理模式: {water_regime} ({WATER_REGIME_NAMES.get(water_regime, '未知')})")
    lines.append(f"- 土壤砂粒含量: {sand_value}%")
    lines.append(f"- 慢速分解有机质 (OMS): {oms} kg/ha")
    lines.append(f"- 快速分解有机质 (OMN): {omn} kg/ha")

    if cultivar_df is not None and selected_varieties:
        lines.append("\n## 选中品种的关键参数\n")
        for variety in selected_varieties:
            row = cultivar_df[cultivar_df["PZ"] == variety]
            if not row.empty:
                r = row.iloc[0]
                lines.append(f"### {variety}")
                key_params = ["PS", "TS", "TO", "IE", "PHI", "TGW", "PF", "AMX"]
                for p in key_params:
                    if p in r.index:
                        lines.append(f"- {p}: {r[p]}")
                lines.append("")

    return "\n".join(lines)


def build_results_context(results: List[Dict[str, Any]]) -> str:
    """从模拟结果构建上下文文本"""
    if not results:
        return "暂无模拟结果。"

    lines = ["## 模拟结果汇总\n"]

    # 表头
    lines.append("| 品种 | 产量(kg/ha) | 总CH4排放(kg/ha) | 最大LAI | 综合评分 |")
    lines.append("|------|------------|-----------------|---------|---------|")

    for r in results:
        variety = r.get("variety", "未知")
        final_yield = r.get("final_yield", 0)
        ch4 = r.get("total_ch4_emission", 0)
        lai = r.get("max_lai", 0)
        score = r.get("comprehensive_score", "N/A")
        lines.append(f"| {variety} | {final_yield:.1f} | {ch4:.1f} | {lai:.2f} | {score} |")

    # 统计摘要
    yields = [r.get("final_yield", 0) for r in results if r.get("final_yield")]
    ch4s = [r.get("total_ch4_emission", 0) for r in results if r.get("total_ch4_emission")]

    if yields:
        lines.append(f"\n**产量范围**: {min(yields):.1f} ~ {max(yields):.1f} kg/ha")
        lines.append(f"**平均产量**: {sum(yields)/len(yields):.1f} kg/ha")
    if ch4s:
        lines.append(f"**CH4排放范围**: {min(ch4s):.1f} ~ {max(ch4s):.1f} kg/ha")
        lines.append(f"**平均CH4排放**: {sum(ch4s)/len(ch4s):.1f} kg/ha")

    # 最佳品种
    if yields:
        best_yield_idx = yields.index(max(yields))
        lines.append(f"\n**最高产品种**: {results[best_yield_idx].get('variety', '未知')} ({max(yields):.1f} kg/ha)")
    if ch4s:
        best_ch4_idx = ch4s.index(min(ch4s))
        lines.append(f"**最低CH4品种**: {results[best_ch4_idx].get('variety', '未知')} ({min(ch4s):.1f} kg/ha)")

    return "\n".join(lines)


def build_full_context(
    selected_varieties: List[str],
    water_regime: int,
    sand_value: float,
    oms: float,
    omn: float,
    cultivar_df: Optional[pd.DataFrame] = None,
    results: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """构建完整的 AI 上下文（参数 + 结果）"""
    parts = [build_simulation_context(
        selected_varieties, water_regime, sand_value, oms, omn, cultivar_df
    )]

    if results:
        parts.append("\n" + build_results_context(results))

    return "\n".join(parts)
