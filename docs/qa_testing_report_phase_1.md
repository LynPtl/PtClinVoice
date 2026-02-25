# PtClinVoice 测试与质量评估报告 (QA & Testing Report)

**报告标题**: Phase 1 核心 AI 引擎原型测试报告
**日期**: 2026-02-25
**测试框架**: Pytest 9.0.2

本文档是对 Phase 1（核心 AI 原型）开发的测试策略、用例设计及其集成运行结果的总结，提供了端到端（E2E）质量断言报告，专供研发与 SRE 人员参阅。

## 1. 测试体系概览 (Testing Framework Overview)

在第一阶段，我们的核心流是无需图形界面的纯数据流转。整个测试管线使用 **Pytest** 驱动，主要涉及三大模块。

我们严格遵循 **SRE 防御性验证规范**：所有的外部 API 调用一律使用 `unittest.mock` 进行隔离，对于内核级的 OOM 崩溃则通过进程发送 `SIGKILL` 进行模拟测试。

**总计执行全自动化用例**: 8
**测试结果**: 全部通过 (100% PASS)
**自动化跑桩耗时**: ~9.57s

---

## 2. 单元测试明细 (Unit Tests)

### 2.1 STT 模型听写引擎 (`test_stt_core.py`)
主要负责验证 `Faster-Whisper` 能否抗住系统物理封杀，并在不抛出 GPU 缺失错误的情况下成功跑回病理文本。

*   **用例 A: 音频通过性验证 (`test_stt_standard_audio_handling`)**
    *   **测试桩 (Fixture)**: 位于 `tests/fixtures/standard_accent.mp3` 的真实 MP3 音频（由 Microsoft Edge-TTS "en-US-SteffanNeural" 合成的 45岁男性患者病史发音）。
    *   **验证逻辑 (Asserts)**: 
        1. 验证输出结构是否为原生 Python `str`。
        2. 验证引擎是否成功在噪音/口音中捕获了关键词 `patient` 及 `abdominal pain` (腹痛)。
        3. 验证 `initial_prompt` 的约束效果：输出文本必须以大写字母开头，结尾带合法标点 (`.`, `?`, `!`)。
    *   **结果**: **[PASS]**

*   **用例 B: OOM 内核退出与主进程存活测试 (`test_stt_oom_isolation_survival`)**
    *   **测试桩 (Fixture)**: 采用 `multiprocessing.get_context('spawn')` 物理隔离空间；通过注入 `malicious_oom_worker` 发出 `SIGKILL` 指令。
    *   **验证逻辑 (Asserts)**: 子进程非正常死亡时，主控循环必须捕获 `p.exitcode != 0` 的死亡标识。系统必须抛出受控的 `MemoryError("STT Process killed violently")` 异常，而不影响主线程。
    *   **结果**: **[PASS]**

### 2.2 本地医疗隐私滤网 (`test_privacy_filter.py`)
本模块旨在验证基于 `Microsoft Presidio` 引擎和小巧的 `en_core_web_sm` (SpaCy) 模型，能否在拔断网线的条件下准确屏蔽病历特征。

*   **用例 C: 绝对人名销毁 (`test_privacy_filter_person_redaction`)**
    *   **测试桩**: 构造上下文相关的英文复合病句: "Hello, my name is Emily Chen and my doctor is Dr. James Wilson."
    *   **验证逻辑**: 全句经过 `ClinicalPrivacyFilter.mask_pii()` 后，确认文本内不包含字符串 "Emily", "Chen", "James", "Wilson"。替换符 `[REDACTED]` 必须占位成功。
    *   **结果**: **[PASS]**

*   **用例 D: 敏感数字与证件封堵 (`test_privacy_filter_ssn_and_phone`)**
    *   **测试桩**: 带有美国社保号 (012-34-5678) 和常规电话号 (555-019-8372) 的文案。
    *   **验证逻辑**: 数字串全部检索不到。确认文本含有至少两次 `[REDACTED]` 屏蔽。
    *   **结果**: **[PASS]**

