# PtClinVoice - 前端架构 (Frontend Architecture)

这是 **PtClinVoice** 临床转录与 SOAP 笔记生成系统的 React + TypeScript 前端工作台。它利用 Mantine UI 组件库实现了严谨、专业的医疗级视觉界面，并通过 Axios 和 Server-Sent Events (SSE) 技术与底层的 FastAPI 后端实现全双工的高速通信。

## [架构选型] 技术栈 (Technology Stack)

- **核心框架**: [React 18](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- **构建引擎**: [Vite](https://vitejs.dev/) (提供极速的模块热替换 HMR)
- **UI 组件库**: [Mantine UI v7](https://mantine.dev/) (高定制化、无缝支持暗色模式)
- **路由控制**: [React Router DOM v6](https://reactrouter.com/)
- **状态管理**: [Zustand](https://docs.pmnd.rs/zustand/) (用于极轻量级的全局 Auth 状态同步)
- **图标生态**: [@tabler/icons-react](https://tabler.io/icons)
- **API 客户端**: [Axios](https://axios-http.com/)

## [工程结构] 物理目录结构 (Directory Structure)

```text
frontend/
├── src/
│   ├── api/          # Axios 实例、JWT 拦截器与核心 API 接口层 (tasks.ts, auth.ts)
│   ├── components/   # 高度复用的 UI 积木 (UploadDropzone, TaskList, ProtectedRoute)
│   ├── pages/        # 主路由视图容器 (Login, Dashboard, Workspace)
│   ├── store/        # Zustand 全局状态池 (useAuthStore.ts)
│   ├── App.tsx       # 根组件与应用路由导航结构
│   └── main.tsx      # 入口文件与 MantineProvider 全局注入
├── nginx.conf        # 生产级别的 Nginx 反向代理与前端路由配置文件
├── Dockerfile        # 面向云原生部署的生产级前后台联合镜像构建项
└── vite.config.ts    # 开发期的 Vite 引擎配置 (含防跨域代理指令)
```

## [开发环境] 本地极速开发指引 (Development Setup)

请在此之前确保您已安装 Node.js 18+ 环境。

1. **安装所有依赖包**:
   ```bash
   npm install
   ```

2. **拉起本地代理开发服务器**:
   ```bash
   npm run dev
   ```
   > **架构注记**: Vite 本地开发服务器将自动拦截所有以 `/api` 开头的网络请求，并将其无缝代理转发至 `http://localhost:8000` 以彻底规避浏览器的 CORS 跨域限制。因此，您必须保证本机的 FastAPI 后端进程也在正常的运行状态并且开启在此端口。

## [部署发布] 生产模式构建 (Building for Production)

在分发之前请执行全量编译指令：

```bash
npm run build
```
这部分产物将被高强度压缩并置于 `dist/` 目录下，该目录下的纯态 HTML 与 JS 文件可以被放心地交给任何超轻量 HTTP 伺服器（如 Nginx）进行零状态、零配置的集群分发。

## [质量保障] 视图组件与链路测试 (Automated Testing)

为了通过 CI/CD 构建链，请先利用 Vitest 对各个界面与状态机进行断言：

```bash
npm run test
```
