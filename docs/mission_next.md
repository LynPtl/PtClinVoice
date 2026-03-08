# Mission Next: 未来演进与补充需求

项目在达到基础的生产可用状态后，将继续拓展以下高优先级特性，以满足更复杂的真实医疗场景需求。

## 1. 原生多语言与本地化翻译架构 (Native Multilingual & Local Translation)
**核心业务流**: 医生录音 (英文 / 阿拉伯语) -> **本地转录并翻译为英文** -> 本地 NER 脱敏 -> 云端 LLM (DeepSeek) 生成全英文 SOAP 笔记。

**为什么必须本地翻译？**
为了坚守**零数据泄露**与**本地重计算**的绝对底线，含有患者生物特征和原始病情的非英语语音/文本，绝不能跨过安全边界发往任何云端 API（包括 DeepSeek）进行翻译再脱敏。如果发往云端翻译，将彻底破坏我们的脱敏防火墙体系。

**推荐的本地翻译/转录选型方案：**

1.  **方案 A：Faster-Whisper 原生直译 (最推荐，零额外架构开销)**
    *   **原理**: Whisper 模型本身就是在海量多语言对上训练的，先天具备将非英语语音直接转录并翻译成英文文本的能力。
    *   **实现**: 在加载 Faster-Whisper 推理请求时，指定 `task="translate"` 而非默认的 `task="transcribe"`。
    *   **优点**: 架构极简，不增加任何新的模型依赖；省去了“先转录为阿语 -> 再翻译为英语”的两段式开销，直接输出英文字符，完美衔接现有的 NER 脱敏引擎（Presidio 英文包最成熟）。
    *   **注意**: 必须评估所使用的 Faster-Whisper 模型权重（如 `small` / `medium`）对于医疗领域阿拉伯语的直译精度。如果精度不够，可能需要升级为 `large-v2/v3`，这将带来极大的本地内存与算力开销。

2.  **方案 B：两段式级联模型 (Whisper 转录 + 本地 NMT 模型翻译)**
    *   **原理**: Whisper 专职负责 `Arabic Audio -> Arabic Text`，随后串联一个专门的开源本地离线机器翻译模型（如 **Argos Translate** / **HuggingFace Opus-MT** `Helsinki-NLP/opus-mt-ar-en`）进行 `Arabic Text -> English Text`。
    *   **实现**: 在 FastAPI 的 Worker 进程中，额外预加载一个翻译模型流水线。
    *   **优点**: 分而治之，翻译模型的定制化能力更强。如果 Whisper 对医学阿语直译效果差，专有翻译模型可能拥有更好的领域适应性。
    *   **缺点**: 显存/内存开销翻倍。系统需要同时驻留声学模型和 NLP 翻译模型；增加了一条失败链路；而且目前的本地 NER 工具对阿拉伯原文的直接脱敏效果极差，这意味着即使是两段式，也必须先翻译成英语再去脱敏，过程耗时显著增加。

3.  **方案 C：本地轻量级通用 LLM 直出 (Ollama + Llama3 8B / Qwen)**
    *   **原理**: 在本地部署一个量化后的小型大语言模型，让 Whisper 仅输出阿文逐字稿，然后由本地 LLM 执行翻译加初级结构化。
    *   **缺点**: 违背了我们在低配机器上部署（甚至无 GPU 实例）的初衷，极大拔高了硬件门槛。不符合我们的轻量级架构妥协方案。

**结论确认**: 已确认采用 **方案 A (Faster-Whisper `task="translate"`)**。它的实现最为优雅且与当前架构完美契合。

**关于语言选择 (Language Selection) 与自动检测 (Auto-Detect)：**
*   **无需强制用户选择**：Whisper 引擎原生支持强大的语言自动检测能力（Auto-Language Detection）。当使用 `task="translate"` 或开启默认行为时，Whisper 会截取前几秒音频自动探测源语言，并将其翻译为英文（默认语种）。
*   **建议方案**：在上传/录音界面增加一个**“录音语言 (Source Language)”**下拉框，默认选中 **“自动检测 (Auto-Detect)”**。对于方言或口音特别重的极其极端情况，允许医生手动指定为 `English` 或 `Arabic`。后端 Worker 将读取此元数据，若为 Auto 则依赖 Whisper 自行判断，若指定语言则传入 `language="ar"` 等参数，这能略微提升首字响应速度并避免识别漂移。

## 2. 增强前端音频采集入口 (Enhanced Audio Ingestion)
为了提升医生的临床使用体验，前端必须提供除“文件拖拽上传”外的直接录音手段：
*   **前端网页原声录音 (In-browser Recording)**:
    *   在工作台左侧接入 `MediaRecorder API` (Web Audio)。
    *   实现“开始录音 -> 暂停 -> 结束”的状态机闭环。
    *   录制完成后，在前端内存中生成 Blob，经过预览确认后，通过原有的 `/api/upload` 接口以流的形态直接推送到后端。不再强制医生使用手机或其他设备录音再传电脑。

## 2. 账户管理体系 (Account Management)
*   **账户注册机制 (Account Registration)**: 当前前端仅有登录和默认账户。需要全面打通用户注册闭环：
    *   **Backend**: 补充 `POST /api/auth/register`，包含密码的哈希加盐存储 (bcrypt) 及输入合法性校验。
    *   **Frontend**: 增加精美的注册页面表单，与登录逻辑平滑衔接，完善 JWT 下发。

## 3. 进阶临床交互与任务管理 (Advanced Clinical UX & Task Management)
*   **临床化标识替换 (Clinical Identifiers)**:
    *   目前前端 Dashboard 列表全部显示无语意的 Task ID 和乱码文件名。
    *   **改进**: 允许在录音/上传阶段让医生输入“患者姓名 (Patient Name)” 或 “病历号 (MRN)”；若未提供，则后端通过 LLM 自动给这段病历生成一个精简的 Title。
*   **富文本可编辑 SOAP (Editable SOAP Text)**:
    *   在前端工作台 (Workspace) 右侧，引入现代富文本编辑器框架（如 TipTap, Quill 等）。
    *   打破原先纯结构化只读的限制，允许医生在最终确认归档前，灵活地对 AI 生成的临床笔记进行增删、高亮、备注等深度校对操作。
*   **废弃病历管理 (Task Deletion & Curation)**:
    *   增加对低质量录音、错误音频或无效数据的**硬删除/软删除**功能。
    *   **Backend**: 补充 `DELETE /api/tasks/{task_id}` 接口，确保同步从数据库中清理记录。
    *   **Frontend**: 在 Dashboard 列表每一项增加删除按钮及二次确认弹窗。

## 4. 模型监控与质量控制 (Model Quality Assurance)
*   **STT 准确率自动化专项测试 (STT/Translation Accuracy Testing)**:
    *   建立测试集：选取带各种口音（如中东口音英文/纯阿拉伯语）与极端医疗专有名词的标准对照音频库。
    *   引入评估指标：通过工程化手段，在 CI 或单独测试脚本中自动计算每次大版本迭代的 **WER** (Word Error Rate 词错率)。建立一套数据支撑的测试体系，而非仅凭黑盒主观感觉评估 STT 及直译引擎的质量。
