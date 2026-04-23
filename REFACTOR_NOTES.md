# Refactor Notes

## Mục Tiêu

Refactor này chuyển chatbot từ prototype chỉ thu thập đủ thông tin sang backend có business search layer rõ ràng. Thay đổi được giữ ở mức vừa phải: không viết lại toàn bộ dự án, vẫn giữ pipeline NLP hiện có và thêm lớp repository/service để tìm tour có cấu trúc.

## Thay Đổi Chính

- Gỡ hard-coded Gemini API key khỏi `google_genAI.py`.
- `GOOGLE_API_KEY` được đọc từ biến môi trường.
- `.env.example` chỉ còn placeholder, `.env` được ignore.
- `server.py` có `/health`, lazy-load pipeline và truyền đúng `request.user_id`.
- Session reset trong pipeline dùng đúng `user_id`.
- `requirements.txt` được bổ sung dependency runtime/test cần thiết.
- Thêm response schema trong `schemas/chat_response.py` và tour/entity schema trong `schemas/tour_models.py`.
- Thêm `services/entity_normalizer.py` để chuẩn hóa entity raw thành filter business.
- Thêm `repositories/tour_repository.py` với `JsonTourRepository` làm adapter tạm thời cho dữ liệu tour.
- Thêm `services/tour_search_service.py` để lọc và rank tour deterministic.
- Thêm `data/tours_sample.json` để chatbot có thể trả structured tour results khi chưa có database thật.
- Refactor `pipelines/tour_pipeline.py` để success flow gọi tour search thay vì chỉ sinh text.
- Refactor `pipelines/retrieval.py` để FAQ trả metadata như question, score và source.
- Refactor `extractors/extract_price.py` sang rule-based parsing, không gọi LLM cho giá.
- Làm import runtime nặng thành optional để project không chết ngay khi thiếu model/artifact trong môi trường test.
- Thêm tests cho API smoke, parser giá/thời gian, tour search và session isolation.

## Kiến Trúc Mới

NLP layer:

- Intent classification bằng PhoBERT nếu artifact có sẵn.
- Rule-based fallback khi model chưa có.
- Entity extraction giữ các module hiện tại.
- Entity normalization tạo `destination_normalized`, `date_start`, `date_end`, `price_min`, `price_max`.
- FAQ retrieval giữ FAISS flow riêng.

Business layer:

- `TourRepository` cung cấp danh sách tour từ data source.
- `TourSearchService` lọc theo destination/date/price và rank đơn giản.
- Pipeline trả `ChatResponse` có `status`, `message`, `entities`, `missing_fields`, `tours`, `faq_sources`.

## Khoảng Trống Tích Hợp

Repo hiện không có database schema, ORM, API client hoặc code web-app data access. Vì vậy chưa thể kết nối trực tiếp tới database website thật trong refactor này.

Điểm cần tích hợp tiếp:

1. Xác định database thật đang dùng trong website: SQL, MongoDB, CMS API hoặc backend API.
2. Tạo repository mới, ví dụ `SqlTourRepository` hoặc `WebsiteTourApiRepository`.
3. Map field database thật sang `schemas.tour_models.Tour`.
4. Thay `JsonTourRepository` bằng repository thật trong dependency wiring.
5. Bổ sung test integration với database staging hoặc fixture dump từ production.

## Quy Tắc Business Logic

- Destination dùng exact normalized match trước.
- Date lọc theo ngày hoặc khoảng tháng từ entity normalized.
- Price mặc định là ngân sách trần `price_max`.
- Query dạng khoảng giá có thể tạo `price_min` và `price_max`.
- Ranking ưu tiên destination match, date closeness, price closeness, rating/popularity nếu có.
- LLM không được quyết định tour nào đủ điều kiện.

## Lưu Ý Vận Hành

- Nếu thiếu `GOOGLE_API_KEY`, chatbot vẫn trả fallback deterministic message.
- Nếu thiếu PhoBERT artifact, chatbot dùng rule-based intent fallback.
- Nếu thiếu FAISS artifact/dependency, FAQ retrieval bị disable nhưng tour search vẫn có thể hoạt động.
- Production nên chuyển session in-memory sang Redis hoặc database.
