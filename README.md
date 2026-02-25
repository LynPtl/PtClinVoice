# PtClinVoice (Engineering Edition)

PtClinVoice 是一个面向医疗场景的智能转录系统，旨在将临床医生与患者的对话录音自动转化为结构化的 **SOAP (Subjective, Objective, Assessment, Plan)** 病历笔记。

本项目通过“本地 CPU/GPU STT 预转写 + 云端 DeepSeek 高级语义分析”的混合架构，解决医院数据隐私与高质量病历生成的平衡问题。

## 🚀 当前开发进度 (Current Progress)

我们已完成 **Phase 3: 安全增强与生产级重构 (Production-Ready Backend)**。
目前系统已具备以下核心能力：
- [x] **Zero-Trust JWT**: 全 API 鉴权，支持用户模型与多租户数据隔离。
- [x] **Secure File Pipeline**: 支持 `multipart/form-data` 音频流上传，绑定任务生命周期。
- [x] **Burn-After-Reading**: 底层 Worker 实现物理级的音频碎纸机机制（`os.remove()`），确保存储层不留原始 PII。
- [x] **Modular Restructuring**: 规范化的 `app/` 包结构，解耦核心引擎与 API 逻辑。
- [x] **SQLite WAL Resilience**: 支持高并发读写的数据库预写日志模式，通过 100+ 并发压力测试。

---

## 🛠️ 快速启动 (Quickstart Guide)

### 1. 核心部署：容器化一键启动 (推荐)
本项目现已完成容器化，基础镜像包含了底层要求的 `ffmpeg` 解码引擎与 12MB 的 SpaCy `en_core_web_sm` 自然语言大模型基座。

**A. 配置云端 API 密钥**
在项目根目录创建一个 `.env` 文件：
```env
DEEPSEEK_API_KEY=sk-xxxxxx
JWT_SECRET_KEY=your_secure_secret_key
```

**B. 拉取与运行服务栈**
```bash
docker-compose up -d
```
> *(服务将在 `http://localhost:8000` 就绪。)*

---

### 2. 开发环境部署 (Development Environment)

**前置依赖**: `ffmpeg` (系统级安装)。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 启动开发服务器 (注意需要设置 PYTHONPATH)
PYTHONPATH=. uvicorn app.main:app --reload
```

---

## 🧪 自动化测试验证 (Testing Suite)

本项目采用 SRE 级测试标准，所有功能点均由 Pytest 覆盖。

| 类别 | 执行指令 |
| :--- | :--- |
| **全量验收** | `PYTHONPATH=. pytest tests/ -v` |
| **鉴权与安全** | `PYTHONPATH=. pytest tests/test_auth.py` |
| **物理碎纸机** | `PYTHONPATH=. pytest tests/test_upload_and_shred.py` |
| **算法 zone** | `PYTHONPATH=. pytest tests/test_stt_core.py tests/test_privacy_filter.py` |
| **数据库压力** | `PYTHONPATH=. pytest tests/test_database.py` |

---

## 📁 目录规范 (Repository Structure)

```text
.
├── app/                # 核心应用包
│   ├── core/           # 算法引擎 (STT, Privacy, DeepSeek)
│   ├── auth.py         # JWT 安全守卫
│   ├── database.py     # SQLModel ORM 与 WAL 配置
│   ├── main.py         # FastAPI 路由入口
│   └── worker.py       # 异步任务流水线
├── tests/              # 测试套件 (Auth, Integration, Load)
├── scripts/            # 运维管理脚本
├── docs/               # 详细里程碑文档与重构报告
└── data/               # 宿主机数据持久化挂载卷 (SQLite, Logs)
```

---

## 📖 技术文档与重构报告
1. **[架构重构]** 包结构规范化指南: [`docs/refactoring_report_phase_3_cleanup.md`](docs/refactoring_report_phase_3_cleanup.md)
2. **[安全报告]** JWT 与阅后即焚实现: [`docs/milestone_phase_3.md`](docs/milestone_phase_3.md)
3. **[SRE 报告]** 并发测试与质量分析: `docs/qa_testing_report_phase_3.md`
