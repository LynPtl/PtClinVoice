# PtClinVoice (Production Engineering Edition)

PtClinVoice 是一款面向临床环境的高性能智能转录系统。该系统专注于将医生与患者的原始对话录音，通过混合 AI 架构自动化转换为结构化的 **SOAP (Subjective, Objective, Assessment, Plan)** 临床病历笔记。

系统采用“本地化边缘 STT (Faster-Whisper) + 本地化隐私拦截 (Presidio) + 云端语义建模 (DeepSeek)”的深度解耦架构，在确保数据合规性的前提下提供极高性能的病历重构能力。

---

## 现状与核心能力 (System Status & Capabilities)

项目已通过 Phase 3 “安全与重构”阶段验收，后端环境目前处于生产就绪状态（Production-Ready）：

*   **零信任架构 (Zero-Trust JWT)**：实现完整的 API 鉴权机制，支持多租户数据隔离与基于 Scopes 的权限控制。
*   **安全数据流 (Secure Data Pipeline)**：支持 `multipart/form-data` 流式上传，绑定任务生命周期。
*   **物理级数据自毁 (Burn-After-Reading)**：底层 Background Worker 在任务生命周期结束（成功或异常）后，强制执行文件系统级的物理抹除（`os.remove()`），确保存储层不留存任何原始 PII 语音片段。
*   **工业级目录规范**：采用高度标准化的 `app/` 包结构，完全解耦核心算法引擎、Web 路由与异步调度层。
*   **数据库高容灾特性**：SQLite 全面启用 Write-Ahead Logging (WAL) 模式，通过 100+ 并发压力测试，确保高负载下的数据一致性。

---

## 部署规范 (Deployment Standards)

### 1. 生产环境全栈部署 (Containerized Execution)
推荐使用 `docker-compose` 进行包含前后端的全栈一键部署。系统内已集成 `ffmpeg` 解码引擎与 SpaCy 环境。由于系统可能涉及高频底层 AI 配置调优，强烈建议直接自源码构建以确保拉取最新策略：

**配置环境变量**
在项目根目录维护 `.env` 配置文件：
```env
DEEPSEEK_API_KEY=sk-xxxxxx
# 生成强密钥命令: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=your_secure_random_key 
```

**拉取与启动服务栈**
```bash
# 1. 克隆托管仓库
git clone https://github.com/lynptl/PtClinVoice.git
cd PtClinVoice

# 2. 注入 .env 凭证后，执行全栈构建与启动
docker-compose up -d --build
```
> 服务默认在 `http://localhost:8000` 节点挂载，持久化数据（SQLite, Logs）挂载于宿主机 `./data` 目录。

---

### 2. 本地联调测试与双端架构启动 (Full Stack Development)
由于项目升级至包含现代 Web 控制台的全栈架构，请使用以下步骤进行完全拟真的系统测试。详细分离指令请参阅：[快速本地联调向导](docs/local_testing_guide.md)。

**1. 准备系统依赖 (FFmpeg)**
Faster-Whisper 要求系统环境中安装 `ffmpeg` 核心库。
*   **Linux (Ubuntu/Debian)**: `sudo apt update && sudo apt install ffmpeg`
*   **MacOS**: `brew install ffmpeg`

**2. 开启 FastAPI 数据核心引擎**
在根目录启动具备 CUDA 可加速条件与持久化的后端：
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 提前下载并缓存临床级(Small)多语种翻译模型避免超时
python3 -c 'from faster_whisper import WhisperModel; WhisperModel("small", device="cpu", compute_type="int8")'

# 暴露 8000 端口
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

**2. 开启 Vite / React 可视化前端工作台**
在 `frontend/` 目录启动客户端：
```bash
cd frontend
npm install
npm run dev
```
前端 UI 将在 `http://localhost:5173` 就绪，并通过内置代理自动联通后端的 JWT 守卫与 SSE 推送流。此全栈模式极度适合 SRE 进行链路穿透测试及开发调试。

---

## 性能优化指南 (Performance Tuning)

### NVIDIA CUDA 硬件加速 (RTX 30/40 Series)
如需在本地环境实现最佳表现与实时率 (Real-Time Factor, RTF)，需配置专有的深度学习动态链接库：

1.  **安装 CUDA 运行时加速包**：
    ```bash
    pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
    ```
2.  **配置链接库路径**：
    ```bash
    export LD_LIBRARY_PATH=$(python3 -c 'import sys; print(f"{sys.prefix}/lib/python3.12/site-packages/nvidia/cublas/lib:{sys.prefix}/lib/python3.12/site-packages/nvidia/cudnn/lib")'):$LD_LIBRARY_PATH
    ```

---

## 质量检测体系 (Testing Framework)

本系统遵循 SRE 级交付标准。项目测试集分为以下维度：

| 维度 | 执行指令 | 技术说明 |
| :--- | :--- | :--- |
| **全量验收** | `PYTHONPATH=. pytest tests/ -v` | 覆盖全链路逻辑校验 |
| **鉴权隔离** | `PYTHONPATH=. pytest tests/test_auth.py` | 验证多租户不越权、Token 溢出等安全场景 |
| **数据安全销毁** | `PYTHONPATH=. pytest tests/test_upload_and_shred.py` | 验证底层物理文件系统的阅后即焚 (Burn-After-Reading) 并发抹除机制 |
| **并发压测** | `PYTHONPATH=. pytest tests/test_database.py` | 100 瞬间并发下的 WAL 连通性测试 |

---

## 物理架构概览 (Structure Overview)

```text
.
├── app/                # Application Package (FastAPI Backend)
│   ├── core/           # Logic Isolation (STT, Privacy, DeepSeek Adapter)
│   ├── auth.py         # Security Guard (JWT)
│   ├── database.py     # SQLModel & Persistence Configuration
│   ├── main.py         # API Gateway & Routing
│   └── worker.py       # Asynchronous Pipeline & Shredding Logic
├── tests/              # Test Suite (Standardized Pytest Area)
├── scripts/            # Management & Maintenance Scripts
├── docs/               # Milestone Reports & Refactoring Logs
└── data/               # Persistent Volume Mount Point (SQLite/Logs)
```

---

## 基准文档 (Documentation)
*   **架构重构深度报告**：[`docs/refactoring_report_phase_3_cleanup.md`](docs/refactoring_report_phase_3_cleanup.md)
*   **安全与数据生命周期设计**：[`docs/milestone_phase_3.md`](docs/milestone_phase_3.md)
*   **系统最终全栈稳定性测试报告**：[`docs/qa_testing_report_phase_4.md`](docs/qa_testing_report_phase_4.md)
