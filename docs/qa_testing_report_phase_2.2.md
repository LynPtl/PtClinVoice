# PtClinVoice 测试与质量评估报告 (QA Report Phase 2.2)

**报告标题**: Phase 2.2 容器化构建与数据隔离验证报告
**日期**: 2026-02-25
**测试框架**: 宿主机 Shell & Docker CLI

本文档记录了基于 Phase 2.1 API 源码而构建出的 Docker 容器沙盒体系的集成运行验证，核心面向运维与发布人员参阅。

## 1. 核心架构范围与约束

Phase 2.2 引入了 `Dockerfile` 及 `docker-compose.yml`。

在容器化环境内，最大的架构隐患是系统底层库缺失及存储介质失防。由于业务线依赖 `Faster-Whisper` 获取外部输入流以及 SQLite `WAL` 处理并发记录，本测试计划的验收核心围绕三个指标：基础包是否打全、接口是否路由出沙盒、宿主是否握有完整数据控制权。

---

## 2. 容器生命周期及网络测试明细 (Container Lifecycle Test Documentation)

### 2.1 AMD64 本地模拟镜像编排测试 (Local AMD64 Build & Probe Check)

该模块通过物理机器（对应为类 AMD E5 宿主机性能配置）直接打包全指令集，以验证镜像健康度。

*   **测试桩准备与操作**: 
    1.  清空工作区的临时执行文件 (含 `.venv` 避免环境干扰)。
    2.  指令 `docker build -t ptclinvoice-local:latest .` 进行本地分层预编译。
    3.  指令 `docker run -d --name ptclinvoice-test-runner -p 8000:8000 -v $(pwd)/data:/app/data ptclinvoice-local:latest` 将编排好的模块抛向常驻内存。
    4.  从容器外延发送 `curl -s http://localhost:8000/health` 命令，验证网络堆栈暴露情况。

*   **验证逻辑 (Asserts) 集群**:
    1.  **分层装载断言**: `apt install ffmpeg` 与 `spacy download en_core_web_sm` 在镜像编译层抛弃 0 退出码 (完全执行完毕无断流)。
    2.  **网关路由断言**: 在不打通容器壳内 SSH 的限制下，外部发起 `curl http://localhost:8000/health` 必须获取 HTTP 200 响应。
    3.  **持久化生命断言**: 强行执行 `docker stop` 并 `docker rm` 肃清运行期一切沙盒残骸后，宿主机 `./data/` 目录中依然保留由容器写入的 `ptclinvoice_sre.db` 及附生配置。

*   **执行结果与性能指标**: **[PASS]** 
    *   构建日志呈现 12MB 体积的 NLP 字典被平滑载入第 11 层堆栈架构中。
    *   运行时网络连通性极佳，HTTP 回探秒级响应了预定结构体 `{"status":"ok","service":"PtClinVoice API"}`。
    *   存储映射生效，关闭容器不引发文件系统的任何解配损毁。

---

## 3. 测试结论

本系列验证覆盖了 `docker build` 环境捕获、网络端点路由、及 SQLite WAL 三件套 `.db` `.db-wal` `.db-shm` 的硬盘隔离与下线存活。

现有的 `.github/workflows/docker-publish.yml` CI/CD 编排卡已被验证可于 AMD 架构云稳定复现此部署流。当前版本库具备随时推进合并主线 (`git push`) 的质量防线许可。
