# Amp Feedback — Đánh Giá Phương Án Codex & Đề Xuất Cải Tiến

> Người đánh giá: Amp  
> Ngày: 2026-04-23  
> Phạm vi: Toàn bộ `docs/ai_context/`, source code hiện tại, `CHATBOT_REVIEW_AND_ROADMAP.md`, `REFACTOR_NOTES.md`

---

## I. Tổng Quan Đánh Giá Về Công Việc Codex Đã Làm

### Điểm tích cực

Codex đã thực hiện một đợt refactor có chiều sâu, chuyển dự án từ prototype thuần NLP sang kiến trúc hybrid NLP + deterministic business search. Cụ thể:

1. **Kiến trúc tách tầng rõ ràng**: `extractors/` → `services/` → `repositories/` → `schemas/` là hướng đi đúng. Protocol-based `TourRepository` giúp swap data source dễ dàng.
2. **Quyết định D-002 và D-003 rất đúng**: LLM không được quyết định business logic, Gemini chỉ đóng vai trò phrasing. Đây là nguyên tắc quan trọng nhất của dự án và Codex giữ nó nhất quán.
3. **Graceful degradation (D-005)**: Optional import cho torch/faiss/vncorenlp + fallback rule-based là cách tiếp cận thực tế, giúp dev/test không cần đầy đủ artifact.
4. **Structured response schema**: `ChatResponse` với `status`/`entities`/`tours`/`faq_sources` là contract tốt cho frontend.
5. **Tài liệu AI context**: Bộ 6 file trong `docs/ai_context/` viết tốt, giúp bất kỳ AI session nào sau này hiểu dự án nhanh. Đây là practice hiếm thấy và rất có giá trị.
6. **Test coverage ban đầu**: Có test cho API smoke, parser, tour search, session isolation — đủ để phát hiện regression cơ bản.

### Điểm cần cải thiện

1. **`TourRetrievalPipeline` vẫn là God Object**: Dù đã tách service, pipeline vẫn đảm nhận intent classification, entity extraction, session management, FAQ routing, tour search orchestration, và response formatting. Đây là single point of failure cho mọi thay đổi.
2. **Entity flow bị normalize 2 lần**: Trong `get_tour_response()`, `extract_entities()` đã gọi `normalize_entities()` rồi, nhưng sau đó `get_tour_response()` lại gọi `normalize_entities()` lần nữa với kết quả raw. Điều này có thể gây inconsistency.
3. **Extractor trả `"None"` string thay vì `None`**: `extract_location()`, `extract_all_times()`, `extract_price_vn()` đều trả string `"None"` khi không tìm thấy. Code phải check `!= "None"` thay vì `is not None` — rất dễ gây bug khi refactor.
4. **Roadmap thiếu quantifiable milestones**: Codex viết roadmap theo nhóm Now/Next/Later nhưng không có metric đo lường thành công. Ví dụ: "Improve FAQ retrieval" nhưng không nói recall/precision target là bao nhiêu.

---

## II. Đánh Giá Từng Hạng Mục Trong Roadmap Codex

### Hạng mục 1: Integrate Real Website Tour Data Source

**Đánh giá: ✅ Đúng ưu tiên, thiếu chi tiết thực thi**

Codex xác định đúng rằng đây là blocker lớn nhất. Tuy nhiên, roadmap chỉ nói "depends on knowing the real data source" mà không đưa ra bất kỳ action plan nào để unblock.

**Đề xuất Amp:**
- Ngay lập tức tạo `repositories/api_tour_repository.py` — một adapter gọi REST API từ website du lịch thật (nếu website đã có API). Pattern:
  ```python
  class ApiTourRepository:
      def __init__(self, base_url: str, api_key: str | None = None):
          ...
      def list_tours(self, **kwargs) -> List[Tour]:
          # GET /api/tours với pagination
          ...
  ```
