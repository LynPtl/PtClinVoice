# 快速本地联调向导 (Local Testing Guide)

本指南专为开发者与测试专员 (QA) 编写，指导如何在本地同时拉起 **FastAPI 后端** 与 **React / Vite 前端**，并执行完整的单元与全链路测试。

## 1. 环境准备 (Prerequisites)
1. 确保安装了 `python >= 3.10` 且已安装 `ffmpeg` (处理音频流依赖)。
2. 确保安装了 `node >= 18` 与 `npm`。
3. 拥有一个可用的 DeepSeek API Key。

## 2. 后端核心栈启动 (Backend API Server)

1. **进入后段根环境**:
   ```bash
   cd PtClinVoice
   ```
2. **初始化虚拟环境**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **配置凭证 (新建 `.env` 文件)**:
   ```env
   DEEPSEEK_API_KEY=your_key_here
   JWT_SECRET_KEY=dev_local_secret
   ```
4. **拉起 FastAPI 网关**:
   ```bash
   PYTHONPATH=. uvicorn app.main:app --reload --port 8000
   ```
   *服务将在 `http://localhost:8000/docs` 上线。*

## 3. 前端交互控制台拉起 (Frontend Web UI)

新开一个终端窗口：

1. **进入前端目录并下载依赖**:
   ```bash
   cd PtClinVoice/frontend
   npm install
   ```
2. **启动 Vite 代理开发服务器**:
   ```bash
   npm run dev
   ```
   *控制台将在 `http://localhost:5173` 上线，且针对 `/api` 的请求将自动通过 Vite proxy 被重定向至 `http://localhost:8000/api` 以规避 CORS 跨域问题。*

## 4. 全量自动化测试集执行 (Automated Test Suites)

为了保障系统鲁棒性，本工程实现了严格的后端（Pytest）与前端（Vitest）分离测试策略。

### 4.1 后端容灾防盗测试 (Backend Pytest)
测试内容涵盖：JWT 零信任阻断拦截、OS级物理音频粉碎机制验证、高并发 SQLite 数据库锁灾恢复、进程隔离级别的 STT 内存耗尽自愈等。
```bash
# 在 PtClinVoice 根目录操作
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -v
```

### 4.2 前端视图集成测试 (Frontend Vitest)
测试内容涵盖：Zustand 状态机切换（登录与登出副作用）、Mantine 断言 UI 渲染、EventSource流拦截映射等。
```bash
# 在 PtClinVoice/frontend 目录操作
npm run test
```

## 5. 常规 E2E 手动走查流 (Manual QA Flow)
1. 打开 `http://localhost:5173/login`。
2. （初始版本无注册页）您可以使用后端 `tests/test_auth.py` 中生成的默认测试表单，或者临时调用 `/docs` 的快捷登录下发 Token。
3. 上传一段录音，观察列表中的状态由 `PENDING` 到 `COMPLETED` 的无需刷新自动转译。
4. 审查目录物理磁盘，验证源音频已根据*阅后即焚*机制被删除。
