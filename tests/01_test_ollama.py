import ollama

response = ollama.chat(
    model="qwen3.5:4b",
    messages=[
        {"role": "user", "content": "Triệu chứng của cảm cúm là gì? Trả lời ngắn gọn bằng tiếng Việt."}
    ],
)

print(response["message"]["content"])