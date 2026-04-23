# Nhận Xét Chatbot Hiện Tại Và Hướng Phát Triển

Tài liệu này đánh giá trạng thái hiện tại của chatbot trong repository và đề xuất hướng cải tiến theo mức độ ưu tiên. Mục tiêu là giúp dự án chuyển từ prototype có khả năng demo sang hệ thống ổn định hơn, dễ triển khai và dễ mở rộng.

## Tóm Tắt Hiện Trạng

Chatbot hiện là một backend FastAPI cho bài toán tư vấn du lịch tiếng Việt. Pipeline chính gồm:

- Phân loại intent bằng model PhoBERT fine-tuned.
- Trích xuất địa điểm bằng VnCoreNLP NER.
- Trích xuất thời gian bằng regex và xử lý thời gian tương đối.
- Trích xuất giá bằng Gemini trước, regex dự phòng sau.
- Trả lời FAQ bằng SentenceTransformer, FAISS và Gemini.
- Quản lý ngữ cảnh hội thoại bằng `SessionManager` in-memory.

Điểm mạnh là dự án đã có hướng kiến trúc rõ ràng: intent classifier, entity extraction, retrieval và LLM response được tách thành các module riêng. Dữ liệu FAQ và intent cũng đã có số lượng đủ lớn để tiếp tục đánh giá, làm sạch và mở rộng.

## Điểm Mạnh

- Có dữ liệu FAQ tương đối lớn với khoảng 3.504 mục trong `data/processed/faq_cleaned.json`.
- Có dataset intent khoảng 11.904 mẫu, gồm nhiều tổ hợp thông tin tour và nhóm `out_of_scope`.
- Có pipeline RAG đơn giản bằng FAISS, phù hợp để demo nhanh FAQ du lịch.
- Có cơ chế session để người dùng bổ sung dần điểm đến, thời gian và ngân sách.
- Có các extractor riêng cho location, time và price, giúp dễ thay thế từng phần.
- Có script tạo index và script huấn luyện intent, cho thấy dự án đã có pipeline dữ liệu ban đầu.

## Vấn Đề Cần Xử Lý

### 1. Bảo mật API key

`google_genAI.py` đang chứa API key trực tiếp trong source code, và `.env.example` cũng đang chứa một key thật. Đây là rủi ro bảo mật cao.

Tác động:

- Key có thể bị lộ nếu repository được chia sẻ hoặc đẩy lên Git.
- Khó rotate key và khó triển khai qua nhiều môi trường.
- Có thể phát sinh chi phí API ngoài ý muốn.

Khuyến nghị:

- Thu hồi key đã lộ và tạo key mới.
- Chuyển toàn bộ code sang đọc `GOOGLE_API_KEY` từ biến môi trường.
- Chỉ để placeholder trong `.env.example`.
- Đảm bảo `.env` nằm trong `.gitignore`.

### 2. Dự án chưa chạy sạch từ fresh clone

`requirements.txt` hiện chỉ có `jsonschema`, `regex`, `unicodedata2`, trong khi runtime cần nhiều package khác như `fastapi`, `uvicorn`, `torch`, `transformers`, `sentence-transformers`, `faiss-cpu`, `vncorenlp`, `google-genai`, `numpy`, `python-dateutil`.

Ngoài ra, `training/phobert_intent_finetuned/` đang bị ignore bởi `.gitignore`, nhưng `TourRetrievalPipeline` lại bắt buộc load model từ đường dẫn này khi khởi động.

Tác động:

- Người khác clone repo sẽ khó chạy API.
- Deploy server có thể lỗi ngay lúc import `server.py`.
- Không có hướng dẫn rõ artifact nào cần tạo lại, artifact nào cần tải từ model registry.

Khuyến nghị:

- Cập nhật `requirements.txt` hoặc tạo `requirements-dev.txt` và `requirements-prod.txt`.
- Thêm hướng dẫn rõ cách tạo hoặc tải `training/phobert_intent_finetuned/`.
- Cân nhắc dùng Hugging Face Hub, MLflow, DVC hoặc object storage để quản lý model artifact.