- Nếu website chưa có API, ưu tiên viết scraper hoặc DB read-only adapter trước. Không nên chờ "biết data source" mà nên tạo interface contract + mock data phong phú hơn (50-100 tours đa dạng điểm đến/giá/ngày).
- Bổ sung `data/tours_sample.json` lên ít nhất **30-50 tours** phủ 10+ điểm đến, nhiều mức giá, nhiều tháng khởi hành. Chỉ 6 tours hiện tại thì không thể test ranking hay edge case.

### Hạng mục 2: Support Partial Search

**Đánh giá: ✅ Đồng ý rất cần làm, nhưng cần thiết kế UX flow rõ hơn**

D-007 ("Require all 3 fields") là quyết định an toàn ban đầu, nhưng ảnh hưởng UX nghiêm trọng. User hỏi "Tour Đà Lạt tháng 12" (không có giá) thì bị block — đây là scenario rất phổ biến.

**Đề xuất Amp:**
- Cho phép search khi có `location` + ít nhất 1 trong 2 (`time` hoặc `price`). Nếu thiếu `price`, search không lọc giá. Nếu thiếu `time`, search tất cả ngày trong 3-6 tháng tới.
- Response status mới: `"partial_search"` — trả tour nhưng kèm gợi ý: "Quý khách muốn giới hạn ngân sách không ạ?"
- Riêng `location` là trường bắt buộc duy nhất. Không nên search nếu không biết điểm đến.
- Cập nhật `_missing_fields()`:
  ```python
  def _missing_fields(self, entities):
      # location là bắt buộc
      if not entities.destination_normalized:
          return ["location"]
      # time và price là optional, chỉ gợi ý
      return []
  ```

### Hạng mục 3: Add Evaluation For Search And FAQ

**Đánh giá: ✅ Quan trọng, nhưng Codex chưa đưa ra framework cụ thể**

**Đề xuất Amp:**
- Tạo `tests/evaluation/` với 2 file:
  - `eval_intent.py`: 50-100 câu hỏi thực tế + expected intent. Chạy so sánh PhoBERT vs rule fallback.
  - `eval_faq_retrieval.py`: 30-50 câu hỏi + expected FAQ answer. Đo Recall@1, Recall@3, MRR.
- Tạo `data/evaluation/` chứa gold test sets dạng JSONL:
  ```json
  {"query": "Tour Đà Lạt tháng 12 dưới 5 triệu", "expected_intent": "find_with_all", "expected_location": "Đà Lạt"}
  ```
- Chạy eval trước/sau mỗi thay đổi NLP và ghi kết quả vào `log/eval_results/`.

### Hạng mục 4: Improve Destination Normalization

**Đánh giá: ⚠️ Đúng hướng nhưng chưa đủ triệt để**

`DESTINATION_ALIASES` hiện chỉ có 15 entries. Với Việt Nam có 63 tỉnh/thành + hàng trăm điểm du lịch, đây là quá ít.

**Đề xuất Amp:**
- Tách `DESTINATION_ALIASES` ra file `data/destination_catalog.json` thay vì hardcode trong code. Format:
  ```json
  {
    "da-lat": {
      "canonical": "Đà Lạt",
      "aliases": ["dalat", "đa-lat", "tp-da-lat", "thanh-pho-da-lat"],
      "province": "Lâm Đồng",
      "region": "Tây Nguyên"
    }
  }
  ```
- Thêm **fuzzy matching** cho tên địa điểm: dùng `rapidfuzz` hoặc Levenshtein distance. User gõ "Đà Lạc" hay "đalạt" cũng nên match được.
- Bổ sung lookup theo tỉnh/vùng: "Tour miền Tây" → search tất cả điểm đến thuộc vùng Tây Nam Bộ.
- Tự động extract destination catalog từ tour data thật khi có database.

### Hạng mục 5: Revisit FAQ Retrieval Model

**Đánh giá: ✅ Rất cần, `all-MiniLM-L6-v2` yếu cho tiếng Việt**

