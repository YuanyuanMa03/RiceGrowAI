"""
AI 结果分析功能模块

对模拟结果生成 AI 深度分析报告。
"""
import logging
from typing import Any, Dict, List, Optional

from ai.client import AIClient
from ai.prompts.system_prompts import ANALYSIS_SYSTEM_PROMPT
from ai.prompts.context_builders import build_results_context, build_simulation_context

logger = logging.getLogger('rice_app')


def generate_results_analysis(
    ai_client: AIClient,
    results: List[Dict[str, Any]],
    simulation_params: Dict[str, Any],
) -> Optional[str]:
    """生成 AI 结果分析报告

    Args:
        ai_client: AI 客户端
        results: 模拟结果列表
        simulation_params: 模拟参数 (varieties, water_regime, sand_value, oms, omn)

    Returns:
        Markdown 格式分析报告，失败返回 None
    """
    if not results:
        return None

    # 构建上下文
    params_context = build_simulation_context(
        selected_varieties=simulation_params.get("varieties", []),
        water_regime=simulation_params.get("water_regime", 1),
        sand_value=simulation_params.get("sand_value", 35.0),
        oms=simulation_params.get("oms", 1300.0),
        omn=simulation_params.get("omn", 1600.0),
    )

    results_context = build_results_context(results)

    messages = [
        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"请分析以下水稻生长模拟结果，生成详细的分析报告：\n\n"
            f"{params_context}\n\n{results_context}"
        )},
    ]

    try:
        return ai_client.chat_complete(messages, temperature=0.5, max_tokens=4096)
    except ValueError as e:
        logger.warning(f"AI 分析请求失败: {e}")
        return str(e)
    except Exception as e:
        logger.warning(f"生成结果分析失败: {e}")
        return None
