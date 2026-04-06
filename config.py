"""
配置模块 - 企业级水稻生长与CH4排放模拟系统

本模块集中管理所有配置常量、路径和魔术数字
"""
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import logging

# ===== 项目路径配置 =====
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
UPLOADS_DIR = PROJECT_ROOT / "uploads"
MODELS_DIR = PROJECT_ROOT / "models"

# 确保目录存在
LOGS_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

# ===== 文件名常量 =====
REQUIRED_DATA_FILES = [
    "调参数据.csv",
    "气象数据.csv",
    "土壤数据.csv",
    "秸秆数据.csv",
    "管理数据_多种方案.csv",
    "施肥数据.csv",
    "品种参数.csv"
]

FILE_MAPPING = {
    '调参数据.csv': 'FieldPath',
    '气象数据.csv': 'WeatherPath',
    '土壤数据.csv': 'SoilFieldPath',
    '秸秆数据.csv': 'ResiduePath',
    '管理数据_多种方案.csv': 'PlantingPath',
    '施肥数据.csv': 'FertilizerPath',
}

# ===== 编码配置 =====
# 文件读取时尝试的编码顺序
ENCODING_FALLBACK = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'utf-8-sig', 'latin1']

# 默认文件写入编码
DEFAULT_WRITE_ENCODING = 'gbk'

# ===== 文件上传限制 =====
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = ['.csv']

# ===== 灌溉模式常量 =====
WATER_REGIME_NAMES = {
    1: "Continuous Flooding",
    2: "Intermittent Irrigation",
    3: "Wet Irrigation",
    4: "Controlled Irrigation",
    5: "Alternate Wet-Dry"
}

WATER_REGIME_DESCRIPTIONS = {
    1: "淹水灌溉 (最高CH4排放)",
    2: "间歇灌溉 (中高CH4排放)",
    3: "湿润灌溉 (中低CH4排放)",
    4: "控制灌溉 (中等CH4排放)",
    5: "干湿交替 (最低CH4排放，最高效率)"
}

# ===== 模拟常量 =====
# 品种参数列名
CULTIVAR_COLUMNS = [
    'PZ', 'PS', 'TS', 'TO', 'IE', 'HF', 'FDF', 'PHI', 'SLAc', 'PF',
    'AMX', 'KF', 'TGW', 'RGC', 'LRS', 'TLN', 'EIN', 'TA', 'SGP', 'PC', 'RAR'
]

# 气象数据列名
WEATHER_COLUMNS = ['Stationno', 'Jour', 'Tmax', 'Tmin', 'RAIN', 'SRAD', 'CO2']

# ===== UI 常量 =====
# 推荐同时模拟的品种数量
RECOMMENDED_VARIETIES = 5
MAX_VARIETIES = 8

# 土壤砂粒含量范围
SAND_CONTENT_MIN = 0
SAND_CONTENT_MAX = 100

# 有机质输入范围
OM_MIN = 0
OM_MAX = 5000

# ===== 时间常量 =====
SECONDS_TO_WAIT = 1  # 清除文件后的等待时间
CACHE_TTL = 3600  # 缓存生存时间（秒）
PROGRESS_UPDATE_DELAY = 0.3  # 进度更新延迟（秒）

# ===== 数据处理常量 =====
DAY_START_INDEX = 1  # 天数起始索引
RANKING_START_INDEX = 1  # 排名起始索引
PANDAS_ILON_FIRST_ROW = 0  # pandas iloc 第一行索引

# ===== UI 显示常量 =====
KB_SIZE_DIVISOR = 1024  # KB转换除数
MB_SIZE_DIVISOR = 1024 * 1024  # MB转换除数
FLOAT_PRECISION_DEFAULT = 1  # 默认浮点精度

# ===== 日志配置 =====
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_FILE_ENCODING = 'utf-8'

# ===== 应用信息 =====
APP_NAME = "水稻生长与CH4排放模拟系统"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Rice Simulation Team"

# ===== 错误消息常量 =====
ERROR_MESSAGES = {
    'file_not_found': "❌ 文件不存在: {filename}",
    'encoding_error': "❌ 无法读取文件 {filename}，尝试的编码: {encodings}",
    'invalid_file_type': "❌ 只支持 CSV 文件格式",
    'file_too_large': "❌ 文件过大，最大支持 {max_size}MB",
    'simulation_failed': "❌ 模拟失败: {error}",
    'no_variety_selected': "⚠️ 请至少选择一个品种",
    'missing_files': "❌ 缺少必需的数据文件: {files}",
}

# ===== 自定义异常类 =====
class RiceSimulationError(Exception):
    """水稻模拟基础异常类"""
    pass


class FileReadError(RiceSimulationError):
    """文件读取错误"""
    pass


class EncodingError(RiceSimulationError):
    """编码错误"""
    pass


class ValidationError(RiceSimulationError):
    """验证错误"""
    pass


