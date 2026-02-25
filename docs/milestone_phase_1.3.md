# PtClinVoice 开发日志 - 里程碑 (Milestone)

## 阶段：Phase 1.3 - Privacy Filter (本地端 NER 脱敏)
**日期**: 2026-02-25

### 成就与指标 (Achievements)
- **零泄漏屏障**：成功实装 `ClinicalPrivacyFilter`，利用微软 Presidio 架构在本地内存中对 `PERSON`、`PHONE_NUMBER`、`US_SSN` 等敏感实体进行深层扫描与静态字符不可逆掩码 (`[REDACTED]`) 替换。
- **极低资源开销**：作为 NLP 分析基础，选用了仅 12MB 的 `en_core_web_sm` (SpaCy)，在保障拦截率的同时，确保这段安检代码跑在无卡的云端 CPU 上不会产生资源竞争。
- **快速验证测试**：更新了 3 个全新的 Pytest 边界用例，验证了 Emily Chen 的名字和类似 SSN 格式的字符串被成功替换。

### 核心特性与架构索引 (Features & Architecture Index)

以下是本阶段隐私加固防线的实现机制及对应的类与文件：

| 机制 (Mechanism) | 源码位置 (Code Location) | 设计考量 (Architecture Decisions) |
| :--- | :--- | :--- |
| **微软引擎集成** | `privacy_filter.py` (Line 13) | `ClinicalPrivacyFilter` 初始化装载了 Presidio 的 `AnalyzerEngine` 和 `AnonymizerEngine`。我们采用了基于模式匹配的强类型静态掩码 `[REDACTED]`。 |
| **极简模型占用** | `requirements.txt` | 选用了仅 12MB 的 SpaCy `en_core_web_sm` 模型。确保了在内存不到 1GB 的 Docker 内依然能快速识别 `PERSON`、`US_SSN`。 |
| **版本断层修复** | `privacy_filter.py` (Line 38) | 修复了高版 Presidio 对 Dict 的 API 废弃。显式引入了 `OperatorConfig` 将拦截策略合法化注入引擎，防范架构崩塌。 |
| **本地防御前置** | `test_integration.py` (Line 59) | 在 E2E 联动编排中，明确必须先跑过 `mask_pii()` 的安检栈，再将字符串交予网络模块 (`deepseek_adapter.py`)。实现了真正意义上的“物理阻断”。 |

### 遗留问题与下一步 (Next Steps)
自此，我们已经跑通了 **Phase 1: 核心 AI 引擎原型验证 (Script Level)** 的全部三个拼图！
- [x] 1.1 Whisper (隔离)
- [x] 1.2 DeepSeek (重组)
- [x] 1.3 Presidio (掩码)

原型的核心数据处理引擎全部验证完成。等待上级会议批准后，我们可以进军 **Phase 2: 基础设施、后端骨架与 CI/CD**，开始将这些模块包装成可多并发、带数据库存储的异步 API 服务！