### 3. `user_id` chưa được dùng đúng

`server.py` định nghĩa request có `user_id`, nhưng endpoint `/chat` chỉ gọi `pipeline.get_tour_response(request.query)`. Vì vậy mọi request đều rơi về `default_user`.

Trong `TourRetrievalPipeline`, khi đủ thông tin, code gọi `self.reset_session("default_user")` thay vì reset đúng `user_id`.

Tác động:

- Nhiều người dùng có thể bị lẫn context.
- Session không phản ánh đúng người dùng thật.
- Khó kiểm thử hội thoại nhiều lượt.

Khuyến nghị:

- Truyền `request.user_id` từ API vào `get_tour_response`.
- Reset session theo đúng `user_id`.
- Thay session in-memory bằng Redis hoặc database nếu triển khai nhiều process.

### 4. Chưa có kho tour thật để trả kết quả

Khi đủ location, time và price, chatbot hiện chỉ sinh câu mở đầu bằng Gemini. Pipeline chưa truy vấn database tour, chưa lọc theo ngân sách, ngày khởi hành hoặc điểm đến, và chưa trả danh sách tour cụ thể.

Tác động:

- Trạng thái `success` chưa thực sự hoàn tất nhu cầu tìm tour.
- Người dùng nhận được câu xác nhận nhưng chưa có tour để chọn.
- Rất khó đánh giá chất lượng tư vấn theo business outcome.

Khuyến nghị:

- Thiết kế schema `tours` gồm destination, departure_date, duration, price, seats, itinerary, included_services, tags.
- Thêm service tìm kiếm tour có filter cứng trước, ranking mềm sau.
- Response `success` nên trả về danh sách tour có cấu trúc, không chỉ text.

### 5. FAQ retrieval còn đơn giản

`RetrievalPipeline` dùng `all-MiniLM-L6-v2`, index L2 và ngưỡng khoảng cách cố định `> 1` để loại kết quả. Model embedding này không chuyên cho tiếng Việt, và ngưỡng chưa được đánh giá định lượng.

Tác động:

- FAQ tiếng Việt có thể truy xuất sai hoặc bỏ sót.
- Không có score, source, question gốc hoặc tag trong response để debug.
- Gemini đang được dùng để kiểm tra lại độ liên quan nhưng vẫn có nguy cơ diễn đạt sai hoặc hallucinate.

Khuyến nghị:

- Thử embedding đa ngôn ngữ hoặc tiếng Việt tốt hơn, ví dụ `paraphrase-multilingual-MiniLM-L12-v2`, `intfloat/multilingual-e5-base`, hoặc model embedding tiếng Việt phù hợp.
- Lưu score, question gốc, tags và location trong context trả về.
- Đánh giá retrieval bằng tập câu hỏi kiểm thử có nhãn expected FAQ.
- Dùng top-k lớn hơn và reranking nếu FAQ tăng quy mô.

### 6. Entity extraction còn dễ vỡ

Location phụ thuộc chủ yếu vào NER của VnCoreNLP. Time parser mới hỗ trợ một số mẫu phổ biến. Price extraction gọi Gemini trước cho mỗi truy vấn có intent liên quan đến giá, sau đó mới dùng regex.

Tác động:

- Địa điểm có cách viết khác, viết tắt hoặc lỗi chính tả có thể không nhận ra.
- Câu có khoảng giá chỉ giữ được một giá trong nhiều trường hợp.
- Gọi Gemini để trích giá làm tăng latency, chi phí và độ bất định.

Khuyến nghị:

- Xây danh mục địa điểm chuẩn và alias cho các tỉnh, thành, điểm du lịch.
- Chuẩn hóa entity về cấu trúc, ví dụ `price_min`, `price_max`, `currency`, `date_start`, `date_end`.
- Ưu tiên rule-based parser cho giá, chỉ gọi LLM khi rule không đủ.
- Viết test riêng cho các mẫu tiếng Việt phổ biến, tiếng lóng và lỗi chính tả.

### 7. Prompt và phản hồi chưa được kiểm soát chặt