**Đề xuất Amp:**
- Thay `all-MiniLM-L6-v2` bằng **`intfloat/multilingual-e5-base`** hoặc **`BAAI/bge-m3`** — cả hai đều mạnh hơn nhiều cho tiếng Việt và multilingual.
- Quan trọng hơn model: **sửa metric distance**. Hiện dùng L2 distance với ngưỡng cố định `1.0` — nên chuyển sang **cosine similarity** với ngưỡng `0.5-0.7` (tuỳ model). Cosine similarity ổn định hơn L2 khi vector dimension thay đổi.
- Thêm **reranker** nếu top-k > 3: lấy top-10 rồi dùng cross-encoder rerank. Gợi ý: `BAAI/bge-reranker-v2-m3` hoặc dùng Gemini làm reranker nhẹ.
- Ngưỡng (`distance_threshold`) nên được calibrate từ eval set, không hardcode magic number.

### Hạng mục 6-9: Session, Observability, Dataset Lifecycle

**Đánh giá: ✅ Đúng nhưng chưa cấp bách**

Đồng ý với Codex rằng đây là "Later" items. Tuy nhiên, bổ sung thêm:

- **Session**: Trước khi chuyển Redis, thêm TTL cleanup cho `SessionManager`. Hiện tại `_is_expired()` chỉ check khi access — sessions hết hạn vẫn tồn tại trong memory mãi mãi. Thêm background cleanup hoặc LRU eviction.
- **Observability**: Ưu tiên thêm **request_id** vào mọi log entry ngay bây giờ — chi phí thấp, giá trị debug cao. Middleware FastAPI:
  ```python
  @app.middleware("http")
  async def add_request_id(request, call_next):
      request.state.request_id = str(uuid4())
      response = await call_next(request)
      return response
  ```

---

## III. Các Vấn Đề Codex Chưa Đề Cập (Amp Bổ Sung)

### A. Bug: Entity extraction gọi 2 lần normalize

Trong `tour_pipeline.py`:
```python
# Dòng 219: extract_entities() đã gọi normalize_entities() bên trong
raw_entities = self.extract_entities(query, intent, user_id)
# Dòng 272: gọi lại normalize_entities() với kết quả raw
entities = normalize_entities(raw_entities, query)
```

`extract_entities()` trả về dict `{"location": ..., "time": ..., "price": ...}` đã qua normalize. Nhưng `get_tour_response()` lại normalize lần nữa. Lần thứ 2 có thể overwrite giá trị session đã cập nhật.

**Fix:** `extract_entities()` nên trả về `ExtractedEntities` trực tiếp thay vì dict raw, và `get_tour_response()` không cần gọi `normalize_entities()` lần nữa.

### B. Thiếu rate limiting cho Gemini calls

Mỗi request `/chat` có thể gọi Gemini 1-2 lần (missing_info message hoặc tour search message). Không có rate limiting hay caching.

**Đề xuất:**
- Thêm simple cache (LRU hoặc TTL cache) cho `get_genai_response()` với các prompt lặp lại.
- Thêm rate limiter: tối đa N calls/phút cho Gemini. Khi vượt ngưỡng, dùng fallback deterministic.
- Cân nhắc: Với `missing_info`, message deterministic đã đủ tốt — không nhất thiết phải gọi Gemini. Chỉ nên dùng Gemini cho FAQ rephrasing.

### C. Thiếu input validation và sanitization

`server.py` không validate/sanitize `query` đầu vào:
- Không giới hạn độ dài query (DoS vector).
- Không strip HTML/script tags (nếu message được hiển thị trên frontend).
- `user_id` không có format validation.

**Đề xuất:**
```python
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    user_id: str = Field(default="default_user", max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
```

### D. Thiếu CORS configuration

`server.py` không có CORS middleware. Nếu frontend chạy trên domain khác, mọi request sẽ bị browser block.

