import os
import json
from app.core.deepseek import DeepSeekClinicalAdapter

def run_real_deepseek_test():
    """
    Manual Verification Script for Real DeepSeek API Keys.
    This script bypasses Pytest mocks and actually consumes tokens on api.deepseek.com.
    """
    # 1. Check if the key is configured in the environment or .env file
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 错误: 环境中没有发现 DEEPSEEK_API_KEY。")
        print("请在项目根目录的 .env 文件中设置您的真实 Key:")
        print("echo 'DEEPSEEK_API_KEY=sk-xxxxxx' > .env")
        return

    # 2. Instantiate the adapter with the real key
    print(f"✅ 找到 API_KEY (前缀为: {api_key[:6]}...)")
    print("正在连接 https://api.deepseek.com...")
    
    adapter = DeepSeekClinicalAdapter(api_key=api_key)
    
    # 3. Dummy medical text
    test_text = (
        "[Doctor]: How are you feeling today?\n"
        "[Patient]: I've had a headache for 3 days.\n"
        "[Doctor]: Let's prescribe some Tylenol."
    )
    
    print(f"\n发送测试病历文本 (约 30 Tokens):\n{test_text}\n")
    print("等待模型返回 JSON...")
    
    try:
        # This will actually hit the cloud
        result = adapter.generate_soap_note(test_text)
        
        print("\n✅ 深蓝测试 (DeepSeek API) 成功通过！返回包解析如下:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"\n❌ 连接或生成失败. 具体报错: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_real_deepseek_test()
