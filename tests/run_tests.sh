#!/bin/bash
# 测试运行脚本

set -e

echo "========================================="
echo "  水稻生长与CH4排放模拟系统 - 测试套件"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否安装了pytest
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest 未安装${NC}"
    echo "请运行: pip install pytest pytest-cov"
    exit 1
fi

# 解析命令行参数
TEST_TYPE=""
COVERAGE_FLAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_TYPE="-m unit"
            shift
            ;;
        --integration)
            TEST_TYPE="-m integration"
            shift
            ;;
        --no-coverage)
            COVERAGE_FLAG="--no-cov"
            shift
            ;;
        --fast)
            TEST_TYPE="-m 'not slow'"
            shift
            ;;
        -h|--help)
            echo "用法: ./run_tests.sh [选项]"
            echo ""
            echo "选项:"
            echo "  --unit         只运行单元测试"
            echo "  --integration  只运行集成测试"
            echo "  --fast         跳过慢速测试"
            echo "  --no-coverage  不生成覆盖率报告"
            echo "  -h, --help     显示此帮助信息"
            exit 0
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            exit 1
            ;;
    esac
done

# 显示测试信息
echo "测试类型: ${TEST_TYPE:-所有测试}"
echo "覆盖率: ${COVERAGE_FLAG:+否}${COVERAGE_FLAG:-是}"
echo ""

# 运行测试
echo -e "${YELLOW}▶ 运行测试...${NC}"
echo ""

if pytest tests/ $TEST_TYPE $COVERAGE_FLAG -v; then
    echo ""
    echo -e "${GREEN}✅ 所有测试通过!${NC}"

    # 显示覆盖率报告路径
    if [ -z "$COVERAGE_FLAG" ]; then
        echo ""
        echo -e "${GREEN}📊 覆盖率报告已生成: htmlcov/index.html${NC}"
    fi
    exit 0
else
    echo ""
    echo -e "${RED}❌ 测试失败${NC}"
    exit 1
fi
