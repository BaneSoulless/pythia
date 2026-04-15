# test_ollama_connection.py — esegui da ROOT monorepo
import openai
import json

client = openai.OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

try:
    resp = client.chat.completions.create(
        model="qwen2.5-coder:14b",
        messages=[
            {"role": "user", "content": "Reply with exactly: {\"status\": \"ok\"}"}
        ],
        max_tokens=50,
        temperature=0,
    )
    print(resp.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")
