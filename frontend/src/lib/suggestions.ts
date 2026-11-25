export const SUGGESTIONS = [
  {
    tag: "Triệu chứng",
    question: "Đau đầu kéo dài kèm buồn nôn nên xử lý thế nào?",
  },
  {
    tag: "Phòng bệnh",
    question: "Cách phòng bệnh cúm mùa cho người cao tuổi?",
  },
  {
    tag: "Dinh dưỡng",
    question: "Người bị tiểu đường type 2 nên ăn gì?",
  },
  {
    tag: "Thuốc",
    question: "Paracetamol có tác dụng phụ gì cần lưu ý?",
  },
] as const;

export const ENTITY_LABELS: Record<string, string> = {
  SYMPTOM_AND_DISEASE: "triệu chứng/bệnh",
  drug: "thuốc",
  medical_procedure: "thủ thuật y tế",
};
