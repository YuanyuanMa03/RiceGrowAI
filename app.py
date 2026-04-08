import streamlit as st
import pandas as pd
import os
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Generator, Tuple
from models.RG2CH4 import CH4Flux_coupled
from models.Ricegrow_py_v1_0 import CalFun, GetTmax, GetTmin, CalT24H, GetCultivarParams

# ===== 企业级UI组件导入 =====
from ui_components import (
    render_sidebar_header,
    render_variety_selector,
    render_variety_feedback,
    render_water_regime_selector,
    render_soil_parameter_sliders,
    render_run_button,
    render_results_header,
    create_comparison_chart,
    create_timeseries_chart
)

# ===== Session State管理导入 =====
from session_manager import (
    init_session_state,
    get_session_state,
    set_session_state,
    clear_session_state,
    cleanup_after_simulation,
    validate_session_state,
    log_session_state_usage
)

# ===== 简化调参模块 =====
from calibration_page import show_simple_calibration_page

# ===== AI 智能功能模块 =====
try:
    from ai.client import OPENAI_AVAILABLE, PROVIDERS, get_provider_model_ids, get_model_display_name
    from ai.ui.assistant_page import show_ai_assistant_page
    from ai.ui.recommendation_panel import render_recommendation_panel
    from ai.ui.analysis_tab import render_ai_analysis_tab
except ImportError:
    OPENAI_AVAILABLE = False

# ===== 企业级配置模块导入 =====
from config import (
    PROJECT_ROOT,
    DATA_DIR,
    LOGS_DIR,
    UPLOADS_DIR,
    ENCODING_FALLBACK,
    DEFAULT_WRITE_ENCODING,
    MAX_FILE_SIZE,
    ALLOWED_EXTENSIONS,
    WATER_REGIME_NAMES,
    WATER_REGIME_DESCRIPTIONS,
    REQUIRED_DATA_FILES,
    FILE_MAPPING,
    ERROR_MESSAGES,
    PROGRESS_UPDATE_DELAY,
    KB_SIZE_DIVISOR,
    MB_SIZE_DIVISOR,
    FLOAT_PRECISION_DEFAULT,
    DAY_START_INDEX,
    RANKING_START_INDEX,
    PANDAS_ILON_FIRST_ROW,
    setup_application_logging,
    safe_join_path,
)
# Exceptions from unified hierarchy
from core.exceptions import (
    FileReadError,
    EncodingError,
    ValidationError,
)

# 初始化日志系统
logger = setup_application_logging()

# ===== 企业级文件读取工具 =====
@st.cache_data(ttl=3600, max_entries=20, show_spinner="正在加载数据...")
def safe_read_csv(
    filepath: Union[str, Path],
    encodings: Optional[List[str]] = None
) -> pd.DataFrame:
    """安全读取CSV文件，自动检测编码（带缓存）

    Args:
        filepath: 文件路径
        encodings: 要尝试的编码列表，默认使用配置中的编码降级列表

    Returns:
        pandas.DataFrame

    Raises:
        FileReadError: 文件不存在或读取失败时抛出

    Note:
        使用 @st.cache_data 缓存结果，避免重复读取
    """
    if encodings is None:
        encodings = ENCODING_FALLBACK

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileReadError(ERROR_MESSAGES['file_not_found'].format(filename=filepath))

    last_error = None
    for encoding in encodings:
        try:
            df = pd.read_csv(filepath, encoding=encoding)
            if encoding != 'gbk':
                logger.info(f"使用编码 {encoding} 读取文件: {filepath}")
            return df
        except (UnicodeDecodeError, UnicodeError) as e:
            last_error = e
            continue
        except Exception as e:
            logger.warning(f"使用编码 {encoding} 读取时出错: {e}")
            last_error = e
            continue

    # 所有编码都失败了
    raise EncodingError(
        ERROR_MESSAGES['encoding_error'].format(
            filename=filepath,
            encodings=', '.join(encodings)
        )
    )

# ===== 临时文件管理工具 =====
@contextmanager
def temporary_file(filepath: Union[str, Path]) -> Generator[Path, None, None]:
    """临时文件上下文管理器，确保文件在使用后被清理

    Args:
        filepath: 临时文件路径

    Yields:
        Path: 临时文件路径

    Example:
        with temporary_file(Path("/tmp/temp.csv")) as temp_path:
            # 使用临时文件
            write_data(temp_path)
            process_data(temp_path)
        # 文件自动清理
    """
    filepath = Path(filepath)
    try:
        logger.debug(f"创建临时文件: {filepath}")
        yield filepath
    finally:
        if filepath.exists():
            try:
                filepath.unlink()
                logger.debug(f"清理临时文件: {filepath}")
            except Exception as e:
                logger.warning(f"清理临时文件失败 {filepath}: {e}")

# ===== 文件上传验证工具 =====
def validate_uploaded_file(
    uploaded_file: Any,
    max_size_mb: Optional[int] = None
) -> bool:
    """验证上传的文件是否符合要求

    Args:
        uploaded_file: Streamlit上传的文件对象
        max_size_mb: 最大文件大小（MB），默认使用配置中的值

    Returns:
        bool: 验证通过返回True

    Raises:
        ValidationError: 验证失败时抛出
    """
    if uploaded_file is None:
        raise ValidationError(ERROR_MESSAGES['no_variety_selected'])

    # 检查文件大小
    max_size = max_size_mb or (MAX_FILE_SIZE / (1024 * 1024))
    file_size = uploaded_file.size
    if file_size > MAX_FILE_SIZE:
        raise ValidationError(
            ERROR_MESSAGES['file_too_large'].format(
                max_size=int(MAX_FILE_SIZE / (1024 * 1024))
            )
        )

    # 检查文件扩展名
    file_ext = Path(uploaded_file.name).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(ERROR_MESSAGES['invalid_file_type'])

    logger.info(f"文件验证通过: {uploaded_file.name} ({file_size / KB_SIZE_DIVISOR:.1f} KB)")
    return True

def save_uploaded_file(
    uploaded_file: Any,
    target_dir: Union[str, Path],
    encoding: str = DEFAULT_WRITE_ENCODING
) -> Path:
    """安全保存上传的文件

    Args:
        uploaded_file: Streamlit上传的文件对象
        target_dir: 目标目录路径
        encoding: 目标编码，默认为GBK

    Returns:
        Path: 保存的文件路径

    Raises:
        ValidationError: 文件验证失败
        EncodingError: 编码转换失败
    """
    # 验证文件
    validate_uploaded_file(uploaded_file)

    # 确保目标目录存在
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    # 安全拼接路径
    target_path = safe_join_path(target_dir, uploaded_file.name)

    # 读取文件内容
    try:
        df = safe_read_csv(uploaded_file)
    except Exception as e:
        raise EncodingError(f"无法解析上传的文件 {uploaded_file.name}: {e}")

    # 保存为目标编码
    try:
        df.to_csv(target_path, index=False, encoding=encoding, errors='replace')
        logger.info(f"成功保存上传文件: {target_path} (编码: {encoding})")
        return target_path
    except Exception as e:
        raise EncodingError(f"保存文件失败 {target_path}: {e}")

