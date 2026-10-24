import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app.services.pipeline import MedicalChatbot

LABEL_VI = {
    "SYMPTOM_AND_DISEASE": "triệu chứng/bệnh",
    "drug": "thuốc",
    "medical_procedure": "thủ thuật y tế",
}

st.set_page_config(page_title="Chatbot hỗ trợ sức khoẻ", page_icon="🩺")


@st.cache_resource(show_spinner="Đang nạp mô hình, vui lòng chờ khoảng 15 giây...")
def get_bot():
    bot = MedicalChatbot()
    bot.warmup()
    return bot


def entity_caption(entities):
    seen = dict.fromkeys((e["text"], e["label"]) for e in entities)
    if not seen:
        return ""
    return "Nhận diện: " + "; ".join(
        f"{t} ({LABEL_VI.get(lab, lab)})" for t, lab in seen
    )


def render_sources(container, sources):
    if not sources:
        return
    with container.expander("Nguồn tham khảo"):
        for s in sources:
            line = f"- {s['question'][:120]}"
            if s["link"]:
                line += f" ([liên kết]({s['link']}))"
            st.markdown(line)


bot = get_bot()

st.title("Chatbot hỗ trợ sức khoẻ y tế")
st.caption(
    "Chỉ trả lời các câu hỏi về sức khoẻ và y tế. "
    "Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ."
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    debug = st.toggle("Hiển thị thông tin kỹ thuật", value=False)
    if st.button("Xoá cuộc trò chuyện"):
        st.session_state.messages = []
        st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m.get("entities_caption"):
            st.caption(m["entities_caption"])
        st.markdown(m["content"])
        render_sources(st.container(), m.get("sources"))
        if debug and m.get("debug"):
            st.caption(m["debug"])

question = st.chat_input("Nhập câu hỏi về sức khoẻ...")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        ent_ph, ans_ph = st.empty(), st.empty()
        src_ph, dbg_ph = st.container(), st.empty()
        ans_ph.markdown("Đang tìm thông tin...")

        answer, cap, debug_text, sources = "", "", "", []
        try:
            for ev in bot.ask_stream(question):
                kind = ev["type"]
                if kind == "meta":
                    cap = entity_caption(ev["entities"])
                    if cap:
                        ent_ph.caption(cap)
                    debug_text = (
                        f"Lọc chủ đề: {ev['topic'].zone} (d={ev['topic'].distance:.3f})"
                    )
                elif kind in ("static", "text"):
                    answer += ev["text"]
                    ans_ph.markdown(answer + "▌")
                elif kind == "final":
                    sources = ev["sources"]
                    if ev.get("topic") and not debug_text:
                        debug_text = (
                            f"Lọc chủ đề: {ev['topic'].zone} (d={ev['topic'].distance:.3f})"
                        )
                    if ev.get("stats"):
                        debug_text += f" | qwen: {ev['stats']}"
        except Exception as e:
            answer += f"\n\nXin lỗi, hệ thống gặp sự cố ({type(e).__name__}). Hãy kiểm tra Ollama đang chạy."

        ans_ph.markdown(answer)
        render_sources(src_ph, sources)
        if debug and debug_text:
            dbg_ph.caption(debug_text)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "entities_caption": cap,
        "sources": sources,
        "debug": debug_text,
    })