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

### 2.1 Web 服务器托管与 Oracle Cloud ARM64 实例申领 (Phase 2)
考虑到项目核心 AI 的低计算配额与极致降本需求，我们的目标生产环境为 **Oracle Cloud (甲骨文云) 的 Always Free ARM64 (Ampere A1) 实例**。

**运维实操指南 (Oracle Cloud Provisioning)**：
1. **注册与绑卡**：访问 `cloud.oracle.com` 注册账号并验证外币信用卡。
2. **创建计算实例 (Compute)**：
   - 导航至：`Compute` -> `Instances` -> `Create Instance`。
   - **Image (镜像)**: 选择 `Canonical Ubuntu 22.04/24.04 (aarch64)`。
   - **Shape (规格)**: 选择 `Ampere (ARM)` 架构下的 `VM.Standard.A1.Flex`。
   - **配置拉满 (关键)**: 在 OCPU 数选择 `4`，Memory (内存) 选择 `24GB`。(这是免费额度的上限，满足我们的多路 STT 引擎计算需求)。
3. **网络安全组与域名解析 (Nginx 铺垫)**：
   - 在 Oracle VCN 中，开放 Ingress 端口 `80` (HTTP) 和 `443` (HTTPS)。
   - (可选) 去您的域名注册商处，将子域名的 `A` 记录指向刚分配的服务器公网 IP。
4. **服务器出厂预装**：使用 SSH 登录这台新机器，仅需安装基础环境：
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose git ffmpeg
   ```
至此，最底层的免费云宿主机就搭好了，后续将配合 GitHub Actions 和多架构 Docker 无缝承接构建流。

### 2.2 Docker 容器云编排 (跨架构跨云迁移)
- **预留规划**: 本项目未来的完整形态将抛弃繁杂的 `python -m venv`。在 2.1 规划的 Oracle 机器就绪后，我们将编写多架构 `Dockerfile (linux/amd64, linux/arm64)`。您只需在服务器上拉下代码并执行 `docker-compose up -d` 即可。

### 2.3 前端站点 CDN 加速分发 (静态资源托管)
- **预留规划**: （Phase 4 后端联调时）指导您如何利用 Vercel, Cloudflare, 或 Nginx 将基于 React / Vite 编译出的静态病历阅览后台打包分发到全球边缘节点。
