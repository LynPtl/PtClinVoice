# PtClinVoice 开发日志 - 里程碑 (Milestone)

## 阶段：Phase 2.2 - Docker 容器化与 GitHub Actions CI/CD
**日期**: 2026-02-25

### 成就与指标 (Achievements)
本项目已完成“不可变基础设施 (Immutable Infrastructure)”演进。本阶段成功构建了基于 `python:3.12-slim` 的运行环境，并集成 `ffmpeg` 与 SpaCy 语言模型。同时确立了 GitHub Actions 自动化构建与推流流水线。

### 核心特性与架构变更 (Features & Architecture Changes)

以下是在引入容器编排与 CI/CD 过程中的变更机制与代码实现：

| 机制 (Mechanism) | 修改对象 (Modified Files) | 设计与架构考量 (Architecture Decisions) |
| :--- | :--- | :--- |
| **单平台极速构建** | `.github/workflows/docker-publish.yml` | 配置了触发于 `push` 事件的 CI/CD 流水线，并明确约束目标架构为 `linux/amd64`，旨在避免因 QEMU 跨架构编译 C++ 依赖而引发的流水线超时问题。构建物将被推至 GitHub Container Registry (GHCR)。 |
| **构建期缓存装载** | `Dockerfile` | 在镜像构建阶段（非运行时）执行 `python -m spacy download en_core_web_sm` 与 `apt install ffmpeg`，将 12MB 的 NLP 模型及系统级音视频解码库固化为镜像底包层，规避了启动时的下载耗时及网络不可控因素。 |
| **环境变量拦截防护**| `.dockerignore` | 显式声明屏蔽 `.env` 与 `.git`，从物理边界隔绝包含了 `DEEPSEEK_API_KEY` 等敏感秘钥的文件被合并压缩进公开镜像层，防范代码仓库级的数据泄露。 |
| **持久卷深度映射** | `docker-compose.yml`, `database.py` | 设定 SQLite 在 `DB_PATH` 指定的容器内绝对路径 (`/app/data`)。在 Docker Compose 中采用目录级挂载策略 (`./data:/app/data`)，确保与主 `.db` 文件伴生的暂态锁存文件 (`.db-wal`, `.db-shm`) 一并导出宿主机，进而防止在无状态容器重启期间触发 `database disk image is malformed` 数据破损。 |

### 容器系统层验证结论 (Testing & Metrics)
根据在宿主机上的实弹构建及运行测试：
*   **方法论**: 在本地使用 `docker build -t ptclinvoice-local:latest .` 完整模拟线上编译周期。随后以 `docker run` 暴露 8000 端口并在宿主调用 `/health` 探针。
*   **结果**: `/health` 节点按预期响应 `{"status":"ok","service":"PtClinVoice API"}`。且宿主机的 `./data` 内如期捕获 SQLite 文件簇。容器从创建到销毁数据零丢失。
*   详情可见：[Phase 2.2 QA Testing Report](./qa_testing_report_phase_2.2.md)。

### 遗留问题与下一步 (Next Steps)
- 利用 FastAPI 的轻量特性，将处于沉寂状态的 Phase 1 内核 (`stt_core.py` 独立进程跑转器) 缝合进 API 生命周期内，将其改造为后端独立异步存活的 Worker (Phase 2.3)。
