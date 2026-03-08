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
如见 `[PASS] 深蓝测试 (DeepSeek API) 成功通过` 字样，即代表您的密钥拥有合法的余额并且能成功绕开医院防火墙到达外网大模型集群。

---

## 2. Web 服务器托管与 AWS EC2 实例部署指南 (Phase 2+)

为了在云端稳定运行包含了本地 STT 引擎和全栈 Web 架构的 PtClinVoice，我们将使用 **Amazon Web Services (AWS) EC2** 作为核心托管平台。

由于我们在 Docker 镜像中预先烘焙了 Faster-Whisper `small` 模型 (约 460MB) 和 `SpaCy` 模型，转录时有一定的内存峰值消耗，**强烈建议选择至少 4GB 内存的实例（如 `t3.medium` 或 `t3.large`）**，而非 1GB 的免费层 `t2.micro`（极容易 OOM 崩溃）。

### 2.1 启动 AWS EC2 实例 (Launch EC2 Instance)

1. **登录 AWS 管理控制台**并导航至 **EC2 Dashboard**。
2. 点击橙色按钮 **Launch instance (启动实例)**。
3. **Name and tags (名称和标签)**: 输入实例名称，例如 `PtClinVoice-Prod-Server`。
4. **Application and OS Images (Amazon Machine Image)**:
   - 搜索并选择 **Ubuntu**。
   - 版本选择 **Ubuntu Server 22.04 LTS (HVM) 或是 24.04 LTS**，架构保留默认的 **64-bit (x86_64)**。
5. **Instance type (实例类型)**:
   - 在下拉菜单中选择 **`t3.medium`** (2 vCPU, 4 GiB 内存) 或更高配置。
6. **Key pair (密钥对)**:
   - 选择一个现有的密钥对，或者点击 **Create new key pair**。
   - 命名为 `ptclinvoice-key`，类型 `RSA`，格式 `.pem`。**务必将下载的 `.pem` 文件妥善保管**，这是 SSH 登录的唯一凭证。
7. **Network settings (网络设置)**:
   - 点击 **Edit**。确保选择了拥有公网访问能力的 VPC 和 Subnet。
   - **Auto-assign public IP**: 设置为 **Enable (启用)**。
   - **Firewall (security groups)**: 选择 **Create security group**。
   - **Inbound security group rules (入站规则)**：在默认放行 SSH 以外，点击 **Add security group rule**，增加以下规则放路对外界的访问：
     - 类型: **HTTP**, 端口范围: `80`, 来源: `Anywhere (0.0.0.0/0)`
     - 类型: **Custom TCP**, 端口范围: `8000`, 来源: `Anywhere (0.0.0.0/0)` (FastAPI直接测试端口，可选)
8. **Configure storage (配置存储)**:
   - 将根卷大小调整为至少 **20 GiB** (gp3)，因为拉取和构建 Docker 镜像需要一定的磁盘空间。
9. 点击右下角的 **Launch instance** 完成创建。

### 2.2 连接到服务器并初始化环境 (Server Initialization)

1. 在 EC2 实例列表中，选中刚创建的实例，复制其 **Public IPv4 address (公网 IP)**。
2. 在您的本地终端中，通过 SSH 连接到服务器（注意替换密钥路径和 IP 地址）：
   ```bash
   # 修改密钥文件权限
   chmod 400 ptclinvoice-key.pem
   
   # SSH 登录目标服务器
   ssh -i "ptclinvoice-key.pem" ubuntu@<您的EC2公网IP>
   ```

3. **服务器出厂预装 (Docker & Git)**：
   登录成功后，执行以下命令安装基础设施引擎：
   ```bash
   # 更新包管理器并安装 Docker, Docker-Compose 和 Git
   sudo apt update
   sudo apt install -y docker.io docker-compose git
   
   # 将当前 ubuntu 用户加入 docker 组以避免每次都敲 sudo
   sudo usermod -aG docker $USER
   ```
   *(注：加入 docker 组后，最好断开 SSH 重新连接一次，让权限组立刻生效。)*

### 2.3 注入隐私数据防线 (Secure Environment Setup)

在服务器上创建存放数据和配置的专属沙盒目录：

```bash
# 1. 克隆代码仓库
git clone https://github.com/lynptl/PtClinVoice.git
cd PtClinVoice

# 2. 创建持久化数据挂载目录
mkdir -p data

# 3. >>> [AUTHORIZATION CHECKPOINT] <<<
# 创建隐形环境变量记录表，并贴入您的真实 DeepSeek API Key 与自生成的 JWT 密钥
cat << 'EOF' > .env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
JWT_SECRET_KEY=your_secure_random_production_key_here
EOF
```

### 2.4 全栈云端编排 (Full-Stack Docker Orchestration)

我们的 `docker-compose.yml` 已经对前端 Nginx 代理和后端 FastAPI 进行了深度编排，且最新版本的后端 `Dockerfile` 内置了对 `ffmpeg`, 语言模型 `en_core_web_sm` 以及 STT `small` 引擎的烘焙（Bake-in）。

现在，您可以直接在服务器上拉起生产环境：

```bash
# 执行全栈联合构建并作为守护进程启动
# 由于包含了底包编译，初次构建可能需要 3-5 分钟左右
docker-compose up -d --build

# 立刻探活后端数据链路，确认容器未因 OOM 或其他异常退出
curl http://localhost:8000/health
# 预期正常返回：{"status": "ok", "service": "PtClinVoice API"}
```

>**架构注记**：`docker-compose.yml` 中的前端静态站通过轻量级 Nginx 挂载在宿主机端口 `80` 进行分发。内置的反向代理会自动将发往 `/api/*` 的请求无缝路由至背面的 `ptclinvoice-api:8000` 节点，彻底杜绝云端的跨域 (CORS) 阻断问题。

#### [PASS] 视觉交互系统走查流程 (E2E Cloud Dashboard QA)：
1. 打开浏览器，直接访问 `http://<您的EC2公网IP>`。您应该能看到熟悉的登录界面。
2. 使用先前创建的账户进行系统登录。此时前端会把凭证通过 Nginx Reverse-Proxy 透传给后方 Python JWT 守卫引擎。
3. 进入 Dashboard 后尝试上传一段临床录音，验证云端的 Server-Sent Events (SSE) 事件流能否顺利完成 `PENDING` -> `TRANSCRIBING` -> `ANALYZING` -> `COMPLETED` 的全生命周期状态推送！