Một số prompt được nối trực tiếp từ query và context. Gemini cũng được yêu cầu kiểm tra FAQ và diễn đạt câu trả lời, nhưng chưa có guardrail rõ ràng về nguồn dữ liệu, format JSON hoặc giới hạn không bịa thông tin.

Tác động:

- Dễ bị prompt injection từ user query.
- Phản hồi có thể không ổn định giữa các lần gọi.
- API response khó parse nếu sau này cần frontend hiển thị dạng card.

Khuyến nghị:

- Tách system prompt, developer instruction và user content rõ ràng.
- Với API backend, ưu tiên structured output JSON cho các bước nội bộ.
- Không để LLM tự quyết định thông tin business quan trọng nếu chưa có nguồn dữ liệu.
- Thêm lớp kiểm duyệt output: status, message, entities, citations hoặc retrieved_items.

### 8. Logging, error handling và observability còn thiếu

Code hiện có logging cơ bản nhưng vẫn còn nhiều `print`. Chưa có request id, latency, token usage, metric retrieval hoặc metric intent.

Tác động:

- Khó debug khi chatbot trả lời sai.
- Khó biết lỗi đến từ intent, entity extraction, retrieval hay Gemini.
- Khó theo dõi chi phí và hiệu năng khi triển khai thật.

Khuyến nghị:

- Chuẩn hóa logging JSON theo request id.
- Log intent, confidence, entities, retrieval score, LLM latency và lỗi ngoài.
- Thêm endpoint health check và readiness check.
- Theo dõi số lượng request, tỉ lệ missing_info, tỉ lệ fallback FAQ và lỗi API ngoài.

### 9. Thiếu test tự động và đánh giá model

Chưa thấy test suite cho API, extractor, retrieval hoặc intent classifier. Training script cũng chưa lưu metric đánh giá như accuracy, F1 theo từng intent, confusion matrix.

Tác động:

- Khó biết thay đổi có làm giảm chất lượng chatbot không.
- Các bug về session, parser và prompt có thể chỉ phát hiện khi demo.
- Không có baseline để quyết định model mới có tốt hơn model cũ.

Khuyến nghị:

- Thêm `pytest` cho extractor và API.
- Tạo evaluation set cố định cho intent và FAQ retrieval.
- Lưu classification report sau mỗi lần train.
- Chạy smoke test trong CI trước khi merge.

### 10. Pipeline dữ liệu còn chưa nhất quán

`data/README.md` nói FAQ có khoảng 100 đến 200 hoặc 225 mục, nhưng dữ liệu hiện tại có hơn 3.500 mục. `scripts/preprocess_faq.py` chứa phần xử lý FAQ bị comment, còn phần active lại xử lý intent. Một số script sinh dữ liệu dùng Gemini SDK khác nhau.

Tác động:

- Người mới khó hiểu script nào là nguồn chuẩn.
- Dễ dùng nhầm file input hoặc output.
- Khó tái lập chính xác dataset và model.

Khuyến nghị:

- Tách script rõ ràng: `preprocess_faq.py`, `preprocess_intent.py`, `merge_faq.py`, `merge_intent.py`.
- Cập nhật lại tài liệu dữ liệu theo số lượng và file hiện tại.
- Thêm Makefile hoặc task runner cho các bước chuẩn.
- Lưu manifest gồm version dữ liệu, ngày tạo, script tạo và checksum.

## Hướng Phát Triển Đề Xuất

### Giai Đoạn 1: Làm Cho Dự Án Chạy Ổn Định

Ưu tiên trong giai đoạn này là giảm lỗi vận hành và làm project có thể chạy lại từ đầu.

- Di chuyển API key ra biến môi trường và thu hồi key đã lộ.
- Cập nhật dependency đầy đủ.
- Sửa `user_id` trong API và session reset.
- Thêm endpoint `/health`.
- Thêm hướng dẫn setup model artifact.
- Viết smoke test cho `/chat`.

Kết quả mong muốn: một developer mới có thể clone repo, cấu hình key, chuẩn bị model và chạy API theo README.