**Đề xuất:**
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
```
(Production nên restrict `allow_origins` về domain cụ thể.)

### E. `extract_location()` trả về chỉ location đầu tiên

Khi user nói "Tour từ Sài Gòn đi Đà Lạt", VnCoreNLP sẽ extract 2 locations. Hiện tại `extract_location()` chỉ trả về location đầu tiên — có thể là điểm xuất phát (Sài Gòn) thay vì điểm đến (Đà Lạt).

**Đề xuất:**
- Trả về danh sách tất cả locations: `extract_locations(query) -> List[str]`.
- Thêm heuristic đơn giản: location sau "đi/đến/tới" là destination, location sau "từ/xuất phát" là departure.
- Bổ sung `departure_location` vào `ExtractedEntities` schema nếu cần.

### F. Không handle concurrent requests an toàn

`pipeline` là global singleton, `SessionManager` dùng dict thuần. Với uvicorn chạy multiple workers hoặc async, có thể xảy ra race condition trên session data.

**Đề xuất ngắn hạn:** Thêm `asyncio.Lock` hoặc `threading.Lock` cho session access. Dài hạn: chuyển Redis/external store như Codex đã plan.

### G. Chưa có endpoint reset session

User muốn bắt đầu tìm tour mới nhưng session cũ vẫn giữ location/time/price cũ. Không có cách reset ngoài chờ TTL hết hạn.

**Đề xuất:** Thêm endpoint:
```python
@app.post("/reset")
async def reset_session(request: ResetRequest):
    get_pipeline().reset_session(request.user_id)
    return {"status": "ok", "message": "Phiên tìm kiếm đã được làm mới."}
```
(`ResetRequest` đã được define trong `tour_pipeline.py` nhưng chưa dùng.)

### H. Tour schema thiếu fields quan trọng cho UX

`Tour` model hiện tại thiếu:
- `thumbnail` / `image_url`: hình ảnh tour
- `highlights`: điểm nổi bật
- `included_services`: dịch vụ bao gồm
- `departure_location`: điểm xuất phát
- `available_seats`: số chỗ còn trống

Những fields này cần có khi kết nối database thật. Nên bổ sung vào schema sớm (optional fields) để frontend team có thể develop song song.

---

## IV. Đề Xuất Thứ Tự Ưu Tiên Của Amp

Dựa trên impact/effort, đề xuất thứ tự làm khác với Codex:

| # | Hạng mục | Impact | Effort | Ghi chú |
|---|----------|--------|--------|---------|
| 1 | Fix bug normalize 2 lần (III.A) | High | Low | Bug logic, fix trong 30 phút |
| 2 | Fix extractor trả `"None"` string (II trên) | High | Low | Refactor extractor return type |
| 3 | Input validation + CORS (III.C, III.D) | High | Low | Bảo mật cơ bản |
| 4 | Mở rộng `tours_sample.json` (30-50 tours) | High | Low | Cần data tốt hơn để test |
| 5 | Partial search — bỏ yêu cầu bắt buộc price (II.2) | High | Medium | UX improvement lớn nhất |
| 6 | Tách destination catalog ra file JSON (II.4) | Medium | Low | Dễ mở rộng, dễ maintain |
| 7 | Thêm endpoint `/reset` (III.G) | Medium | Low | Đã có code, chỉ cần wire |
| 8 | Tạo evaluation framework (II.3) | High | Medium | Gate chất lượng cho mọi thay đổi |
| 9 | Upgrade FAQ embedding model (II.5) | High | Medium | Cải thiện FAQ quality đáng kể |
| 10 | Integrate real tour data source (II.1) | Critical | High | Blocker chính, nhưng phụ thuộc external |
| 11 | Reduce Gemini calls (III.B) | Medium | Low | Tiết kiệm cost + giảm latency |
| 12 | Refactor pipeline thành nhiều service nhỏ | Medium | High | Technical debt, làm sau |

---

## V. Kết Luận

Codex đã làm tốt phần nền tảng kiến trúc và document hoá rõ ràng. Roadmap của Codex hợp lý ở mức chiến lược nhưng **thiếu chi tiết thực thi** và **bỏ sót một số bug/gap quan trọng** trong code hiện tại. 

Khuyến nghị: **Xử lý nhóm bug/quick-win (items 1-4, 6-7) trước**, sau đó mới tiến vào partial search và evaluation framework. Real data source integration nên chạy song song khi đã có thông tin từ team website.

Điều quan trọng nhất mà Codex đã làm đúng và cần giữ: **LLM chỉ là phrasing layer, business logic phải deterministic**. Mọi thay đổi tiếp theo phải tuân thủ nguyên tắc này.
