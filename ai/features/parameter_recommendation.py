"""
AI 参数推荐功能模块

根据品种特性推荐最优的水管理、土壤参数、有机质配比。
"""
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from ai.client import AIClient
from ai.prompts.system_prompts import RECOMMENDATION_SYSTEM_PROMPT
from ai.prompts.context_builders import build_simulation_context

logger = logging.getLogger('rice_app')


@dataclass
class ParameterRecommendation:
    """AI 参数推荐结果"""
    water_regime: int
    water_regime_reason: str
    sand_value: float
    sand_reason: str
    oms: float
    oms_reason: str
    omn: float
    omn_reason: str
    summary: str


def get_parameter_recommendation(
    ai_client: AIClient,
    selected_varieties: List[str],
    current_params: Dict[str, Any],
    cultivar_df: Optional[pd.DataFrame] = None,
) -> Optional[ParameterRecommendation]:
    """获取 AI 参数推荐

    Args:
        ai_client: AI 客户端
        selected_varieties: 选中的品种列表
        current_params: 当前参数 (water_regime, sand_value, oms, omn)
        cultivar_df: 品种参数 DataFrame

    Returns:
        推荐结果，失败返回 None
    """
    # 构建上下文
    context = build_simulation_context(
        selected_varieties=selected_varieties,
        water_regime=current_params.get("water_regime", 1),
        sand_value=current_params.get("sand_value", 35.0),
        oms=current_params.get("oms", 1300.0),
        omn=current_params.get("omn", 1600.0),
        cultivar_df=cultivar_df,
    )

    messages = [
        {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
        {"role": "user", "content": f"请根据以下信息推荐最优参数：\n\n{context}"},
    ]

    try:
        response_text = ai_client.chat_complete(messages, json_mode=True)
        data = json.loads(response_text)

        # 验证和约束值范围
        rec = ParameterRecommendation(
            water_regime=max(1, min(5, int(data.get("water_regime", 1)))),
            water_regime_reason=data.get("water_regime_reason", ""),
            sand_value=max(20.0, min(70.0, float(data.get("sand_value", 35.0)))),
            sand_reason=data.get("sand_reason", ""),
            oms=max(0.0, min(5000.0, float(data.get("oms", 1300.0)))),
            oms_reason=data.get("oms_reason", ""),
            omn=max(0.0, min(5000.0, float(data.get("omn", 1600.0)))),
            omn_reason=data.get("omn_reason", ""),
            summary=data.get("summary", ""),
        )
        return rec

    except json.JSONDecodeError as e:
        logger.warning(f"AI 推荐 JSON 解析失败: {e}")
        return None
    except ValueError as e:
        logger.warning(f"AI 请求失败: {e}")
        return None
    except Exception as e:
        logger.warning(f"获取参数推荐失败: {e}")
        return None
