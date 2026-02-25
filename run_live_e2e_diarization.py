import os
import json
import time
from dotenv import load_dotenv

from stt_core import run_stt_isolated
from privacy_filter import ClinicalPrivacyFilter
from deepseek_adapter import DeepSeekClinicalAdapter

def run_true_e2e_pipeline():
    """
    此为 PtClinVoice 最核心的【真实世界 E2E (端到端)】测试流水线。
    数据流: 真实录音 (MP3/WAV) -> Whispser (本地 STT) -> Presidio (本地隐私脱敏) -> DeepSeek (云端大模型角色分离与 SOAP 提取)
    """
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 未检测到 DEEPSEEK_API_KEY。请在 .env 中设置后重试。")
        return

    # 1. 挂载三大核心引擎
    print("🚀 [Step 1] 初始化系统核心架构...")
    
    # 1b. 本地安检防御引擎 (Presidio)
    print("   -> 正在启动 Microsoft Presidio (隐私拦截防线)...")
    privacy_filter = ClinicalPrivacyFilter()
    
    # 1c. 云端语义切分与提取引擎 (DeepSeek)
    print("   -> 正在连接远端 DeepSeek API (大模型智能脑)...")
    llm_adapter = DeepSeekClinicalAdapter(api_key=api_key)

    # 2. 定位测试音频 (带有医生与患者交替对话，且包含隐私数据的测试录音)
    audio_path = os.path.join(os.path.dirname(__file__), "tests", "fixtures", "standard_accent.mp3")
    if not os.path.exists(audio_path):
        print(f"❌ 找不到测试音频: {audio_path}")
        return

    # 3. 开始全链路处理
    print("\n=======================================================")
    print("🎯 [Step 2] 端到端 (End-to-End) 核心工作流已启动")
    print("=======================================================\n")
    
    start_time = time.time()
    
    try:
        # 环节 A: 本地语音转文字
        print("🔊 [A. 本地听写] 正在转写音频 (加载 Faster-Whisper base.en)...")
        raw_transcript = run_stt_isolated(audio_path, model_size="base.en")
        print(f"   ✓ [原始逐字稿]: {raw_transcript[:100]}...\n")
        
        # 环节 B: 本地数据脱敏 
        print("🛡️  [B. 隐私阻断] 正在执行本地 NER 身份销毁 (Presidio)...")
        # 故意将一段带有致命隐私（人名+社保号）的话追加到转录稿末尾进行熔断测试
        poisoned_transcript = raw_transcript + " Oh by the way, my name is Robert Oppenheimer and my SSN is 999-88-7777."
        safe_transcript = privacy_filter.mask_pii(poisoned_transcript)
        print(f"   ✓ [脱敏后病历]: {safe_transcript[-100:]}\n")

        # 环节 C: 云端发声员分离与结构体重组
        print("☁️  [C. 云端重构] 发送脱敏文本至 DeepSeek API 进行角色分离及 SOAP 提取...")
        final_result = llm_adapter.generate_soap_note(safe_transcript)
        
        # 4. 打印最终答卷
        print("\n=======================================================")
        print("✅ [成功] 最终输出 (Final SOAP & Diarization Result)")
        print("=======================================================")
        print(json.dumps(final_result, indent=2, ensure_ascii=False))
        
        total_time = time.time() - start_time
        print(f"\n⏱️ 全栈端到端处理耗时: {total_time:.2f} 秒")
        
    except Exception as e:
        print(f"\n❌ 流水线崩溃挂起: {e}")

if __name__ == "__main__":
    run_true_e2e_pipeline()
