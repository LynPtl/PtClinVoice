# PtClinVoice (Engineering Edition)

PtClinVoice 是一个面向医疗场景的智能转录系统，旨在将临床医生与患者的对话录音自动转化为结构化的 **SOAP (Subjective, Objective, Assessment, Plan)** 病历笔记。

本项目通过“本地 CPU/GPU STT 预转写 + 云端 DeepSeek 高级语义分析”的混合架构，解决医院数据隐私与高质量病历生成的平衡问题。

## 当前开发进度 (Current Progress)

我们正在进行 **Phase 1: 核心 AI 引擎原型验证 (Script Level)**。
目前已跑通以下流程的骨架并配有 Pytest 断言：
- [x] **1.1 Local STT Engine**: `faster-whisper` 多进程内存墙隔离机制（支持 GPU/CPU 自适应降级）。
- [x] **1.2 DeepSeek Adapter**: 兼容 OpenAI SDK 格式的 Strict-JSON SOAP 并发提取测试。
- [ ] 1.3 Local PII NER (Privacy Filter): 在途设计中。

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

### 2. 安装核心依赖
本阶段刻意将其架构解耦，我们仅安装必不可少的推理引擎骨架。
```bash
pip install -r requirements.txt
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

### 4. 运行里程碑单元测试
如果您刚刚拉取了最新代码，您可以通过下方的测试用例确诊环境是否配置成功：

```bash
pytest -v
```
- **STT 引擎拦截测试 (`test_stt_core.py`)**：会测试模型能否跑出带有标点的正常文本。其中还会强制模拟一次 OOM (`SIGKILL`) 事件，断言测试它不会炸毁主线程。
- **DeepSeek 结构断言 (`test_deepseek_adapter.py`)**：通过 Mock 服务器拦截深度验证 Prompt 是否能将乱序拼凑的转录稿拆解归类至合格的 JSON SOAP 格式中。

### 扩展阅读
所有关于底层内存防泄露拦截和 Prompt Temperature 选择等技术选型决策，请阅读 `docs/` 目录下的各个里程碑开发日志 (Milestone Logs)。
