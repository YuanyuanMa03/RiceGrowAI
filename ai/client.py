"""
AI 客户端封装模块

支持多提供商：OpenAI、智谱AI (ZhipuAI)。
统一 API 调用接口，支持流式和非流式请求。
"""
import logging
from typing import Generator, Optional

import streamlit as st

logger = logging.getLogger('rice_app')

try:
    from openai import OpenAI, APIError, AuthenticationError, RateLimitError, APITimeoutError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ===== 模型提供商配置 =====
PROVIDERS = {
    "zhipu": {
        "name": "智谱AI (ZhipuAI)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": [
            # ---- GLM-5 系列 ----
            {"id": "glm-5",           "name": "GLM-5 (旗舰)",         "tags": ["reasoning"]},
            {"id": "glm-5-turbo",     "name": "GLM-5 Turbo",          "tags": ["reasoning"]},
            # ---- GLM-4.7 系列 ----
            {"id": "glm-4.7",         "name": "GLM-4.7",              "tags": ["reasoning"]},
            {"id": "glm-4.7-flash",   "name": "GLM-4.7 Flash",        "tags": ["reasoning"]},
            {"id": "glm-4.7-flashx",  "name": "GLM-4.7 FlashX",       "tags": ["reasoning"]},
            # ---- GLM-4.6 系列 ----
            {"id": "glm-4.6",         "name": "GLM-4.6",              "tags": ["reasoning"]},
            {"id": "glm-4.6v",        "name": "GLM-4.6V (视觉)",      "tags": ["reasoning", "vision"]},
            {"id": "glm-4.6v-flash",  "name": "GLM-4.6V Flash (免费·视觉)", "tags": ["reasoning", "vision", "free"]},
            # ---- GLM-4.5 系列 ----
            {"id": "glm-4.5",         "name": "GLM-4.5",              "tags": ["reasoning"]},
            {"id": "glm-4.5-air",     "name": "GLM-4.5 Air",          "tags": ["reasoning"]},
            {"id": "glm-4.5-flash",   "name": "GLM-4.5 Flash (免费)",  "tags": ["reasoning", "free"]},
            {"id": "glm-4.5v",        "name": "GLM-4.5V (视觉)",      "tags": ["reasoning", "vision"]},
        ],
    },
    "openai": {
        "name": "OpenAI",
        "base_url": None,  # 使用默认值
        "models": [
            {"id": "gpt-4o",           "name": "GPT-4o"},
            {"id": "gpt-4o-mini",      "name": "GPT-4o Mini"},
            {"id": "gpt-4-turbo",      "name": "GPT-4 Turbo"},
        ],
    },
}


def get_provider_model_ids(provider_key: str) -> list:
    """获取指定提供商的模型 ID 列表"""
    provider = PROVIDERS.get(provider_key, {})
    return [m["id"] for m in provider.get("models", [])]


def get_model_display_name(provider_key: str, model_id: str) -> str:
    """获取模型的显示名称"""
    provider = PROVIDERS.get(provider_key, {})
    for m in provider.get("models", []):
        if m["id"] == model_id:
            return m["name"]
    return model_id


class AIClient:
    """统一 AI 客户端（兼容 OpenAI / 智谱AI 等）"""

    def __init__(self, api_key: str, model: str = "glm-5", provider: str = "zhipu"):
        if not OPENAI_AVAILABLE:
            raise RuntimeError("openai 包未安装，请运行: pip install openai")

        provider_cfg = PROVIDERS.get(provider, {})
        base_url = provider_cfg.get("base_url")

        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url

        self.client = OpenAI(**kwargs)
        self.model = model
        self.provider = provider

    def chat_stream(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        """流式聊天补全，逐字输出"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except AuthenticationError:
            raise ValueError("API Key 无效，请检查后重试")
        except RateLimitError:
            raise ValueError("API 请求频率超限，请稍后再试")
        except APITimeoutError:
            raise ValueError("API 请求超时，请检查网络连接")
        except APIError as e:
            raise ValueError(f"API 错误: {e}")

    def chat_complete(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        """非流式聊天补全，返回完整文本"""
        try:
            kwargs = dict(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except AuthenticationError:
            raise ValueError("API Key 无效，请检查后重试")
        except RateLimitError:
            raise ValueError("API 请求频率超限，请稍后再试")
        except APITimeoutError:
            raise ValueError("API 请求超时，请检查网络连接")
        except APIError as e:
            raise ValueError(f"API 错误: {e}")

    def is_available(self) -> bool:
        """检查客户端是否可用"""
        return OPENAI_AVAILABLE and self.client is not None


def get_ai_client() -> Optional["AIClient"]:
    """从 session state 获取 AI 客户端实例"""
    api_key = st.session_state.get("ai_api_key", "")
    if not api_key or not OPENAI_AVAILABLE:
        return None
    model = st.session_state.get("ai_model", "glm-4.5-flash")
    provider = st.session_state.get("ai_provider", "zhipu")
    try:
        return AIClient(api_key=api_key, model=model, provider=provider)
    except Exception as e:
        logger.warning(f"创建 AI 客户端失败: {e}")
        return None
