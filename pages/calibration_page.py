"""
校准页面

薄包装层，委托给 calibration_page 模块
"""
import streamlit as st


def show_calibration_page() -> None:
    """显示自动校准页面"""
    from calibration_page import show_simple_calibration_page
    show_simple_calibration_page()
