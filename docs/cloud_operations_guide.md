# PtClinVoice 云端作业与运维部署指南 (Cloud Operations Guide)

**文档目标**: 
本项目虽然核心 STT 与 PII 拦截层由于隐私红线必须部署在医院本地（On-Premise），但后续诸多高级功能的提炼与前端站点的托管将依赖云基础设施。
本文档专为 SRE 和运维负责人编写，用于逐步记录整个项目生命周期中所有**必须由人工介入（或手工配置）的云端对接操作**。

---

## 1. 大语言模型 API 对接 (已完成验收)

**涉及模块**: `deepseek_adapter.py`
**外部服务依赖**: DeepSeek Cloud API (`api.deepseek.com`)

### 1.1 手动操作指导 (Manual Operations Required)
为了分离开发代码与云端账单权限，您需要：
1. 登录您的 DeepSeek 开发者控制台。
2. 生成一个全新的 API 密钥 (API Key)。
3. 在部署 PtClinVoice 后台服务的服务器上，进入项目根目录。
4. **必须手动创建**一个隐形文件 `.env`，并在此文件内定义云密钥：
   ```bash
   DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   ```
   *(注: `.env` 永远不应该被推送到任何代码管理库中，项目中已有 `.gitignore` 强制拦截。)*

### 1.2 连通性测试 (Connectivity Validation)
完成上述环境变量注入后，请在项目根目录运行预装的核查探针脚本，无需启动整个 Web 后台即可验证云端握手：
```bash
source .venv/bin/activate
python3 test_real_deepseek_api.py
```
如见 `✅ 深蓝测试 (DeepSeek API) 成功通过` 字样，即代表您的密钥拥有合法的余额并且能成功绕开医院防火墙到达外网大模型集群。

---

## 2. 后续将要集成的云端操作 (Upcoming Workloads - Phase 2+)

*(以下条目将在我们推进开发时，持续更新为您提供详尽的保姆级入参和云端配置教程)*

### 2.1 Web 服务器托管 (VPS / 弹性计算云)
- **预留规划**: 将在未来指导您如何在 AWS EC2 或阿里云等计算节点上架设 Nginx，开启 443 端口，并申请免费的自签 HTTPS CA 证书以满足医疗数据加密传输。

### 2.2 Docker 容器云编排
- **预留规划**: 本项目未来的完整形态将抛弃繁杂的 `python -m venv`，我将为您手写轻量级的 `Dockerfile`。届时您需要在云服务器上安装 Docker 环境，并通过我给您的 `docker-compose.yml` 命令行实现一键无痛起转。

### 2.3 前端站点 CDN 加速分发 (前端静态资源托管)
- **预留规划**: （Phase 4 后端点联调时）指导您如何利用 Vercel, Cloudflare, 或 Nginx 将基于 React / Vite 编译出的静态病历阅览后台 `.html, .js` 等资产打包并分发到外网，对接您刚刚启动的后台 API。
