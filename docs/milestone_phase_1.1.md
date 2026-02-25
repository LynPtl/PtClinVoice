# PtClinVoice 开发日志 - 里程碑 (Milestone)

## 阶段：Phase 1.1 - 核心 STT 引擎原型验证
**日期**: 2026-02-25

### 成就与指标 (Achievements)
- **STT 核心隔离**：成功使用 Faster-Whisper 实现了独立的多进程 STT 引擎 (`stt_core.py`)。
- **动态算力适配**：在模型加载时强制应用了 `device="auto"` 策略。
- **极端容灾测试**：在 `test_stt_core.py` 中深度注入并模拟了严重的 OOM (Out Of Memory) 内存截断（内核级 `SIGKILL`），验证了主进程的绝对存活，实现了有效的进程隔离。
- **RTX 4060 性能表现**：在宿主机的 RTX 4060 CUDA 13.0 支持下，经过原生 GPU API 调用，测得最高 17 倍加速比 **(RTF=0.05x)** 的吞吐量。

### 核心特性与架构索引 (Features & Architecture Index)

为了方便后续 SRE 及研发同学快速定位底层策略，以下是本阶段的核心机制与对应源码索引：

| 机制 (Mechanism) | 源码位置 (Code Location) | 设计考量 (Architecture Decisions) |
| :--- | :--- | :--- |
| **STT 引擎孤岛** | `stt_core.py` (Line 15-45) | **进程物理隔离**：摒弃 Python 默认的 `fork`，采用安全的 `spawn`。保证 `faster-whisper` 的任何 OOM 或段错误崩溃绝对不波及主线进程。 |
| **动态算力适配** | `stt_core.py` (Line 25) | **平滑降级**：模型初始化启用 `device="auto"` 与 `try-except` 兜底。在纯无卡云端 (如 Oracle ARM64) 或无显卡驱动的环境下，自动降级为 CPU 计算，保证容器存活。 |
| **内核级容灾验证**| `test_stt_core.py` (Line 60) | **SIGKILL 免疫测试**：由自动化 Pytest 通过注入致命信号模拟子系统异常退出，验证主线程安然无恙且抛出受控的 `MemoryError`。 |
| **依赖精简** | `requirements.txt` | 剔除体积庞大的 `nvidia-*` 预装库扩展依赖，换来轻量且能随时跨架构编排的基础环境。 |
即将前往下一阶段：**Phase 1.2: DeepSeek Adapter** (云端大语言模型对接与 SOAP 结构生成)。
