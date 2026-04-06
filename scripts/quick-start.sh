#!/bin/bash

# ============================================
# 快速启动脚本（用于已配置环境）
# ============================================

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TUNNEL_NAME="rice-simulation"

cd $PROJECT_DIR

echo "🚀 快速启动水稻模拟系统..."

# 启动Streamlit
if ! lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null ; then
    echo "启动Streamlit..."
    streamlit run app.py --server.port 8501 > /tmp/streamlit.log 2>&1 &
    STREAMLIT_PID=$!
    echo $STREAMLIT_PID > /tmp/rice-streamlit.pid
    echo "✅ Streamlit已启动 (PID: $STREAMLIT_PID)"
else
    echo "✅ Streamlit已在运行"
fi

# 启动Cloudflare Tunnel
if ! pgrep -f "cloudflared tunnel run.*$TUNNEL_NAME" > /dev/null; then
    echo "启动Cloudflare Tunnel..."
    cloudflared tunnel run --config ~/.cloudflared/$TUNNEL_NAME.yml > /tmp/tunnel.log 2>&1 &
    TUNNEL_PID=$!
    echo $TUNNEL_PID > /tmp/rice-tunnel.pid
    echo "✅ Cloudflare Tunnel已启动 (PID: $TUNNEL_PID)"
else
    echo "✅ Cloudflare Tunnel已在运行"
fi

echo ""
echo "🎉 系统已启动！"
echo "📱 访问: https://rice.mayuanyuan.top"
echo "📊 本地: http://localhost:8501"
