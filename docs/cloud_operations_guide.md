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
   - **配置拉满 (关键)**: 由于这是 Flex (弹性) 实例，默认显示可能只有 1 OCPU 和 6GB 内存。请手动拖拽进度条：在 OCPU 数选择 `4`，Memory (内存) 选择 `24GB`。(这是免费额度的上限，满足我们的多路 STT 引擎计算需求)。
     - ⚠️ **SRE 避坑预警 (Out of Capacity)**: 如果您在点击创建时遇到 `Out of capacity for shape VM.Standard.A1.Flex` 的错误，这是 Oracle 免费宿主机池常见现象（通常是因为您所在的机房/区域当前没有空闲的 ARM 物理机资源）。**解决方法**：尝试更换 Availability Domain（如果您的区域有多个可用区），或者等待几天后避开高峰期重试。在此期间，我们的所有代码均支持在本地或任何 x86 服务器上进行开发与测试。
3. **网络连通性编排 (Networking & Security)**：
   默认情况下，Oracle 的实例即使绑定了公网 IP 也是处于“失联”状态的。必须执行以下链路打通：
   - **创建 VCN (虚拟云网络)**: 导航至 Networking -> Virtual Cloud Networks。新建 VCN (如 `10.0.0.0/24`) 与 Public Subnet。**无需分配 IPv6**。
   - **配置互联网网关 (Internet Gateway)**: 在 VCN 详情页左侧点击 Internet Gateways，新建一个网关并命名。
   - **更新路由表 (Route Table)**: 点击 VCN 左侧的 Route Tables，进入 `Default Route Table`，添加规则：Target Type 选 `Internet Gateway`，Destination CIDR 填 `0.0.0.0/0`，Target 选刚才建好的网关。（这一步让服务器的公网流量能找到出口）。
   - **放行安全列表 (Security List)**: 点击 VCN 左侧的 Security Lists，进入 `Default Security List`。默认已放行 SSH (端口 `22`)。为了后续 API 访问，请**务必添加 Ingress (入站) 规则**：Source CIDR `0.0.0.0/0`，IP Protocol `TCP`，Destination Port Range 填 `80,443,8000` (8000为后续 FastAPI 端口)。
4. **绑定密钥与实例开通**:
   - 在创建实例页面的网络层，选择刚才配置好的 VCN 和 Public Subnet。
   - **关键环节**: 在 `Add SSH keys` 处选择 `Save private key`，一定要下载 `.key` 文件，这是唯一登录凭证。点击创建。
4. **服务器出厂预装**：使用 SSH 登录这台新机器，仅需安装基础环境：
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose git ffmpeg
   ```
至此，最底层的免费云宿主机就搭好了，后续将配合 GitHub Actions 和多架构 Docker 无缝承接构建流。

### 2.2 Docker 容器云编排测试 (Phase 2.3+)
由于我们的 `ghcr.io/lynptl/ptclinvoice:latest` 镜像是严格基于 `linux/amd64` 构建，并且全量包含好了 `12MB SpaCy` 与 `ffmpeg` 依赖底包，它非常适合在您的 Oracle VM.Standard.E5.Flex (AMD x86_64) 或其他架构上进行“即开即用”的空降测试。

为了遵守我们定下的“极简与不可变基础设施”底线，您在云端实例上**完全不需要拉取整个 Git 仓库的代码**。请通过 SSH 登入您的 Oracle Cloud 实例，依次执行：

#### 第一步：云端装配容器引擎 (如果未经开通)
```bash
# 刷新包记录并装配 Docker
sudo apt update && sudo apt install -y docker.io docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# (若新将用户拉入 docker 用户组，建议退出 SSH 重登录使权限生效)
```

#### 第二步：注入隐私数据防线 (构建 `.env` 与隔离挂载点)
```bash
# 构建工程专属沙盒目录
mkdir -p ~/ptclinvoice_deploy/data
cd ~/ptclinvoice_deploy

# >>> 【授权检查点】：这是您需要手工处理的唯一地方 <<<
# 创建隐形环境变量记录表，并贴入您的真实 DeepSeek API Key
cat << 'EOF' > .env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EOF
```

#### 第三步：一键同步 SRE 规范编排文件
为了让云主机复现我们本地刚写好的 SQLite WAL 防御挂载和原生 Healthcheck 探针，您**不需要手动使用 vim/nano 新建文件去粘贴**。

请**直接将下方这整段 Bash 命令框里的内容完整复制**，然后粘贴到您的 SSH 终端按下回车。这条命令会自动利用内置工具在当前目录下生成配置无误的 `docker-compose.yml` 文件：
```bash
cat << 'EOF' > docker-compose.yml
services:
  ptclinvoice-api:
    image: ghcr.io/lynptl/ptclinvoice:latest
    container_name: ptclinvoice-api
    restart: always
    ports:
      - "8000:8000"
    healthcheck:
      test: [ "CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\" || exit 1" ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
    environment:
      - DB_PATH=/app/data/ptclinvoice_sre.db
      - TZ=UTC
    env_file:
      - .env
    volumes:
      - ./data:/app/data
EOF
```

#### 第四步：远程拉起与验收打卡
```bash
# 一键空降指令：强制拉取我们在 Github Actions 上刚出炉的 Phase 2.3 最新包，并在后台拉起
sudo docker-compose pull && sudo docker-compose up -d

# 立刻探活
curl http://localhost:8000/health
# 预期秒回：{"status": "ok", "service": "PtClinVoice API"}

# (可选) 查看刚写好的 SRE 自诊断探针运行履历
sudo docker inspect --format="{{json .State.Health}}" ptclinvoice-api
```
一旦走完最后一步且 `curl` 通畅无误的返回 JSON，并在浏览器能够访问 `http://<您的Oracle公网IP>:8000/docs` 查看 Swagger UI，代表部署彻底收官！

### 2.3 前端站点 CDN 加速分发 (静态资源托管)
- **预留规划**: （Phase 4 后端联调时）指导您如何利用 Vercel, Cloudflare, 或 Nginx 将基于 React / Vite 编译出的静态病历阅览后台打包分发到全球边缘节点。
