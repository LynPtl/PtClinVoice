# PtClinVoice 开发日志 - 里程碑 (Milestone)

## 阶段：Phase 2.3 - 耗时任务 (STT/LLM) FastAPI 后端 Worker 队列改造
**日期**: 2026-02-26

### 成就与指标 (Achievements)
本项目已成功完成从“同步阻塞/脚本级调用”向“容灾级异步任务后台管线”的演进。本阶段深度实施了 SRE “极简架构”理念，拒绝引入 Redis 或 Celery 等重量级外部依赖，而完全基于 FastAPI 的 `BackgroundTasks` 机制与配置了 Write-Ahead Logging (WAL) 的 SQLite 充当单机高并发调度的核心。

### 核心特性与架构变更 (Features & Architecture Changes)

| 机制 (Mechanism) | 修改对象 (Modified Files) | 设计与架构考量 (Architecture Decisions) |
| :--- | :--- | :--- |
| **异步管道编排** | `worker.py` | 新增了独立管道，串联了 `stt_core` (音频特征提取), `privacy_filter` (人名与社保号掩码), 和 `deepseek_adapter` (结构化 SOAP 生成)。所有的流转都在后台独立线程执行。 |
| **OOM 灾难防线** | `worker.py`, `stt_core.py` | 确保执行 `Faster-Whisper` 推理的工作节点永远寄宿在由 `multiprocessing` spawn 出的独立进程块中。如果遭遇 Kernel 的 SIGKILL (因显存或内存超载)，抛错将在 `worker.py` 中被 `try...except` 高位截流，任务即刻置为 `FAILED` 并附带诊断抛漏，**绝对不波及 FastAPI 主容器存活**。 |
| **持久状态推流** | `worker.py`, `main.py` | Worker 在管线的每个重要流转点 (`TRANSCRIBING` -> `ANALYZING` -> `COMPLETED`/`FAILED`) 实时更新 SQLite 状态机，保障了前端后续能够精准轮询状态。 |
| **模拟入口装配** | `main.py` | 提供了崭新的 `POST /api/v1/transcribe/mock` 接口，用以测试系统异步防线的鲁棒性，并在接到请求后瞬间返回 UUID。 |

### 系统层验证结论 (Testing & Metrics)
新增了对等的黑盒防线测试：
*   `test_worker_pipeline.py::test_background_worker_pipeline`：**PASSED**. 端到端模拟了 HTTP 请求从接收入库、开启后台转录、脱敏阻断到最终生成 SOAP 的全生命周期，管线轮询断言有效收敛于 `COMPLETED`。
*   `test_worker_oom.py::test_worker_oom_handling`：**PASSED**. 成功对 STT 核心注入了一轮恶意的 `MemoryError` 内存耗尽模拟异常，管线完美捕捉并将状态反转至 `FAILED` 状态机停损，且 FastAPI 底座纹丝不动。

### 遗留问题与下一步 (Next Steps)
- 由于后端核心算子管道已彻底稳固，可以开启安全审计 (Auth Module) / 基于 HTTP 的真实实体文件上传收纳逻辑。
- 此后将向构建纯原生 React Frontend 进发。
