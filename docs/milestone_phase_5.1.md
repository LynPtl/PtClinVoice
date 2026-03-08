# Phase 5.1 Milestone: 翻译流水线与音频录入增强 (Translation & Audio Enhancements)

## 概述 (Overview)
本项目已成功完成 Phase 5.1，全面升级了数据采集端和后端 AI 模型的联动能力，达成了架构层面的统一和进化。核心目标是赋予医生在无客户端的前提下直接录音的能力，并使得核心 STT 引擎可以原生地、安全地直译非英文语境对话（如阿拉伯语）。

## 关键技术落地 (Key Implementations)

### 1. 前端原声流捕获引擎 (In-Browser Audio Capture)
*   **MediaRecorder Web API 深度整合**: 彻底剥离了对外设硬件的绝对依赖，在 React (Vite) 的 `Workspace` 中引入了原生的 `AudioRecorder.tsx` 组件。
*   **富状态流转**: 包含计时器、状态机（Record -> Stop -> Upload/Discard），并将最终捕获的切片合并为现代流格式 `.webm`。

### 2. 交互式语种元数据传递 (Language Metadata Bridge)
*   **Mantine 动态表单**: 在 `UploadDropzone.tsx` 及 `AudioRecorder.tsx` 中增配下拉选框，支持 `Auto-Detect`, `English`, `Arabic`。
*   **Axios FormData 同源透传**: 取缔单文件流弊端，将 `language` 变量同原始二进制文件共同封发，实现了 `multipart/form-data` 的多模态接驳。

### 3. Whisper 的跨语系“刺客”协议 (Zero-Cost Translation Strategy)
*   **零代价扩展**: 在后端的子进程隔离区 (`app/core/stt.py`) 中，针对 `ar` 语种动态唤醒了 Faster-Whisper 的底层基石 `task="translate"`。
*   **核心安全防御**: 省去了将非脱敏外语先传向第三方 LLM 进行意译的极高泄密风险。现在，它在一张本地推理图谱中同时完成了 **Arabic Speech -> English Text**，然后将全能的纯英文文本抛给本地的 Presidio (NER 脱敏引擎)，这在保证安全的前提下实现了最优雅的翻译拓扑设计。

### 4. 抗噪鲁棒性流水线 (Acoustic Noise Robustness)
*   **浏览器端 DSP 净化**: 在浏览器层面强制开启 `noiseSuppression`, `echoCancellation` 及 `autoGainControl`。这意味着在复杂的临床病房背景音中，设备能自动压制空调、风扇等白噪，并稳压人声。
*   **后端 FFmpeg 离线滤镜**: 在推理前置流水线中引入了 `afftdn` (基于 FFT 的频域降噪) 和 `loudnorm` (广播级响度重归一化)。这确保了无论输入音频质量如何，Whisper 接收到的都是标准化的、高信噪比的单一音源。

### 5. 高性能模型升维 (Model Tier Upgrade)
*   **“幻觉”现象硬核修复**: 针对 `tiny` 模型在处理长段非母语录音时的乱码漂移问题，全量升级为 **`small`** 级别权重（约 460MB）。
*   **VAD 语音活动检测**: 启用了 Silero VAD 过滤机制，在推理前自动切除无意义的静音和环境杂音区，彻底解决了静音段诱发的模型幻觉现象。

## 最新阶段架构结论 (Architectural Conclusion)
前端已由纯静态呈现转为强交互型（具备净化能力的录音入口），而后端则进化为具备“脏数据清洗”能力的工业级翻译流水线。基础架构的健壮性已全面对标商业级 SRE 产品水平，为后续的 UIUX 深度定制和病历号管理打下了铁板基座。
