# Hướng dẫn trên Windows (cho đồng nghiệp)

Clone code + tải KB từ Release là đủ, nhưng **commands khác Linux** ở 4 chỗ:
đường dẫn `python` trong venv, cách ghép 5 phần KB (không có lệnh `cat`), mã hoá
console khi in tiếng Việt, và lần chạy đầu phải tải model từ HuggingFace.

## 1. Cài đặt

```powershell
git clone https://github.com/LeQuangHieu281206/medical_chatbot.git
cd medical_chatbot
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Nếu PowerShell báo *"running scripts is disabled"*:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Hoặc **không cần activate**, gọi trực tiếp:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Từ đây mọi lệnh dùng `.\.venv\Scripts\python.exe` thay cho `.venv/bin/python`
trong tài liệu Linux.

## 2. Lấy KB (chỉ cần cho Việc 2, Việc 3 không cần)

Tải 5 tệp trong Release rồi ghép **bằng lệnh của Windows** — `cat` không có, và
đừng dùng `Get-Content` (nó phá tệp nhị phân):

```cmd
copy /b kb_v3_part_aa+kb_v3_part_ab+kb_v3_part_ac+kb_v3_part_ad+kb_v3_part_ae kb.tar.gz
tar -xzf kb.tar.gz
dir app\db\chroma_db
```

Windows 10 (1803 trở lên) có sẵn `tar`. Giải nén **tại thư mục gốc repo** để ra
đúng `app\db\chroma_db\chroma.sqlite3` và `app\db\embed_model.txt`.

## 3. Kiểm tra

```powershell
chcp 65001                                       # để tiếng Việt không bị lỗi font
.\.venv\Scripts\python.exe tests\56_doc_recall.py
```

Kết quả đúng: `bài đúng chủ đề trong ngữ cảnh: 13/19`.

Lần chạy đầu sẽ tải model `intfloat/multilingual-e5-small` (~470 MB) từ
HuggingFace — cần internet và chờ vài phút. Các lần sau không tải lại.

## 4. Việc 3 (bộ test) — không cần KB

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest tests\ -q
```

## Lỗi hay gặp trên Windows

| hiện tượng | nguyên nhân | cách xử lý |
|---|---|---|
| `'cat' is not recognized` | Linux command | dùng `copy /b` như mục 2 |
| `Activate.ps1 cannot be loaded` | execution policy | `Set-ExecutionPolicy -Scope Process Bypass`, hoặc gọi `python.exe` trực tiếp |
| Chữ Việt ra `?` hoặc ký tự lạ | console dùng bảng mã cũ | `chcp 65001` trước khi chạy |
| `FileNotFoundError: app/db/chroma_db` | giải nén sai chỗ | giải nén ở **gốc repo**, không phải trong `app\` |
| `sqlite3` báo database is locked | thư mục nằm trong OneDrive/Desktop đang sync | chuyển repo ra `C:\dev\medical_chatbot` |
| Đường dẫn quá dài | giới hạn 260 ký tự | đặt repo gần gốc ổ đĩa, ví dụ `C:\dev\` |
| Chạy rất lâu ở lần đầu | đang tải model 470 MB | xem thanh tiến trình `Loading weights` |
| Cảnh báo `HF_TOKEN` | chưa đăng nhập HuggingFace | bỏ qua được, chỉ chậm hơn |

## Dữ liệu cần có sau khi clone

Đã nằm trong git, không phải tải thêm: `data/sources/eval_answers_50.jsonl`,
`tests/56_doc_recall.py`, `tests/_recall_patterns.py`, `app/services/hybrid.py`,
`requirements.txt`, `.env.example`.

Chỉ hai thứ **không** có trong git: thư mục KB (`app/db/chroma_db`, lấy từ Release)
và cache model (`models/`, tự tải).
