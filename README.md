# Medical Chatbot — Trợ lý y tế tiếng Việt (chạy local, có thể bật Gemini)

Chatbot tư vấn y tế tiếng Việt với kiến trúc RAG, chạy **hoàn toàn trên máy cá nhân** (không gửi dữ liệu đi đâu):

- **Giao diện**: Streamlit (`app/ui.py`)
- **Sinh câu trả lời**: LLM chạy qua [Ollama](https://ollama.com) — đổi model bằng biến môi trường `OLLAMA_MODEL`
- **RAG**: ChromaDB + embedding `intfloat/multilingual-e5-small` (2 bộ sưu tập: QA y tế ViHealthQA + bài viết ViMedAQA)
- **NER y tế**: model local `models/ner_model` (XLM-R) nhận diện triệu chứng/bệnh/thuốc/thủ thuật
- **Luồng xử lý**: lọc chủ đề → NER → truy hồi tài liệu → sinh câu trả lời → lọc an toàn (liều lượng, câu hỏi ngoài y tế)

> ⚠️ **Lưu ý y tế**: Chatbot chỉ mang tính tham khảo, không thay thế chẩn đoán hay tư vấn của bác sĩ.

---

## Cài đặt trên Windows (khuyên dùng — 4 bước)

1. **Tải file** `medical_chatbot_windows.zip` (~1,1 GB) ở mục **Releases** bên phải trang repo trên GitHub.
2. **Giải nén** (chuột phải → *Extract All*) vào thư mục bất kỳ, ví dụ `D:\medical_chatbot`.
3. **Nhấp đúp** `scripts\cai_dat_app.bat` và trả lời các câu hỏi script hỏi:
   - Chưa có Ollama → script hiện link tải, đồng ý (`y`) thì **tự tải về và cài** giúp bạn.
   - Hiển thị danh sách model phù hợp với máy → **chọn số**, hoặc nhấn **Enter** để lấy model được gợi ý tự động theo VRAM.
   - Script tự: tạo môi trường Python, cài thư viện, giải nén model NER, tải model về Ollama, chạy thử đo tốc độ, và hỏi lưu model mặc định vĩnh viễn.
4. **Nhấp đúp** `scripts\chay_app.bat` → trình duyệt mở giao diện chatbot.

> Yêu cầu: Windows 10/11, dung lượng trống ≥ 6 GB (thêm dung lượng của model bạn chọn), mạng internet cho lần cài đầu.

### Gợi ý model theo VRAM

Script `chon_model.ps1` tự chọn giúp, nhưng nếu muốn tự tay thì tham khảo:

| Model (Ollama tag) | Dung lượng | VRAM cần (khuyến nghị) | Ghi chú |
|---|---|---|---|
| `qwen3.5:4b` | 3,3 GB | ≥ 5 GB | Mặc định, tiếng Việt tốt, nhanh |
| `medgemma:4b` | 3,3 GB | ≥ 5 GB | Chuyên y tế (từ Gemma 3) |
| `gemma3:4b` | 3,4 GB | ≥ 5 GB | Đa ngôn ngữ tốt (140+ ngôn ngữ) |
| `llama3.1:8b` | 4,9 GB | ≥ 7 GB | Tiếng Việt trung bình |
| `deepseek-r1:8b` | 4,9 GB | ≥ 7 GB | Suy luận mạnh, trả lời chậm hơn |
| `aya-expanse:8b` | 5,1 GB | ≥ 7 GB | Chính thức hỗ trợ tiếng Việt (Cohere) |
| `glm4:9b` | 5,5 GB | ≥ 7 GB | Đa ngôn ngữ |
| `qwen3.5:9b` | 6,6 GB | ≥ 9 GB | Cân bằng chất lượng / tốc độ |
| `mistral-nemo:12b` | 7,1 GB | ≥ 10 GB | Đa ngôn ngữ, context 1M |
| `gemma3:12b` | 8,2 GB | ≥ 10 GB | Chất lượng cao hơn |
| `qwen3.5:27b` | 17 GB | ≥ 20 GB | Chất lượng cao |
| `gemma3:27b` | 17 GB | ≥ 20 GB | Chất lượng cao |
| `medgemma:27b` | 17 GB | ≥ 20 GB | Chuyên y tế, mạnh nhất về y khoa |
| `aya-expanse:32b` | 20 GB | ≥ 24 GB | Tiếng Việt chính thức, chất lượng cao |
| `qwen3.5:35b-a3b` | 22 GB | ≥ 24 GB | MoE, nhanh với chất lượng tốt nhất |

Không có GPU mạnh? Script vẫn chạy được trên CPU (model ≤ RAM × 0,4) nhưng sẽ **rất chậm** — dùng `qwen3.5:4b`.

### Cài thủ công trên Windows (nếu muốn tự làm từng bước)

```bat
git clone https://github.com/<user>/medical_chatbot.git
cd medical_chatbot

python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

:: Giải nén models\ner_model.zip (tải từ Releases nếu chưa có)
:: Tải model Ollama (chọn một theo bảng trên)
ollama pull qwen3.5:4b
setx OLLAMA_MODEL "qwen3.5:4b"

:: Mo app (mo cua so PowerShell moi de setx co hieu luc)
.venv\Scripts\python -m streamlit run app\ui.py
```

---

## Chạy trên Linux (Ubuntu / Mint)

```bash
git clone https://github.com/<user>/medical_chatbot.git
cd medical_chatbot

# 1. Tải medical_chatbot_windows.zip từ mục Releases (chứa sẵn chroma_db + ner_model),
#    rồi giải nén đè lên thư mục hiện tại
unzip medical_chatbot_windows.zip

# 2. Môi trường Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Model NER (nếu zip chưa có)
unzip models/ner_model.zip -d models/

# 4. Cài Ollama (nếu chưa) + tải model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3.5:4b          # chọn model khác theo bảng VRAM ở trên

# 5. Chạy app
export OLLAMA_MODEL=qwen3.5:4b  # hoặc model khác đã tải
streamlit run app/ui.py
```

---

## Giao diện Next.js (khuyến nghị)

Ngoài Streamlit, repo có giao diện web mới trong `frontend/` (Next.js 16 + Tailwind 4) dùng
cùng pipeline RAG. Cần chạy 2 tiến trình:

```bash
# Terminal 1 — cầu nối Python (nạp model như Streamlit)
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.api.server:app --host 127.0.0.1 --port 8000

# Terminal 2 — giao diện
cd frontend
npm install
npm run dev        # mở http://localhost:3000
```

Thiết kế bám theo `DESIGN-claude.md` (nền kem, serif cho tiêu đề, coral cho CTA,
bề mặt tối cho điểm nhấn). Lịch sử hội thoại lưu trong trình duyệt; không gửi dữ liệu
ra ngoài. Streamlit vẫn dùng được song song.

## Dùng thêm Gemini (tuỳ chọn)

Mặc định app chạy hoàn toàn local bằng Ollama. Có thể bật thêm Gemini để so sánh
chất lượng hoặc làm phương án dự phòng, qua `app/services/llm.py`.

```bash
.venv/bin/pip install google-genai          # chỉ cần khi dùng Gemini
export LLM_PROVIDER=gemini                  # ollama (mặc định) | gemini | auto
export GEMINI_API_KEY=...                   # lấy ở https://aistudio.google.com/apikey
export GEMINI_MODEL=gemini-2.5-flash        # tên model đổi khá nhanh, kiểm tra lại
```

| `LLM_PROVIDER` | Hành vi |
|---|---|
| `ollama` (mặc định) | chỉ chạy trên máy, không gửi dữ liệu ra ngoài |
| `gemini` | chỉ dùng Gemini |
| `auto` | thử Ollama trước, lỗi thì chuyển Gemini (nếu có key) |

Lưu ý:

- **Bộ lọc chủ đề luôn chạy local.** Câu ngoài chủ đề bị từ chối thì không bao giờ
  rời khỏi máy.
- **Giao diện có menu chọn model** ở góc trên bên phải (Qwen / Gemini). Lựa chọn
  áp dụng cho **từng câu hỏi**, không phải biến môi trường, nên đổi model giữa
  chừng vẫn so sánh được. Gemini chỉ hiện khi `GEMINI_API_KEY` đã có.
- **Dữ liệu bệnh nhân**: free tier của Gemini dùng nội dung để cải thiện sản phẩm;
  chỉ paid tier mới không dùng. Cân nhắc trước khi bật với dữ liệu thật.
- **Số đo**: ghi kèm `provider`/`model` (đã có trong `stats`) vì Google có thể đổi
  model ngầm, làm số liệu cũ không còn so sánh được.

---

## Đổi model sau khi cài

- **Windows**: nhấp đúp `scripts\chon_model.bat` — chọn model mới, script tự tải và lưu lại.
- **Linux**: `ollama pull <tag>` rồi `export OLLAMA_MODEL=<tag>` trước khi chạy app.

---

## Xử lý sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| "May chua cai Ollama" / app báo không kết nối được Ollama | Mở app Ollama (biểu tượng sistema), kiểm tra `ollama list` chạy được trong PowerShell |
| Trả lời rất chậm | Chọn model nhỏ hơn qua `scripts\chon_model.bat` (mỗi bậc nhỏ hơn nhanh gấp đôi) |
| Lỗi hết VRAM / treo máy | Dùng model có dung lượng nhỏ hơn VRAM card (xem bảng trên) |
| Chỉ có CPU | Dùng `qwen3.5:4b`; tốc độ vài token/giây là bình thường |
| Lỗi NER / không nhận diện triệu chứng | Kiểm tra `models\ner_model\config.json` tồn tại (chạy lại `cai_dat_app.bat` để giải nén zip) |
| Lỗi thiếu vector DB (`chroma_db`) | Chạy lại `cai_dat_app.bat`, hoặc tự build: `.venv\Scripts\python.exe app\services\ingest.py` (+ `ingest_kb.py`, `ingest_vimedaqa.py`) |

---

## Cấu trúc thư mục

```
app/
  ui.py                 # Giao diện Streamlit (tuỳ chọn)
  api/server.py         # FastAPI bridge cho giao diện Next.js (SSE)
  services/
    pipeline.py         # Luồng RAG: lọc chủ đề → NER → truy hồi → sinh → lọc an toàn
    topic_filter.py     # Lọc chủ đề + hằng số model (OLLAMA_MODEL)
    llm.py              # Cầu nối LLM: Ollama (local) hoặc Gemini (API key)
    ner.py              # NER y tế local
    normalizer.py       # Chuẩn hoá câu hỏi: teencode, khôi phục dấu, sửa tên thuốc gõ sai
    red_flags.py        # Nhận diện dấu hiệu cấp cứu + lời khuyên sơ cứu theo nhóm
    ingest*.py          # Script build vector DB từ dữ liệu
  db/chroma_db/         # Vector database (đóng gói sẵn trong Release)
data/
  DATA_CONTRACT.md     # Luật chất lượng dữ liệu + ngưỡng + số đo hiện tại
  sources/              # Nguồn: Dược thư (mirror Bạch Mai), red_flags.jsonl, ...
  processed/            # KB đã xử lý (kb.jsonl, kb_drugs_full.jsonl, drug_names.json, ...)
  raw/                  # Dữ liệu thô (không đóng gói)
models/
  ner_model/            # Model NER (giải nén từ ner_model.zip)
  ner_model.zip
scripts/
  validate_data.py      # Cổng kiểm tra dữ liệu: sai luật hard thì exit 1
  build_drug_index.py   # Cào + lập danh mục chuyên luận Dược thư
  build_drug_qa.py      # Sinh KB thuốc (5 khía cạnh mỗi hoạt chất)
  build_vinmec_qa.py    # Cào bài Vinmec cho chủ đề vaccine / dinh dưỡng
  eval_retrieval_semantic.py  # Đo truy hồi theo ngữ nghĩa đáp án (thước đo chính)
  build_drug_names.py   # Danh mục tên thuốc cho việc sửa lỗi gõ
  chon_model.ps1/.bat   # Dò cấu hình → gợi ý → tải model Ollama
  cai_dat_app.ps1/.bat  # Cài đặt toàn bộ app trên Windows
  chay_app.bat          # Chạy app (nhấp đúp)
  pack_windows.sh       # (Linux) Đóng gói medical_chatbot_windows.zip
frontend/               # Giao diện Next.js (App Router, Tailwind 4)
                        # hiệu ứng: bot-avatars (avatar "đang làm việc"),
                        # thinking-orbs (orb khi đang trả lời), torph (morph nhãn model)
  src/app/              # layout, page, globals.css, api/chat (proxy SSE)
  src/components/chat/  # sidebar, header, composer, message, sources
  src/hooks/use-chat.ts # trạng thái + stream câu trả lời
  src/lib/              # SSE client, localStorage store, types
tests/                  # Các script thí nghiệm
```

---

## Ghi chú cho người quản lý repo

Để tạo bản phát hành mới cho Windows:

```bash
bash scripts/pack_windows.sh
gh release create v1.1 medical_chatbot_windows.zip \
  --title "Bản cài cho Windows" \
  --notes "Tải về, giải nén, nhấp đúp scripts\cai_dat_app.bat"
```

Code trong repo chỉ chứa phần nhẹ — phần nặng (vector DB, model NER) đi theo zip ở Releases vì GitHub giới hạn 100 MB/file.

## Lời cảm ơn

- Dữ liệu: [ViMQ](https://github.com/tadeephuy/ViMQ), ViHealthQA, [tmnam20/ViMedAQA](https://huggingface.co/datasets/tmnam20/ViMedAQA)
- Suy luận local: [Ollama](https://ollama.com)
