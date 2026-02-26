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

## 2. 后续将要集成的云端操作 (Upcoming Workloads - Phase 2+)

*(以下条目将在后续迭代中更新，提供详尽的参数配置与部署指导)*

### 2.1 Web 服务器托管与 Oracle Cloud ARM64 实例申领 (Phase 2)
考虑到项目核心 AI 的低计算配额与极致降本需求，我们的目标生产环境为 **Oracle Cloud (甲骨文云) 的 Always Free ARM64 (Ampere A1) 实例**。

**运维实操指南 (Oracle Cloud Provisioning)**：
1. **注册与绑卡**：访问 `cloud.oracle.com` 注册账号并验证外币信用卡。
2. **创建计算实例 (Compute)**：
   - 导航至：`Compute` -> `Instances` -> `Create Instance`。
   - **Image (镜像)**: 选择 `Canonical Ubuntu 22.04/24.04 (aarch64)`。
   - **Shape (规格)**: 选择 `Ampere (ARM)` 架构下的 `VM.Standard.A1.Flex`。
   - **资源配置上限** (关键): 由于这是 Flex (弹性) 实例，默认显示可能只有 1 OCPU 和 6GB 内存。请在 OCPU 数选择 `4`，Memory (内存) 选择 `24GB`。(这是免费额度的上限，能够满足多路 STT 引控计算需求)。
     - **[WARNING] 容量耗尽告警 (Out of Capacity)**: 若执行创建时系统提示 `Out of capacity for shape VM.Standard.A1.Flex`，此为 Oracle 免费宿主机池常见现象（通常指向所选可用区当前无空闲 ARM 物理资源）。**缓解方案**：尝试更换可用域（Availability Domain），或错峰重试。在此期间，项目代码完全兼容在本地或常规 x86 服务器上进行测试验证。
3. **网络连通性编排 (Networking & Security)**：
   默认情况下，Oracle 的实例即使绑定了公网 IP 也是处于“失联”状态的。必须执行以下链路打通：
   - **创建 VCN (虚拟云网络)**: 导航至 Networking -> Virtual Cloud Networks。新建 VCN (如 `10.0.0.0/24`) 与 Public Subnet。**无需分配 IPv6**。
   - **配置互联网网关 (Internet Gateway)**: 在 VCN 详情页左侧点击 Internet Gateways，新建一个网关并命名。
   - **更新路由表 (Route Table)**: 点击 VCN 左侧的 Route Tables，进入 `Default Route Table`，添加规则：Target Type 选 `Internet Gateway`，Destination CIDR 填 `0.0.0.0/0`，Target 选刚才建好的网关。（这一步让服务器的公网流量能找到出口）。
   - **放行安全列表 (Security List)**: 点击 VCN 左侧的 Security Lists，进入 `Default Security List`。默认已放行 SSH (端口 `22`)。为了后续 API 访问，请**务必添加 Ingress (入站) 规则**：Source CIDR `0.0.0.0/0`，IP Protocol `TCP`，Destination Port Range 填 `80,443,8000` (8000为后续 FastAPI 端口)。
4. **绑定密钥与实例开通**:
   - 在创建实例页面的网络层，选择刚才配置好的 VCN 和 Public Subnet。
   - **关键环节**: 在 `Add SSH keys` 处选择 `Save private key`，一定要下载 `.key` 文件，这是唯一登录凭证。点击创建。
4. **服务器出厂预装与 OS 防火墙放行**：使用 SSH 登录这台新机器。
   
    **操作系统层安全组拦截机制**：除了云端控制台的 Security List，Oracle 的 Ubuntu 镜像默认在操作系统级别通过 `iptables` 限制了除端口 22 以外的所有入站请求。您必须首先执行内核级的网络端口放行：
    ```bash
    # 放行 8000 (FastAPI), 80 (HTTP), 443 (HTTPS) 端口
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
    
    # 持久化 iptables 规则以防止系统重启后失效
    sudo netfilter-persistent save
    ```
    
    然后安装我们的基础环境：
    ```bash
    sudo apt update && sudo apt install -y docker.io docker-compose git ffmpeg
    ```
