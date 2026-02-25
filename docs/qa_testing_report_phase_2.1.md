# PtClinVoice 测试与质量评估报告 (QA Report Phase 2)

**报告标题**: Phase 2 后端中间件与数据库并发测试报告
**日期**: 2026-02-25
**测试框架**: Pytest 9.0.2 (`pytest-asyncio`)

本文档记录了 Phase 2.1 中引入 FastAPI Web 框架与 SQLite (SQLModel) 数据库后的并发能力验证，专为技术与测试人员参阅。

## 1. 核心架构范围与约束

Phase 2 实现了应用从单线程执行模型向具备并发 HTTP 请求处理能力的 Web 服务的过渡。

主要的架构约束在于采用本地 SQLite 数据库文件 (`ptclinvoice_sre.db`) 以满足无需额外部署配置的需求。在默认情况下，SQLite 极易在并发写入负载下抛出 `OperationalError: database is locked` 异常。本阶段的核心测试目标是：评估及验证 Write-Ahead Logging (WAL) 机制能否在多个并发连接中提供可靠的状态管理保障。

---

## 2. 并发压力测试明细 (Concurrency Stress Test Documentation)

### 2.1 SQLite WAL 韧性测试 (`test_database.py`)

该测试模块旨在验证系统在遭受并发写入操作时维持事务完整性的能力。

*   **测试用例**: `test_concurrent_sqlite_wal_resilience`
    *   **测试桩准备 (Fixture)**: 
        *   销毁并重新创建一个干净的 `ptclinvoice_sre.db` 实例。
        *   使用 `asyncio.gather()` 启动 100 个并发异步任务。
        *   每个任务依次执行三次写入操作：创建任务 (PENDING) -> 更新状态 (TRANSCRIBING) -> 完成 (COMPLETED)。
    *   **验证逻辑 (Asserts)**:
        1. 确保在 100 个并发任务的长生命周期（共计 300 次数据库提交）中，发生 0 起 `OperationalError (database is locked)` 异常。
        2. 在 `asyncio.gather` 操作完成后，查询数据库以断言总计生成了 100 条状态为 `TaskStatus.COMPLETED` 的精确记录。
    *   **结果**: **[PASS]** 
    *   **性能指标**: 完整的 300 次数据库事物读写耗时约为 0.52 秒。
    *   **回归性核查 (Regression)**: 验证在迁移至 `datetime.now(timezone.utc)` 后，Pytest 输出日志中不再包含任何由 Pydantic 2.x 抛出的 `datetime.utcnow()` 过时警告。

---

## 3. 测试结论

`test_database.py` 的成功执行验证了 SQLite WAL 配置的有效性。该配置使得数据库能够在无死锁的情况下处理高吞吐量、多并发的状态变更。

FastAPI (`main.py`) 的集成及标准 `/health` 探针的实装，证明该后端骨架已达到预期，具备向下阶段（Phase 2.2 容器化编排）及后续（Phase 2.3 后台任务队列）集成的工程条件。
