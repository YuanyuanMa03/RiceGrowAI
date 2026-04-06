#!/bin/bash

# ============================================
# 水稻模拟系统 - Cloudflare本地部署脚本
# 域名: rice.mayuanyuan.top
# ============================================

set -e

DOMAIN="rice.mayuanyuan.top"
TUNNEL_NAME="rice-simulation"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "🚀 ========================================"
echo "   水稻模拟系统 - Cloudflare部署"
echo "   域名: $DOMAIN"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查cloudflared
echo -e "${BLUE}[1/7]${NC} 检查cloudflared..."
if ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}⚠️  未安装cloudflared，正在安装...${NC}"
    brew install cloudflare/cloudflare/cloudflared
    echo -e "${GREEN}✅ cloudflared安装完成${NC}"
else
    echo -e "${GREEN}✅ cloudflared已安装${NC}"
fi

# 登录Cloudflare
echo ""
echo -e "${BLUE}[2/7]${NC} 检查Cloudflare登录状态..."
if [ ! -d ~/.cloudflared ]; then
    echo -e "${YELLOW}⚠️  需要登录Cloudflare...${NC}"
    cloudflared tunnel login
    echo -e "${GREEN}✅ 登录成功${NC}"
else
    echo -e "${GREEN}✅ 已登录${NC}"
fi

# 创建隧道
echo ""
echo -e "${BLUE}[3/7]${NC} 创建Cloudflare Tunnel..."
if ! cloudflared tunnel info $TUNNEL_NAME &> /dev/null; then
    echo "创建新隧道..."
    cloudflared tunnel create $TUNNEL_NAME
    echo -e "${GREEN}✅ 隧道创建成功${NC}"
else
    echo -e "${GREEN}✅ 隧道已存在${NC}"
fi

# 获取隧道ID
TUNNEL_ID=$(cloudflared tunnel list | grep $TUNNEL_NAME | awk '{print $1}')
echo "隧道ID: $TUNNEL_ID"

# 配置隧道
echo ""
echo -e "${BLUE}[4/7]${NC} 配置隧道..."
mkdir -p "$HOME/.cloudflared"
cat > "$HOME/.cloudflared/$TUNNEL_ID.yml" << EOF
tunnel: $TUNNEL_ID
credentials-file: $HOME/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: $DOMAIN
    service: http://localhost:8501
  - hostname: app.mayuanyuan.top
    service: http://localhost:8501
  - service: http_status:404
EOF

# 配置DNS
echo ""
echo -e "${BLUE}[5/7]${NC} 配置DNS记录..."
echo "请确保在Cloudflare控制台添加以下DNS记录："
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "类型: CNAME"
echo "名称: rice"
echo "目标: $TUNNEL_ID.cfarg.net"
echo "代理状态: ☁️ 已代理（橙色云朵）"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
read -p "已完成DNS配置? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}✅ DNS配置完成${NC}"
else
    echo -e "${YELLOW}⚠️  请稍后在Cloudflare控制台配置DNS${NC}"
fi

# 启动Streamlit
echo ""
echo -e "${BLUE}[6/7]${NC} 启动Streamlit应用..."
cd $PROJECT_DIR

# 检查是否已在运行
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}⚠️  端口8501已被占用，尝试停止...${NC}"
    kill $(lsof -t -i:8501)
    sleep 2
fi

echo "启动Streamlit..."
streamlit run app.py --server.port 8501 &
STREAMLIT_PID=$!
echo -e "${GREEN}✅ Streamlit已启动 (PID: $STREAMLIT_PID)${NC}"

# 等待Streamlit启动
echo "等待应用启动..."
sleep 5

# 启动Cloudflare Tunnel
echo ""
echo -e "${BLUE}[7/7]${NC} 启动Cloudflare Tunnel..."
cloudflared tunnel run --config ~/.cloudflared/$TUNNEL_ID.yml &
TUNNEL_PID=$!
echo -e "${GREEN}✅ Cloudflare Tunnel已启动 (PID: $TUNNEL_PID)${NC}"

# 保存PID
echo $STREAMLIT_PID > /tmp/rice-streamlit.pid
echo $TUNNEL_PID > /tmp/rice-tunnel.pid

# 完成
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "📱 访问地址:"
echo -e "   ${BLUE}https://$DOMAIN${NC}"
echo -e "   ${BLUE}https://app.mayuanyuan.top${NC}"
echo ""
echo -e "📊 本地地址:"
echo -e "   ${BLUE}http://localhost:8501${NC}"
echo ""
echo -e "⚙️  管理命令:"
echo -e "   查看日志: tail -f ~/.cloudflared/*.log"
echo -e "   停止服务: kill $STREAMLIT_PID $TUNNEL_PID"
echo -e "   重启服务: ./deploy-local.sh"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo ""

# 捕获退出信号
cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止服务...${NC}"
    kill $STREAMLIT_PID 2>/dev/null || true
    kill $TUNNEL_PID 2>/dev/null || true
    rm -f /tmp/rice-streamlit.pid /tmp/rice-tunnel.pid
    echo -e "${GREEN}✅ 服务已停止${NC}"
    exit 0
}

trap cleanup INT TERM

# 保持运行
wait
