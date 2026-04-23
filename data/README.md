## Overview
JSON file `faq_cleaned.json` (~100-200 Q&A) used by the retrieval pipeline.

## How to preprocess
```bash
python scripts/preprocess_faq.py --input data/raw/faq_raw.json --output data/processed/faq_cleaned.json

Tổng quan
Thư mục data/ chứa dữ liệu Q&A dùng cho pipeline RAG của chatbot tư vấn du lịch.
Cấu trúc

raw/: Dữ liệu thô, chưa xử lý.
faq_group1.json, faq_group2.json, v.v.: Dữ liệu Q&A theo nhóm chủ đề.
manual_qna.json: Dữ liệu nhập tay.


processed/: Dữ liệu đã làm sạch.
faq_group1_cleaned.json, v.v.: File đã qua xử lý.
faq_combined.json: File gộp chứa 225 mục Q&A.



Định dạng dữ liệu
Mỗi mục Q&A có cấu trúc JSON:
{
  "question": "Câu hỏi (dưới 300 ký tự)",
  "answer": "Câu trả lời (2-3 câu, dưới 500 ký tự)",
  "tags": ["tag1", "tag2"]
}

Cách xử lý dữ liệu

Làm sạch:python scripts/preprocess_faq.py --input data/raw/faq_group1.json --output data/processed/faq_group1_cleaned.json


Gộp dữ liệu:python scripts/mergeData.py



Lưu ý

File faq_combined.json là nguồn chính để huấn luyện chatbot.
Kiểm tra trùng lặp và chất lượng nội dung trước khi sử dụng.

