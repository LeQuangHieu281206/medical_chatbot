import time
import ollama

def ask(think):
    start = time.time()
    response = ollama.chat(
        model="qwen3.5:4b",
        messages=[
            {"role": "user", "content": "Triệu chứng của cảm cúm là gì? Trả lời ngắn gọn bằng tiếng Việt."}
        ],
        think=think,
    )
    print(f"think={think} | {time.time() - start:.1f}s")
    print(response["message"]["content"])
    print("-" * 40)

ask(False)
ask(True)