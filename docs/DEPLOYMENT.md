# 水稻模拟系统 - Cloudflare部署指南

## 🌐 域名信息
- 主域名: `mayuanyuan.top`
- 应用地址: `rice.mayuanyuan.top`
- 备用地址: `app.mayuanyuan.top`

---

## 📋 部署前准备

### 1. 检查Cloudflare状态
确保 `mayuanyuan.top` 已添加到Cloudflare：
1. 登录 https://dash.cloudflare.com
2. 检查域名是否在列表中
3. 确保域名状态为 "Active"

### 2. 安装cloudflared
```bash
# macOS
brew install cloudflare/cloudflare/cloudflared

# 验证安装
cloudflared --version
```

---

## 🚀 方式一：本地部署（推荐用于测试）

### 步骤1: 首次部署
```bash
cd /Users/mayuanyuan/Desktop/R_C_N

# 赋予执行权限
chmod +x deploy-local.sh stop.sh quick-start.sh

# 运行部署脚本
./deploy-local.sh
```

脚本会自动：
1. ✅ 检查并安装cloudflared
2. ✅ 登录Cloudflare账户
3. ✅ 创建隧道
4. ✅ 配置隧道
5. ✅ 提示配置DNS

### 步骤2: 配置DNS
在Cloudflare控制台添加DNS记录：

**记录1:**
- 类型: `CNAME`
- 名称: `rice`
- 目标: `your-tunnel-id.cfarg.net`
- TTL: Auto
- 代理状态: ☁️ 已代理（橙色云朵）

**记录2（可选）:**
- 类型: `CNAME`
- 名称: `app`
- 目标: `your-tunnel-id.cfarg.net`
- TTL: Auto
- 代理状态: ☁️ 已代理

### 步骤3: 访问应用
```
https://rice.mayuanyuan.top
```

### 日常使用
```bash
# 启动服务
./quick-start.sh

# 停止服务
./stop.sh

# 查看日志
tail -f /tmp/streamlit.log
tail -f /tmp/tunnel.log
```

---

## 🖥️ 方式二：Docker部署（推荐用于生产）

### 1. 构建并启动
```bash
cd /Users/mayuanyuan/Desktop/R_C_N

# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 2. 管理命令
```bash
# 停止服务
docker-compose stop

# 启动服务
docker-compose start

# 重启服务
docker-compose restart

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f app
docker-compose logs -f tunnel
```

### 3. 更新应用
```bash
# 停止并删除容器
docker-compose down

# 重新构建
docker-compose up -d --build
```

---

## 🌍 方式三：VPS部署（最稳定）

### 前提条件
- 一台VPS（推荐: 阿里云/腾讯云/AWS）
- 域名已添加到Cloudflare
- VPS可以访问Docker Hub

### 步骤1: 准备VPS
```bash
# SSH连接VPS
ssh root@your-vps-ip

# 安装Docker
curl -fsSL https://get.docker.com | sh

# 安装Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 步骤2: 上传代码
```bash
# 在本地执行
scp -r /Users/mayuanyuan/Desktop/R_C_N root@your-vps-ip:/root/rice-simulation
```

### 步骤3: 在VPS上部署
```bash
# SSH到VPS
ssh root@your-vps-ip

# 进入项目目录
cd /root/rice-simulation

# 启动服务
docker-compose up -d

# 检查状态
docker-compose ps
```

### 步骤4: 配置DNS
在Cloudflare添加A记录：
- 类型: `A`
- 名称: `rice`
- IPv4地址: `your-vps-ip`
- 代理状态: ☁️ 已代理

### 步骤5: 访问应用
```
https://rice.mayuanyuan.top
```

---

## 🔧 故障排查

### 问题1: 无法访问域名
**检查:**
```bash
# 1. 检查DNS解析
ping rice.mayuanyuan.top

# 2. 检查隧道状态
cloudflared tunnel info rice-simulation

# 3. 检查本地服务
curl http://localhost:8501
```

### 问题2: 隧道连接失败
**解决:**
```bash
# 重启隧道
cloudflared tunnel run --config ~/.cloudflared/rice-simulation.yml

# 查看隧道日志
cat ~/.cloudflared/*.log
```

### 问题3: Streamlit无法启动
**检查:**
```bash
# 查看端口占用
lsof -i :8501

# 查看Python版本
python --version

# 手动启动测试
streamlit run app.py
```

---

## 📊 性能优化

### 1. Cloudflare缓存设置
在Cloudflare控制台 → 缓存 → 配置：
- 浏览器缓存TTL: 4小时
- 闩级: 开启
- Brotli: 开启

### 2. 安全设置
- 防火墙规则: 仅允许Cloudflare IP访问VPS
- SSL/TLS: Full (strict)
- 始终使用HTTPS: 开启

### 3. 监控
```bash
# Cloudflare分析
https://dash.cloudflare.com/anan/app/traffic

# 应用健康检查
curl https://rice.mayuanyuan.top/_stcore/health
```

---

## 📞 支持

如有问题，请检查：
1. Cloudflare Dashboard
2. Docker日志: `docker-compose logs -f`
3. Streamlit日志: `/tmp/streamlit.log`
