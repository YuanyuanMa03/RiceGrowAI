"""
AI 智能功能模块 (RiceGrowAI)

提供三个 AI 功能：
- 智能助手 (assistant): 自然语言问答
- 参数推荐 (parameter_recommendation): AI 驱动的参数优化建议
- 结果分析 (results_analysis): 模拟结果的 AI 深度分析
"""

try:
    from ai.client import AIClient, get_ai_client, OPENAI_AVAILABLE
except ImportError:
    OPENAI_AVAILABLE = False