### Giai Đoạn 2: Hoàn Thiện Chatbot Tìm Tour

Giai đoạn này biến flow `success` thành tư vấn tour thật.

- Xây database hoặc file dữ liệu tour mẫu.
- Chuẩn hóa entity đầu vào thành filter có cấu trúc.
- Tạo hàm search tour theo destination, date và price.
- Trả response gồm `message`, `entities`, `tours`, `missing_fields`.
- Thiết kế fallback khi không có tour phù hợp: gợi ý đổi ngày, đổi ngân sách hoặc địa điểm gần.

Kết quả mong muốn: chatbot không chỉ hỏi đủ thông tin mà còn trả được danh sách tour cụ thể.

### Giai Đoạn 3: Nâng Chất Lượng NLP Và RAG

Giai đoạn này tập trung vào chất lượng trả lời.

- Đánh giá lại PhoBERT intent bằng test set cố định.
- Thêm confidence threshold cho intent để giảm phân loại sai.
- Thử embedding tiếng Việt hoặc multilingual tốt hơn cho FAQ.
- Thêm reranker cho top-k FAQ.
- Trả về source và score để debug FAQ.
- Chuẩn hóa prompt theo format có cấu trúc.

Kết quả mong muốn: chatbot trả lời FAQ chính xác hơn, ít fallback sai và ít phụ thuộc vào LLM để sửa lỗi retrieval.

### Giai Đoạn 4: Sẵn Sàng Triển Khai

Giai đoạn này chuẩn bị cho môi trường staging hoặc production.

- Dockerize API và khai báo Java dependency cho VnCoreNLP.
- Dùng Redis cho session.
- Dùng secrets manager hoặc biến môi trường cho API key.
- Thêm CI chạy lint, test và smoke test.
- Thêm monitoring latency, lỗi LLM, retrieval miss và chi phí.
- Version hóa model, dữ liệu và FAISS index.

Kết quả mong muốn: hệ thống có thể chạy ổn định, theo dõi được lỗi và rollback được khi model hoặc dữ liệu mới có vấn đề.

## Đề Xuất Kiến Trúc Response Mới

Nên chuẩn hóa response API để frontend dễ xử lý:

```json
{
  "status": "missing_info",
  "message": "Dạ, em đã ghi nhận quý khách muốn đi Đà Lạt. Quý khách vui lòng cho em biết thêm:",
  "entities": {
    "location": "Đà Lạt",
    "date_start": null,
    "date_end": null,
    "price_min": null,
    "price_max": null
  },
  "missing_fields": ["time", "price"],
  "tours": [],
  "faq_sources": []
}
```

Khi tìm được tour:

```json
{
  "status": "success",
  "message": "Dạ, em tìm được 3 tour phù hợp:",
  "entities": {
    "location": "Đà Lạt",
    "date_start": "2026-12-01",
    "date_end": "2026-12-31",
    "price_min": 0,
    "price_max": 5000000
  },
  "missing_fields": [],
  "tours": [
    {
      "id": "tour_dalat_001",
      "name": "Đà Lạt 3N2Đ",
      "price": 4590000,
      "departure_date": "2026-12-12",
      "highlights": ["Thung lũng Tình Yêu", "Langbiang", "Chợ đêm Đà Lạt"]
    }
  ],
  "faq_sources": []
}
```

## Ưu Tiên Thực Hiện Ngắn Hạn

Nếu chỉ chọn 5 việc để làm ngay, nên ưu tiên:

1. Thu hồi API key đã lộ, chuyển sang `GOOGLE_API_KEY` và cập nhật `.env.example`.
2. Cập nhật `requirements.txt` để dự án cài đặt được đầy đủ.
3. Sửa bug `user_id` trong `server.py` và `reset_session`.
4. Thêm dữ liệu tour mẫu và trả danh sách tour thật ở trạng thái `success`.
5. Thêm test cơ bản cho `/chat`, `extract_time`, `extract_price_vn` và `RetrievalPipeline`.

Sau 5 việc này, dự án sẽ dễ demo, dễ phát triển tiếp và giảm rủi ro lỗi nền tảng.
