"""
AI 助手页面

薄包装层，委托给 ai.ui.assistant_page 模块
"""
import streamlit as st


def show_ai_page() -> None:
    """显示AI助手页面"""
    try:
        from ai.ui.assistant_page import show_ai_assistant_page
        show_ai_assistant_page()
    except ImportError:
        st.warning("⚠️ AI 功能需要安装 openai 包")
        st.code("pip install openai", language="bash")
