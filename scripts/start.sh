#!/bin/bash

# 水稻模拟系统 - 启动脚本
# 用法: ./start.sh

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TUNNEL_NAME="rice-simulation"
CONFIG_FILE="$HOME/.cloudflared/$TUNNEL_NAME.yml"

cd $PROJECT_DIR

echo "🚀 启动水稻模拟系统..."

# 启动Streamlit
if ! lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null ; then
    echo "启动 Streamlit..."
    nohup streamlit run app.py --server.port 8501 --server.headless true > /tmp/streamlit.log 2>&1 &
    STREAMLIT_PID=$!
    echo $STREAMLIT_PID > /tmp/rice-streamlit.pid
    echo "✅ Streamlit已启动 (PID: $STREAMLIT_PID)"
else
    echo "✅ Streamlit已在运行"
fi

# 启动Cloudflare Tunnel
if ! pgrep -f "cloudflared tunnel.*$TUNNEL_NAME" > /dev/null; then
    echo "启动 Cloudflare Tunnel..."
    nohup cloudflared tunnel --config "$CONFIG_FILE" run > /tmp/tunnel.log 2>&1 &
    TUNNEL_PID=$!
    echo $TUNNEL_PID > /tmp/rice-tunnel.pid
    echo "✅ Cloudflare Tunnel已启动 (PID: $TUNNEL_PID)"
else
    echo "✅ Cloudflare Tunnel已在运行"
fi

echo ""
echo "🎉 系统已启动！"
echo "📱 公网访问: https://rice.mayuanyuan.top"
echo "📊 本地访问: http://localhost:8501"
echo ""
echo "查看日志:"
echo "  tail -f /tmp/streamlit.log  # 应用日志"
echo "  tail -f /tmp/tunnel.log     # 隧道日志"
