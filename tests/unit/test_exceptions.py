"""
异常处理单元测试

测试统一异常层次结构和辅助函数。
"""
import pytest
from pathlib import Path
from core.exceptions import (
    # 基础异常
    RiceError,
    # 数据相关异常
    DataError,
    FileReadError,
    EncodingError,
    ValidationError,
    ColumnMismatchError,
    MissingRequiredColumnError,
    # 模型相关异常
    ModelError,
    ModelRunError,
    ModelNotFoundError,
    ParameterError,
    ParameterOutOfBoundsError,
    # 优化相关异常
    OptimizationError,
    OptimizerError,
    ConvergenceError,
    # UI相关异常
    UIError,
    FileUploadError,
    # 辅助函数
    format_error,
    get_error_details,
)


# ==================== 基础异常测试 ====================

class TestRiceError:
    """RiceError基础异常测试"""

    def test_create_basic_error(self):
        """测试创建基础错误"""
        error = RiceError("基础错误消息")
        assert error.message == "基础错误消息"
        assert error.details == {}
        assert str(error) == "基础错误消息"

    def test_create_error_with_details(self):
        """测试创建带详情的错误"""
        details = {"param": "value", "code": 123}
        error = RiceError("带详情的错误", details=details)

        assert error.details == details
        assert error.details["param"] == "value"

    def test_to_dict(self):
        """测试转换为字典"""
        error = RiceError("测试错误", details={"key": "value"})
        error_dict = error.to_dict()

        assert error_dict["error_type"] == "RiceError"
        assert error_dict["message"] == "测试错误"
        assert error_dict["details"]["key"] == "value"


# ==================== 数据异常测试 ====================

class TestDataErrors:
    """数据相关异常测试"""

    def test_file_read_error(self):
        """测试文件读取错误"""
        path = Path("/test/path.csv")
        error = FileReadError("无法读取文件", file_path=path)

        assert "无法读取文件" in error.message
        assert error.details["file_path"] == str(path)

    def test_encoding_error_basic(self):
        """测试编码错误"""
        error = EncodingError("编码不支持")

        assert "编码" in error.message

    def test_encoding_error_with_details(self):
        """测试带详情的编码错误"""
        path = Path("/test/file.csv")
        encodings = ["utf-8", "gbk", "gb2312"]
        error = EncodingError(
            "编码失败",
            file_path=path,
            attempted_encodings=encodings
        )

        assert error.details["file_path"] == str(path)
        assert error.details["attempted_encodings"] == encodings

    def test_validation_error(self):
        """测试验证错误"""
        error = ValidationError("验证失败", field="test_field", value=123)

        assert error.details["field"] == "test_field"
        assert error.details["value"] == "123"

    def test_column_mismatch_error(self):
        """测试列不匹配错误"""
        expected = ["A", "B", "C"]
        actual = ["A", "B"]
        error = ColumnMismatchError("test.csv", expected, actual)

        assert "test.csv" in error.message
        assert error.details["expected_columns"] == expected
        assert error.details["actual_columns"] == actual

    def test_missing_required_column_error_basic(self):
        """测试缺少必需列错误"""
        error = MissingRequiredColumnError("Biomass")

        assert "Biomass" in error.message
        assert error.details["column"] == "Biomass"

    def test_missing_required_column_error_with_type(self):
        """测试带文件类型的缺少必需列错误"""
        error = MissingRequiredColumnError("LAI", file_type="气象数据")

        assert "气象数据" in error.message
        assert error.details["file_type"] == "气象数据"


# ==================== 模型异常测试 ====================

class TestModelErrors:
    """模型相关异常测试"""

    def test_model_run_error_basic(self):
        """测试模型运行错误"""
        error = ModelRunError("运行失败")

        assert "运行失败" in error.message

    def test_model_run_error_with_details(self):
        """测试带详情的模型运行错误"""
        error = ModelRunError(
            "模拟失败",
            model_name="RiceGrow",
            params={"PS": 0.05}
        )

        assert error.details["model"] == "RiceGrow"
        assert error.details["params"]["PS"] == 0.05

    def test_model_not_found_error(self):
        """测试模型未找到错误"""
        path = Path("/nonexistent/model.py")
        error = ModelNotFoundError(path)

        assert "模型文件未找到" in error.message
        assert error.details["model_path"] == str(path)

    def test_parameter_error(self):
        """测试参数错误"""
        error = ParameterError("参数无效", param_name="PS", param_value=0.5)

        assert "参数无效" in error.message
        assert error.details["parameter"] == "PS"
        assert error.details["value"] == "0.5"

    def test_parameter_out_of_bounds_error(self):
        """测试参数超出边界错误"""
        error = ParameterOutOfBoundsError(
            param_name="PS",
            value=0.5,
            lower=0.0,
            upper=0.1
        )

        assert "PS" in error.message
        assert "0.5" in error.message
        assert error.details["bounds"] == (0.0, 0.1)

    def test_parameter_out_of_bounds_error_format(self):
        """测试参数超出边界错误格式"""
        error = ParameterOutOfBoundsError("TS", 5.0, 2.0, 4.0)

        error_str = str(error)
        assert "TS" in error_str
        assert "5.0" in error_str
        assert "[2.0, 4.0]" in error_str


