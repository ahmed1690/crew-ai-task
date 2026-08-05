import os
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()

print(">>> Connecting to NVIDIA API...")
try:
    test_llm = LLM(
        model=f"openai/{os.getenv('NVIDIA_MODEL', 'meta/llama3-70b-instruct')}",
        base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        api_key=os.getenv("NVIDIA_API_KEY"),
    )
    
    response = test_llm.call(messages=[{"role": "user", "content": "Say 'Hello, API is working!'"}])
    print(">>> SUCCESS! Response:")
    print(response)
except Exception as e:
    print(f">>> ERROR: {e}")