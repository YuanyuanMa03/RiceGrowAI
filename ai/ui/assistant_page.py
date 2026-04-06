"""
AI 智能助手页面 UI

使用 Streamlit chat 组件实现聊天界面。
"""
import streamlit as st

from ai.client import get_ai_client, OPENAI_AVAILABLE
from ai.features.assistant import process_chat_message
from ai.prompts.context_builders import build_full_context


def show_ai_assistant_page():
    """渲染 AI 智能助手页面"""
    # 页面头部 - 紫色渐变主题
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%);
        padding: 1.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 20px rgba(139, 92, 246, 0.3);
    ">
        <h2 style="margin:0; color:white; font-size:1.5rem;">RiceGrowAI 智能助手</h2>
        <p style="margin:0.3rem 0 0 0; opacity:0.9; font-size:0.85rem;">
            询问关于水稻生长、CH4排放、模拟参数的任何问题
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 检查 openai 包是否可用
    if not OPENAI_AVAILABLE:
        st.warning("AI 功能需要安装 openai 包。请运行：`pip install openai`")
        return

    # 检查 API key
    if not st.session_state.get("ai_api_key"):
        st.info("""
        **请先配置 AI API Key**

        在左侧边栏底部找到「AI 助手设置」，选择提供商并输入 API Key 即可开始使用。
        """)
        return

    # 获取 AI 客户端
    ai_client = get_ai_client()
    if ai_client is None:
        st.error("AI 客户端初始化失败，请检查 API Key。")
        return

    # 构建当前上下文
    try:
        cultivar_df = _load_cultivar_df()
    except Exception:
        cultivar_df = None

    context = build_full_context(
        selected_varieties=st.session_state.get("selected_varieties", []),
        water_regime=st.session_state.get("water_regime", 1),
        sand_value=st.session_state.get("sand_value", 35.0),
        oms=st.session_state.get("oms", 1300.0),
        omn=st.session_state.get("omn", 1600.0),
        cultivar_df=cultivar_df,
        results=st.session_state.get("simulation_results"),
    )

    # 显示聊天历史
    for msg in st.session_state.get("ai_chat_history", []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 聊天输入
    if prompt := st.chat_input("询问关于水稻生长、CH4排放、模拟结果的问题..."):
        # 添加用户消息
        st.session_state.setdefault("ai_chat_history", [])
        st.session_state.ai_chat_history.append({"role": "user", "content": prompt})

        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)

        # 流式输出 AI 回复
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            try:
                for chunk in process_chat_message(
                    user_message=prompt,
                    chat_history=st.session_state.ai_chat_history[:-1],
                    ai_client=ai_client,
                    context=context,
                ):
                    full_response += chunk
                    response_placeholder.markdown(full_response + " ▌")
                response_placeholder.markdown(full_response)
            except ValueError as e:
                full_response = f"抱歉，出现错误：{e}"
                response_placeholder.error(full_response)
            except Exception:
                full_response = "抱歉，AI 服务暂时不可用，请稍后再试。"
                response_placeholder.error(full_response)

        # 保存 AI 回复到历史
        st.session_state.ai_chat_history.append({"role": "assistant", "content": full_response})


def _load_cultivar_df():
    """加载品种参数数据"""
    import pandas as pd
    import os

    # 尝试从上传的文件或默认路径加载
    upload_key = "custom_品种参数_csv"
    if st.session_state.get(upload_key) is not None:
        uploaded = st.session_state[upload_key]
        return pd.read_csv(uploaded, encoding="gbk")

    # 尝试默认路径
    for path in [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "品种参数.csv"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "品种参数.csv"),
    ]:
        if os.path.exists(path):
            encodings = ["gbk", "utf-8", "gb2312"]
            for enc in encodings:
                try:
                    return pd.read_csv(path, encoding=enc)
                except (UnicodeDecodeError, Exception):
                    continue
    return None
