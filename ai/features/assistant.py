"""
AI 智能助手功能模块

提供基于 OpenAI 的自然语言聊天功能。
"""
from typing import Generator, List, Optional

from ai.client import AIClient
from ai.prompts.system_prompts import ASSISTANT_SYSTEM_PROMPT

MAX_HISTORY = 20


def process_chat_message(
    user_message: str,
    chat_history: List[dict],
    ai_client: AIClient,
    context: str = "",
) -> Generator[str, None, None]:
    """处理用户消息并流式返回 AI 回复

    Args:
        user_message: 用户输入
        chat_history: 聊天历史 [{'role': 'user'|'assistant', 'content': str}]
        ai_client: AI 客户端实例
        context: 当前模拟上下文

    Yields:
        AI 回复的文本片段
    """
    # 构建系统消息
    system_content = ASSISTANT_SYSTEM_PROMPT
    if context:
        system_content += "\n\n---\n\n## 当前用户的模拟数据\n\n" + context

    messages = [{"role": "system", "content": system_content}]

    # 截断历史（保留最近的对话）
    recent_history = chat_history[-MAX_HISTORY:]
    messages.extend(recent_history)

    # 添加当前用户消息
    messages.append({"role": "user", "content": user_message})

    yield from ai_client.chat_stream(messages)
