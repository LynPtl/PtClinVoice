# PtClinVoice 测试策略与用例文档 (Testing Strategy & Fixtures QA)

本文档旨在记录 PtClinVoice 项目的质量保证体系、测试目标以及对应测试桩 (Fixtures) 的设计思路。本工程坚持严格的**白盒驱动测试**与**架构约束断言**。

## 目录
1. [Phase 1.1: 隔离多进程 STT 测试引擎](#phase-11)
2. [Phase 1.2: DeepSeek LLM 适配器拦截测试](#phase-12)

---

## 1. Phase 1.1: 隔离多进程 STT 测试引擎 (`test_stt_core.py`)

### 1-A. 真实医疗语境转写穿透测试
**测试目标 (Test Objective):**
验证底层的 `faster-whisper` 是否能够准确从语音流中提取包含临床价值的英文专业术语，并验证首字母大写与末尾标点的 Prompt 强制策略是否生效。

**测试用例与 Fixtures:**
- `texts/fixtures/standard_accent.mp3`: 
  - **来源**: 由微软 `edge-tts` (en-US-SteffanNeural) 生成。
  - **内容**: "The patient is a 45-year-old male with acute right lower quadrant abdominal pain."
  - **断言逻辑**:
    - 检查输出是否为 String 类型结构体。
    - 强制断言输出文本首字母必须大写。
    - 强制断言输出文本必须以有效标点结尾 (`.`, `?`, `!`)。
    - 对提取物的自然语义中是否精准捕捉到单词 `patient` 以及核心病灶词汇 `abdominal pain` 进行深层探测。

### 1-B. OOM 进程绞杀隔离免疫测试
**测试目标 (Test Objective):**
医疗语音模型因加载显存或内存波动，极易发生幽灵内存泄漏 (OOM) 或底层 C++ 段错误 (Segmentation Fault)。本测试断言主进程必须完全免疫子进程的极端暴力死亡。

**测试用例:**
- `malicious_oom_worker()`: 一个恶意的 Mock 工作函数，被注入到了底层的隔离沙盒内。
- **触发逻辑**: 该工作者一旦启动，立刻向 Linux 发送真实的 `SIGKILL` 自尽信号（等同于被内核极其暴力的 OOM Killer 强行斩首，不走任何 Python 的 Exception 处理池）。
- **断言逻辑**:
  - `run_stt_isolated` 的看门狗逻辑必须能在主进程察觉其异状捕捉到 `p.exitcode` 非 0 的状态。
  - 必须优雅地将底层死亡包装为受控的 `MemoryError("STT Process killed violently")` 抛出，使得提供并发 API 的主干线不仅不会崩溃，还能将错误反馈给前端系统。

---

## 2. Phase 1.2: DeepSeek LLM 适配器拦截测试 (`test_deepseek_adapter.py`)

### 2-A. Strict-JSON 强路由与大模型零成本 Mock 测试
**测试目标 (Test Objective):**
鉴于 DeepSeek API 调用基于真实互联网消耗 Token（产生真实财务账单计费），我们在此利用拦截器实现脱机状态下的架构全覆盖跑通。必须确保从模型侧发送回来的内容能被 100% 反解析回严格带格式的 JSON/Python Dict，并且拒绝混杂 Markdown 的富文本污染系统的数据层。

**测试用例:**
- 拦截器 (Interceptor): 利用 Python 的 `unittest.mock.patch` 以极其激进的手法注入 OpenAI SDK 内部最深层的执行对象树 (`client.chat.completions.create().choices[0].message.content`)。
- **输入**: 长段糅杂医患交谈的模拟病历。
- **断言逻辑**:
  - 全流程不产生实际网络 IO，瞬间返回 Mocked 数据。
  - 核心断言 JSON 解析是否由于格式不合法而爆炸。
  - 深层探测结构树的完整性：断点检测返回的 Python 字典内是否存在顶层 `dialogue`, `soap` 字段。
  - 探测 `soap` 对象下是否具有完备的子项体系（`subjective`, `objective`, `assessment`, `plan`），缺失任何一项直接拉响警报 (`AssertionError`)。

### 2-B. 边界条件防御 (Edge Cases)
**测试目标 (Test Objective):**
防止空数据流经过昂贵的大模型引发无意义的网络耗时与日志污染。
**断言逻辑**:
- 对传入 `generate_soap_note` 进行前置空集（空格符、换行符）注入测试。
- 确保系统立刻以 `ValueError` ("Transcript cannot be empty") 熔断，拒绝转发给云端。
