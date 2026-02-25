# PtClinVoice 测试与质量评估报告 (QA & Testing Report)

**报告标题**: Phase 3 访问控制与数据销毁测试报告
**日期**: 2026-02-26
**验证模块**: 应用层鉴权边界与系统级 `os.remove` 审计

本文档为 Phase 3 访问链路授权机制与底层多媒体资源“阅后即焚”逻辑的持续集成测试断言记录。

## 1. 测试用例明细 (E2E Authentication & Lifecycle Auditing)

本阶段测试聚焦 API 端点安全性和磁盘挂载点的合规性，共计执行 4 项核心测试。

### 1.1 授权拦截基线测试 (`test_unauthorized_access_rejected`)
*   **测试桩**: 向保护路由发起缺乏 `Authorization: Bearer` 头部的 HTTP POST 请求，注入伪造音频路径。
*   **验证逻辑**: 确保 FastAPI 依赖项抛出鉴权失败异常，严格断言接口返回 `HTTP 401 Unauthorized` 状态码，阻止任务编排管道的调度。
*   **结果**: **[PASS]**

### 1.2 JWT 签名验证与有效状态检查 (`test_jwt_auth_success`)
*   **测试桩**: 调用 `/api/auth/login` 进行用户登陆生成有效 token，随即将合法的 Bearer Token 与真实 `.mp3` 测试用夹具共同发送至端点。
*   **验证逻辑**: 验证系统正常返回 `HTTP 200 OK`，并成功派发 `task_id`，且使用者有权后续发起请求对对应 `task_id` 进行状态追踪。
*   **结果**: **[PASS]**

### 1.3 隔离权限越权测试 (`test_horizontal_privilege_escalation_blocked`)
*   **测试桩**: 初始化独立测试账号 User A 和 User B。由 User A 生成一条关联其 `owner_id` 的任务记录。随后由 User B 携带合法 Token 跨越身份去调用此记录的元数据查询接口。
*   **验证逻辑**: 查验数据库提取记录时的归属权校验断言。确保非授权访问被即时拦截并引发 `HTTP 403 Forbidden`，切断水平越权数据泄露。
*   **结果**: **[PASS]**

### 1.4 音频生命周期销毁审计 (`test_upload_and_physical_shredding`)
*   **测试桩**: 挂载测试账户并实际上传一个高风险音频文件。测试线程随后主动陷入轮询机制监听后台的 worker 管线状态机变迁。
*   **验证逻辑**: 当检测到核心管道状态跃迁至终态 (`COMPLETED` 或 `FAILED`) 落库时，审计探针停止循环，穿透至操作系统底层目录执行 `os.path.exists()` 探寻 `/data/uploads/` 挂载点下的原始接收音频文件。
*   **关键断言**: 底层文件系统存在性必须返回 `False`，在任何状况下（包括引发处理管线崩溃时），验证后台的回收机制被 100% 调用执行了物理擦拭动作。
*   **结果**: **[PASS]**

## 2. 工程缺陷与环境修正记录 (Bug Fixes Context)

1. **依赖库适配层重构**: 最初使用的 `passlib` 中 `bcrypt` 模块隐式调配了即将在 Python 3.13 退役的内置 `crypt` 模块而引发废弃警告；同时通过测试发现了使用该包底层产生的长度超过 72 bytes 限制抛出 ValueError 而截断的系统库级问题。
   - **重构方案**: 卸载 `passlib` 并应用环境固定安装 `pip install bcrypt==3.2.2`。修改 `auth.py` 安全组件模块，直接用底层标准库处理 `hashpw` 字节级比对。重置运行生命周期后执行警告升级报错测试（`pytest -W error`），全站警告消解。
2. **FastAPI 生命周期事件更新**: `main.py` 内用于启动 SQLite-WAL 资源连接的 `@app.on_event("startup")` 装饰器产生过时诊断提醒。
   - **重构方案**: 重写替换为符合新版标准的异步 `asynccontextmanager` 生命周期上下文控制器，规范了底层资源生命管线。同样通过无警告级别测试。

## 3. 测试结论

Phase 3 的安全认证隔离层和自动化销毁逻辑经受住了严苛断言。未经验证请求与横向越权尝试被百分之百阻断，而临时缓存的多媒体病例挂载也在管线完结时（包含成功及故障处理侧分支）完全触发销毁动作。符合工程预期完成质量验收。
