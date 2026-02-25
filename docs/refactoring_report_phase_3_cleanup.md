# 技术文档：后端架构重构与目录规范化报告 (Phase 3 Cleanup)

## 1. 概述
在 Phase 3 开发接近尾声时，为了提升系统的可扩展性、安全性和符合 Python 后端行业规范，我们对 PtClinVoice 的项目结构进行了深度重构。本次重构将原本散落在根目录的源文件整合为标准的 Python Package 结构，并同步修复了由此引发的测试链路与环境配置问题。

## 2. 核心架构变更
我们将目录结构从“扁平化”转向“模块化”，新的逻辑坐标如下：

| 原路径 | 现路径 | 说明 |
| :--- | :--- | :--- |
| `main.py` | `app/main.py` | API 入口点 |
| `auth.py` | `app/auth.py` | JWT 鉴权逻辑 |
| `database.py` | `app/database.py` | SQLModel ORM 与数据库配置 |
| `worker.py` | `app/worker.py` | 异步任务调度逻辑 |
| `stt_core.py` | `app/core/stt.py` | 核心 STT 高能耗 zone |
| `privacy_filter.py` | `app/core/privacy.py` | 本地 PII 脱敏逻辑 |
| `deepseek_adapter.py` | `app/core/deepseek.py` | 云端 LLM 适配器 |
| `run_*.py` | `scripts/run_*.py` | 管理与维护脚本 |
| `test_*.py` (根目录) | `tests/test_*.py` | 单元与集成测试 |

## 3. 技术调整细节

### 3.1 导向绝对包引用 (Absolute Package Imports)
为了支持包级运行，所有内部引用均已更新。例如：
- 错误引用：`from database import engine`
- 标准引用：`from app.database import engine`
- 测试引用：`from app.main import app`

### 3.2 自动化测试修复
重构后，我们针对回归的 15 项测试进行了专项修复：
- **鉴权注入**：为 `test_worker_oom.py` 和 `test_worker_pipeline.py` 补充了 JWT 鉴权前置逻辑，确保测试请求不会触发 401 Unauthorized。
- **并发冲突隔离**：在 `test_database.py` 中引入了独立的测试数据库 `test_concurrent.db`，防止高压力 WAL 测试污染生产/开发数据库文件。
- **多进程路径修正**：针对 `stt_core` 的隔离进程测试，修正了子进程中的模块加载路径，解决了 `ModuleNotFoundError`。

### 3.3 环境配置同步
- **Dockerfile**：更新启动命令为 `CMD ["uvicorn", "app.main:app", ...]`，确保容器内入口点正确。
- **.gitignore**：大幅扩充规则，严格屏蔽 `__pycache__`、`.venv`、`.pytest_cache` 以及包含 PII 的持久化数据卷目录。

## 4. 维护指南
- **启动服务**：在根目录下执行 `PYTHONPATH=. uvicorn app.main:app --reload`。
- **运行测试**：执行 `PYTHONPATH=. pytest tests/ -v` 以确保 100% 通过率。
- **脚本运行**：所有管理脚本需通过包路径调用，如 `python scripts/run_live_e2e_diarization.py`。

---
**结论**：重构后的代码库具备了更清晰的边界感（Domain Boundary），为 Phase 4 前端建设提供了稳健的后端消费接口。
