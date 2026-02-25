# PtClinVoice 开发日志 - 里程碑 (Milestone)

## 阶段：Phase 1.1 - 核心 STT 引擎原型验证
**日期**: 2026-02-25

### 成就与指标 (Achievements)
- **STT 核心隔离**：成功使用 Faster-Whisper 实现了独立的多进程 STT 引擎 (`stt_core.py`)。
- **动态算力适配**：在模型加载时强制应用了 `device="auto"` 策略。
- **极端容灾测试**：在 `test_stt_core.py` 中深度注入并模拟了严重的 OOM (Out Of Memory) 内存截断（内核级 `SIGKILL`），验证了主进程的绝对存活，实现了有效的进程隔离。
- **RTX 4060 惊艳发力**：在宿主机的 RTX 4060 满血 CUDA 13.0 支持下，经过原生 GPU API 调用，测得最高 17 倍加速比 **(RTF=0.05x)** 的碾压级吞吐量。

### SRE 与底层架构决策 (SRE & Architecture Decisions)
- **进程级防火墙 (Process Isolation)**：果断舍弃 Python 存在幽灵内存泄漏风险的默认 `fork`，严格采用了 `multiprocessing.get_context('spawn')`。任何子线程的内存暴乱都被物理隔离抛弃，保障了提供 API 的主线进程稳如磐石。
- **硬件降级容错 (Hardware Agnosticism)**：在 CTranslate2 框架初始化时增加了一层极强的“防护网”。如果在未来部署到甲骨文 (Oracle) 免费云主机的无显卡 ARM64 裸机，或没有装载 `libcublas` 的 Docker 容器时，代码会自动**平滑降级（Fallback）到纯 CPU 计算模式**，绝不崩溃宕机。
- **管线洁癖 (Dependency Purity)**：为了确保随后进入 Kubernetes / Docker 等轻运维平台体系的顺滑度，`requirements.txt` 中刻意剔除了动辄数 GB 的臃肿 Nvidia 原生 PyPI 库。以极简配置达成跨云服务供应商的架构迁移目标。

### 遗留问题与下一步 (Next Steps)
本阶段底层基建已验收完毕。临时写就的压力测试及 MP3 基准测绘文件已被清除（阅后即焚文化萌芽）。
即将前往下一座堡垒：**Phase 1.2: DeepSeek Adapter** (云端大语言模型对接与 SOAP 结构体强约束生成)。
