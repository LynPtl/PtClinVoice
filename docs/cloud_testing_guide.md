# 云端部署验收与全栈测试指南 (Cloud E2E Testing Guide)

在通过 `docker-compose` 将本全栈解决方案（Nginx Web 代理 + FastAPI 后端）拉起至公有云（如 Oracle Cloud）或隔离的内网宿主机后，需按照本测试文档进行系统性的一致性校验（Sanity Checks）与端到端（E2E）功能走查。

---

## 摘要 (Summary)
**前置条件**: 
* 您已按照 [云端作业与运维部署指南 (Cloud Operations Guide)](cloud_operations_guide.md) 中的指引，完成了 `docker-compose up -d` 启动操作。
* 已获得宿主机的可用公网 IP 或域名映射，并已在云厂商控制台（如 Security Lists）和操作系统层（`iptables` / `firewalld`）双重放行了 `80` 和 `8000` 端口。

## 1. 基础设施底座探活 (Infrastructure Health Checks)

### 1.1 后端 API 心跳校验
后端设计了脱离业务逻辑的纯粹探针，用于验证 Python 进程和端口挂载是否成功被容器运行时透传。
```bash
# 在您的本地电脑或任意终端执行：
curl http://<宿主机_IP>:8000/health

# ✅ [预期输出]
# {"status": "ok", "service": "PtClinVoice API"}
```
> **排雷建议 (Troubleshooting)**: 如果长时间无响应（挂起卡死），100% 概率是因为云服务商网络安全组限制或云主机内的 `iptables` 未放行入站 `8000` 请求。如果返回 `Connection Refused`，请登录宿主机执行 `docker ps -a` 检查容器是否由于 `.env` 缺失或镜像拉取失败等原因未能存活。

### 1.2 前端 Nginx 网关拉取
直接在浏览器地址栏敲入目标主机的外网地址进入 PtClinVoice 临床前端系统：
```text
http://<宿主机_IP>
```
* **✅ [预期行为]**: 浏览器立即重定向至 `http://<宿主机_IP>/login`，呈现带有 "Welcome to PtClinVoice" 和医疗配色的登录表单，而不是浏览器默认的 404 或 Nginx 欢迎页。

## 2. 核心链路贯通性校验 (Core Pipeline E2E Walkthrough)

云端测试不应过分关注代码层面的单元覆盖，而应聚拢在网络边界互信（CORS）与异步长效队列（Celery 机制的 Background Tasks）之上。

### 2.1 鉴权与 Nginx 反向代理校验 (Proxy Routing Test)
在可视化的 Login 表单中：
1. **输入凭证**: 使用内置测服账号，例如 `dr_bob` / `password123`。（如果由于隐私模式未开放注册，系统设计在 `test_auth.py` 里固定了此 Mock 账户数据或者要求直接调用 API 生成）。
2. **点击提交**: 
   - **✅ [成功预期]**: 控制台将跳转回 `/dashboard`，界面上渲染出对应的欢迎词。这同时也**侧面证明了**部署在 Nginx 端内的 `location /api/ { proxy_pass http://ptclinvoice-api:8000; }` 内部反向解析链路100% 完美连通且规避了同源 CORS 跨域。
   - **❌ [失败情形]**: 如果浏览器 DevTools 的 Network 面板抛出对 `/api/auth/login` 的 `502 Bad Gateway` 报错，那意味着虽然 Nginx 起立了，但后端的 FastAPI 挂了（需排查 `ptclinvoice-api` 容器日志）。

### 2.2 上发通道与物理防泄漏测试 (Upload & Shredding Pipeline)
1. 在 Dashboard 核心区域，随意拖拽或选择一个 `.wav` / `.mp3` 音频文件上传。
2. 上传完毕后立刻进入右侧的 **历史任务列表 (Task List)**。
3. **✅ [动态同步预期]**: 您应该看到该任务以 `PENDING` 态展示。关键验证点：**不要手动刷新页面**，几十秒内它必须自动演变成 `COMPLETED`（代表基于 SSE 技术的服务端长连接推送通道已穿透 Nginx）。
4. **✅ [隐私销毁预期 (Burn-after-reading)]**: 此时，SSH 切入云主机，执行内部探查：
    ```bash
    # 进入宿主机数据持久化挂载目录
    sudo ls -la ~/ptclinvoice_deploy/data/uploads/
    ```
    **要求**: 目录必须是空的，或者严格不见您刚上传的数据源片段。这表明业务代码成功在转录结束后执行了深度物理 `os.remove()`。

## 3. 并发抗压评估 (Load Testing Basics)

如果您的 Oracle A1 实例获得了 4 OCPU 和 24GB 内存：

使用并发施压工具（如 `ab`，且携带 JWT），对其发包以验证 SQLite WAL（写前日志）在极速 I/O 下的脏页收敛能力：
```bash
# 生成 JWT
TOKEN=$(curl -s -X POST "http://<宿主机_IP>:8000/api/auth/login" -H "Content-Type: application/x-www-form-urlencoded" -d "username=dr_bob&password=password123" | jq -r .access_token)

# 对列表查询接口施加 200 并发压测
ab -n 5000 -c 200 -H "Authorization: Bearer $TOKEN" http://<宿主机_IP>:8000/api/tasks/
```
**✅ [预期结果]**: API 拒绝率为 0%，并且宿主机的 SQLite 持久化目录 `~/ptclinvoice_deploy/data` 内的 `.db-wal` 的尺寸发生剧烈抖动然后快速合并，说明存储引擎运作在最优状态。

---
*本文档受控于系统架构组。所有核心全流程验证跑通后，允许截取 Dashboard 首页并签署进入生产期 (GA)。*
