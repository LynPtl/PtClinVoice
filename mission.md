# Mission: PtClinVoice (Engineering Edition)

## 1. 项目概述 (Project Overview)
**PtClinVoice** 是一个面向医疗场景的智能转录系统，旨在将临床医生与患者的对话录音自动转化为结构化的 **SOAP (Subjective, Objective, Assessment, Plan)** 病历笔记。
项目核心在于解决“数据隐私”与“模型性能”的矛盾，通过**混合 AI 架构**在低成本云资源上实现临床级的处理精度。

## 2. 技术架构与选型 (Architecture & Tech Stack)

### 2.1 核心策略 (Core Strategy)
*   **混合 AI 处理 (Hybrid AI Pipeline)**:
    *   **本地重计算 (Local Compute)**: 音频转文字 (STT) 环节涉及大量数据流，且包含原始生物特征，必须在私有服务器本地运行，**绝不上传第三方**。
    *   **云端强推理 (Cloud Intelligence)**: 文本格式化 (NLP) 环节计算量小但逻辑复杂度高，且需极高的医学语义理解能力，脱敏后调用 **DeepSeek API** 处理。DeepSeek 提供极高的性价比和强大推理能力，非常适合处理复杂的角色分离和医学文本生成任务。
*   **高度可移植性与弹性部署 (High Portability & Elastic Deployment)**:
    *   **本地极速开发**: 借助 `device="auto"` 等动态设备分配策略，在开发期完美兼容带 GPU (如 RTX 系) 的本地 WSL 环境，实现 STT 模型的本地并行极速调试。
    *   **跨云/跨架构兼容**: 系统必须通过 Docker `buildx` 多架构构建方案打包。做到仅需一套代码底座，即可直接在**免费的无 GPU Oracle Cloud ARM64 实例** 和 **未来付费升级的 AMD/x86 Linux 实例** 之间无缝迁移和切换计算模式。

### 2.2 技术栈 (Tech Stack)
*   **Frontend (SPA)**:
    *   **Framework**: **React** (Vite 构建) - 保证组件化与扩展性。
    *   **UI Library**: **Mantine UI** (或 Chakra UI) - 快速构建医疗风格的专业 Dashboard。
    *   **State**: React Query / Axios - 处理异步数据流。
*   **Backend (Rest API)**:
    *   **Framework**: **FastAPI** (Python 3.10+) - 高性能异步框架，原生支持 OpenAPI 文档。
    *   **Task State Management (可靠队列)**: 放弃易失的内存队列，直接使用 **SQLite 状态机机制** (Status: `PENDING` -> `PROCESSING` -> `COMPLETED`/`FAILED`)。开启 **WAL 模式 (Write-Ahead Logging)** 与连接超时配置，确保单机高并发下绝不锁死，且能在服务器宕机重启后恢复任务。
    *   **Audio Preprocessing & Security**: 通过后端级联 `ffmpeg` 强制标准化为单声道 16kHz，并严格执行**“阅后即焚 (Burn-after-reading)”**物理删除策略，绝不长期留存原始完整录音。
*   **AI Engine**:
    *   **STT**: **Faster-Whisper** (CTranslate2 引擎) - 针对 CPU 推理极致优化，比原始 Whisper 快 4 倍。针对 Whisper 极高的内存消耗，实施**进程隔离 (Process Isolation)**：每次推理在独立子进程中运行，一旦发生 OOM 被系统 kill，仅标记当前任务失败，绝不波及主进程。
    *   **NLP**: DeepSeek API (如 deepseek-chat 或 deepseek-reasoner) - 用于通过语义推理实现说话人分离 (Speaker Diarization) 并生成 SOAP 结构。
*   **Infrastructure & DevOps**:
    *   **Database**: **SQLite** (开启 WAL 模式)。精益求精，省去部署庞大的 PostgreSQL / Redis，凭借高效代码设计单挑几十路并发。
    *   **Container**: Docker & Docker Compose。采用 **“同构镜像双开”** 魔法：写一套 Dockerfile，利用 docker-compose 启动两个容器 `web-server` (提供 API) 和 `stt-worker` (纯 Python 死循环轮询执行推理)，挂载相同共享 volume 即可实现存算解耦与高可用。
    *   **Gateway**: Nginx (反向代理，处理前后端路由与 SSL)。精简架构，去掉臃肿的可观测性套件。
    *   **CI/CD**: GitHub Actions - 实现自动化测试 (Lint/Pytest) 与镜像的自动归档推送。

## 3. 核心业务流程 (Core Workflow)

1.  **Ingestion (采集)**: 医生在 React 前端上传录音 (WAV/MP3)。
2.  **Queuing (入队)**: Backend 接收文件 -> 落盘存储 -> 生成 Task ID -> 推入异步队列 -> 立即返回前端 "Processing"。
3.  **Audio Normalization (预处理)**: 后端使用 ffmpeg 将音频压缩/重采样为 16kHz 单声道 WAV。
4.  **Local STT (本地转写)**:
    *   Worker 线程轮询数据库中 `PENDING` 状态记录获取任务。
    *   加载本地 **Faster-Whisper (Small/Medium)** 模型。
    *   **关键配置**: 开启并强化初始 Prompt，强制生成带首字母大写及标准标点符号的文本，防止后续脱敏引擎失效。
    *   输出：逐字稿 (Verbatim Transcript)。
4.  **Privacy Hardening (隐私加固 - 本地执行)**:
    *   **PII Redaction (身份脱敏)**: 放弃鸡肋的正则匹配。在内存中对逐字稿运行工业级本地 NER（命名实体识别）引擎——**Microsoft Presidio** 或 **spaCy**。它们无需 GPU，能精准识别并替换人名 (PERSON)、地点 (LOCATION)、机构 (ORG) 等，将原文替换为 `[REDACTED]`，确保发给云端的文本绝对安全。
