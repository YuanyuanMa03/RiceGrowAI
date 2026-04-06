#!/bin/bash

# ============================================
# 停止水稻模拟系统服务
# ============================================

echo "🛑 停止水稻模拟系统服务..."

# 停止Streamlit
if [ -f /tmp/rice-streamlit.pid ]; then
    PID=$(cat /tmp/rice-streamlit.pid)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "✅ Streamlit已停止 (PID: $PID)"
    else
        echo "⚠️  Streamlit进程不存在"
    fi
    rm -f /tmp/rice-streamlit.pid
else
    # 尝试通过端口查找并停止
    if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null ; then
        PID=$(lsof -t -i:8501)
        kill $PID
        echo "✅ Streamlit已停止 (PID: $PID)"
    fi
fi

# 停止Cloudflare Tunnel
if [ -f /tmp/rice-tunnel.pid ]; then
    PID=$(cat /tmp/rice-tunnel.pid)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "✅ Cloudflare Tunnel已停止 (PID: $PID)"
    else
        echo "⚠️  Cloudflare Tunnel进程不存在"
    fi
    rm -f /tmp/rice-tunnel.pid
else
    # 尝试停止所有cloudflared进程
    pkill -f "cloudflared tunnel run" && echo "✅ Cloudflare Tunnel已停止" || true
fi

echo "🎉 所有服务已停止"