class SimulationError(RiceSimulationError):
    """模拟运行错误"""
    pass

# ===== 路径工具函数 =====
def get_data_path(filename: str) -> Path:
    """获取数据文件路径

    Args:
        filename: 文件名

    Returns:
        完整的文件路径
    """
    return DATA_DIR / filename


def get_log_path() -> Path:
    """获取日志目录路径"""
    return LOGS_DIR


def get_upload_path(filename: str = "") -> Path:
    """获取上传目录路径

    Args:
        filename: 可选的文件名

    Returns:
        上传目录路径或完整文件路径
    """
    if filename:
        return UPLOADS_DIR / filename
    return UPLOADS_DIR


def safe_join_path(base: Path, *paths) -> Path:
    """安全地拼接路径，防止路径遍历攻击

    Args:
        base: 基础路径
        *paths: 要拼接的路径部分

    Returns:
        拼接后的安全路径

    Raises:
        ValueError: 如果路径不在基础路径内
    """
    full_path = (base / Path(*paths)).resolve()
    base_resolved = base.resolve()

    if not str(full_path).startswith(str(base_resolved)):
        raise ValueError(f"非法的路径: {full_path}")

    return full_path


# ===== 日志配置函数 =====
def setup_application_logging(name: str = 'rice_app') -> logging.Logger:
    """配置应用程序日志

    Args:
        name: 日志记录器名称

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 文件处理器 - 详细日志
    log_file = LOGS_DIR / f'app_{datetime.now().strftime("%Y%m%d")}.log'
    file_handler = logging.FileHandler(log_file, encoding=LOG_FILE_ENCODING)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    file_handler.setFormatter(file_formatter)

    # 控制台处理器 - 错误和警告
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# ===== 优化配置 =====
# 默认优化试验次数
DEFAULT_OPTIMIZATION_TRIALS = 100

# 默认优化超时时间（秒）
DEFAULT_OPTIMIZATION_TIMEOUT = 3600

# 默认优化指标
DEFAULT_OPTIMIZATION_METRIC = 'rmse'

# 默认采样器类型
DEFAULT_OPTIMIZATION_SAMPLER = 'TPE'

# 优化指标选项
OPTIMIZATION_METRICS = ['rmse', 'mae', 'r2', 'weighted']

# 采样器选项
OPTIMIZATION_SAMPLERS = ['TPE', 'Random', 'CMAES']

# 优化目标选项
OPTIMIZATION_TARGETS = ['both', 'cultivar', 'ch4']

# 观测数据必需列
OBSERVED_DATA_REQUIRED_COLUMNS = ['DAT']

# 观测数据可选列
OBSERVED_DATA_OPTIONAL_COLUMNS = ['Biomass', 'CH4', 'RootBiomass', 'LAI', 'Yield', 'Stage', 'Notes']

# 参数空间定义（基于28个品种的统计分析）
PARAMETER_SPACE_CULTIVAR = {
    # 生育期参数（高度敏感）
    'PS': (0.020, 0.078),      # 感光性
    'TS': (2.55, 3.20),        # 感温性
    'TO': (25.8, 28.6),        # 最适温度
    'IE': (0.10, 0.20),        # 基本早熟性
    'HF': (0.010, 0.015),      # 高温因子
    'FDF': (0.688, 0.727),     # 灌浆因子

    # 收获相关（高度敏感）
    'PHI': (0.427, 0.480),     # 收获指数 ✅ 修正：原为 (185, 210)
    'TGW': (24.0, 28.0),       # 千粒重 (g)

    # 光合参数（高度敏感）
    'SLAc': (184, 207),        # 比叶面积 (cm²/g)
    'PF': (0.0138, 0.0161),    # 光合衰减因子
    'AMX': (41.0, 48.0),       # 最大光合速率
    'KF': (0.0072, 0.0090),    # 消光系数因子

    # 呼吸参数
    'RGC': (0.27, 0.32),       # 生长呼吸系数
    'LRS': (0.0058, 0.0075),   # 根系相对呼吸

    # 形态参数（中度敏感）
    'TLN': (14.5, 18.3),       # 总叶龄
    'EIN': (4.6, 5.5),         # 伸长节间数
    'TA': (0.42, 0.52),        # 分蘖能力

    # 品质参数（低敏感）
    'SGP': (6.15, 6.50),       # 籽粒生长势
    'PC': (7.4, 8.4),          # 蛋白质含量 (%)
    'RAR': (1.92, 2.36),       # 根系吸收速率
}

PARAMETER_SPACE_CH4 = {
    'Q10': (2.0, 4.0),       # 温度敏感性系数
    'Eh0': (200.0, 300.0),   # 初始氧化还原电位
    'EhBase': (-50.0, 50.0), # 基础氧化还原电位
    'WaterC': (0.5, 0.8),    # 水分含量
}