# 页面配置
st.set_page_config(
    page_title="水稻生长与CH4排放模拟系统",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 现代绿色主题CSS样式 - 增强版
st.markdown("""
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

    /* 基础布局 - 紧凑型 */
    .main {
        background: var(--neutral-bg) !important;
        padding: 1rem !important;
        min-height: 100vh;
        position: relative !important;
        z-index: 1 !important;
    }

    /* 给主内容区添加微妙的纹理 */
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

    /* 确保主内容区域的所有元素都在正确的层级 */
    .main > div {
        position: relative !important;
        z-index: 2 !important;
    }

    /* 确保所有文字在深色背景下可见 */
    .main h1, .main h2, .main h3, .main h4, .main h5, .main h6,
    .main p, .main span, .main div, .main label {
        text-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
    }

    /* 确保所有卡片、容器有正确的背景 */
    .main .stContainer, .main .block-container {
        background-color: transparent !important;
    }

    /* 现代卡片系统 - 紧凑多彩版 */
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

    /* 按钮增强 - 紧凑多彩版 */
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

    /* 输入框美化 - 修复汉字显示 */
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

    /* Radio按钮美化 - 深色背景优化 */
    .stRadio > div > div {
        gap: 0.5rem !important;
    }

    .stRadio > div > div > label {
        background: rgba(255, 255, 255, 0.95) !important;
        border: 2px solid rgba(16, 185, 129, 0.3) !important;
        border-radius: var(--radius-sm) !important;
        padding: 0.6rem 0.85rem !important;
        transition: all var(--transition-fast) !important;
        margin: 0 !important;
        color: #1E293B !important;
        font-size: 0.85rem !important;
    }

    .stRadio > div > div > label:hover {
        border-color: #10B981 !important;
        background: #ECFDF5 !important;
        transform: translateX(3px) !important;
    }

    .stRadio > div > div > label[data-checked="true"] {
        background: linear-gradient(135deg, #D1FAE5, #ECFDF5) !important;
        border-color: #10B981 !important;
        color: #065F46 !important;
        font-weight: 700 !important;
    }

    /* 标签页增强 - 深色背景优化 */
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.6) !important;
        border: 2px solid rgba(16, 185, 129, 0.2) !important;
        border-bottom: none !important;
        color: #475569 !important;
        font-weight: 600 !important;
        padding: 10px 16px !important;
        font-size: 13px !important;
        transition: all var(--transition-fast) !important;
        border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #059669 !important;
        background: rgba(255, 255, 255, 0.85) !important;
        border-color: #10B981 !important;
    }

    .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.95) !important;
        color: #059669 !important;
        border-color: #10B981 !important;
        font-weight: 700 !important;
    }

    /* 数据表格增强 - 深色背景优化 */
    .dataframe {
        border-radius: var(--radius-lg) !important;
        overflow: hidden !important;
        box-shadow: var(--shadow-md) !important;
        border: 1px solid var(--border-color) !important;
        font-size: 13px !important;
        background: white !important;
    }

    .dataframe th {
        background: linear-gradient(135deg, #059669, #10B981) !important;
        color: white !important;
        font-weight: 700 !important;
        padding: 12px 14px !important;
        font-size: 12px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        position: sticky !important;
        top: 0 !important;
    }

    .dataframe td {
        padding: 10px 14px !important;
        border-bottom: 1px solid #E5E7EB !important;
        transition: background var(--transition-fast) !important;
        color: #1E293B !important;
    }

    .dataframe tr {
        transition: all var(--transition-fast) !important;
        background: white !important;
    }

    .dataframe tr:hover {
        background: #ECFDF5 !important;
        transform: scale(1.005) !important;
    }

    .dataframe tr:nth-child(even) {
        background: #F9FAFB !important;
    }

    .dataframe tr:nth-child(even):hover {
        background: #ECFDF5 !important;
    }

    /* 图表容器增强 */
    .stPlotlyChart {
        border-radius: var(--radius-lg) !important;
        overflow: hidden !important;
        box-shadow: var(--shadow-md) !important;
        border: 1px solid var(--border-color) !important;
        background: white !important;
        transition: all var(--transition-normal) !important;
    }

    .stPlotlyChart:hover {
        box-shadow: var(--shadow-lg) !important;
        transform: translateY(-2px) !important;
    }

    /* 侧边栏美化 - 深色主题 */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(248,250,252,0.95) 100%) !important;
        border-right: 2px solid rgba(16, 185, 129, 0.3) !important;
        padding: 1rem 0.75rem !important;
        backdrop-filter: blur(10px) !important;
    }

    .stSidebar .modern-card {
        background: rgba(255, 255, 255, 0.95) !important;
        margin-bottom: 0.75rem !important;
    }

    /* 侧边栏文字颜色 */
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stText {
        color: #1E293B !important;
    }

    /* 进度条增强 */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--primary-green-light), var(--primary-green), var(--primary-green-dark)) !important;
        border-radius: 4px !important;
        height: 8px !important;
        transition: width 0.3s ease !important;
    }

    /* 指标卡片 */
    .stMetric {
        background: var(--neutral-card) !important;
        border-radius: var(--radius-md) !important;
        padding: 1rem !important;
        box-shadow: var(--shadow-sm) !important;
        border: 1px solid var(--border-color) !important;
        transition: all var(--transition-fast) !important;
    }

    .stMetric:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-md) !important;
    }

    .stMetric > div > div > div {
        font-weight: 700 !important;
        color: var(--primary-green-dark) !important;
    }

    /* 警告和信息框 */
    .stAlert {
        border-radius: var(--radius-md) !important;
        border-left: 4px solid !important;
        padding: 1rem !important;
        box-shadow: var(--shadow-sm) !important;
    }

    .stAlert > div {
        padding: 0 !important;
    }

    /* 动画效果 */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.8;
        }
    }

    .animate-fade-in-up {
        animation: fadeInUp 0.6s ease-out !important;
    }

    .animate-pulse {
        animation: pulse 2s infinite !important;
    }

    /* 响应式优化 */
    @media (max-width: 768px) {
        .main {
            padding: 0.75rem 0.5rem !important;
        }

        .modern-card {
            padding: 0.75rem !important;
        }

        .stButton > button {
            font-size: 13px !important;
            padding: 0.5rem 0.85rem !important;
        }

        .stTabs [data-baseweb="tab"] {
            padding: 8px 12px !important;
            font-size: 11px !important;
        }
    }

    /* 自定义滚动条 */
    ::-webkit-scrollbar {
        width: 8px !important;
        height: 8px !important;
    }

    ::-webkit-scrollbar-track {
        background: var(--neutral-bg) !important;
    }

    ::-webkit-scrollbar-thumb {
        background: var(--primary-green-light) !important;
        border-radius: 4px !important;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary-green) !important;
    }
</style>
""", unsafe_allow_html=True)

# 主标题 - 紧凑多彩版
st.markdown("""
<div style="
    background: linear-gradient(135deg, #10B981 0%, #3B82F6 50%, #8B5CF6 100%);
    color: white;
    padding: 1.25rem 1rem;
    border-radius: 12px;
    margin-bottom: 1rem;
    text-align: center;
    box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3), 0 4px 10px rgba(59, 130, 246, 0.2);
    position: relative;
    overflow: hidden;
    animation: fadeInUp 0.6s ease-out;
">
    <div style="
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 60%);
        animation: shimmer 4s infinite linear;
    "></div>
    <h1 style="
        margin: 0;
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        text-shadow: 0 2px 8px rgba(0,0,0,0.2);
        position: relative;
        z-index: 1;
    ">
        🌾 水稻生长与CH4排放模拟系统
    </h1>
    <p style="
        margin: 0.35rem 0 0 0;
        font-size: 0.85rem;
        opacity: 0.95;
        font-weight: 500;
        letter-spacing: 0.5px;
        position: relative;
        z-index: 1;
    ">
        Rice Growth & Methane Emission Modeling System
    </p>
    <div style="
        margin-top: 0.65rem;
        display: flex;
        justify-content: center;
        gap: 0.6rem;
        flex-wrap: wrap;
        position: relative;
        z-index: 1;
    ">
        <span style="
            background: rgba(255,255,255,0.25);
            padding: 0.2rem 0.65rem;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 600;
            backdrop-filter: blur(10px);
        ">🌱 精准农业</span>
        <span style="
            background: rgba(255,255,255,0.25);
            padding: 0.2rem 0.65rem;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 600;
            backdrop-filter: blur(10px);
        ">💨 碳排放预测</span>
        <span style="
            background: rgba(255,255,255,0.25);
            padding: 0.2rem 0.65rem;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 600;
            backdrop-filter: blur(10px);
        ">📊 数据驱动</span>
    </div>
</div>

<style>
    @keyframes shimmer {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
</style>
""", unsafe_allow_html=True)

# 侧边栏内容函数
def show_sidebar_content(cultivar_df):
    """显示侧边栏内容并管理用户输入"""
    # 初始化session state
    if 'use_custom_files' not in st.session_state:
        st.session_state['use_custom_files'] = True

    # 现代侧边栏头部 - 紧凑多彩版
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #10B981 0%, #3B82F6 100%);
        color: white;
        padding: 0.85rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        text-align: center;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
        position: relative;
        overflow: hidden;
    ">
        <div style="
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 100%;
            background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.15) 50%, transparent 70%);
            animation: shine 2.5s infinite;
        "></div>
        <h3 style="margin: 0; font-size: 1.1rem; font-weight: 700; letter-spacing: 0.5px; position: relative; z-index: 1;">
            ⚙️ 模拟控制台
        </h3>
        <p style="margin: 0.2rem 0 0 0; font-size: 0.75rem; opacity: 0.95; position: relative; z-index: 1;">
            配置参数并运行模拟
        </p>
    </div>

    <style>
        @keyframes shine {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            50% { transform: scale(1.02); box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
        }
    </style>
    """, unsafe_allow_html=True)

    # ========== 醒目的开始模拟按钮 ==========
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%);
        border: 3px solid #10B981;
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        text-align: center;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.3);
    ">
        <div style="
            color: #065F46;
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        ">
            🚀 <span>开始模拟</span>
        </div>
        <div style="
            color: #047857;
            font-size: 0.7rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
        ">
            配置好参数后，点击下方按钮运行模拟
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 检查是否可以运行模拟
    selected_varieties = st.session_state.get('selected_varieties', [])
    can_run = len(selected_varieties) > 0

    # 大型开始按钮
    if can_run:
        if st.button(
            """🎯 开始运行模拟""",
            type="primary",
            use_container_width=True,
            help="点击开始运行多品种耦合模拟"
        ):
            st.session_state['run_simulation'] = True
            st.rerun()
    else:
        st.markdown("""
        <div style="
            background: #F3F4F6;
            color: #9CA3AF;
            padding: 0.85rem;
            border-radius: 8px;
            text-align: center;
            font-weight: 600;
            border: 2px dashed #D1D5DB;
        ">
            🔒 请先选择品种
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 选择品种 - 增强版
    try:
        varieties = cultivar_df['PZ'].tolist()

        # 智能品种选择卡片 - 紧凑多彩版
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%);
            border: 2px solid #10B981;
            padding: 0.75rem;
            margin-bottom: 0.75rem;
            border-radius: 10px;
        ">
            <h4 style="
                color: #065F46;
                margin: 0 0 0.35rem 0;
                font-size: 0.95rem;
                font-weight: 700;
                display: flex;
                align-items: center;
                gap: 0.4rem;
            ">
                🌱 <span>品种选择</span>
            </h4>
            <p style="
                color: #047857;
                margin: 0;
                font-size: 0.75rem;
                font-weight: 500;
                opacity: 0.9;
            ">
                选择2-5个品种进行对比分析
            </p>
        </div>
        """, unsafe_allow_html=True)

        selected_varieties = st.multiselect(
            "选择品种",
            varieties,
            default=st.session_state.get('selected_varieties', []),
            help="💡 提示：选择2-5个品种可获得最佳对比效果"
        )

        # 实时验证和反馈
        if selected_varieties:
            variety_count = len(selected_varieties)

            # 智能反馈颜色和图标
            if variety_count <= 5:
                bg_color = "#D1FAE5"
                text_color = "#065F46"
                icon = "✅"
                message = f"已选择 {variety_count} 个品种 - 完美！"
            elif variety_count <= 8:
                bg_color = "#FEF3C7"
                text_color = "#92400E"
                icon = "⚠️"
                message = f"已选择 {variety_count} 个品种 - 可能影响性能"
            else:
                bg_color = "#FEE2E2"
                text_color = "#991B1B"
                icon = "❌"
                message = f"已选择 {variety_count} 个品种 - 建议减少选择"

            st.markdown(f"""
            <div style="
                background: {bg_color};
                padding: 0.5rem 0.75rem;
                border-radius: 6px;
                margin-top: 0.4rem;
                border-left: 3px solid {text_color};
                animation: fadeInUp 0.3s ease-out;
            ">
                <p style="color: {text_color}; margin: 0; font-size: 0.8rem; font-weight: 600; display: flex; align-items: center; gap: 0.4rem;">
                    <span style="font-size: 1rem;">{icon}</span>
                    <span>{message}</span>
                </p>
            </div>
            """, unsafe_allow_html=True)

            # 品种详情预览 - 紧凑版
            if variety_count > 0:
                with st.expander(f"📋 查看已选品种详情 ({variety_count})", expanded=False):
                    for variety in selected_varieties:
                        variety_data = cultivar_df[cultivar_df['PZ'] == variety].iloc[PANDAS_ILON_FIRST_ROW]
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(248,250,252,0.9) 100%);
                            padding: 0.5rem;
                            border-radius: 6px;
                            margin-bottom: 0.4rem;
                            border-left: 3px solid #10B981;
                            border-right: 1px solid rgba(16,185,129,0.2);
                            border-top: 1px solid rgba(16,185,129,0.2);
                            border-bottom: 1px solid rgba(16,185,129,0.2);
                        ">
                            <strong style="color: #064E3B;">{variety}</strong>
                            <div style="font-size: 0.7rem; color: #64748B; margin-top: 0.2rem;">
                                生育期: {variety_data.get('PS', 'N/A')}天 |
                                理论产量: {variety_data.get('PF', 'N/A')}kg/ha
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

        # 保存到session state
        st.session_state['selected_varieties'] = selected_varieties

    except Exception as e:
        st.error(f"❌ 读取品种参数文件失败: {e}")
        st.info("💡 请检查 '品种参数.csv' 文件是否存在且格式正确")
        st.session_state['selected_varieties'] = []

    # 自定义品种参数输入
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%);
        border: 2px solid #22C55E;
        padding: 0.6rem;
        margin-top: 0.75rem;
        margin-bottom: 0.5rem;
        border-radius: 8px;
    ">
        <h5 style="
            color: #166534;
            margin: 0 0 0.15rem 0;
            font-size: 0.8rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.3rem;
        ">
            ✏️ <span>自定义品种参数</span>
        </h5>
        <p style="
            color: #15803D;
            margin: 0;
            font-size: 0.65rem;
            font-weight: 500;
        ">
            手动添加新品种或修改现有品种参数
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🌿 添加/编辑品种参数", expanded=False):
        # 品种名称输入
        custom_variety_name = st.text_input(
            "品种名称 (必填)",
            placeholder="例如: 扬稻6号",
            help="输入品种的名称或代号"
        )

        # 品种参数分组显示
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            <div style="
                background: #FEF3C7;
                padding: 0.3rem;
                border-radius: 4px;
                margin-bottom: 0.3rem;
                border-left: 2px solid #F59E0B;
            ">
                <span style="color: #92400E; font-size: 0.65rem; font-weight: 700;">
                    📐 生育期参数
                </span>
            </div>
            """, unsafe_allow_html=True)

            ps = st.number_input(
                "感光性 PS",
                min_value=0.0,
                max_value=0.2,
                value=0.06,
                step=0.001,
                format="%.4f",
                help="品种的光敏感性，范围0-0.2"
            )

            ts = st.number_input(
                "感温性 TS",
                min_value=2.0,
                max_value=4.0,
                value=2.7,
                step=0.01,
                format="%.3f",
                help="品种的温度敏感性，范围2-4"
            )

            to_val = st.number_input(
                "最适温度 TO (°C)",
                min_value=20.0,
                max_value=35.0,
                value=27.0,
                step=0.1,
                format="%.2f",
                help="品种生长的最适温度"
            )

            ie = st.number_input(
                "基本早熟性 IE",
                min_value=0.0,
                max_value=0.3,
                value=0.16,
                step=0.001,
                format="%.3f",
                help="品种的基本早熟性指数"
            )

            hf = st.number_input(
                "灌浆因子 HF",
                min_value=0.0,
                max_value=0.05,
                value=0.012,
                step=0.0001,
                format="%.4f",
                help="灌浆速率因子"
            )

            fdf = st.number_input(
                "灌浆持续期 FDF",
                min_value=0.5,
                max_value=1.0,
                value=0.72,
                step=0.001,
                format="%.3f",
                help="灌浆持续时间因子"
            )

        with col2:
            st.markdown("""
            <div style="
                background: #DBEAFE;
                padding: 0.3rem;
                border-radius: 4px;
                margin-bottom: 0.3rem;
                border-left: 2px solid #3B82F6;
            ">
                <span style="color: #1E40AF; font-size: 0.65rem; font-weight: 700;">
                    🎯 产量与效率参数
                </span>
            </div>
            """, unsafe_allow_html=True)

            phi = st.number_input(
                "收获指数 PHI",
                min_value=0.3,
                max_value=0.6,
                value=0.45,
                step=0.001,
                format="%.3f",
                help="经济系数（收获指数），范围0.3-0.6"
            )

            slac = st.number_input(
                "比叶面积 SLAc (cm²/g)",
                min_value=150,
                max_value=250,
                value=200,
                step=1,
                help="比叶面积，影响光合作用"
            )

            pf = st.number_input(
                "光合转化效率 PF",
                min_value=0.01,
                max_value=0.02,
                value=0.015,
                step=0.0001,
                format="%.4f",
                help="光合作用转化为生物量的效率"
            )

            amx = st.number_input(
                "最大光合速率 AMX",
                min_value=30.0,
                max_value=60.0,
                value=45.0,
                step=0.5,
                help="最大光合速率"
            )

            kf = st.number_input(
                "消光系数因子 KF",
                min_value=0.005,
                max_value=0.015,
                value=0.0085,
                step=0.0001,
                format="%.4f",
                help="冠层消光系数"
            )

            tgw = st.number_input(
                "千粒重 TGW (g)",
                min_value=20.0,
                max_value=35.0,
                value=27.0,
                step=0.1,
                format="%.1f",
                help="千粒重"
            )

        # 高级参数（分隔显示）
        st.markdown("---")
        st.markdown("""
        <div style="
            background: #F3E8FF;
            padding: 0.4rem;
            border-radius: 6px;
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
            border-left: 3px solid #9333EA;
        ">
            <span style="color: #6B21A8; font-size: 0.75rem; font-weight: 700;">
                🔬 高级遗传参数（可选）
            </span>
        </div>
        """, unsafe_allow_html=True)

        col3, col4 = st.columns(2)

        with col3:
            rgc = st.number_input(
                "单位根长N潜在吸收速率 RGC",
                min_value=0.2,
                max_value=0.4,
                value=0.3,
                step=0.01,
                format="%.3f"
            )

            lrs = st.number_input(
                "单位籽粒潜在累积速率 LRS",
                min_value=0.005,
                max_value=0.01,
                value=0.007,
                step=0.0001,
                format="%.4f"
            )

            tln = st.number_input(
                "总叶龄 TLN",
                min_value=12.0,
                max_value=20.0,
                value=17.5,
                step=0.1,
                format="%.1f"
            )

            ein = st.number_input(
                "伸长节间数 EIN",
                min_value=4.0,
                max_value=7.0,
                value=5.0,
                step=0.1
            )

            ta = st.number_input(
                "温度敏感性参数 TA",
                min_value=6.0,
                max_value=7.0,
                value=6.5,
                step=0.1
            )

        with col4:
            sgp = st.number_input(
                "籽粒蛋白质含量 SGP (%)",
                min_value=0.4,
                max_value=0.6,
                value=0.5,
                step=0.01
            )

            pc = st.number_input(
                "籽粒蛋白质含量 PC",
                min_value=0.07,
                max_value=0.09,
                value=0.08,
                step=0.001,
                format="%.3f"
            )

            rar = st.number_input(
                "RAR参数",
                min_value=1.8,
                max_value=2.5,
                value=2.1,
                step=0.01
            )

        # 保存自定义品种按钮
        col_save1, col_save2, col_save3 = st.columns([2, 2, 1])
        with col_save1:
            save_custom_variety = st.button(
                "💾 保存自定义品种",
                use_container_width=True,
                type="primary"
            )

        with col_save2:
            clear_custom_varieties = st.button(
                "🗑️ 清除自定义品种",
                use_container_width=True
            )

        # 处理保存自定义品种
        if save_custom_variety:
            if not custom_variety_name:
                st.warning("⚠️ 请输入品种名称")
            else:
                # 构建品种参数字典
                custom_variety_params = {
                    'PZ': custom_variety_name,
                    'PS': ps,
                    'TS': ts,
                    'TO': to_val,
                    'IE': ie,
                    'HF': hf,
                    'FDF': fdf,
                    'PHI': phi,
                    'SLAc': slac,
                    'PF': pf,
                    'AMX': amx,
                    'KF': kf,
                    'TGW': tgw,
                    'RGC': rgc,
                    'LRS': lrs,
                    'TLN': tln,
                    'EIN': ein,
                    'TA': ta,
                    'SGP': sgp,
                    'PC': pc,
                    'RAR': rar
                }

                # 保存到session state
                if 'custom_varieties' not in st.session_state:
                    st.session_state['custom_varieties'] = {}

                st.session_state['custom_varieties'][custom_variety_name] = custom_variety_params
                st.success(f"✅ 成功添加品种: {custom_variety_name}")
                st.rerun()

        # 处理清除自定义品种
        if clear_custom_varieties:
            if 'custom_varieties' in st.session_state:
                st.session_state['custom_varieties'] = {}
                st.success("🗑️ 已清除所有自定义品种")
                st.rerun()

        # 显示已保存的自定义品种
        if 'custom_varieties' in st.session_state and st.session_state['custom_varieties']:
            st.markdown("""
            <div style="
                background: #F0FDFA;
                padding: 0.4rem;
                border-radius: 6px;
                margin-top: 0.5rem;
                border-left: 3px solid #14B8A6;
            ">
                <span style="color: #0F766E; font-size: 0.7rem; font-weight: 700;">
                    📋 已保存的自定义品种:
                </span>
            </div>
            """, unsafe_allow_html=True)

            for var_name, var_params in st.session_state['custom_varieties'].items():
                with st.expander(f"🌾 {var_name}", expanded=False):
                    col_show1, col_show2 = st.columns(2)
                    with col_show1:
                        st.write(f"**感光性 PS:** {var_params['PS']:.4f}")
                        st.write(f"**感温性 TS:** {var_params['TS']:.3f}")
                        st.write(f"**最适温度 TO:** {var_params['TO']:.2f} °C")
                        st.write(f"**收获指数 PHI:** {var_params['PHI']:.3f}")
                        st.write(f"**千粒重 TGW:** {var_params['TGW']:.1f} g")
                    with col_show2:
                        st.write(f"**比叶面积 SLAc:** {var_params['SLAc']:.0f} cm²/g")
                        st.write(f"**光合效率 PF:** {var_params['PF']:.4f}")
                        st.write(f"**最大光合 AMX:** {var_params['AMX']:.1f}")
                        st.write(f"**总叶龄 TLN:** {var_params['TLN']:.1f}")

                    # 删除单个品种按钮
                    if st.button(f"🗑️ 删除 {var_name}", key=f"delete_{var_name}"):
                        del st.session_state['custom_varieties'][var_name]
                        st.rerun()

    # 管理参数设置 - 紧凑多彩版
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%);
        border: 2px solid #F59E0B;
        padding: 0.75rem;
        margin-top: 0.75rem;
        margin-bottom: 0.75rem;
        border-radius: 10px;
    ">
        <h4 style="
            color: #92400E;
            margin: 0 0 0.2rem 0;
            font-size: 0.95rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        ">
            💧 <span>管理参数配置</span>
        </h4>
        <p style="
            color: #B45309;
            margin: 0;
            font-size: 0.7rem;
            font-weight: 500;
            opacity: 0.9;
        ">
            配置水分管理和土壤参数
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 水分管理方式 - 紧凑版
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%);
        padding: 0.5rem;
        border-radius: 6px;
        margin-bottom: 0.6rem;
        border-left: 3px solid #3B82F6;
    ">
        <h5 style="color: #1E40AF; margin: 0 0 0.2rem 0; font-size: 0.8rem; font-weight: 700;">
            💧 水分管理方式
        </h5>
        <p style="color: #1E3A8A; margin: 0; font-size: 0.65rem; font-weight: 500;">
            选择灌溉模式以预测CH4排放
        </p>
    </div>
    """, unsafe_allow_html=True)

    water_regime_options = {
        "🌊 模式1 - 常规淹水灌溉": {"value": 1, "ch4_impact": "高", "efficiency": "低"},
        "🔄 模式2 - 间歇灌溉": {"value": 2, "ch4_impact": "中高", "efficiency": "中"},
        "💧 模式3 - 湿润灌溉": {"value": 3, "ch4_impact": "中低", "efficiency": "中高"},
        "🎛️ 模式4 - 控制灌溉": {"value": 4, "ch4_impact": "中", "efficiency": "高"},
        "⚖️ 模式5 - 干湿交替": {"value": 5, "ch4_impact": "最低", "efficiency": "最高"}
    }

    # 使用增强的radio选择
    selected_water_mode = st.radio(
        "选择灌溉模式",
        options=list(water_regime_options.keys()),
        index=st.session_state.get('water_mode_index', 0),
        help="不同模式对CH4排放和水资源利用效率有显著影响",
        label_visibility="collapsed"
    )

    water_regime = water_regime_options[selected_water_mode]["value"]
    ch4_impact = water_regime_options[selected_water_mode]["ch4_impact"]
    efficiency = water_regime_options[selected_water_mode]["efficiency"]

    # 保存到session state
    st.session_state['water_regime'] = water_regime
    st.session_state['water_mode_index'] = list(water_regime_options.keys()).index(selected_water_mode)

    # 水模式描述和实时反馈
    water_descriptions = {
        "🌊 模式1 - 常规淹水灌溉": "持续淹水环境，产甲烷菌活跃，CH4排放较高，但管理简单。",
        "🔄 模式2 - 间歇灌溉": "周期性排水和复水，有效降低CH4排放，需精细管理。",
        "💧 模式3 - 湿润灌溉": "保持土壤湿润但不淹水，CH4排放较低，节水效果好。",
        "🎛️ 模式4 - 控制灌溉": "关键生育期保持水层，平衡产量和排放。",
        "⚖️ 模式5 - 干湿交替": "频繁干湿交替，最大程度抑制CH4生成，节水显著。"
    }

    # 实时反馈卡片 - 紧凑版
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        border: 2px solid #3B82F6;
        padding: 0.75rem;
        margin-top: 0.4rem;
        margin-bottom: 0.75rem;
        border-radius: 10px;
    ">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
            <div style="background: white; padding: 0.5rem; border-radius: 6px; border-left: 3px solid #EF4444;">
                <div style="font-size: 0.65rem; color: #6B7280; font-weight: 600;">CH4排放影响</div>
                <div style="font-size: 0.85rem; color: #DC2626; font-weight: 700; margin-top: 0.1rem;">{ch4_impact}</div>
            </div>
            <div style="background: white; padding: 0.5rem; border-radius: 6px; border-left: 3px solid #10B981;">
                <div style="font-size: 0.65rem; color: #6B7280; font-weight: 600;">水分效率</div>
                <div style="font-size: 0.85rem; color: #059669; font-weight: 700; margin-top: 0.1rem;">{efficiency}</div>
            </div>
        </div>
        <div style="
            background: white;
            padding: 0.5rem;
            border-radius: 6px;
            margin-top: 0.5rem;
            font-size: 0.7rem;
            color: #1E3A8A;
            line-height: 1.3;
        ">
            💡 <strong>说明：</strong>{water_descriptions[selected_water_mode]}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 土壤参数 - 紧凑版
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #E0E7FF 0%, #C7D2FE 100%);
        border: 2px solid #6366F1;
        padding: 0.75rem;
        margin-top: 0.75rem;
        margin-bottom: 0.75rem;
        border-radius: 10px;
    ">
        <h5 style="
            color: #3730A3;
            margin: 0 0 0.2rem 0;
            font-size: 0.85rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        ">
            🌍 <span>土壤参数配置</span>
        </h5>
        <p style="
            color: #4338CA;
            margin: 0;
            font-size: 0.65rem;
            font-weight: 500;
            opacity: 0.9;
        ">
            土壤质地和有机质输入
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        soil_options = {
            "黏土": 20,
            "壤土": 35,
            "砂壤土": 55,
            "砂土": 70
        }

        selected_soil = st.selectbox(
            "土壤类型",
            options=list(soil_options.keys()),
            index=st.session_state.get('soil_index', 1),
            help="土壤质地影响CH4排放通量"
        )

        sand_value = soil_options[selected_soil]

        # 保存到session state
        st.session_state['sand_value'] = sand_value
        st.session_state['soil_index'] = list(soil_options.keys()).index(selected_soil)

        # 土壤类型可视化
        soil_colors = {
            "黏土": "#1F2937",
            "壤土": "#6B7280",
            "砂壤土": "#9CA3AF",
            "砂土": "#D1D5DB"
        }

        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, white 0%, #F9FAFB 100%);
            padding: 0.6rem;
            margin-top: 0.4rem;
            border: 2px solid {soil_colors[selected_soil]};
            border-radius: 8px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.65rem; color: #6B7280; font-weight: 600;">砂含量</div>
                    <div style="font-size: 1.1rem; color: {soil_colors[selected_soil]}; font-weight: 700;">{sand_value}%</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.65rem; color: #6B7280; font-weight: 600;">土壤类型</div>
                    <div style="font-size: 0.85rem; color: #1F2937; font-weight: 600;">{selected_soil}</div>
                </div>
            </div>
            <div style="
                width: 100%;
                height: 5px;
                background: #E5E7EB;
                border-radius: 3px;
                margin-top: 0.4rem;
                overflow: hidden;
            ">
                <div style="
                    width: {sand_value}%;
                    height: 100%;
                    background: {soil_colors[selected_soil]};
                    transition: width 0.3s ease;
                "></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # 外源有机质输入 - 紧凑版
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%);
            padding: 0.4rem;
            border-radius: 6px;
            margin-bottom: 0.4rem;
            border-left: 3px solid #DC2626;
        ">
            <h5 style="color: #991B1B; margin: 0; font-size: 0.7rem; font-weight: 700;">
                🌿 外源有机质 (kg/ha)
            </h5>
        </div>
        """, unsafe_allow_html=True)

        # 使用滑块增强交互体验
        oms = st.slider(
            "难分解组分 OMS",
            min_value=500,
            max_value=3000,
            value=st.session_state.get('oms', 1300),
            step=50,
            help="难分解有机质，降解缓慢，长期影响CH4排放"
        )

        omn = st.slider(
            "易分解组分 OMN",
            min_value=500,
            max_value=3000,
            value=st.session_state.get('omn', 1600),
            step=50,
            help="易分解有机质，快速降解，短期高CH4排放"
        )

        # 保存到session state
        st.session_state['oms'] = oms
        st.session_state['omn'] = omn

        # 实时计算总有机质
        total_om = oms + omn
        om_ratio = omn / total_om if total_om > 0 else 0

        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #FEF3F2 0%, #FEE2E2 100%);
            padding: 0.5rem;
            border-radius: 6px;
            margin-top: 0.4rem;
            border: 1px solid #FCA5A5;
        ">
            <div style="display: flex; justify-content: space-between; font-size: 0.7rem; margin-bottom: 0.2rem;">
                <span style="color: #991B1B; font-weight: 600;">总有机质:</span>
                <span style="color: #7F1D1D; font-weight: 700;">{total_om:,} kg/ha</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.65rem;">
                <span style="color: #DC2626;">易分解比例: {om_ratio:.1%}</span>
                <span style="color: #991B1B;">难分解: {1-om_ratio:.1%}</span>
            </div>
            <div style="
                width: 100%;
                height: 4px;
                background: #FEE2E2;
                border-radius: 2px;
                margin-top: 0.25rem;
                overflow: hidden;
                display: flex;
            ">
                <div style="width: {om_ratio*100}%; background: #EF4444; height: 100%;"></div>
                <div style="width: {(1-om_ratio)*100}%; background: #DC2626; height: 100%;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 土壤信息展示区域
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%);
        border: 2px solid #0EA5E9;
        padding: 0.6rem;
        margin-top: 0.75rem;
        margin-bottom: 0.5rem;
        border-radius: 8px;
    ">
        <h5 style="
            color: #0369A1;
            margin: 0 0 0.15rem 0;
            font-size: 0.75rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.3rem;
        ">
            📊 <span>土壤环境与CH4排放预测</span>
        </h5>
        <p style="
            color: #075985;
            margin: 0;
            font-size: 0.6rem;
            font-weight: 500;
        ">
            基于当前参数的排放趋势分析
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 计算CH4排放等级
    def calculate_ch4_level(sand, om_total, om_easy_ratio, water_mode):
        """计算CH4排放等级"""
        # 砂含量越高，CH4排放越低
        sand_factor = (100 - sand) / 100
        # 有机质总量越高，CH4排放越高
        om_factor = min(om_total / 4000, 1.5)
        # 易分解比例越高，短期排放越高
        easy_ratio_factor = 0.5 + om_easy_ratio
        # 水分管理模式影响
        water_factors = {1: 1.0, 2: 0.85, 3: 0.65, 4: 0.75, 5: 0.5}
        water_factor = water_factors.get(water_mode, 0.75)

        ch4_index = sand_factor * om_factor * easy_ratio_factor * water_factor

        if ch4_index > 0.9:
            return "极高", "#DC2626", "🔴"
        elif ch4_index > 0.7:
            return "高", "#EA580C", "🟠"
        elif ch4_index > 0.5:
            return "中等", "#CA8A04", "🟡"
        elif ch4_index > 0.3:
            return "较低", "#16A34A", "🟢"
        else:
            return "低", "#15803D", "🌱"

    # 获取当前水分模式
    water_mode_display = {
        1: "淹水灌溉",
        2: "间歇灌溉",
        3: "湿润灌溉",
        4: "控制灌溉",
        5: "干湿交替"
    }

    # 计算排放等级
    ch4_level, ch4_color, ch4_icon = calculate_ch4_level(
        sand_value, total_om, om_ratio, water_regime
    )

    # 显示土壤环境信息卡片
    col_info1, col_info2 = st.columns(2)

    with col_info1:
        st.markdown(f"""
        <div style="
            background: white;
            padding: 0.5rem;
            border-radius: 6px;
            border: 1px solid #E5E7EB;
            height: 100%;
        ">
            <div style="font-size: 0.6rem; color: #6B7280; font-weight: 600; margin-bottom: 0.25rem;">
                🏝️ 当前土壤环境
            </div>
            <div style="font-size: 0.65rem; color: #374151; line-height: 1.6;">
                <div style="display: flex; justify-content: space-between;">
                    <span>土壤类型:</span>
                    <span style="font-weight: 700; color: #1F2937;">{selected_soil}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span>砂含量:</span>
                    <span style="font-weight: 700; color: {soil_colors[selected_soil]};">{sand_value}%</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span>灌溉模式:</span>
                    <span style="font-weight: 700; color: #0369A1;">{water_mode_display.get(water_regime, '未知')}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_info2:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {ch4_color}15 0%, {ch4_color}08 100%);
            padding: 0.5rem;
            border-radius: 6px;
            border: 2px solid {ch4_color};
            height: 100%;
        ">
            <div style="font-size: 0.6rem; color: {ch4_color}; font-weight: 600; margin-bottom: 0.25rem;">
                💨 CH4排放预测
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-top: 0.25rem;">
                <span style="font-size: 1.5rem;">{ch4_icon}</span>
                <div>
                    <div style="font-size: 0.85rem; color: {ch4_color}; font-weight: 800;">
                        {ch4_level}排放
                    </div>
                    <div style="font-size: 0.55rem; color: #6B7280;">
                        基于当前配置估算
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 土壤参数说明
    with st.expander("📖 土壤参数说明", expanded=False):
        st.markdown("""
        <div style="
            background: #F8FAFC;
            padding: 0.5rem;
            border-radius: 6px;
            font-size: 0.7rem;
            color: #475569;
            line-height: 1.8;
        ">
            <div style="margin-bottom: 0.5rem;">
                <strong style="color: #1E40AF;">🏝️ 土壤类型与砂含量:</strong><br>
                <span style="color: #475569;">• 黏土(20%砂): 保水性强，透气性差，CH4排放最高</span><br>
                <span style="color: #475569;">• 壤土(35%砂): 保水透气平衡，CH4排放中高</span><br>
                <span style="color: #475569;">• 砂壤土(55%砂): 透气性较好，CH4排放中等</span><br>
                <span style="color: #475569;">• 砂土(70%砂): 透气性强，CH4排放较低</span>
            </div>
            <div style="margin-bottom: 0.5rem;">
                <strong style="color: #DC2626;">🌿 有机质输入:</strong><br>
                <span style="color: #475569;">• OMS(难分解): 稻草、秸秆等，降解缓慢，长期CH4源</span><br>
                <span style="color: #475569;">• OMN(易分解): 绿肥、农家肥等，快速降解，短期高峰</span>
            </div>
            <div>
                <strong style="color: #0369A1;">💧 水分管理影响:</strong><br>
                <span style="color: #475569;">• 淹水状态: 产甲烷菌活跃，CH4排放大幅增加</span><br>
                <span style="color: #475569;">• 干湿交替: 抑制产甲烷菌，CH4排放显著降低</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 自定义文件上传功能
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%);
        border: 2px solid #3B82F6;
        padding: 0.75rem;
        margin-top: 1rem;
        margin-bottom: 0.75rem;
        border-radius: 10px;
    ">
        <h4 style="
            color: #1E40AF;
            margin: 0 0 0.2rem 0;
            font-size: 0.9rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        ">
            📁 <span>自定义数据上传</span>
        </h4>
        <p style="
            color: #1E3A8A;
            margin: 0;
            font-size: 0.65rem;
            font-weight: 500;
            opacity: 0.9;
        ">
            上传自定义文件替代默认数据（可选）
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 文件上传区域
    with st.expander("📂 上传自定义数据文件", expanded=False):
        st.markdown("""
        <div style="
            background: #F8FAFC;
            padding: 0.5rem;
            border-radius: 6px;
            margin-bottom: 0.5rem;
            font-size: 0.75rem;
            color: #475569;
        ">
            <strong>💡 提示：</strong>上传文件后将自动替换对应的默认数据文件
        </div>
        """, unsafe_allow_html=True)

        # 上传各种数据文件
        uploaded_cultivar = st.file_uploader(
            "🌾 品种参数 (CultivarData.csv)",
            type=['csv'],
            help="上传品种参数CSV文件，包含品种遗传参数（PS, TS, PHI等）",
            key="cultivar_upload"
        )

        uploaded_fertilizer = st.file_uploader(
            "🧪 施肥数据 (FertilizerData.csv)",
            type=['csv'],
            help="上传施肥数据CSV文件",
            key="fertilizer_upload"
        )

        uploaded_irrigation = st.file_uploader(
            "💧 灌溉管理数据 (IrrigationData.csv)",
            type=['csv'],
            help="上传灌溉管理数据CSV文件",
            key="irrigation_upload"
        )

        uploaded_soil = st.file_uploader(
            "🏜️ 土壤数据 (SoilData.csv)",
            type=['csv'],
            help="上传土壤数据CSV文件",
            key="soil_upload"
        )

        uploaded_weather = st.file_uploader(
            "🌤️ 气象数据 (WeatherData.csv)",
            type=['csv'],
            help="上传气象数据CSV文件",
            key="weather_upload"
        )

        uploaded_residue = st.file_uploader(
            "🌾 秸秆数据 (ResidueData.csv)",
            type=['csv'],
            help="上传秸秆数据CSV文件",
            key="residue_upload"
        )

        uploaded_management = st.file_uploader(
            "📋 管理数据 (ManagementData.csv)",
            type=['csv'],
            help="上传管理数据CSV文件",
            key="management_upload"
        )

        # 处理上传的文件
        import tempfile
        import shutil

        uploaded_files = {
            '品种参数.csv': uploaded_cultivar,
            '施肥数据.csv': uploaded_fertilizer,
            '灌溉数据.csv': uploaded_irrigation,
            '土壤数据.csv': uploaded_soil,
            '气象数据.csv': uploaded_weather,
            '秸秆数据.csv': uploaded_residue,
            '管理数据_多种方案.csv': uploaded_management
        }

        # 创建上传文件目录
        upload_dir = str(UPLOADS_DIR)
        if not Path(upload_dir).exists():
            Path(upload_dir).mkdir(parents=True, exist_ok=True)

        # 保存上传的文件
        saved_files = []
        for filename, uploaded_file in uploaded_files.items():
            if uploaded_file is not None:
                try:
                    # 尝试多种编码读取文件
                    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1', 'iso-8859-1', 'cp1252']
                    full_df = None
                    used_encoding = None
                    errors = []

                    for encoding in encodings:
                        try:
                            # 直接读取完整文件
                            full_df = pd.read_csv(uploaded_file, encoding=encoding)
                            used_encoding = encoding
                            break
                        except (UnicodeDecodeError, UnicodeError) as e:
                            errors.append(f"{encoding}: {str(e)[:30]}")
                            continue
                        except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
                            errors.append(f"{encoding}: 解析错误 - {str(e)[:30]}")
                            continue
                        except Exception as e:
                            errors.append(f"{encoding}: {str(e)[:30]}")
                            # 如果是解析错误但不是编码问题，说明编码可能对了但文件格式有问题
                            if 'codec' not in str(e).lower() and 'parse' in str(e).lower():
                                # 尝试用当前编码继续，可能是数据格式问题
                                try:
                                    full_df = pd.read_csv(uploaded_file, encoding=encoding, on_bad_lines='skip')
                                    used_encoding = encoding
                                    break
                                except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
                                    # 跳过这个编码，继续尝试下一个
                                    pass
                            continue

                    if full_df is not None:
                        # 保存为GBK编码（模拟函数要求的格式）
                        file_path = str(Path(upload_dir) / filename)
                        full_df.to_csv(file_path, index=False, encoding='gbk')
                        saved_files.append(filename)

                        st.markdown(f"""
                        <div style="
                            background: #ECFDF5;
                            padding: 0.5rem;
                            border-radius: 6px;
                            margin-top: 0.5rem;
                            border-left: 3px solid #10B981;
                        ">
                            <div style="font-size: 0.7rem; color: #065F46; font-weight: 600;">
                                ✅ {filename} 上传成功
                            </div>
                            <div style="font-size: 0.65rem; color: #047857; margin-top: 0.2rem;">
                                形状: {full_df.shape} | 列: {', '.join(full_df.columns.tolist()[:3])}{'...' if len(full_df.columns) > 3 else ''} | 原编码: {used_encoding.upper()} → 已转换为GBK
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        # 保存使用的编码到session state
                        st.session_state[f'custom_{filename.replace(".", "_")}_encoding'] = used_encoding
                        st.session_state[f'custom_{filename.replace(".", "_")}'] = file_path
                    else:
                        st.error(f"❌ 无法识别 {filename} 的文件编码")
                        st.info(f"💡 尝试的编码: {', '.join(encodings)}")
                        with st.expander("🔍 查看详细错误信息"):
                            for err in errors[:3]:
                                st.text(f"  • {err}")

                except pd.errors.EmptyDataError:
                    st.error(f"❌ 文件 {filename} 为空或格式不正确")
                except Exception as e:
                    st.error(f"❌ 处理文件 {filename} 时出错: {str(e)}")

        if saved_files:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%);
                padding: 0.6rem;
                border-radius: 6px;
                margin-top: 0.5rem;
                border-left: 3px solid #10B981;
            ">
                <div style="font-size: 0.75rem; color: #065F46; font-weight: 600;">
                    🎉 成功上传 {len(saved_files)} 个文件，将在下次模拟时使用
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 模板展示区域 - 移到上传expander外面
    st.markdown("---")
    with st.expander("📖 查看数据文件模板格式", expanded=False):
        st.markdown("""
        <div style="
            background: #EFF6FF;
            padding: 0.6rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            border-left: 4px solid #3B82F6;
        ">
            <div style="font-size: 0.8rem; color: #1E40AF; font-weight: 600; margin-bottom: 0.3rem;">
                📋 数据文件格式参考
            </div>
            <div style="font-size: 0.7rem; color: #1E3A8A; line-height: 1.5;">
                以下是系统要求的标准 CSV 文件格式。您的文件应包含相同的列名和数据类型。
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 定义模板数据
        template_data = {
                "品种参数.csv": {
                    "icon": "🌾",
                    "desc": "品种遗传参数（每个品种一行）",
                    "columns": ["PZ", "PS", "TS", "TO", "IE", "HF", "FDF", "PHI", "SLAc", "PF", "AMX", "KF", "TGW", "RGC", "LRS", "TLN", "EIN", "TA", "SGP", "PC", "RAR"],
                    "example": [
                        ["扬稻6号", "0.0613", "2.687", "28.19", "0.157", "0.01", "0.713", "0.45", "200", "0.015", "45", "0.0087", "27", "0.3", "0.0067", "17.5", "5", "6.5", "0.5", "0.0784", "2"],
                        ["两优培九", "0.0718", "2.709", "27.05", "0.177", "0.014", "0.727", "0.468", "207", "0.0161", "46", "0.0084", "27.5", "0.3", "0.0069", "18.3", "4.9", "6.5", "0.46", "0.0885", "2.05"]
                    ],
                    "notes": [
                        "PZ: 品种代号/名称",
                        "PS: 感光性，范围0-0.2，值越大对光照越敏感",
                        "TS: 感温性，范围2-4，值越大对温度越敏感",
                        "TO: 品种最适温度(°C)，通常25-30",
                        "IE: 基本早熟性，范围0-0.3，影响生育期长短",
                        "HF: 灌浆因子，影响灌浆速率",
                        "FDF: 灌浆持续期因子，范围0.5-1.0",
                        "PHI: 收获指数，范围0.3-0.6，经济产量占比",
                        "SLAc: 比叶面积(cm²/g)，通常180-220",
                        "PF: 光合转化效率，影响干物质积累",
                        "AMX: 最大光合速率，范围35-55",
                        "KF: 消光系数因子，影响光截获",
                        "TGW: 千粒重，范围22-32",
                        "RGC: 单位根长N潜在吸收速率",
                        "LRS: 单位籽粒潜在累积速率",
                        "TLN: 总叶龄，范围14-20",
                        "EIN: 伸长节间数，范围4-7",
                        "TA: 温度敏感性参数",
                        "SGP: 籽粒蛋白质含量参数",
                        "PC: 蛋白质含量参数",
                        "RAR: RAR参数"
                    ]
                },
                "气象数据.csv": {
                    "icon": "🌤️",
                    "desc": "逐日气象数据（必须包含365行，代表全年）",
                    "columns": ["Stationno", "Jour", "Tmax", "Tmin", "RAIN", "SRAD", "CO2"],
                    "example": [
                        ["1", "1990/1/1", "12.3", "2.8", "0.0", "7.3", "486"],
                        ["1", "1990/1/2", "9.1", "-0.1", "0.0", "11.3", "486"],
                        ["1", "1990/1/3", "6.0", "1.3", "0.0", "13.4", "486"]
                    ],
                    "notes": [
                        "Stationno: 站点编号（数字）",
                        "Jour: 日期，格式为 YYYY/M/D 或 YYYY/M/D",
                        "Tmax: 日最高温度(°C)",
                        "Tmin: 日最低温度(°C)",
                        "RAIN: 日降水量(mm)",
                        "SRAD: 太阳辐射(MJ/m²)",
                        "CO2: CO2浓度(ppm)，通常为350-500"
                    ]
                },
                "土壤数据.csv": {
                    "icon": "🏜️",
                    "desc": "土壤理化性质（支持多层土壤，每层一行）",
                    "columns": ["pH", "depth", "thickness", "bulkWeight", "clayParticle", "actualWater", "fieldCapacity", "wiltingPoint", "fieldSaturation", "organicMatter", "totaNitrogen", "nitrateNitrogen", "ammoniaNitrogen", "fastAvailablePhosphorus", "totalPhosphorus", "fastAvailableK", "slowAvailableK", "caco3", "soilTexture", "soilMineRate", "soilNConcentration"],
                    "example": [
                        ["6.87", "20", "20", "1.37", "0.34", "0.16", "0.32", "0.14", "0.417", "16.5", "1.5", "25", "1.1", "20.2", "1.206", "233.5", "941", "0.003", "中壤土", "2.15", "6.18"],
                        ["6.87", "40", "20", "1.37", "0.34", "0.15", "0.32", "0.14", "0.417", "16.5", "1.5", "25", "1.1", "20.2", "1.206", "233.5", "941", "0.003", "中壤土", "2.15", "6.18"]
                    ],
                    "notes": [
                        "pH: 土壤酸碱度，通常4.5-8.5",
                        "depth: 土层深度(cm)，从地表开始计算",
                        "thickness: 土层厚度(cm)",
                        "bulkWeight: 土壤容重(g/cm³)，通常1.1-1.7",
                        "clayParticle: 黏粒含量(比例0-1)",
                        "actualWater: 实际含水率(体积比)",
                        "fieldCapacity: 田间持水量(体积比)",
                        "wiltingPoint: 萎凋点(体积比)",
                        "fieldSaturation: 饱和含水量(体积比)",
                        "organicMatter: 有机质含量(g/kg)",
                        "totaNitrogen: 全氮(g/kg)",
                        "nitrateNitrogen: 硝态氮(mg/kg)",
                        "ammoniaNitrogen: 铵态氮(mg/kg)",
                        "fastAvailablePhosphorus: 有效磷(mg/kg)",
                        "totalPhosphorus: 全磷(g/kg)",
                        "fastAvailableK: 速效钾(mg/kg)",
                        "slowAvailableK: 缓效钾(mg/kg)",
                        "caco3: 碳酸钙含量(g/kg)",
                        "soilTexture: 土壤质地（砂土/砂壤土/轻壤土/中壤土/重壤土/黏土）",
                        "soilMineRate: 土壤矿化率",
                        "soilNConcentration: 土壤临界氮浓度"
                    ]
                },
                "施肥数据.csv": {
                    "icon": "🧪",
                    "desc": "肥料施用记录",
                    "columns": ["type", "methodName", "DOY", "nAmount", "pAmount", "kAmount", "NO3Amount", "NH4Amount", "UREAAmount"],
                    "example": [
                        ["尿素", "撒施", "170", "101.2", "0", "0", "0", "0", "101.2"],
                        ["复合肥", "沟施", "185", "50", "30", "50", "10", "10", "30"]
                    ],
                    "notes": [
                        "type: 肥料类型（尿素/复合肥/磷酸二铵等）",
                        "methodName: 施肥方式（撒施/沟施/穴施/喷施）",
                        "DOY: 施肥日期的年积日(1-365)，例如6月19日约为第170天",
                        "nAmount: 氮素量(kg N/ha)",
                        "pAmount: 磷素量(kg P2O5/ha)",
                        "kAmount: 钾素量(kg K2O/ha)",
                        "NO3Amount: 硝态氮含量(kg/ha)",
                        "NH4Amount: 铵态氮含量(kg/ha)",
                        "UREAAmount: 酰胺态氮含量(kg/ha，主要是尿素)"
                    ]
                },
                "秸秆数据.csv": {
                    "icon": "🌾",
                    "desc": "秸秆还田数据",
                    "columns": ["previousCropType", "previousCropAccount", "previousCropStraw", "previousCropStubble", "residueDepth"],
                    "example": [
                        ["小麦秸秆", "3200", "1500", "1700", "20"],
                        ["水稻秸秆", "4500", "2000", "1800", "15"]
                    ],
                    "notes": [
                        "previousCropType: 前茬作物类型（小麦秸秆/水稻秸秆/油菜秸秆等）",
                        "previousCropAccount: 作物生物量(kg/ha)，包括地上部全部生物量",
                        "previousCropStraw: 秸秆还田量(kg/ha)",
                        "previousCropStubble: 残茬量(kg/ha)，留茬部分的生物量",
                        "residueDepth: 翻耕深度(cm)，秸秆还田的翻埋深度"
                    ]
                },
                "管理数据_多种方案.csv": {
                    "icon": "📋",
                    "desc": "种植管理方案（每行一个方案，可包含多个方案进行对比）",
                    "columns": ["plantSeedQuantity", "plantingDepth", "numberPerHill", "numberHillsM2", "VI", "SoilSand", "OMN", "OMS", "WaterRegime"],
                    "example": [
                        ["5", "2.5", "3", "20", "1", "30", "1600", "1300", "1"],
                        ["5", "3.0", "3", "20", "2", "30", "1600", "1300", "2"],
                        ["5", "3.5", "3", "20", "3", "30", "1600", "1300", "3"]
                    ],
                    "notes": [
                        "plantSeedQuantity: 播种量(kg/ha)",
                        "plantingDepth: 播种深度(cm)",
                        "numberPerHill: 每穴株数（移栽稻通常2-3株）",
                        "numberHillsM2: 每平方米穴数",
                        "VI: 品种序号，对应品种参数.csv中的品种",
                        "SoilSand: 土壤砂粒含量(%)，影响CH4排放",
                        "OMN: 快速分解有机质输入量(kg C/ha)，影响CH4排放",
                        "OMS: 慢速分解有机质输入量(kg C/ha)，影响CH4排放",
                        "WaterRegime: 灌溉模式(1-5)，1=淹水,2=间歇,3=湿润,4=控制,5=干湿交替"
                    ]
                }
            }

        # 显示每个模板
        for filename, tmpl in template_data.items():
            st.markdown(f"""
            <div style="
                background: white;
                padding: 0.8rem;
                border-radius: 8px;
                margin-bottom: 1rem;
                border: 1px solid #E5E7EB;
            ">
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                    <span style="font-size: 1.2rem;">{tmpl['icon']}</span>
                    <div>
                        <div style="font-size: 0.85rem; color: #1F2937; font-weight: 600;">
                            {filename}
                        </div>
                        <div style="font-size: 0.7rem; color: #6B7280;">
                            {tmpl['desc']}
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 创建示例表格
            df_example = pd.DataFrame(tmpl['example'], columns=tmpl['columns'])
            st.dataframe(
                df_example,
                use_container_width=True,
                height=min(150, len(tmpl['example']) * 40 + 50)
            )

            # 字段说明 - 使用tab展示而不是嵌套expander
            st.markdown("**📝 字段说明：**")
            for note in tmpl['notes']:
                st.markdown(f"<div style='font-size: 0.7rem; color: #4B5563; margin-bottom: 0.2rem;'>• {note}</div>", unsafe_allow_html=True)

            st.markdown("<hr style='margin: 1rem 0; border: none; border-top: 1px solid #E5E7EB;'>", unsafe_allow_html=True)

    # 简化的文件格式要求提示 - 移到expander外面
    st.markdown("""
    <div style="
        background: #FEF3C7;
        padding: 0.5rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
        border-left: 3px solid #F59E0B;
    ">
        <div style="font-size: 0.7rem; color: #92400E; font-weight: 600;">
            💡 <strong>提示：</strong>点击上方 "📖 查看数据文件模板格式" 可查看每个文件的标准格式示例
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 下载模板文件功能
    st.markdown("""
    <div style="
        background: #F0FDFA;
        padding: 0.5rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
        border-left: 3px solid #14B8A6;
    ">
        <div style="font-size: 0.7rem; color: #0F766E; font-weight: 600; margin-bottom: 0.3rem;">
            📥 下载模板文件
        </div>
            <div style="font-size: 0.65rem; color: #115E59;">
                点击下方按钮下载标准格式的空模板文件，填入您的数据后上传
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 创建下载按钮
    col1, col2, col3 = st.columns(3)

    def create_template_csv(filename, columns, example_rows):
        """创建模板CSV文件"""
        df = pd.DataFrame(example_rows, columns=columns)
        return df.to_csv(index=False).encode('gbk')

    with col1:
        # 气象数据模板
        weather_template = create_template_csv(
            "气象数据.csv",
            ["Stationno", "Jour", "Tmax", "Tmin", "RAIN", "SRAD", "CO2"],
            [["1", "1990/1/1", "12.3", "2.8", "0.0", "7.3", "486"]]
        )
        st.download_button(
            label="🌤️ 气象数据模板",
            data=weather_template,
            file_name="气象数据_模板.csv",
            mime="text/csv",
            use_container_width=True,
            help="下载气象数据标准格式模板"
        )

        # 施肥数据模板
        fert_template = create_template_csv(
            "施肥数据.csv",
            ["type", "methodName", "DOY", "nAmount", "pAmount", "kAmount", "NO3Amount", "NH4Amount", "UREAAmount"],
            [["尿素", "撒施", "170", "101.2", "0", "0", "0", "0", "101.2"]]
        )
        st.download_button(
            label="🧪 施肥数据模板",
            data=fert_template,
            file_name="施肥数据_模板.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        # 土壤数据模板
        soil_template = create_template_csv(
            "土壤数据.csv",
            ["pH", "depth", "thickness", "bulkWeight", "clayParticle", "actualWater", "fieldCapacity",
             "wiltingPoint", "fieldSaturation", "organicMatter", "totaNitrogen", "nitrateNitrogen",
             "ammoniaNitrogen", "fastAvailablePhosphorus", "totalPhosphorus", "fastAvailableK",
             "slowAvailableK", "caco3", "soilTexture", "soilMineRate", "soilNConcentration"],
            [["6.87", "20", "20", "1.37", "0.34", "0.16", "0.32", "0.14", "0.417", "16.5",
              "1.5", "25", "1.1", "20.2", "1.206", "233.5", "941", "0.003", "中壤土", "2.15", "6.18"]]
        )
        st.download_button(
            label="🏜️ 土壤数据模板",
            data=soil_template,
            file_name="土壤数据_模板.csv",
            mime="text/csv",
            use_container_width=True
        )

        # 秸秆数据模板
        residue_template = create_template_csv(
            "秸秆数据.csv",
            ["previousCropType", "previousCropAccount", "previousCropStraw", "previousCropStubble", "residueDepth"],
            [["小麦秸秆", "3200", "1500", "1700", "20"]]
        )
        st.download_button(
            label="🌾 秸秆数据模板",
            data=residue_template,
            file_name="秸秆数据_模板.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col3:
        # 管理数据模板
        manage_template = create_template_csv(
            "管理数据_多种方案.csv",
            ["plantSeedQuantity", "plantingDepth", "numberPerHill", "numberHillsM2", "VI", "SoilSand", "OMN", "OMS", "WaterRegime"],
            [["5", "2.5", "3", "20", "1", "30", "1600", "1300", "1"]]
        )
        st.download_button(
            label="📋 管理数据模板",
            data=manage_template,
            file_name="管理数据_多种方案_模板.csv",
            mime="text/csv",
            use_container_width=True
        )

    # 控制是否使用自定义文件的开关
    use_custom = st.checkbox(
        "✨ 使用上传的自定义文件进行模拟",
        value=True,
        help="启用后将使用上传的自定义文件，否则使用默认文件"
    )
    st.session_state['use_custom_files'] = use_custom

    # 清除上传的文件按钮
    if Path(upload_dir).exists() and [f.name for f in Path(upload_dir).iterdir()]:
        if st.button("🗑️ 清除所有上传文件", use_container_width=True):
            import shutil
            try:
                shutil.rmtree(upload_dir)
                Path(upload_dir)
                st.success("✅ 已清除所有上传文件")
                time.sleep(SECONDS_TO_WAIT)
                st.rerun()
            except Exception as e:
                st.error(f"❌ 清除文件时出错: {e}")
                Path(upload_dir).mkdir(parents=True, exist_ok=True)

    # 数据文件检查 - 紧凑版
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #F1F5F9 0%, #E2E8F0 100%);
        padding: 0.75rem;
        margin-top: 1rem;
        border: 2px solid #64748B;
        border-radius: 10px;
    ">
        <h4 style="
            color: #334155;
            margin: 0 0 0.35rem 0;
            font-size: 0.85rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        ">
            📊 <span>数据文件状态</span>
        </h4>
        <p style="
            color: #475569;
            margin: 0;
            font-size: 0.65rem;
            font-weight: 500;
        ">
            检查必需的数据文件是否就绪
        </p>
    </div>
    """, unsafe_allow_html=True)

    required_files = [
        ("调参数据.csv", "📁 调参数据", "模型调优参数"),
        ("气象数据.csv", "🌤️ 气象数据", "温度、降水等"),
        ("土壤数据.csv", "🏜️ 土壤数据", "质地、养分"),
        ("秸秆数据.csv", "🌾 秸秆数据", "残茬输入"),
        ("管理数据_多种方案.csv", "📋 管理数据", "种植管理"),
        ("施肥数据.csv", "🧪 施肥数据", "肥料施用")
    ]

    # 检查上传的文件和默认文件
    upload_dir = str(UPLOADS_DIR)
    file_statuses = []
    for file, display_name, description in required_files:
        # 优先检查上传的文件
        uploaded_path = str(Path(upload_dir) / file)
        default_path = str(DATA_DIR / file)

        if Path(uploaded_path).exists():
            exists = True
            is_custom = True
        elif Path(default_path).exists():
            exists = True
            is_custom = False
        else:
            exists = False
            is_custom = False

        file_statuses.append((file, display_name, description, exists, is_custom))

    # 计算完成度
    total_files = len(file_statuses)
    existing_files = sum(1 for _, _, _, exists, _ in file_statuses if exists)
    completion_rate = existing_files / total_files if total_files > 0 else 0

    # 进度条显示 - 紧凑版
    st.markdown(f"""
    <div style="margin: 0.4rem 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem;">
            <span style="font-size: 0.7rem; font-weight: 600; color: #475569;">准备进度</span>
            <span style="font-size: 0.7rem; font-weight: 700; color: #059669;">{existing_files}/{total_files}</span>
        </div>
        <div style="
            width: 100%;
            height: 6px;
            background: #E2E8F0;
            border-radius: 3px;
            overflow: hidden;
        ">
            <div style="
                width: {completion_rate*100}%;
                height: 100%;
                background: linear-gradient(90deg, #EF4444, #F59E0B, #10B981);
                transition: width 0.5s ease;
            "></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 文件状态网格
    cols = st.columns(2)
    for i, (file, display_name, description, exists, is_custom) in enumerate(file_statuses):
        with cols[i % 2]:
            if exists:
                custom_badge = " ✨自定义" if is_custom else ""
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%);
                    padding: 0.5rem;
                    border-radius: 6px;
                    border: 2px solid #10B981;
                    margin-bottom: 0.4rem;
                    transition: transform 0.2s ease;
                " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                    <div style="display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.2rem;">
                        <span style="font-size: 1rem;">✅</span>
                        <span style="font-weight: 700; color: #065F46; font-size: 0.75rem;">{display_name}{custom_badge}</span>
                    </div>
                    <div style="font-size: 0.6rem; color: #047857; font-weight: 500;">{description}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%);
                    padding: 0.5rem;
                    border-radius: 6px;
                    border: 2px solid #EF4444;
                    margin-bottom: 0.4rem;
                    opacity: 0.8;
                ">
                    <div style="display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.2rem;">
                        <span style="font-size: 1rem;">❌</span>
                        <span style="font-weight: 700; color: #991B1B; font-size: 0.75rem;">{display_name}</span>
                    </div>
                    <div style="font-size: 0.6rem; color: #DC2626; font-weight: 500;">{description}</div>
                </div>
                """, unsafe_allow_html=True)

    # 智能建议 - 紧凑版
    if completion_rate < 1.0:
        missing = [name for _, name, _, exists, _ in file_statuses if not exists]
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
            padding: 0.5rem;
            border-radius: 6px;
            border-left: 3px solid #F59E0B;
            margin-top: 0.4rem;
        ">
            <div style="font-weight: 700; color: #92400E; font-size: 0.7rem; margin-bottom: 0.2rem;">
                💡 需要补充的文件:
            </div>
            <div style="font-size: 0.65rem; color: #B45309; font-weight: 500;">
                {', '.join(missing)}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%);
            padding: 0.5rem;
            border-radius: 6px;
            border-left: 3px solid #10B981;
            margin-top: 0.4rem;
            animation: fadeInUp 0.5s ease-out;
        ">
            <div style="font-weight: 700; color: #065F46; font-size: 0.75rem; text-align: center;">
                ✅ 所有数据文件已就绪，可以开始模拟！
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ===== AI 助手设置 =====
    if OPENAI_AVAILABLE:
        with st.expander("AI 助手设置", expanded=False):
            st.markdown("""
            <div style="font-size:0.75rem; color:#6B7280; margin-bottom:0.5rem;">
                配置 AI 模型提供商和 API Key 以启用智能功能
            </div>
            """, unsafe_allow_html=True)

            # 提供商选择
            provider_keys = list(PROVIDERS.keys())
            provider_names = [PROVIDERS[k]["name"] for k in provider_keys]
            current_provider = st.session_state.get("ai_provider", "zhipu")
            provider_idx = provider_keys.index(current_provider) if current_provider in provider_keys else 0

            selected_provider = st.selectbox(
                "AI 提供商",
                provider_keys,
                format_func=lambda k: PROVIDERS[k]["name"],
                index=provider_idx,
                key="select_ai_provider",
            )
            st.session_state["ai_provider"] = selected_provider

            # API Key 输入
            api_key = st.text_input(
                "API Key",
                type="password",
                value=st.session_state.get("ai_api_key", ""),
                key="input_ai_api_key",
                help=f"输入 {PROVIDERS[selected_provider]['name']} API Key，仅存储在当前会话中",
            )
            if api_key:
                st.session_state["ai_api_key"] = api_key

            # 模型选择（根据提供商动态变化）
            model_ids = get_provider_model_ids(selected_provider)
            current_model = st.session_state.get("ai_model", model_ids[0] if model_ids else "")
            model_idx = model_ids.index(current_model) if current_model in model_ids else 0

            selected_model = st.selectbox(
                "AI 模型",
                model_ids,
                format_func=lambda mid: get_model_display_name(selected_provider, mid),
                index=model_idx,
                key="select_ai_model",
            )
            st.session_state["ai_model"] = selected_model

            if st.session_state.get("ai_api_key"):
                display = get_model_display_name(selected_provider, selected_model)
                st.success(f"已配置: {display} ({PROVIDERS[selected_provider]['name']})")
            else:
                st.info("输入 API Key 以启用 AI 助手、参数推荐和结果分析")


def run_single_variety_simulation(
    cultivar_params: Tuple[float, ...],
    variety_name: str,
    base_dir: Union[str, Path],
    water_regime: int,
    sand_value: float,
    oms: float,
    omn: float,
    use_custom_files: bool = True
) -> Optional[Dict[str, Any]]:
    """运行单个品种的模拟"""
    # 定义数据文件映射
    file_mapping = {
        '调参数据.csv': 'FieldPath',
        '气象数据.csv': 'WeatherPath',
        '土壤数据.csv': 'SoilFieldPath',
        '秸秆数据.csv': 'ResiduePath',
        '管理数据_多种方案.csv': 'PlantingPath',
        '施肥数据.csv': 'FertilizerPath'
    }

    # 创建文件路径字典
    file_paths = {}
    upload_dir = str(UPLOADS_DIR)

    # 优先使用上传的文件，否则使用默认文件
    for filename, var_name in file_mapping.items():
        uploaded_path = str(Path(upload_dir) / filename)
        default_path = str(DATA_DIR / filename)

        if use_custom_files and Path(uploaded_path).exists():
            file_paths[var_name] = uploaded_path
        else:
            file_paths[var_name] = default_path

    # 提取路径
    FieldPath = file_paths['FieldPath']
    WeatherPath = file_paths['WeatherPath']
    SoilFieldPath = file_paths['SoilFieldPath']
    ResiduePath = file_paths['ResiduePath']
    PlantingPath = file_paths['PlantingPath']
    FertilizerPath = file_paths['FertilizerPath']

    # 创建临时品种参数文件
    cultivar_columns = ['PZ', 'PS', 'TS', 'TO', 'IE', 'HF', 'FDF', 'PHI', 'SLAc', 'PF', 'AMX', 'KF', 'TGW', 'RGC', 'LRS', 'TLN', 'EIN', 'TA', 'SGP', 'PC', 'RAR']

    full_cultivar_data = [variety_name] + list(cultivar_params)
    cultivar_df_temp = pd.DataFrame([full_cultivar_data], columns=cultivar_columns)
    CultivarPath = str(PROJECT_ROOT / f"temp_{variety_name}_cultivar.csv")

    logger.info(f"创建临时品种文件: {CultivarPath}")

    # 确保数据类型正确，避免编码问题
    for col in cultivar_df_temp.columns:
        if pd.api.types.is_numeric_dtype(cultivar_df_temp[col]):
            cultivar_df_temp[col] = cultivar_df_temp[col].astype(float)

    # 使用更安全的编码写入方式
    try:
        cultivar_df_temp.to_csv(CultivarPath, index=False, encoding='gbk', errors='replace')
        logger.debug(f"成功写入品种文件: {CultivarPath}")
    except UnicodeEncodeError as e:
        logger.warning(f"GBK编码失败，尝试清理数据: {e}")
        # 如果GBK编码失败，清理字符串列
        for col in cultivar_df_temp.columns:
            if cultivar_df_temp[col].dtype == 'object':
                cultivar_df_temp[col] = cultivar_df_temp[col].astype(str).str.encode(
                    'gbk', errors='replace'
                ).str.decode('gbk')
        cultivar_df_temp.to_csv(CultivarPath, index=False, encoding='gbk')
        logger.info(f"使用备用方法成功写入品种文件")

    except Exception as e:
        logger.error(f"创建品种文件失败: {e}")
        raise RuntimeError(f"无法创建品种文件 {CultivarPath}: {e}")

    try:
        logger.info(f"开始运行Ricegrow模型: variety={variety_name}")
        # 运行Ricegrow模型
        AROOTWTSeq, AWLVGSeq, WSTSeq, WSPSeq, ATOPWTSeq, LAISeq, dTNUMTILLERSeq, YIELDSeq, dTotNuptakeSeq = CalFun(
            FieldPath, WeatherPath, SoilFieldPath, ResiduePath, PlantingPath, CultivarPath, FertilizerPath
        )
        logger.info(f"Ricegrow模型完成: variety={variety_name}, yield={YIELDSeq[-1]:.1f}")

        # 获取温度数据
        WeatherDF = safe_read_csv(WeatherPath)
        Tmax = GetTmax(WeatherDF)
        Tmin = GetTmin(WeatherDF)
        T24H = CalT24H(Tmax, Tmin)

        # 运行CH4通量模拟
        result = CH4Flux_coupled(
            day_begin=1,
            day_end=len(ATOPWTSeq),
            IP=water_regime,
            sand=sand_value,
            Tair=T24H,
            OMS=oms,
            OMN=omn,
            ATOPWTSeq=ATOPWTSeq,
            AROOTWTSeq=AROOTWTSeq
        )
        
        # 准备结果数据
        simulation_results = {
            'variety': variety_name,
            'final_yield': YIELDSeq[-1],
            'total_days': len(ATOPWTSeq),
            'max_lai': max(LAISeq) if LAISeq else 0,
            'total_ch4_emission': result['E'].sum() if 'E' in result else 0,
            'detailed_data': pd.DataFrame({
                'DAYs': range(DAY_START_INDEX, len(ATOPWTSeq) + DAY_START_INDEX),
                'ATOPWTSeq': ATOPWTSeq,
                'AROOTWTSeq': AROOTWTSeq,
                'YIELDSeq': YIELDSeq,
                'LAISeq': LAISeq,
                'dTotNuptakeSeq': dTotNuptakeSeq
            }),
            'ch4_data': result
        }
        
        return simulation_results
        
    except Exception as e:
        st.error(f"处理品种 {variety_name} 时出错: {e}")
        return None
    finally:
        # 清理临时文件
        if Path(CultivarPath).exists():
            Path(CultivarPath).unlink()

def display_simulation_results(results: List[Optional[Dict[str, Any]]]) -> None:
    """显示模拟结果"""
    if not results:
        return

    # 现代结果展示头部 - 紧凑多彩版
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #10B981 0%, #3B82F6 50%, #8B5CF6 100%);
        color: white;
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        text-align: center;
        box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3), 0 4px 10px rgba(59, 130, 246, 0.2);
    ">
        <h2 style="margin: 0; font-size: 1.5rem; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">
            <span>📈</span>模拟结果总览
        </h2>
        <p style="margin: 0.35rem 0 0 0; font-size: 0.85rem; opacity: 0.95;">基于Ricegrow模型的综合分析结果</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 创建结果表格
    summary_data = []
    for result in results:
        if result:
            summary_data.append({
                '品种': result['variety'],
                '最终产量 (kg/ha)': result['final_yield'],
                '模拟天数': result['total_days'],
                '最大LAI': result['max_lai'],
                '总CH4排放 (kg/ha)': result['total_ch4_emission']
            })
    
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        
        # 现代结果统计卡片
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_yield = summary_df['最终产量 (kg/ha)'].mean()
            st.metric(
                label="平均产量",
                value=f"{avg_yield:.1f} kg/ha",
                delta=f"{avg_yield - 5000:.0f}" if avg_yield > 5000 else f"{avg_yield - 5000:.0f}"
            )
        with col2:
            max_yield = summary_df['最终产量 (kg/ha)'].max()
            best_variety = summary_df.loc[summary_df['最终产量 (kg/ha)'].idxmax(), '品种']
            st.metric(
                label="最高产量",
                value=f"{max_yield:.1f} kg/ha",
                delta=f"{best_variety}"
            )
        with col3:
            avg_ch4 = summary_df['总CH4排放 (kg/ha)'].mean()
            st.metric(
                label="平均CH4排放",
                value=f"{avg_ch4:.1f} kg/ha"
            )
        with col4:
            min_ch4 = summary_df['总CH4排放 (kg/ha)'].min()
            eco_variety = summary_df.loc[summary_df['总CH4排放 (kg/ha)'].idxmin(), '品种']
            st.metric(
                label="最低CH4排放",
                value=f"{min_ch4:.1f} kg/ha",
                delta=f"{eco_variety}"
            )
        
        # 现代数据表格
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,250,252,0.95) 100%);
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
            border: 2px solid rgba(16, 185, 129, 0.3);
        ">
            <h4 style="color: #059669; margin: 0 0 0.75rem 0; font-size: 1rem; font-weight: 600;">
                <span>📋</span>详细结果对比
            </h4>
        </div>
        """, unsafe_allow_html=True)
        
        # 格式化数据表格
        display_df = summary_df.copy()
        display_df['最终产量 (kg/ha)'] = display_df['最终产量 (kg/ha)'].apply(lambda x: f"{x:.1f}")
        display_df['最大LAI'] = display_df['最大LAI'].apply(lambda x: f"{x:.2f}")
        display_df['总CH4排放 (kg/ha)'] = display_df['总CH4排放 (kg/ha)'].apply(lambda x: f"{x:.1f}")
        
        st.dataframe(display_df, use_container_width=True)
        
        # 现代可视化结果
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,250,252,0.95) 100%);
            padding: 1rem;
            margin: 1rem 0 0.75rem 0;
            border: 2px solid rgba(16, 185, 129, 0.3);
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
        ">
            <h4 style="
                color: #059669;
                margin: 0 0 0.5rem 0;
                font-size: 1.1rem;
                font-weight: 700;
                display: flex;
                align-items: center;
                gap: 0.4rem;
            ">
                📊 <span>多维度可视化分析</span>
            </h4>
            <p style="
                color: #64748B;
                margin: 0;
                font-size: 0.75rem;
                font-weight: 500;
            ">
                交互式图表，支持悬停查看详细数据
            </p>
        </div>
        """, unsafe_allow_html=True)

        # 使用标签页组织不同类型的图表
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 产量对比",
            "💨 CH4排放",
            "⚖️ 效率分析",
            "🎯 综合评分",
            "🤖 AI分析"
        ])

        with tab1:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%);
                padding: 0.75rem;
                border-radius: 8px;
                border-left: 4px solid #10B981;
                margin-bottom: 1rem;
            ">
                <strong>🌱 产量性能对比</strong> - 各品种最终产量和生长效率
            </div>
            """, unsafe_allow_html=True)

            # 产量对比柱状图
            fig_yield = px.bar(
                summary_df,
                x='品种',
                y='最终产量 (kg/ha)',
                title="各品种最终产量对比",
                color='最终产量 (kg/ha)',
                color_continuous_scale='Greens',
                labels={'最终产量 (kg/ha)': '产量 (kg/ha)', '品种': '水稻品种'},
                text='最终产量 (kg/ha)'
            )
            fig_yield.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                title_font_size=16,
                title_font_color='#059669',
                showlegend=False,
                hovermode='x unified'
            )
            fig_yield.update_traces(
                marker_line_color='#059669',
                marker_line_width=2,
                opacity=0.85,
                texttemplate='%{text:.1f}',
                textposition='outside'
            )
            st.plotly_chart(fig_yield, use_container_width=True)

            # LAI对比
            fig_lai = px.bar(
                summary_df,
                x='品种',
                y='最大LAI',
                title="最大叶面积指数(LAI)对比",
                color='最大LAI',
                color_continuous_scale='Blues',
                text='最大LAI'
            )
            fig_lai.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                title_font_size=14,
                title_font_color='#1E40AF',
                showlegend=False
            )
            fig_lai.update_traces(
                opacity=0.8,
                texttemplate='%{text:.2f}',
                textposition='outside'
            )
            st.plotly_chart(fig_lai, use_container_width=True)

        with tab2:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%);
                padding: 0.75rem;
                border-radius: 8px;
                border-left: 4px solid #EF4444;
                margin-bottom: 1rem;
            ">
                <strong>💨 CH4排放分析</strong> - 碳排放对比和环境影响评估
            </div>
            """, unsafe_allow_html=True)

            # CH4排放对比
            fig_ch4 = px.bar(
                summary_df,
                x='品种',
                y='总CH4排放 (kg/ha)',
                title="各品种总CH4排放对比",
                color='总CH4排放 (kg/ha)',
                color_continuous_scale='Reds',
                labels={'总CH4排放 (kg/ha)': 'CH4排放 (kg/ha)', '品种': '水稻品种'},
                text='总CH4排放 (kg/ha)'
            )
            fig_ch4.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                title_font_size=16,
                title_font_color='#DC2626',
                showlegend=False,
                hovermode='x unified'
            )
            fig_ch4.update_traces(
                marker_line_color='#DC2626',
                marker_line_width=2,
                opacity=0.85,
                texttemplate='%{text:.1f}',
                textposition='outside'
            )
            st.plotly_chart(fig_ch4, use_container_width=True)

            # 散点图：产量 vs CH4排放
            fig_scatter = px.scatter(
                summary_df,
                x='最终产量 (kg/ha)',
                y='总CH4排放 (kg/ha)',
                color='品种',
                size='最大LAI',
                title="产量 vs CH4排放关系 (气泡大小=LAI)",
                labels={
                    '最终产量 (kg/ha)': '产量 (kg/ha)',
                    '总CH4排放 (kg/ha)': 'CH4排放 (kg/ha)',
                    '品种': '品种'
                },
                hover_data=['最大LAI', '模拟天数']
            )
            fig_scatter.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                title_font_size=14,
                title_font_color='#8B5CF6',
                hovermode='closest'
            )
            fig_scatter.update_traces(
                marker=dict(size=15, opacity=0.7, line=dict(width=2, color='white'))
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        with tab3:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%);
                padding: 0.75rem;
                border-radius: 8px;
                border-left: 4px solid #F59E0B;
                margin-bottom: 1rem;
            ">
                <strong>⚖️ 效率分析</strong> - 产量与排放的权衡分析
            </div>
            """, unsafe_allow_html=True)

            # 计算效率指标
            efficiency_df = summary_df.copy()
            efficiency_df['产量排放比'] = efficiency_df['最终产量 (kg/ha)'] / (efficiency_df['总CH4排放 (kg/ha)'] + 1)
            efficiency_df['环境效率'] = efficiency_df['最终产量 (kg/ha)'] / efficiency_df['总CH4排放 (kg/ha)']

            # 环境效率柱状图
            fig_efficiency = px.bar(
                efficiency_df,
                x='品种',
                y='环境效率',
                title="环境效率 (产量/CH4排放)",
                color='环境效率',
                color_continuous_scale='RdYlGn_r',
                text='环境效率'
            )
            fig_efficiency.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                title_font_size=14,
                title_font_color='#059669',
                showlegend=False
            )
            fig_efficiency.update_traces(
                opacity=0.8,
                texttemplate='%{text:.2f}',
                textposition='outside'
            )
            st.plotly_chart(fig_efficiency, use_container_width=True)

            # 雷达图 - 多维度对比
            if len(summary_df) >= 2:
                # 归一化数据用于雷达图
                radar_df = summary_df.copy()
                for col in ['最终产量 (kg/ha)', '最大LAI', '总CH4排放 (kg/ha)']:
                    max_val = radar_df[col].max()
                    min_val = radar_df[col].min()
                    if max_val != min_val:
                        # 对CH4排放进行反向归一化（越低越好）
                        if col == '总CH4排放 (kg/ha)':
                            radar_df[f'{col}_norm'] = 1 - (radar_df[col] - min_val) / (max_val - min_val)
                        else:
                            radar_df[f'{col}_norm'] = (radar_df[col] - min_val) / (max_val - min_val)
                    else:
                        radar_df[f'{col}_norm'] = 1.0

                fig_radar = go.Figure()
                for _, row in radar_df.iterrows():
                    fig_radar.add_trace(go.Scatterpolar(
                        r=[
                            row['最终产量 (kg/ha)_norm'],
                            row['最大LAI_norm'],
                            row['总CH4排放 (kg/ha)_norm']
                        ],
                        theta=['产量', 'LAI', '环保性'],
                        fill='toself',
                        name=row['品种'],
                        hovertemplate=f"<b>{row['品种']}</b><br>产量: {row['最终产量 (kg/ha)']:.1f}<br>LAI: {row['最大LAI']:.2f}<br>CH4: {row['总CH4排放 (kg/ha)']:.1f}<extra></extra>"
                    ))

                fig_radar.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0, 1])
                    ),
                    title="多维度性能雷达图",
                    title_font_size=14,
                    title_font_color='#8B5CF6',
                    font=dict(size=12),
                    paper_bgcolor='white',
                    plot_bgcolor='white'
                )
                st.plotly_chart(fig_radar, use_container_width=True)

        with tab4:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%);
                padding: 0.75rem;
                border-radius: 8px;
                border-left: 4px solid #3B82F6;
                margin-bottom: 1rem;
            ">
                <strong>🎯 综合评分</strong> - 基于多指标的品种综合评价
            </div>
            """, unsafe_allow_html=True)

            # 计算综合评分
            score_df = summary_df.copy()

            # 归一化并计算得分（0-100分）
            def normalize_score(series, higher_better=True):
                max_val = series.max()
                min_val = series.min()
                if max_val == min_val:
                    return pd.Series([50] * len(series))
                if higher_better:
                    return (series - min_val) / (max_val - min_val) * 100
                else:
                    return (max_val - series) / (max_val - min_val) * 100

            score_df['产量得分'] = normalize_score(score_df['最终产量 (kg/ha)'], True)
            score_df['LAI得分'] = normalize_score(score_df['最大LAI'], True)
            score_df['环保得分'] = normalize_score(score_df['总CH4排放 (kg/ha)'], False)

            # 综合得分（产量40%，环保40%，LAI 20%）
            score_df['综合得分'] = (
                score_df['产量得分'] * 0.4 +
                score_df['环保得分'] * 0.4 +
                score_df['LAI得分'] * 0.2
            )

            # 排名展示
            score_df = score_df.sort_values('综合得分', ascending=False)
            score_df['排名'] = range(RANKING_START_INDEX, len(score_df) + RANKING_START_INDEX)

            display_score_df = score_df[['排名', '品种', '最终产量 (kg/ha)', '总CH4排放 (kg/ha)', '最大LAI', '综合得分']].copy()
            display_score_df['综合得分'] = display_score_df['综合得分'].apply(lambda x: f"{x:.1f}")
            display_score_df['最终产量 (kg/ha)'] = display_score_df['最终产量 (kg/ha)'].apply(lambda x: f"{x:.1f}")
            display_score_df['总CH4排放 (kg/ha)'] = display_score_df['总CH4排放 (kg/ha)'].apply(lambda x: f"{x:.1f}")
            display_score_df['最大LAI'] = display_score_df['最大LAI'].apply(lambda x: f"{x:.2f}")

            st.markdown("### 🏆 综合排名")
            st.dataframe(display_score_df, use_container_width=True)

            # 综合得分条形图
            fig_score = px.bar(
                score_df,
                x='品种',
                y='综合得分',
                title="品种综合评分 (0-100分)",
                color='综合得分',
                color_continuous_scale='Viridis',
                text='综合得分'
            )
            fig_score.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                title_font_size=16,
                title_font_color='#1E40AF',
                showlegend=False
            )
            fig_score.update_traces(
                opacity=0.85,
                texttemplate='%{text:.1f}',
                textposition='outside'
            )
            st.plotly_chart(fig_score, use_container_width=True)

            # 得分分解图
            score_long = score_df.melt(
                id_vars=['品种'],
                value_vars=['产量得分', 'LAI得分', '环保得分'],
                var_name='指标',
                value_name='得分'
            )

            fig_breakdown = px.bar(
                score_long,
                x='品种',
                y='得分',
                color='指标',
                title="综合得分分解 (各指标贡献)",
                barmode='stack',
                color_discrete_map={
                    '产量得分': '#10B981',
                    'LAI得分': '#3B82F6',
                    '环保得分': '#F59E0B'
                }
            )
            fig_breakdown.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                title_font_size=14,
                title_font_color='#6366F1',
                hovermode='x unified'
            )
            st.plotly_chart(fig_breakdown, use_container_width=True)
        
        # 详细数据展示
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #10B981 0%, #3B82F6 100%);
            color: white;
            padding: 0.85rem;
            border-radius: 10px;
            margin: 1rem 0 0.75rem 0;
            text-align: center;
            box-shadow: 0 6px 15px rgba(16, 185, 129, 0.3), 0 3px 8px rgba(59, 130, 246, 0.2);
        ">
            <h3 style="margin: 0; font-size: 1.2rem; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.15);">
                <span>📊</span>详细数据分析
            </h3>
            <p style="margin: 0.35rem 0 0 0; font-size: 0.75rem; opacity: 0.95;">
                深入分析各品种的生长动态和环境影响
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        selected_variety = st.selectbox("选择要查看详细数据的品种", 
                                       [r['variety'] for r in results if r],
                                       help="选择特定品种查看其详细的生长过程和CH4排放数据")
        
        if selected_variety:
            selected_result = next((r for r in results if r and r['variety'] == selected_variety), None)
            
            if selected_result:
                # 现代标签页设计
                tab1, tab2, tab3 = st.tabs([
                    "🌱 生长过程分析", 
                    "💨 CH4排放动态", 
                    "📋 原始数据表格"
                ])
                
                with tab1:
                    st.markdown("""
                    <div style="
                        background: linear-gradient(135deg, var(--success-50) 0%, var(--success-100) 100%);
                        padding: 1rem;
                        border-radius: 8px;
                        border-left: 4px solid var(--success-500);
                        margin-bottom: 1rem;
                    ">
                        <h4 style="color: var(--success-700); margin: 0 0 0.5rem 0; font-size: 1rem;">
                            <span class="icon-modern">🌱</span>生长过程动态分析
                        </h4>
                        <p style="color: var(--success-600); margin: 0; font-size: 0.875rem;">
                            产量积累和叶面积指数变化趋势
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 现代生长过程图
                    fig_growth = go.Figure()
                    fig_growth.add_trace(go.Scatter(
                        x=selected_result['detailed_data']['DAYs'],
                        y=selected_result['detailed_data']['YIELDSeq'],
                        mode='lines+markers',
                        name='产量积累',
                        line=dict(color='#10B981', width=3),
                        marker=dict(size=6, color='#10B981'),
                        hovertemplate='<b>第%{x}天</b><br>产量: %{y:.1f} kg/ha<extra></extra>'
                    ))
                    fig_growth.add_trace(go.Scatter(
                        x=selected_result['detailed_data']['DAYs'],
                        y=selected_result['detailed_data']['LAISeq'],
                        mode='lines+markers',
                        name='叶面积指数(LAI)',
                        line=dict(color='#3B82F6', width=3),
                        marker=dict(size=6, color='#3B82F6'),
                        yaxis='y2',
                        hovertemplate='<b>第%{x}天</b><br>LAI: %{y:.2f}<extra></extra>'
                    ))
                    
                    fig_growth.update_layout(
                        title=f"🌱 {selected_variety} - 生长过程动态",
                        xaxis_title="生长天数 (天)",
                        yaxis_title="产量 (kg/ha)",
                        yaxis2=dict(
                            title="叶面积指数 (LAI)",
                            overlaying='y',
                            side='right'
                        ),
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        font=dict(size=12),
                        title_font_size=16,
                        title_font_color='#059669',
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        ),
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig_growth, use_container_width=True)
                
                with tab2:
                    st.markdown("""
                    <div style="
                        background: linear-gradient(135deg, var(--error-50) 0%, var(--error-100) 100%);
                        padding: 1rem;
                        border-radius: 8px;
                        border-left: 4px solid var(--error-500);
                        margin-bottom: 1rem;
                    ">
                        <h4 style="color: var(--error-700); margin: 0 0 0.5rem 0; font-size: 1rem;">
                            <span class="icon-modern">💨</span>CH4排放动态分析
                        </h4>
                        <p style="color: var(--error-600); margin: 0; font-size: 0.875rem;">
                            甲烷排放通量随时间变化规律
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # CH4排放图
                    if 'ch4_data' in selected_result and selected_result['ch4_data'] is not None:
                        fig_ch4_detail = go.Figure()
                        fig_ch4_detail.add_trace(go.Scatter(
                            x=selected_result['ch4_data']['DAT'],
                            y=selected_result['ch4_data']['E'],
                            mode='lines+markers',
                            name='CH4排放通量',
                            line=dict(color='#DC2626', width=3),
                            marker=dict(size=6, color='#DC2626'),
                            hovertemplate='<b>第%{x}天</b><br>CH4排放: %{y:.2f} kg/ha/day<extra></extra>'
                        ))
                        
                        fig_ch4_detail.update_layout(
                            title=f"💨 {selected_variety} - CH4排放通量动态",
                            xaxis_title="生长天数 (天)",
                            yaxis_title="CH4排放通量 (kg/ha/day)",
                            plot_bgcolor='white',
                            paper_bgcolor='white',
                            font=dict(size=12),
                            title_font_size=16,
                            title_font_color='#DC2626',
                            hovermode='x unified'
                        )
                        st.plotly_chart(fig_ch4_detail, use_container_width=True)
                    else:
                        st.info("该品种暂无CH4排放数据")
                
                with tab3:
                    st.markdown("""
                    <div style="
                        background: linear-gradient(135deg, var(--info-50) 0%, var(--info-100) 100%);
                        padding: 1rem;
                        border-radius: 8px;
                        border-left: 4px solid var(--info-500);
                        margin-bottom: 1rem;
                    ">
                        <h4 style="color: var(--info-700); margin: 0 0 0.5rem 0; font-size: 1rem;">
                            <span class="icon-modern">📋</span>原始数据表格
                        </h4>
                        <p style="color: var(--info-600); margin: 0; font-size: 0.875rem;">
                            详细的生长数据和CH4排放数据
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 数据表格
                    st.subheader("🌱 详细生长数据")
                    st.dataframe(selected_result['detailed_data'], use_container_width=True)
                    
                    if 'ch4_data' in selected_result and selected_result['ch4_data'] is not None:
                        st.subheader("💨 CH4排放数据")
                        st.dataframe(selected_result['ch4_data'], use_container_width=True)

        # ===== AI 分析标签页 =====
        with tab5:
            simulation_params = {
                "varieties": st.session_state.get("selected_varieties", []),
                "water_regime": st.session_state.get("water_regime", 1),
                "sand_value": st.session_state.get("sand_value", 35.0),
                "oms": st.session_state.get("oms", 1300.0),
                "omn": st.session_state.get("omn", 1600.0),
            }
            render_ai_analysis_tab(results, simulation_params)

# 主程序
if __name__ == "__main__":
    # ===== 页面选择器 =====
    st.markdown("""
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
    """, unsafe_allow_html=True)

    # 使用session state保存当前页面
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'simulation'

    # 页面选择按钮
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
            "🌱 模拟运行",
            use_container_width=True,
            type="primary" if st.session_state['current_page'] == 'simulation' else "secondary"
        ):
            st.session_state['current_page'] = 'simulation'
            st.rerun()

    with col2:
        if st.button(
            "🎯 自动校准",
            use_container_width=True,
            type="primary" if st.session_state['current_page'] == 'calibration' else "secondary"
        ):
            st.session_state['current_page'] = 'calibration'
            st.rerun()

    with col3:
        ai_label = "🤖 AI 助手" if OPENAI_AVAILABLE else "🤖 AI 助手 (需安装openai)"
        if st.button(
            ai_label,
            use_container_width=True,
            type="primary" if st.session_state['current_page'] == 'ai_assistant' else "secondary"
        ):
            st.session_state['current_page'] = 'ai_assistant'
            st.rerun()

    # 根据选择的页面显示不同内容
    if st.session_state['current_page'] == 'calibration':
        # 显示自动校准页面（使用简化版本）
        show_simple_calibration_page()
        st.stop()  # 停止执行，不继续执行模拟运行代码

    if st.session_state['current_page'] == 'ai_assistant':
        show_ai_assistant_page()
        st.stop()

    # 以下是模拟运行页面的原有代码
    base_dir = PROJECT_ROOT  # 使用config中的PROJECT_ROOT

    # 检查必需文件
    required_files = ["调参数据.csv", "气象数据.csv", "土壤数据.csv",
                     "秸秆数据.csv", "管理数据_多种方案.csv", "施肥数据.csv"]
    missing_files = [file for file in required_files if not (DATA_DIR / file).exists()]

    if missing_files:
        st.error(f"❌ 缺少必需的数据文件: {', '.join(missing_files)}")
        st.stop()

    # 读取品种参数（用于历史结果展示）
    try:
        cultivar_df = safe_read_csv(os.path.join(base_dir, "data", "品种参数.csv"))
    except Exception as e:
        st.error(f"读取品种参数文件失败: {e}")
        st.stop()

    # 显示侧边栏并获取用户配置
    with st.sidebar:
        # 显示侧边栏内容
        show_sidebar_content(cultivar_df)

    # 从session state获取用户配置
    selected_varieties = st.session_state.get('selected_varieties', [])
    water_regime = st.session_state.get('water_regime', 1)
    sand_value = st.session_state.get('sand_value', 35)
    oms = st.session_state.get('oms', 1300)
    omn = st.session_state.get('omn', 1600)
    run_simulation = st.session_state.get('run_simulation', False)

    # AI 参数推荐面板（仅在有 API key 时显示）
    if OPENAI_AVAILABLE:
        render_recommendation_panel(cultivar_df=cultivar_df)

    # 运行模拟
    if run_simulation and selected_varieties:
        # 检查是否有自定义文件
        use_custom = st.session_state.get('use_custom_files', True)
        upload_dir = str(UPLOADS_DIR)
        has_custom = use_custom and Path(upload_dir).exists() and [f.name for f in Path(upload_dir).iterdir()]

        # 显示使用的文件类型
        if has_custom:
            custom_count = len([f for f in [f.name for f in Path(upload_dir).iterdir()] if f.endswith('.csv')])
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%);
                border: 2px solid #3B82F6;
                padding: 0.75rem;
                border-radius: 8px;
                margin-bottom: 1rem;
            ">
                <div style="font-size: 0.8rem; color: #1E40AF; font-weight: 600;">
                    ✨ 使用 {custom_count} 个自定义文件进行模拟
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #E0E7FF 0%, #C7D2FE 100%);
                border: 2px solid #6366F1;
                padding: 0.75rem;
                border-radius: 8px;
                margin-bottom: 1rem;
            ">
                <div style="font-size: 0.8rem; color: #3730A3; font-weight: 600;">
                    📁 使用默认数据文件进行模拟
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #F59E0B 0%, #EF4444 100%);
            color: white;
            padding: 1rem;
            border-radius: 12px;
            margin: 1rem 0;
            text-align: center;
            box-shadow: 0 8px 20px rgba(245, 158, 11, 0.3), 0 4px 10px rgba(239, 68, 68, 0.2);
            animation: pulse 2s infinite;
        ">
            <h3 style="margin: 0; font-size: 1.2rem; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                <span>🔄</span>模拟进行中...
            </h3>
            <p style="margin: 0.35rem 0 0 0; font-size: 0.8rem; opacity: 0.95;">
                正在运行Ricegrow模型和CH4排放耦合模型
            </p>
        </div>
        """, unsafe_allow_html=True)

        # 现代进度条容器
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

        results = []
        total_varieties = len(selected_varieties)

        # 现代状态卡片容器
        status_container = st.container()

        for i, variety in enumerate(selected_varieties):
            progress_percent = (i) / total_varieties
            progress_bar.progress(progress_percent)
            status_text.text(f"🌱 正在模拟: {variety} ({i+1}/{total_varieties})")

            with status_container:
                st.info(f"🔄 开始模拟品种: **{variety}** ({i+1}/{total_varieties})")

            # 为当前品种创建临时品种参数文件
            cultivar_row = cultivar_df[cultivar_df['PZ'] == variety].iloc[PANDAS_ILON_FIRST_ROW]
            cultivar_temp_df = pd.DataFrame([cultivar_row])
            cultivar_temp_path = str(PROJECT_ROOT / f"temp_{variety}_cultivar.csv")

            # 确保数据类型正确，避免编码问题
            # 将numpy类型转换为Python原生类型
            for col in cultivar_temp_df.columns:
                if pd.api.types.is_numeric_dtype(cultivar_temp_df[col]):
                    cultivar_temp_df[col] = cultivar_temp_df[col].astype(float)

            # 使用更安全的编码写入方式
            try:
                cultivar_temp_df.to_csv(cultivar_temp_path, index=False, encoding='gbk', errors='replace')
            except UnicodeEncodeError as e:
                # 如果GBK编码失败，尝试清理数据后重试
                with status_container:
                    st.warning(f"⚠️ GBK编码警告，尝试清理数据: {e}")
                # 清理可能的问题字符
                for col in cultivar_temp_df.columns:
                    if cultivar_temp_df[col].dtype == 'object':
                        cultivar_temp_df[col] = cultivar_temp_df[col].astype(str).str.encode(
                            'gbk', errors='replace'
                        ).str.decode('gbk')
                cultivar_temp_df.to_csv(cultivar_temp_path, index=False, encoding='gbk')

            # 读取品种参数
            try:
                cultivar_params_tuple = GetCultivarParams(cultivar_temp_path)
                cultivar_params = cultivar_params_tuple[1:]  # 跳过品种名称

                # 运行模拟
                use_custom = st.session_state.get('use_custom_files', True)
                result = run_single_variety_simulation(
                    cultivar_params, variety, base_dir, water_regime, sand_value, oms, omn, use_custom
                )
                results.append(result)

                if result:
                    with status_container:
                        st.success(f"✅ **{variety}** 模拟完成 - 产量: **{result['final_yield']:.1f} kg/ha**")

            except Exception as e:
                with status_container:
                    st.error(f"❌ **{variety}** 模拟失败: {e}")
                results.append(None)
            finally:
                # 清理临时文件
                if Path(cultivar_temp_path).exists():
                    Path(cultivar_temp_path).unlink()

            time.sleep(PROGRESS_UPDATE_DELAY)  # 延迟以便用户看到进度

        progress_bar.progress(1.0)
        status_text.text("🎉 模拟完成!")

        # 模拟完成庆祝动画
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #10B981 0%, #059669 100%);
            color: white;
            padding: 1rem;
            border-radius: 12px;
            margin: 1rem 0;
            text-align: center;
            box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3), 0 4px 10px rgba(5, 150, 105, 0.2);
            animation: fadeInUp 0.8s ease-out;
        ">
            <h3 style="margin: 0; font-size: 1.2rem; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                <span>🎉</span>模拟完成！
            </h3>
            <p style="margin: 0.35rem 0 0 0; font-size: 0.8rem; opacity: 0.95;">
                所有品种模拟成功，正在生成分析报告...
            </p>
        </div>
        """, unsafe_allow_html=True)

        # 显示结果
        st.session_state['simulation_results_cache'] = results
        display_simulation_results(results)

        # 重置运行状态
        st.session_state['run_simulation'] = False

    # 从缓存恢复上次模拟结果（解决按钮点击后 rerun 丢失结果的问题）
    elif not run_simulation and st.session_state.get('simulation_results_cache'):
        cached_results = st.session_state['simulation_results_cache']
        if any(r is not None for r in cached_results):
            display_simulation_results(cached_results)

    # 现代应用信息页脚 - 博客风格
    st.markdown("""
    <div style="
        background: #FFFFFF;
        border: 2px solid #E5E7EB;
        padding: 1.5rem;
        border-radius: 12px;
        margin-top: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    ">
        <h3 style="margin: 0 0 1rem 0; font-size: 1.2rem; font-weight: 700; color: #1E293B;">
            <span>ℹ️</span>系统信息
        </h3>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1rem; max-width: 600px; margin-left: auto; margin-right: auto;">
            <div style="text-align: left; padding: 0.85rem; background: #F8FAFC; border-radius: 8px; border: 1px solid #E5E7EB;">
                <h4 style="color: #10B981; margin: 0 0 0.4rem 0; font-size: 0.95rem; font-weight: 700;">🌾 模型架构</h4>
                <p style="margin: 0; font-size: 0.8rem; color: #475569; line-height: 1.4;">Ricegrow + CH4排放耦合模型</p>
            </div>
            <div style="text-align: left; padding: 0.85rem; background: #F8FAFC; border-radius: 8px; border: 1px solid #E5E7EB;">
                <h4 style="color: #10B981; margin: 0 0 0.4rem 0; font-size: 0.95rem; font-weight: 700;">🎯 核心功能</h4>
                <p style="margin: 0; font-size: 0.8rem; color: #475569; line-height: 1.4;">水稻生长模拟与甲烷排放预测</p>
            </div>
            <div style="text-align: left; padding: 0.85rem; background: #F8FAFC; border-radius: 8px; border: 1px solid #E5E7EB;">
                <h4 style="color: #10B981; margin: 0 0 0.4rem 0; font-size: 0.95rem; font-weight: 700;">📊 数据基础</h4>
                <p style="margin: 0; font-size: 0.8rem; color: #475569; line-height: 1.4;">基于实测气象、土壤和管理数据</p>
            </div>
            <div style="text-align: left; padding: 0.85rem; background: #F8FAFC; border-radius: 8px; border: 1px solid #E5E7EB;">
                <h4 style="color: #10B981; margin: 0 0 0.4rem 0; font-size: 0.95rem; font-weight: 700;">📈 输出结果</h4>
                <p style="margin: 0; font-size: 0.8rem; color: #475569; line-height: 1.4;">产量预测、CH4排放通量、生长过程数据</p>
            </div>
        </div>
        <div style="border-top: 2px solid #E5E7EB; padding-top: 1rem; margin-top: 1rem;">
            <p style="margin: 0; font-size: 0.8rem; color: #64748B; font-weight: 500; line-height: 1.5;">
                🚀 基于现代前端技术构建 | 致力于可持续农业发展 | 精准农业决策支持系统
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)