# 🚀 快速开始指南

## 📱 一键部署（推荐）

### 本地部署（5分钟完成）

```bash
# 1. 进入项目目录
cd /Users/mayuanyuan/Desktop/R_C_N

# 2. 运行部署脚本
./deploy-local.sh
```

**脚本会自动：**
1. ✅ 安装cloudflared
2. ✅ 登录Cloudflare
3. ✅ 创建隧道
4. ✅ 配置隧道
5. ✅ 启动应用
6. ✅ 启动隧道

### 配置DNS（1分钟）

在Cloudflare控制台添加：
- **类型**: CNAME
- **名称**: rice
- **目标**: `your-tunnel-id.cfarg.net`
- **代理**: ☁️ 已代理

### 访问应用
```
https://rice.mayuanyuan.top
```

---

## 🎯 使用Make命令（更简单）

```bash
# 查看所有命令
make help

# 首次部署
make deploy

# 启动服务
make start

# 停止服务
make stop

# 查看状态
make status

# 查看日志
make logs

# 重启服务
make restart
```

---

## 🐳 Docker部署（推荐生产环境）

```bash
# 启动所有服务
make docker-up

# 查看日志
make docker-logs

# 停止服务
make docker-down
```

---

## 📊 管理命令速查

| 操作 | 命令 |
|------|------|
| 启动 | `make start` 或 `./quick-start.sh` |
| 停止 | `make stop` 或 `./stop.sh` |
| 重启 | `make restart` |
| 状态 | `make status` |
| 日志 | `make logs` |
| 部署 | `make deploy` |

---

## 🔗 访问地址

- **主地址**: https://rice.mayuanyuan.top
- **备用**: https://app.mayuanyuan.top
- **本地**: http://localhost:8501

---

## ❓ 遇到问题？

### 查看详细文档
```bash
cat DEPLOYMENT.md
```

### 检查服务状态
```bash
make status
```

### 查看日志
```bash
make logs
```

### 重启服务
```bash
make restart
```

---

## ✅ 部署检查清单

- [ ] cloudflared已安装
- [ ] 已登录Cloudflare
- [ ] 隧道已创建
- [ ] DNS记录已配置
- [ ] Streamlit已启动
- [ ] Cloudflare Tunnel已运行
- [ ] 可以访问 https://rice.mayuanyuan.top

---

**准备就绪？运行 `make deploy` 开始部署！** 🚀
