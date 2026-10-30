# tests/22_test_prompt.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.pipeline import MedicalChatbot

QUESTIONS = [
    "Khi nào cần đi khám khi bị cúm?",
    "Suy thận cấp có thể biểu hiện ra ngoài như thế nào?",
    "Thuốc Atorlog có thể tương tác với thuốc nào?",
]


def main():
    bot = MedicalChatbot()
    bot.warmup()
    for q in QUESTIONS:
        ans = bot.ask(q)
        st = ans.timings.get("qwen_chi_tiet", {})
        print("=" * 100)
        print("Hỏi:", q)
        print(
            f"prompt {st.get('prompt_tokens')} token / {st.get('prompt_s')}s, "
            f"sinh {st.get('gen_tokens')} token / {st.get('gen_s')}s"
        )
        print(ans.text)


if __name__ == "__main__":
    main()