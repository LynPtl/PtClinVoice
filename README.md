# PtClinVoice (Engineering Edition)

PtClinVoice 是一个面向医疗场景的智能转录系统，旨在将临床医生与患者的对话录音自动转化为结构化的 **SOAP (Subjective, Objective, Assessment, Plan)** 病历笔记。

本项目通过“本地 CPU/GPU STT 预转写 + 云端 DeepSeek 高级语义分析”的混合架构，解决医院数据隐私与高质量病历生成的平衡问题。

## 当前开发进度 (Current Progress)

我们正在进行 **Phase 1: 核心 AI 引擎原型验证 (Script Level)**。
目前已跑通以下流程的骨架并配有 Pytest 测试用例：
- [x] **1.1 Local STT Engine**: `faster-whisper` 多进程内存墙隔离机制（支持 GPU/CPU 自适应降级）。
- [x] **1.2 DeepSeek Adapter**: 兼容 OpenAI SDK 格式的 Strict-JSON SOAP 并发提取测试。
- [x] **1.3 Local PII NER (Privacy Filter)**: 引入 Microsoft Presidio 与 SpaCy 拦截患者社保号及姓名等隐私。

## 本地开发快速启动 (Quickstart Guide)

### 1. 核心部署：容器化一键启动 (推荐环境)
本项目现已完成 Phase 2.2 容器化，基础镜像包含了底层要求的 `ffmpeg` 解码引擎与 12MB 的 SpaCy `en_core_web_sm` 自然语言大模型基座。镜像已全部托管于 GitHub Container Registry (GHCR)。

**A. 配置云端 API 密钥**
在项目根目录创建一个 `.env` 文件，并填入您的真实 Key（必须）：
```env
DEEPSEEK_API_KEY=sk-xxxxxx
```

**B. 拉去与运行预编译服务栈**
如果您的机器或私有云已备有 Docker 引擎，请直接通过以下指令拉起并发骨架与 SQLite WAL 持久化服务组：
```bash
docker pull ghcr.io/lynptl/ptclinvoice:latest
docker-compose up -d
```
> *(容器启动后，基于 FastAPI 的并发中枢以及 SQLite 宿主机挂载卷将在 `http://localhost:8000` 就绪待命)*

---

### 2. 传统源码调试部署 (Advanced/Dev Environment)
如果您需要对核心代码进行深度二次研发或裸机调试，您必须手动解决 C-Extension 系统的底层环境与依赖网络。

**前置依赖要求**: 操作系统必须全局装有 `ffmpeg`：
*   **Ubuntu/Debian**: `sudo apt install ffmpeg`
*   **macOS**: `brew install ffmpeg`

```bash
# 克隆仓库与激活沙盒区
git clone https://github.com/LynPtl/PtClinVoice.git
cd PtClinVoice
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

> **⚡ [可选] 为拥有 Nvidia GPU (如 RTX 40系) 的机器解锁满血性能：**
> 如果你想体验高达 `17x+` 比率的 RTF (实时处理率)，请预拉取底层加速库以打破 GPU 内存墙：
> ```bash
> pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
> export LD_LIBRARY_PATH=$(python3 -c 'import sys; print(f"{sys.prefix}/lib/python3.12/site-packages/nvidia/cublas/lib:{sys.prefix}/lib/python3.12/site-packages/nvidia/cudnn/lib")'):$LD_LIBRARY_PATH
> ```

---

## 运行里程碑验收测试 (Running Milestone Tests)

### Phase 2: 后端基础设施与高并发验证 
当服务基于 Docker 容器或原生 `uvicorn main:app` 启动后，请使用探针验证服务组态：
```bash
curl http://localhost:8000/health
# 预期回包 (JSON): {"status":"ok","service":"PtClinVoice API"}
```
如需测试承载后端的 SQLite WAL 并发读写极限护城河，可运行 100 并发的长连接压力用例：
```bash
pytest tests/test_database.py -v
```

### Phase 1: 核心独立算法流验证
如果您未启动 FastAPI API 服务器，可绕开并发前端，直接向独立 STT 模型与 LLM 下发诊断音频黑盒指令：

*   **全保真音频转 SOAP 端到端测试**: `python run_live_e2e_diarization.py`
*   **纯大模型网络投递测试**: `python test_real_deepseek_api.py`
*   **沙盒免疫扫描 (OOM/打码)**: `pytest tests/test_stt_core.py tests/test_privacy_filter.py tests/test_deepseek_adapter.py -v`

---

## 扩展阅读资料 (Documentation & SRE Notes)
所有的技术重构方案、避坑防雷指南均保存在 `docs` 归档区：
1. **[架构开发日志]** API 骨架与 DB WAL: [`docs/milestone_phase_2.1.md`](docs/milestone_phase_2.1.md)
2. **[架构开发日志]** 容器编译流水线: [`docs/milestone_phase_2.2.md`](docs/milestone_phase_2.2.md)
3. **[SRE 并发测试报告]** `docs/qa_testing_report_phase_2.md` 与 `docs/qa_testing_report_phase_2.2.md`
