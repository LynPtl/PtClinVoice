# PtClinVoice (Engineering Edition)

PtClinVoice 是一个面向医疗场景的智能转录系统，旨在将临床医生与患者的对话录音自动转化为结构化的 **SOAP (Subjective, Objective, Assessment, Plan)** 病历笔记。

本项目通过“本地 CPU/GPU STT 预转写 + 云端 DeepSeek 高级语义分析”的混合架构，解决医院数据隐私与高质量病历生成的平衡问题。

## 当前开发进度 (Current Progress)

我们正在进行 **Phase 1: 核心 AI 引擎原型验证 (Script Level)**。
目前已跑通以下流程的骨架并配有 Pytest 断言：
- [x] **1.1 Local STT Engine**: `faster-whisper` 多进程内存墙隔离机制（支持 GPU/CPU 自适应降级）。
- [x] **1.2 DeepSeek Adapter**: 兼容 OpenAI SDK 格式的 Strict-JSON SOAP 并发提取测试。
- [x] **1.3 Local PII NER (Privacy Filter)**: 引入 Microsoft Presidio 与 SpaCy 拦截患者社保号及姓名等隐私。

## 本地开发快速启动 (Quickstart Guide)

### 1. 环境准备
本项目采用纯 Python 3.10+ 开发环境，不强制要求 Nvidia 显卡（支持在普通的无卡 x86 裸机及 WSL 环境内热部署）。

```bash
# 克隆仓库
git clone https://github.com/LynPtl/PtClinVoice.git
cd PtClinVoice

# 创建并激活虚拟环境 (强烈建议)
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安装核心依赖与自然语言核心
本阶段刻意将其架构解耦，我们仅安装必不可少的推理引擎骨架。同时，我们需要拉取极小的英语 SpaCy 骨架以驱动本地的脱敏防线。
```bash
pip install -r requirements.txt
python3 -m spacy download en_core_web_sm
```

> **⚡ [可选] 为拥有 Nvidia GPU (如 RTX 40系) 的机器解锁满血性能：**
> 如果你想体验高达 `17x+` 比率的 RTF (实时处理率)，并且你的系统内已有 CUDA 驱动，请手动安装底层加速库：
> ```bash
> pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
> export LD_LIBRARY_PATH=$(python3 -c 'import sys; print(f"{sys.prefix}/lib/python3.12/site-packages/nvidia/cublas/lib:{sys.prefix}/lib/python3.12/site-packages/nvidia/cudnn/lib")'):$LD_LIBRARY_PATH
> ```

### 3. 配置云端 API 密钥
目前第二阶段的 SOAP 文本重构依赖 DeepSeek 的 API。
在项目根目录创建一个 `.env` 文件，并填入您的 API Key：
```bash
echo "DEEPSEEK_API_KEY=sk-xxxxxx" > .env
```

### 4. 运行里程碑单元联调测试
如果您刚刚拉取了最新代码，您可以通过下方的测试用例确诊环境是否配置成功：

**A. 纯黑盒离线基建测试 (零网络发包，拦截断言)**:
```bash
pytest -v
```
- **STT 引擎拦截测试 (`test_stt_core.py`)**：会测试模型能否从本地 MP3 中跑出带有标点病灶英语。还包含 OOM (`SIGKILL`) 进程免疫测试。
- **DeepSeek 结构断言 (`test_deepseek_adapter.py`)**：Mock 拦截测试，深度验证 JSON SOAP 组装格式。
- **本地患者隐私防线 (`test_privacy_filter.py`)**：阻击本地的 PII (社保号，姓名)，瞬间打码 `[REDACTED]`。
- **集成与端到端 (`test_integration.py`)**: 跑通全链路 (Audio -> WHISPER -> PRESIDIO -> MOCKED DEEPSEEK)。

**B. 真实 DeepSeek 云端实盘测试 (验证您的 Key 是否可用)**:
由于上面的全盘扫描是处于 Mock (省钱) 状态，请单独执行以下脚本消费几十 Token 直连云端验证：
```bash
python3 test_real_deepseek_api.py
```

### 扩展阅读
所有关于底层内存防泄露拦截、环境集成、以及质量保障策略评定，请完整参阅我们的 [端到端质量评估测试报告 (QA Testing Report)](docs/qa_testing_report_phase_1.md)，以及相应的云端运维部署手册。
