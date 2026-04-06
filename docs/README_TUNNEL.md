# 水稻模拟系统 - Cloudflare Tunnel 配置

## 📋 概述

本项目已配置好 Cloudflare Tunnel，用于将本地 Streamlit 应用暴露到公网。

## 🚀 快速开始

### 1. 启动系统

```bash
# 启动 Streamlit 和 Cloudflare Tunnel
./start-all.sh
```

### 2. 检查状态

```bash
# 查看系统状态
./status.sh
```

### 3. 停止系统

```bash
# 停止所有服务
./stop.sh
```

## 📱 访问地址

- **本地访问**: http://localhost:8501
- **外部访问**: https://rice.mayuanyuan.top
- **备用地址**: https://app.mayuanyuan.top

## ⚠️ 当前问题

**Cloudflare Tunnel Token 已过期或无效**

### 解决方案

请按照以下步骤重新生成 Token：

1. **登录 Cloudflare Dashboard**
   - 访问：https://dash.cloudflare.com/
   - 使用你的 Cloudflare 账号登录

2. **进入 Zero Trust 管理**
   - 点击左侧菜单的 **Zero Trust**
   - 选择 **Networks** → **Tunnels**

3. **找到你的 Tunnel**
   - 在 Tunnels 列表中找到 `rice-simulation`
   - 点击 **Configure** 按钮

4. **重新生成 Token**
   - 在配置页面找到 **Installation** 部分
   - 选择 **Token** 选项卡
   - 点击 **Revoke token** 撤销旧 token
   - 复制新生成的 token

5. **更新启动脚本**
   - 编辑 `start-tunnel.sh`
   - 将 `TUNNEL_TOKEN` 的值更新为新 token
   - 保存文件

6. **重启系统**
   ```bash
   ./stop.sh
   ./start-all.sh
   ```

## 📚 详细文档

- **Tunnel 配置指南**: 查看 `TUNNEL_SETUP.md` 获取详细的配置步骤
- **设计文档**: 查看 `DESIGN_DOCUMENTATION.md`
- **部署文档**: 查看 `DEPLOYMENT.md`

## 🔧 管理命令

```bash
# 查看实时日志
tail -f /tmp/cloudflared.log

# 查看 Tunnel 信息
cloudflared tunnel info rice-simulation

# 测试连接
curl -I https://rice.mayuanyuan.top
curl -I http://localhost:8501
```

## 📊 系统架构

```
用户浏览器
    ↓
https://rice.mayuanyuan.top
    ↓
Cloudflare Edge (全球 CDN)
    ↓
Cloudflare Tunnel (加密隧道)
    ↓
localhost:8501 (Streamlit 应用)
    ↓
app.py (水稻生长与 CH4 排放模拟系统)
```

## 🛠️ 技术栈

- **前端**: Streamlit (Python)
- **反向代理**: Cloudflare Tunnel
- **协议**: HTTP/2
- **加密**: TLS 1.3

## 💡 常见问题

### Q: Tunnel 连接失败怎么办？
A: 检查网络连接，确保可以访问 Cloudflare。查看 `TUNNEL_SETUP.md` 获取详细解决方案。

### Q: 如何查看日志？
A: 运行 `tail -f /tmp/cloudflared.log` 查看 Tunnel 日志。

### Q: Token 无效怎么办？
A: 按照"当前问题"部分的步骤重新生成 Token。

### Q: Streamlit 无法访问怎么办？
A: 检查端口 8501 是否被占用，确保 Streamlit 进程正在运行。

## 📞 支持

如有问题，请查看：
- `TUNNEL_SETUP.md` - Tunnel 配置指南
- `TESTING_REPORT.md` - 测试报告
- Cloudflare 官方文档：https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/