至此，最底层的免费云宿主机就搭好了，后续将配合 GitHub Actions 和多架构 Docker 无缝承接构建流。

### 2.2 Docker 容器云编排测试 (Phase 2.3+)
由于我们的 `ghcr.io/lynptl/ptclinvoice:latest` 镜像是严格基于 `linux/amd64` 构建，并且全量包含好了 `12MB SpaCy` 与 `ffmpeg` 依赖底包，它非常适合在您的 Oracle VM.Standard.E5.Flex (AMD x86_64) 或其他架构上进行“即开即用”的空降测试。

为了遵守我们定下的“极简与不可变基础设施”底线，您在云端实例上**完全不需要拉取整个 Git 仓库的代码**。请通过 SSH 登入您的 Oracle Cloud 实例，依次执行：

#### 第一步：配置网络端点与部署容器引擎 (若未经初始化)
**1. 放行 Oracle 操作系统级防火墙**
很多时候在网页端 (Security List) 开放了 8000 端口，但请求仍旧无响应，是因为 Oracle 的 Ubuntu 模板自带严苛的本地 `iptables` 规则。请强行打通操作系统层的拦截：
```bash
# 在 Linux 防火墙规则顶层添加针对 8000, 80, 443 端口的入站放行许可
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT

# 持久化防火墙规则
sudo netfilter-persistent save
```

**2. 刷新包记录并装配 Docker**
```bash
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

# >>> [AUTHORIZATION CHECKPOINT]: The only manual step required <<<
# 创建隐形环境变量记录表，并贴入您的真实 DeepSeek API Key
cat << 'EOF' > .env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EOF
```

#### 第三步：拉取仓库源码与双容器全栈编排 (Full-Stack Orchestration)
由于依赖底包和核心算法可能会经历高频本地调优（例如：STT 语言参数修复、隐私过滤修复），为了确保您能拿到绝对最新的全量代码（不依赖尚未 Push 到云端 Registry 的镜像缓存），请使用 Git 拉取源码并在本地触发 Build：

```bash
# 1. 克隆托管仓库
git clone https://github.com/lynptl/PtClinVoice.git
cd PtClinVoice

# 2. 将您刚才生成的 .env 密钥配置文件移动到根目录
mv ../.env ./

# 3. 强制触发本地联合构建并拉起双容器
sudo docker-compose up -d --build

# 4. 立刻探活后端数据链路
curl http://localhost:8000/health
# 预期正常返回：{"status": "ok", "service": "PtClinVoice API"}
```

>**架构注记**：`docker-compose.yml` 中的前端静态站通过轻量级 Nginx (挂载在宿主机端口 `80`) 进行分发。内置反向代理会自动将任何 `/api/*` 的请求无缝代理至背后的 `ptclinvoice-api:8000` 节点。

**[PASS] 视觉交互系统走查流程 (E2E Cloud Dashboard QA)**：
1. 打开浏览器输入 `http://<您的Oracle公网IP>` 即可直接触达部署在 Nginx 中的前端临床交互控制台。
2. 于 `/login` 登录病区账户，此时 Axios 将把凭证精准无误地由 Nginx Reverse-Proxy 透传给后方 Python JWT 守卫引擎。
3. 拖拽音频进入 Upload 流水线；验证 Nginx 防阻拦特性对 SSE Server-Sent Events 事件流的高速透传。

### 2.3 手工容器化构建指南 (本地打包特供)
若云平台拉取 GHCR 镜像受阻，或您本地执行特殊分支改构，请使用以下双层编译架构进行手工落盘：
```bash
# 构建后端含 ffmpeg 与 spacy 依赖的厚底包（约 800MB）
docker build -t ghcr.io/lynptl/ptclinvoice:latest .

# 构建前端含 React 编译阶段的 Nginx 代理包
docker build -t ghcr.io/lynptl/ptclinvoice-web:latest ./frontend

# 启动全栈
docker-compose up -d
```
