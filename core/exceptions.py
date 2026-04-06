"""
统一异常处理模块

定义项目中所有自定义异常类，提供清晰的错误层次结构。
"""
from typing import Optional, Dict, Any, List
from pathlib import Path


# ==================== 基础异常 ====================

class RiceError(Exception):
    """水稻模型系统错误基类"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'details': self.details
        }


# ==================== 数据相关异常 ====================

class DataError(RiceError):
    """数据错误基类"""
    pass


class FileReadError(DataError):
    """文件读取错误"""

    def __init__(self, message: str, file_path: Optional[Path] = None) -> None:
        details = {'file_path': str(file_path)} if file_path else {}
        super().__init__(message, details)


class EncodingError(DataError):
    """编码错误"""

    def __init__(
        self,
        message: str,
        file_path: Optional[Path] = None,
        attempted_encodings: Optional[List[str]] = None
    ) -> None:
        details = {'file_path': str(file_path)} if file_path else {}
        if attempted_encodings:
            details['attempted_encodings'] = attempted_encodings
        super().__init__(message, details)


class ValidationError(DataError):
    """数据验证错误"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None
    ) -> None:
        details = {}
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = str(value)
        super().__init__(message, details)


class ColumnMismatchError(ValidationError):
    """列不匹配错误"""

    def __init__(self, file_path: str, expected: List[str], actual: List[str]) -> None:
        super().__init__(f"文件 {file_path} 列不匹配")
        self.details['expected_columns'] = expected
        self.details['actual_columns'] = actual


class MissingRequiredColumnError(ValidationError):
    """缺少必需列错误"""

    def __init__(self, column_name: str, file_type: str = "") -> None:
        message = f"缺少必需列: {column_name}"
        if file_type:
            message = f"{file_type} - {message}"
        super().__init__(message, field=column_name)
        self.details['column'] = column_name
        if file_type:
            self.details['file_type'] = file_type


# ==================== 模型相关异常 ====================

class ModelError(RiceError):
    """模型错误基类"""
    pass


class ModelRunError(ModelError):
    """模型运行错误"""

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> None:
        details = {}
        if model_name:
            details['model'] = model_name
        if params:
            details['params'] = params
        super().__init__(message, details)


class ModelNotFoundError(ModelError):
    """模型文件未找到错误"""

    def __init__(self, model_path: Path):
        super().__init__(
            f"模型文件未找到: {model_path}",
            {'model_path': str(model_path)}
        )


class ParameterError(ModelError):
    """参数错误"""

    def __init__(
        self,
        message: str,
        param_name: Optional[str] = None,
        param_value: Any = None
    ) -> None:
        details = {}
        if param_name:
            details['parameter'] = param_name
        if param_value is not None:
            details['value'] = str(param_value)
        super().__init__(message, details)


class ParameterOutOfBoundsError(ParameterError):
    """参数超出边界错误"""

    def __init__(self, param_name: str, value: float, lower: float, upper: float) -> None:
        super().__init__(
            f"参数 {param_name}={value} 超出边界 [{lower}, {upper}]",
            param_name=param_name,
            param_value=value
        )
        self.details['bounds'] = (lower, upper)


# ==================== 优化相关异常 ====================

class OptimizationError(RiceError):
    """优化错误基类"""
    pass


class OptimizerError(OptimizationError):
    """优化器错误"""

    def __init__(self, message: str, optimizer_name: Optional[str] = None) -> None:
        details = {'optimizer': optimizer_name} if optimizer_name else {}
        super().__init__(message, details)


class ConvergenceError(OptimizationError):
    """收敛错误"""

    def __init__(self, message: str, iterations: int = 0, best_value: float = 0) -> None:
        super().__init__(message)
        self.details['iterations'] = iterations
        self.details['best_value'] = best_value


# ==================== UI相关异常 ====================

class UIError(RiceError):
    """UI错误基类"""
    pass


class FileUploadError(UIError):
    """文件上传错误"""

    def __init__(
        self,
        message: str,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None
    ) -> None:
        details = {}
        if file_name:
            details['file_name'] = file_name
        if file_size is not None:
            details['file_size'] = file_size
        super().__init__(message, details)


# ==================== 辅助函数 ====================

def format_error(error: Exception) -> str:
    """格式化错误信息

    Args:
        error: 异常对象

    Returns:
        格式化的错误信息
    """
    if isinstance(error, RiceError):
        return f"[{error.__class__.__name__}] {error.message}"
    else:
        return f"[{error.__class__.__name__}] {str(error)}"


def get_error_details(error: Exception) -> Dict[str, Any]:
    """获取错误详细信息

    Args:
        error: 异常对象

    Returns:
        错误详情字典
    """
    if isinstance(error, RiceError):
        return error.to_dict()
    else:
        return {
            'error_type': error.__class__.__name__,
            'message': str(error)
        }


# ==================== 导出列表 ====================

__all__ = [
    # Base
    'RiceError',

    # Data
    'DataError',
    'FileReadError',
    'EncodingError',
    'ValidationError',
    'ColumnMismatchError',
    'MissingRequiredColumnError',

    # Model
    'ModelError',
    'ModelRunError',
    'ModelNotFoundError',
    'ParameterError',
    'ParameterOutOfBoundsError',

    # Optimization
    'OptimizationError',
    'OptimizerError',
    'ConvergenceError',

    # UI
    'UIError',
    'FileUploadError',

    # Helpers
    'format_error',
    'get_error_details',
]
