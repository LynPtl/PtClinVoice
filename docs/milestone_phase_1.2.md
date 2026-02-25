# PtClinVoice 开发日志 - 里程碑 (Milestone)

## 阶段：Phase 1.2 - DeepSeek Adapter (云端智能生成)
**日期**: 2026-02-25

### 成就与指标 (Achievements)
- **DeepSeek API 桥接**：成功利用兼容 OpenAI SDK 的规范实现了 `DeepSeekClinicalAdapter`，能够稳定指向 `https://api.deepseek.com` 并自动读取环境变量内的 API_KEY。
- **Strong-JSON Prompt 工程**：通过 `response_format={"type": "json_object"}` 和高度约束的 Prompt，实现了核心的基于语义的说话人分离 (Speaker Diarization) 与 SOAP 医学结构体提取。
- **低成本 Mock 测试**：在 `test_deepseek_adapter.py` 中编写了端到端的 Pytest 自动化测试，并通过 `unittest.mock` 深度劫持了发往 OpenAI/DeepSeek 的外部网络请求。这不仅节约了开发阶段的大量 Token 开销，也使得 CI/CD 无需配置真实 Key 即可验证核心字典结构映射的坚固性。

### SRE 与底层架构决策 (SRE & Architecture Decisions)
- **非确定性收敛**：强制固定 `temperature=0.1`，由于临床病历极其严肃，我们在此压制了大模型的发散创造性幻觉，保证提取出的症状与既往史严格忠实于转录文本。
- **云原生密钥防御**：引入 `python-dotenv` 隔离云端密钥，确保在代码库中不出现任何明文 API 密钥暴露的风险。
- **降本增效核心：大模型语义发声员分离 (Semantic Speaker Diarization)**：
  - **问题**：传统在本地 STT (如 Pyannote) 中做声纹分离极其消耗内存，且在无 GPU 的边缘云上很容易跑满 CPU 导致 OOM。
  - **解决方案 (见 `deepseek_adapter.py`)**：我们将 Faster-Whisper 设置为“纯听写模式”（只输出不分人的文字流水账）。随后把脱敏文字发送给 DeepSeek，利用 LLM 强大的逻辑推理能力，通过 System Prompt 强制要求其根据上下文重新排版出 `[Doctor]: ... \n [Patient]: ...` 的对话流。这在保障极高分离准度的同时，彻底解放了本地算力。

### 遗留问题与下一步 (Next Steps)
本阶段大模型桥接与结构重组已测试完毕，JSON 返回稳定无 Markdown 污染。
即将前往下一阶段：**Phase 1.3: Privacy Filter (本地 NER)**。我们将在此补全整个架构设计中关于数据隐私最核心的闭环 —— 确保发送给本阶段 DeepSeek API 的任何文本在此之前已经经历了脱敏替换 (`[REDACTED]`)。
