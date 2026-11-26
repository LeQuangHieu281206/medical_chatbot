"""Từ khoá bệnh ĐÚNG của 19 câu hỏi đã biết là từng bị trả lời sai.

Lấy từ ``reference_facts`` trong ``data/sources/eval_answers_50.jsonl``.
Dùng chung cho tests/56_doc_recall.py và tests/57_hybrid_recall.py.
"""

PATTERNS = {
    "q02": r"sỏi thận|sỏi niệu quản|niệu quản|nhiễm trùng tiết niệu",
    "q03": r"gút|gout",
    "q04": r"thiếu máu|huyết sắc tố",
    "q05": r"viêm loét dạ dày|tá tràng|dạ dày",
    "q07": r"viêm họng",
    "q08": r"đái tháo đường|tiểu đường",
    "q09": r"viêm gan",
    "q11": r"loãng xương|xẹp đốt sống|gãy xương",
    "q12": r"chóng mặt tư thế|tiền đình|BPPV",
    "q14": r"viêm xoang",
    "q15": r"tiêu chảy",
    "q16": r"dị ứng|mày đay|phản vệ",
    "q22": r"gút|gout",
    "q23": r"sốt xuất huyết|dengue",
    "q28": r"thiếu sắt|thiếu máu",
    "q37": r"gút|gout",
    "q39": r"loãng xương|xương",
    "q40": r"trào ngược|dạ dày thực quản",
    "q43": r"cảm|cúm|viêm hô hấp",
}
