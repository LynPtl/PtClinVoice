# PtClinVoice 开发日志 - 里程碑 (Milestone)

## 阶段：Phase 2.1 - API 后端骨架与数据库并发配置
**日期**: 2026-02-25

### 成就与指标 (Achievements)
本项目已完成从独立脚本至 Web 服务架构的演进。本阶段确立了采用 FastAPI 框架响应 HTTP 请求，并通过配置了 Write-Ahead Logging (WAL) 机制的 SQLite 数据库来实现任务生命周期的高并发读写。

### 核心特性与架构变更 (Features & Architecture Changes)

以下是在引入并发架构过程中的变更机制与代码实现：

| 机制 (Mechanism) | 修改对象 (Modified Files) | 设计与架构考量 (Architecture Decisions) |
| :--- | :--- | :--- |
| **Web 框架集成** | `main.py`, `requirements.txt` | 引入了 FastAPI 与 Uvicorn。实现了基础的 `/health` 存活探针接口，以及用于轮询任务状态的 GET 端点 `/tasks/{task_id}`。 |
| **持久化与 ORM** | `database.py`, `requirements.txt` | 引入 `sqlmodel` 定义了 `TranscriptionTask` 及其状态机枚举：`PENDING`, `TRANSCRIBING`, `ANALYZING`, `COMPLETED`, `FAILED`。 |
| **并发读写控制** | `database.py` (Line 29) | 拦截 SQLite 的默认行为。使用 SQLAlchemy `@event.listens_for(engine, "connect")` 钩子，强制随连接执行 `PRAGMA journal_mode=WAL;`，借此解决高负载下常发的 `OperationalError: database is locked` 问题。 |
| **依赖与兼容性修正**| `database.py` (Line 17) | 弃用 `datetime.utcnow()`，全面迁移至原生支持时区的 `datetime.now(timezone.utc)`，从而消除了 Pydantic 2.x 抛出的底层时区过时告警。 |

### 并发验证结论 (Testing & Metrics)
新增的测试文件 `tests/test_database.py` 证明了 WAL 机制的有效性：
*   **方法论**: 借助 `pytest-asyncio` 与 `asyncio.gather`，瞬间投递了 100 个模拟异步任务（经历从创建到更新至完成的 3 次完整提交操作）至本地数据库。
*   **结果**: 全链路 300 次并发事务在 0.52 秒内悉数执行完成，期间数据库未触发任何死锁异常。
*   详情可见：[Phase 2 QA Testing Report](./qa_testing_report_phase_2.md)。

### 遗留问题与下一步 (Next Steps)
- 为 CI/CD 管道集成构建多架构 Dockerfile (`linux/amd64` 与 `linux/arm64`) 支持 (Phase 2.2)。
- 将 Phase 1 阶段处于独立环境中的 `stt_core.py` 进程池接入 FastAPI，转为了异步后端的耗时任务队列 (Phase 2.3)。