# ==================== 优化异常测试 ====================

class TestOptimizationErrors:
    """优化相关异常测试"""

    def test_optimization_error(self):
        """测试优化错误"""
        error = OptimizationError("优化失败")
        assert isinstance(error, RiceError)

    def test_optimizer_error(self):
        """测试优化器错误"""
        error = OptimizerError("PSO算法失败", optimizer_name="PSO")

        assert error.details["optimizer"] == "PSO"

    def test_convergence_error(self):
        """测试收敛错误"""
        error = ConvergenceError(
            "未收敛",
            iterations=1000,
            best_value=999.9
        )

        assert error.details["iterations"] == 1000
        assert error.details["best_value"] == 999.9


# ==================== UI异常测试 ====================

class TestUIErrors:
    """UI相关异常测试"""

    def test_file_upload_error_basic(self):
        """测试文件上传错误"""
        error = FileUploadError("上传失败")

        assert "上传失败" in error.message

    def test_file_upload_error_with_details(self):
        """测试带详情的文件上传错误"""
        error = FileUploadError(
            "文件太大",
            file_name="large_file.csv",
            file_size=1024 * 1024 * 100  # 100MB
        )

        assert error.details["file_name"] == "large_file.csv"
        assert error.details["file_size"] == 1024 * 1024 * 100


# ==================== 辅助函数测试 ====================

class TestHelperFunctions:
    """辅助函数测试"""

    def test_format_error_rice_error(self):
        """测试格式化RiceError"""
        error = RiceError("测试错误", details={"key": "value"})
        formatted = format_error(error)

        assert "[RiceError]" in formatted
        assert "测试错误" in formatted

    def test_format_error_standard_exception(self):
        """测试格式化标准异常"""
        error = ValueError("无效值")
        formatted = format_error(error)

        assert "[ValueError]" in formatted
        assert "无效值" in formatted

    def test_get_error_details_rice_error(self):
        """测试获取RiceError详情"""
        error = ParameterOutOfBoundsError("PS", 0.5, 0.0, 0.1)
        details = get_error_details(error)

        assert details["error_type"] == "ParameterOutOfBoundsError"
        assert "message" in details
        assert "details" in details

    def test_get_error_details_standard_exception(self):
        """测试获取标准异常详情"""
        error = FileNotFoundError("文件不存在")
        details = get_error_details(error)

        assert details["error_type"] == "FileNotFoundError"
        assert details["message"] == "文件不存在"

    def test_get_error_details_no_details_key(self):
        """测试没有details键的异常详情"""
        error = ValueError("简单错误")
        details = get_error_details(error)

        assert "details" not in details
        assert "message" in details


# ==================== 异常层次测试 ====================

class TestExceptionHierarchy:
    """异常继承层次测试"""

    def test_data_error_is_rice_error(self):
        """测试DataError继承"""
        error = FileReadError("测试")
        assert isinstance(error, RiceError)
        assert isinstance(error, DataError)

    def test_model_error_is_rice_error(self):
        """测试ModelError继承"""
        error = ModelRunError("测试")
        assert isinstance(error, RiceError)
        assert isinstance(error, ModelError)

    def test_optimization_error_is_rice_error(self):
        """测试OptimizationError继承"""
        error = OptimizerError("测试")
        assert isinstance(error, RiceError)
        assert isinstance(error, OptimizationError)

    def test_ui_error_is_rice_error(self):
        """测试UIError继承"""
        error = FileUploadError("测试")
        assert isinstance(error, RiceError)
        assert isinstance(error, UIError)

    def test_parameter_error_is_model_error(self):
        """测试ParameterError继承"""
        error = ParameterError("测试")
        assert isinstance(error, ModelError)
        assert isinstance(error, RiceError)

    def test_validation_error_is_data_error(self):
        """测试ValidationError继承"""
        error = ColumnMismatchError("test.csv", [], [])
        assert isinstance(error, DataError)
        assert isinstance(error, RiceError)
