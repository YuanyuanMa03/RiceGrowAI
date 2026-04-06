#!/bin/bash
# 为空目录创建 .gitkeep 文件

DIRS=(
    "uploads/observations"
    "uploads/calibration_results"
    "uploads/temp"
    "logs"
)

for dir in "${DIRS[@]}"; do
    mkdir -p "$dir"
    touch "$dir/.gitkeep"
done

echo "已创建 .gitkeep 文件"