5.  **Clinical Formatting (云端智能生成)**:
    *   将**脱敏后的安全文本**发送至 DeepSeek API。
    *   强化配置 Prompt 模板设计一个 Workflow：第一步，基于语义重构对话序列（如 `[Doctor]: ... [Patient]: ...`）解决说话人分离；第二步，提取关键医学信息生成 SOAP 笔记。
7.  **Storage, Sync & Cleanup (存储、同步与销毁)**:
    *   将脱敏转写 + SOAP 笔记持久化入库，更新状态为 `COMPLETED`。
    *   **Burn-after-reading (阅后即焚)**: 状态一经流转至 COMPLETED/FAILED，或后台定时器扫出存在超过 2 小时的残留音频，立刻执行底层 `os.remove()` 彻底物理抹除原始音频文件！切断泄密源头。
    *   **Real-time Push (轻量级 SSE)**: 废弃需依赖 Redis Pub/Sub 的复杂方案。后端通过 **Server-Sent Events (SSE)**，开启一个轻量级的异步数据库查询循环 (每秒 `SELECT status FROM tasks WHERE id = task_id`)，一旦变更即推送给前端。兼顾了丝滑极客 UI 体验与单机极简架构。

## 4. 开发实施阶段 (Implementation Phases)

### Phase 1: 核心 AI 引擎原型验证 (Core AI Pipeline - Script level)
*   **目标**: 脱离复杂的 Web 框架，通过纯 Python 脚本跑通“录音进，笔记出”的黑盒流程，验证核心技术可行性。
*   [ ] **1.1 Whisper 脚本测试**: 编写脚本，加载 `faster-whisper` (`base.en` 或 `small.en`) 对本地音频进行转写。
*   [ ] **1.2 DeepSeek Adapter**: 编写针对 DeepSeek API 的请求代码。设计 Prompt 模板测试基于语义的角色分离与 SOAP 生成。
*   [ ] **1.3 Privacy Filter (本地 NER)**: 编写基础函数引入 `presidio-analyzer`，验证针对英文/中文对话的本地脱敏逻辑是否精准。

### Phase 2: 基础设施、后端骨架与 CI/CD (Infrastructure & DevOps)
*   **目标**: 建立工程化的 API 服务，部署基础架构监控，并打通持续集成流水线。
*   [ ] **2.1 Docker & CI/CD**: 编写 `Dockerfile` (`python:3.10-slim` + `ffmpeg`)。在 GitHub Actions 中配置 Pipeline，实现代码提交后自动执行单元测试并打 tag。
*   [ ] **2.2 API 骨架与数据库**: 引入 FastAPI 与 SQLite/SQLModel。定义可靠的枚举化 `Status` 并**必须为 SQLite 开启 WAL (Write-Ahead Logging) 和 Timeout**。实现定期清理过期录音的后台守护任务。
*   [ ] **2.3 容灾级任务 Worker**: 编写一个独立运行的 `worker.py`，死循环轮询数据库挂起任务。**核心**：使用 `multiprocessing` 或 `subprocess` 为每个 Whisper 任务孵化独立子进程，确保主循环对 OOM 免疫。
*   [ ] **2.4 极简 SSE 推送机制**: 实现 `/api/stream/{task_id}` 接口，利用轻量级的 `asyncio.sleep(1)` 结合轮询 SQLite 实时上报状态。

### Phase 3: 安全机制与上传接口 (Security & Upload)
*   **目标**: 完善数据输入通道与权限管理。
*   [ ] **3.1 Auth Module**: 实现 JWT 鉴权体系 (`/api/auth/login`)，确保数据私密性。
*   [ ] **3.2 File Upload**: 实现音频文件的安全接收与落盘校验（`/api/upload`）。

### Phase 4: 前端开发 (Frontend Construction)
*   **目标**: 构建可视化的交互界面。
*   [ ] **4.1 Scaffold**: `npm create vite@latest` 初始化 React + TypeScript 项目。安装 Mantine UI。
*   [ ] **4.2 Auth Pages**: 登录/注册页面，前端状态管理。
*   [ ] **4.3 Dashboard**:
    *   **Upload & Record Area**: 拖拽上传组件，以及基于 Web Audio API 的浏览器实时录音功能。
    *   **Task List**: 任务队列的列表展示，通过 SSE (Server-Sent Events) 接收后端实时状态推送，拒绝轮询。
*   [ ] **4.4 Workspace**: 分栏视图：左侧只读转写结果，右侧富文本编辑器展示并支持修改 SOAP 笔记。

### Phase 5: 部署与评估优化 (Deployment & Evaluation)
*   **目标**: 系统上线，达到生产可用状态，并输出各项评估指标。
*   [ ] **5.1 Nginx Proxy**: 配置 Nginx 容器，作为反向代理处理前端静态文件和后端 API 转发 (`/api/` -> Backend Container)。
*   [ ] **5.2 HTTPS**: 在 Oracle 服务器上运行 Certbot，配置 SSL 证书（医疗数据传输必须加密）。
*   [ ] **5.3 Optimization**: 调整 Whisper 模型大小（从 `base` 升级到 `small` 或 `medium`），寻求内存和准确率的最佳平衡。
*   [ ] **5.4 Evaluation**: 编写评估脚本，基于测试录音集计算 WER (词错率)，并统计数据库中的端到端处理延迟 (Latency)，生成最终评估报告。