"""
UI 样式模块 - 集中管理所有 CSS 样式

从 app.py 提取的 CSS 样式，统一管理
"""
import streamlit as st


GLOBAL_CSS = """
<style>
    :root {
        --primary-green: #10B981;
        --primary-green-dark: #059669;
        --primary-green-light: #34D399;
        --primary-green-ultra-light: #D1FAE5;
        --accent-blue: #3B82F6;
        --accent-purple: #8B5CF6;
        --accent-orange: #F59E0B;
        --accent-pink: #EC4899;
        --neutral-bg: linear-gradient(135deg, #0D9488 0%, #0F766E 50%, #115E59 100%);
        --neutral-card: rgba(255, 255, 255, 0.95);
        --neutral-text: #1E293B;
        --neutral-text-secondary: #475569;
        --border-color: rgba(16, 185, 129, 0.2);
        --shadow-sm: 0 2px 4px 0 rgba(0, 0, 0, 0.1);
        --shadow-md: 0 6px 12px -1px rgba(0, 0, 0, 0.15), 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        --shadow-lg: 0 15px 25px -3px rgba(0, 0, 0, 0.15), 0 8px 10px -2px rgba(0, 0, 0, 0.1);
        --shadow-xl: 0 25px 35px -5px rgba(0, 0, 0, 0.2), 0 15px 15px -5px rgba(0, 0, 0, 0.1);
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 20px;
        --transition-fast: 0.15s ease;
        --transition-normal: 0.3s ease;
    }

    .main {
        background: var(--neutral-bg) !important;
        padding: 1rem !important;
        min-height: 100vh;
        position: relative !important;
        z-index: 1 !important;
    }

    .main::before {
        content: '' !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        background:
            radial-gradient(circle at 20% 30%, rgba(16, 185, 129, 0.15) 0%, transparent 50%),
            radial-gradient(circle at 80% 70%, rgba(59, 130, 246, 0.15) 0%, transparent 50%),
            radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0.1) 0%, transparent 50%) !important;
        pointer-events: none !important;
        z-index: -1 !important;
    }

    .main > div {
        position: relative !important;
        z-index: 2 !important;
    }

    .main h1, .main h2, .main h3, .main h4, .main h5, .main h6,
    .main p, .main span, .main div, .main label {
        text-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
    }

    .main .stContainer, .main .block-container {
        background-color: transparent !important;
    }

    .modern-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.95) 100%) !important;
        border-radius: var(--radius-md) !important;
        box-shadow: var(--shadow-md) !important;
        border: 2px solid transparent !important;
        background-clip: padding-box !important;
        padding: 1rem !important;
        transition: all var(--transition-normal) !important;
        position: relative !important;
        overflow: hidden !important;
    }

    .modern-card::before {
        content: '' !important;
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        border-radius: var(--radius-md) !important;
        padding: 2px !important;
        background: linear-gradient(135deg, var(--primary-green), var(--accent-blue), var(--accent-purple)) !important;
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0) !important;
        -webkit-mask-composite: xor !important;
        mask-composite: exclude !important;
        opacity: 0.6 !important;
        transition: opacity var(--transition-normal) !important;
    }

    .modern-card:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-xl) !important;
    }

    .modern-card:hover::before {
        opacity: 1 !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, var(--primary-green) 0%, var(--accent-blue) 100%) !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4) !important;
        transition: all var(--transition-fast) !important;
        position: relative !important;
        overflow: hidden !important;
    }

    .stButton > button::before {
        content: '' !important;
        position: absolute !important;
        top: 50% !important;
        left: 50% !important;
        width: 0 !important;
        height: 0 !important;
        border-radius: 50% !important;
        background: rgba(255, 255, 255, 0.3) !important;
        transform: translate(-50%, -50%) !important;
        transition: width 0.6s, height 0.6s !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-lg) !important;
    }

    .stButton > button:hover::before {
        width: 300px !important;
        height: 300px !important;
    }

    .stButton > button:active {
        transform: translateY(0) !important;
    }

    .stSelectbox > div > div,
    .stMultiselect > div > div,
    .stNumberInput > div > div,
    .stTextInput > div > div,
    .stTextArea > div > div,
    .stSelectbox select,
    .stSelectbox option {
        border-radius: var(--radius-md) !important;
        border: 2px solid var(--border-color) !important;
        background: #FFFFFF !important;
        color: #1E293B !important;
        transition: all var(--transition-fast) !important;
        padding: 0.5rem 0.75rem !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji" !important;
    }

    .stSelectbox > div > div:hover,
    .stMultiselect > div > div:hover,
    .stNumberInput > div > div:hover,
    .stTextInput > div > div:hover,
    .stTextArea > div > div:hover {
        border-color: var(--primary-green-light) !important;
        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1) !important;
    }

    .stSelectbox > div > div:focus-within,
    .stMultiselect > div > div:focus-within,
    .stNumberInput > div > div:focus-within,
    .stTextInput > div > div:focus-within,
    .stTextArea > div > div:focus-within {
        border-color: var(--primary-green) !important;
        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2) !important;
    }

    .stRadio > div > div {
        gap: 0.5rem !important;
    }

    @keyframes shimmer {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
</style>
"""

PAGE_SELECTOR_CSS = """
<style>
    .page-selector {
        display: flex;
        gap: 1rem;
        margin: 1rem 0;
        padding: 0.5rem;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    .page-button {
        flex: 1;
        padding: 0.75rem 1rem;
        border: 2px solid #E5E7EB;
        border-radius: 8px;
        background: #F9FAFB;
        color: #475569;
        font-weight: 600;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.3s ease;
        text-align: center;
    }
    .page-button:hover {
        border-color: #10B981;
        background: #ECFDF5;
        color: #059669;
    }
    .page-button.active {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        border-color: #10B981;
    }
</style>
"""


def inject_global_styles() -> None:
    """注入全局CSS样式"""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def inject_page_selector_styles() -> None:
    """注入页面选择器CSS样式"""
    st.markdown(PAGE_SELECTOR_CSS, unsafe_allow_html=True)
