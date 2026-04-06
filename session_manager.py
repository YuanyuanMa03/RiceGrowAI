"""
Session State 管理模块 - 企业级水稻生长与CH4排放模拟系统

本模块提供Session State的生命周期管理，防止内存泄漏
"""
from typing import Any, Optional, Set
import streamlit as st
import logging

logger = logging.getLogger('rice_app')


# 定义所有合法的session state键
VALID_SESSION_KEYS = {
    # 用户输入
    'selected_varieties',
    'water_regime',
    'water_mode_index',
    'sand_value',
    'soil_index',
    'oms',
    'omn',
    'use_custom_files',
    'run_simulation',

    # 文件上传相关
    'custom_调参数据_csv',
    'custom_气象数据_csv',
    'custom_土壤数据_csv',
    'custom_秸秆数据_csv',
    'custom_管理数据_多种方案_csv',
    'custom_施肥数据_csv',
    'custom_调参数据_csv_encoding',
    'custom_气象数据_csv_encoding',
    'custom_土壤数据_csv_encoding',
    'custom_秸秆数据_csv_encoding',
    'custom_管理数据_多种方案_csv_encoding',
    'custom_施肥数据_csv_encoding',
}

# 临时session state键（应在模拟后清理）
TEMP_SESSION_KEYS_PREFIX = 'temp_'


def init_session_state() -> None:
    """初始化session state，设置默认值"""
    defaults = {
        'selected_varieties': [],
        'water_regime': 1,
        'water_mode_index': 0,
        'sand_value': 35.0,
        'soil_index': 0,
        'oms': 1300.0,
        'omn': 1600.0,
        'use_custom_files': True,
        'run_simulation': False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
            logger.debug(f"初始化session state: {key} = {value}")


def get_session_state(key: str, default: Any = None) -> Any:
    """安全获取session state值

    Args:
        key: session state键名
        default: 默认值

    Returns:
        session state值或默认值
    """
    return st.session_state.get(key, default)


def set_session_state(key: str, value: Any) -> None:
    """安全设置session state值

    Args:
        key: session state键名
        value: 要设置的值

    Raises:
        ValueError: 如果键名不在允许列表中
    """
    if key not in VALID_SESSION_KEYS and not key.startswith(TEMP_SESSION_KEYS_PREFIX):
        logger.warning(f"尝试设置未验证的session state键: {key}")
        # 不抛出异常，允许扩展

    st.session_state[key] = value
    logger.debug(f"设置session state: {key} = {type(value).__name__}")


def clear_session_state(keys: Optional[Set[str]] = None) -> None:
    """清理指定的session state键

    Args:
        keys: 要清理的键集合，如果为None则清理所有临时键
    """
    if keys is None:
        # 清理所有临时键
        keys_to_clear = {k for k in st.session_state.keys() if k.startswith(TEMP_SESSION_KEYS_PREFIX)}
    else:
        keys_to_clear = keys

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
            logger.debug(f"清理session state: {key}")


def cleanup_after_simulation() -> None:
    """模拟完成后清理临时数据"""
    # 重置运行标志
    set_session_state('run_simulation', False)

    # 清理大型数据对象（如果有）
    temp_keys = {k for k in st.session_state.keys() if k.startswith('temp_')}
    clear_session_state(temp_keys)

    logger.info("模拟后清理完成")


def validate_session_state() -> bool:
    """验证session state的完整性

    Returns:
        bool: session state是否有效
    """
    required_keys = {'selected_varieties', 'water_regime', 'sand_value', 'oms', 'omn'}
    missing_keys = required_keys - set(st.session_state.keys())

    if missing_keys:
        logger.warning(f"Session state缺少必需键: {missing_keys}")
        return False

    return True


def get_session_state_info() -> dict:
    """获取session state的统计信息

    Returns:
        dict: 包含session state统计信息的字典
    """
    state_keys = set(st.session_state.keys())

    return {
        'total_keys': len(state_keys),
        'valid_keys': len(state_keys & VALID_SESSION_KEYS),
        'temp_keys': len({k for k in state_keys if k.startswith(TEMP_SESSION_KEYS_PREFIX)}),
        'unknown_keys': len(state_keys - VALID_SESSION_KEYS - {k for k in state_keys if k.startswith(TEMP_SESSION_KEYS_PREFIX)}),
    }


def log_session_state_usage() -> None:
    """记录session state使用情况到日志"""
    info = get_session_state_info()
    logger.info(f"Session State 使用情况: {info}")

    # 警告未知键
    state_keys = set(st.session_state.keys())
    unknown_keys = state_keys - VALID_SESSION_KEYS - {k for k in state_keys if k.startswith(TEMP_SESSION_KEYS_PREFIX)}
    if unknown_keys:
        logger.warning(f"发现未注册的session state键: {unknown_keys}")