*   **用例 E: 空载抗性 (`test_privacy_filter_empty_string`)**
    *   **测试桩**: 纯空格或 `""` 字符串传输。
    *   **验证逻辑**: 引擎不触发异常，直接返回空格本身。
    *   **结果**: **[PASS]**

### 2.3 LLM 解析适配器 (`test_deepseek_adapter.py`)
此环节在不消耗 API Key 真实 Token 的情况下验证基于 OpenAI SDK 的接口解析容错率。

*   **用例 F: JSON 结构解析 (`test_deepseek_adapter_json_structure`)**
    *   **测试桩**: 使用 `unittest.mock.patch` 拦截发往大模型的调用，返回一段人工编写好的 DeepSeek JSON Text 数据。
    *   **验证逻辑**: 验证提取层能否不抛异常地使用 `json.loads` 加载，同时确认返回结构体包含：`soap` 下含有 `subjective`, `objective`, `assessment`, `plan`。
    *   **结果**: **[PASS]**

*   **用例 G: 空集熔断保护 (`test_deepseek_adapter_empty_transcript`)**
    *   **测试桩**: 输入空白的 STT 稿件。
    *   **验证逻辑**: 网络发包层必须直接抛出 `ValueError("Transcript cannot be empty.")`。
    *   **结果**: **[PASS]**

---

## 3. 集成测试阶段 (Phase 1 E2E Integration)

**测试模块**: `test_integration.py` (`test_phase_1_end_to_end_pipeline`)
此模块用于验证 STT、隐私过滤与 LLM 三大组件协同工作时的数据流动完整性。

*   **链路流程**: **音频注入** ➡️ Faster Whisper **生成明文** ➡️ 强行 **注水 PII (假名与证件)** ➡️ Presidio **实施物理打码** ➡️ MOCK 版 DeepSeek **大模型提取 SOAP**。
*   **集成步骤验证**:
    1. 前方 Whispser 捕获了病历的 `abdominal pain`。
    2. 中途注入的高危特征 `Robert Oppenheimer`（名字）和 `999-88-7777` 在途经中段后被有效剔除。
    3. 后段输出的字典树里的最终 `subjective` 对象，必须完好保留原始的 `[REDACTED]` 特征，并且继承了最早一期的 `abdominal pain` 症状记录。
*   **结果**: **[PASS]**

---

## 4. 实机云环境验证 (Live Cloud Environment Validation)

**测试模块**: `test_real_deepseek_api.py` (独立验证方案，非 Pytest Mock 控制)
脱离安全 Mock 壳，用真金白银实弹测试部署者的真实大模型配额能够在复杂的互联网中执行医疗重构。

*   **执行方式**：手工执行带参 `python3 test_real_deepseek_api.py`。
*   **执行与验证记录**:
    *   成功识别到环境变量 `.env` 下属的 `DEEPSEEK_API_KEY`。
    *   成功跨越本地沙盒网关，并借由 https 与 `api.deepseek.com` 执行握手与 SSL 发包。单次扣除不足 50 Tokens。
    *   捕获到了未经幻觉污染的优质回包：
        ```json
        {
          "dialogue": "[Doctor]: How are you...\n[Patient]: I've had a headache for 3 days...",
          "soap": {
            "subjective": "Patient reports a headache lasting for 3 days.",
            "assessment": "Headache of 3 days duration...",
            "plan": "Prescribe Tylenol for symptomatic relief."
          }
        }
        ```
*   **结果**: **[PASS]**

---

## 5. 结论评测 (Closing Assessment)

基于医疗文字流的独立节点与端对端串联测试验证，**PtClinVoice Phase 1 - 基础 AI 算力与过滤引擎池** 架构代码符合要求，不仅能处理内核级的 OOM GPU显存崩溃隔离，同时满足基本的实体消隐脱敏需求，所有组件验证通过。此时可转入异步多并发 (Phase 2 API 层) 的研发轨道部署。
