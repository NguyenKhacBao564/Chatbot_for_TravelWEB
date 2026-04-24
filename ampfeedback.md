# Bug Report — Chatbot Travel AI

> Cập nhật: 2026-04-24 22:44  
> Người viết: Amp (AI agent)

---

## Bug đã fix: Server chạy sai Python (ĐÃ GIẢI QUYẾT)

Server trước đó chạy bằng system Python 3.12 (thiếu deps) thay vì venv Python 3.13.  
**Đã fix** bằng cách chạy `source .venv/bin/activate && uvicorn server:app ...`  
Kết quả: FAQ pipeline hoạt động, phần lớn queries trả lời đúng.

---

## Bug còn lại: Nhiều câu hỏi FAQ hợp lệ vẫn bị trả "out of scope"

### Triệu chứng

Chatbot hoạt động **"được câu không"** — một số FAQ queries trả đúng, một số vẫn bị fallback sai:

| Query | Kết quả | Lý do |
|---|---|---|
| `"Thời điểm nào Hà Nội có thời tiết đẹp nhất?"` | ✅ Trả đúng | Slug chứa `thoi-tiet` → match pattern |
| `"Tour Guide có hỗ trợ làm visa không?"` | ✅ Trả đúng | Slug chứa `ho-tro` + `visa` → match service pattern |
| `"Hà Nội có những quán cà phê nổi tiếng nào nên ghé thăm?"` | ❌ "chỉ hỗ trợ du lịch" | Slug = `ha-noi-co-nhung-quan-ca-phe-noi-tieng-nao-nen-ghe-tham` → **không match pattern nào** |

FAQ metadata **có** câu trả lời chính xác cho query thất bại (tag `food`, 19 entries về cà phê), nhưng routing layer chặn trước khi tới retrieval.

### Nguyên nhân gốc

Routing dùng **slug substring matching** — query phải chứa ít nhất 1 pattern trong `KNOWLEDGE_QUERY_PATTERNS` hoặc `SERVICE_QUERY_PATTERNS` để vào FAQ flow. Nếu user hỏi bằng cách diễn đạt không chứa bất kỳ pattern nào → bị đẩy thẳng vào `out_of_scope`.

**Ví dụ slug patterns hiện có cho food:** `an-gi`, `mon-gi`, `mon-an`, `an-uong`, `am-thuc`, `dac-san`

**Nhưng user hỏi:** `"quán cà phê nổi tiếng nào nên ghé thăm"` → không match vì không có `quan`, `ca-phe`, `ghe-tham`, `noi-tieng` trong patterns.

**Quy mô vấn đề:** Có ~205 câu hỏi recommendation-style trong FAQ data (chứa "nên ghé", "nên đi", "nổi tiếng", "phải thử"...) có thể bị miss tương tự.

---

## Các vấn đề kiến trúc cần bàn luận

### 1. Thiếu startup validation

Server khởi động thành công (HTTP 200) ngay cả khi **toàn bộ FAQ pipeline bị vô hiệu hóa**. Không có health check nào cảnh báo rằng core feature đang chết.

**Đề xuất:** Endpoint `/health` nên report trạng thái các component:

```json
{
  "status": "degraded",
  "components": {
    "faq_retrieval": false,
    "intent_model": false,
    "tour_search": true,
    "gemini_api": false
  }
}
```

### 2. Intent model không tồn tại

`training/phobert_intent_finetuned/` không có trong repo — chưa bao giờ được train hoặc đã bị xóa. Server log warning mỗi lần khởi động nhưng vẫn chạy bình thường bằng rule-based fallback.

**Câu hỏi cần bàn:** Rule-based fallback hiện tại đã đủ tốt chưa? Có cần train lại PhoBERT intent model không?

**Thực trạng intent training data (intent_merged.json):**
- 11,904 entries total
- `out_of_scope`: 5,504 (46%) — bao gồm **TẤT CẢ** FAQ queries (weather, food, culture, service, payment...)
- 7 tour-search intents: 6,400 entries (54%)
- Intent model được thiết kế để phân biệt "tour search" vs "everything else" — KHÔNG phân biệt FAQ subtypes

**Vấn đề:** Nếu train PhoBERT với data này, nó sẽ đúng label `out_of_scope` cho FAQ queries, nhưng rule-based routing vẫn cần chạy phía sau để quyết định FAQ subtypes. Vậy PhoBERT chỉ thêm 1 layer mà rule-based đã xử lý được.

### 3. FAQ retrieval quality — keyword vs FAISS

Hiện tại có 2 đường retrieval:

```
Query → _retrieve_faq_from_metadata() [keyword match] → nếu trống → FAISS [vector search] → Gemini paraphrase
```

**Keyword match** (primary): match location + tag patterns → chính xác nhưng hẹp.  
**FAISS** (fallback): multilingual embedding search → rộng hơn nhưng noisy.

**Vấn đề thấy được:** Với service queries không có location (ví dụ "chính sách hoàn tiền"), keyword metadata match thường trả kết quả không chính xác vì nó match tag `service` rộng quá (457 entries cùng tag). Câu trả lời có thể là về "đón sân bay" thay vì "hoàn tiền".

**Câu hỏi cần bàn:** Có nên thêm text similarity scoring (TF-IDF hoặc BM25) vào keyword metadata search để rank chính xác hơn?

### 4. Kiến trúc xử lý FAQ — quá phụ thuộc vào slug pattern matching (BUG CHÍNH CÒN LẠI)

Toàn bộ routing hiện tại dựa trên `slugify_vietnamese(query)` rồi check substring:

```python
# "Nếu tôi muốn thay đổi lịch trình tour" 
# → slug: "neu-toi-muon-thay-doi-lich-trinh-tour-cong-ty-co-ho-tro-khong"
# → match "thay-doi" in SERVICE_QUERY_PATTERNS → route to FAQ ✅

# "Hà Nội có quán cà phê nổi tiếng nào?"
# → slug: "ha-noi-co-nhung-quan-ca-phe-noi-tieng-nao-nen-ghe-tham"
# → KHÔNG match pattern nào → out_of_scope → "chỉ hỗ trợ du lịch" ❌
```

**Ưu:** Nhanh, deterministic, dễ debug.  
**Nhược:** Mỗi khi user hỏi kiểu mới → rơi vào out_of_scope → trả fallback sai.

**Các query trong FAQ data nhưng KHÔNG match pattern hiện tại:**
- `"Hà Nội có những quán cà phê nổi tiếng nào nên ghé thăm?"` (tag: food, 19 entries)
- `"Tôi có thể mang theo thú cưng khi đi tour không?"` — không match
- `"Tour có wifi trên xe không?"` — không match
- `"Trẻ em dưới 5 tuổi có phải mua vé không?"` — không match
- ~205 câu hỏi recommendation-style ("nên ghé", "nổi tiếng", "phải thử"...)

**Hướng giải quyết tiềm năng (cần bàn luận):**

**Phương án A — Thêm patterns:** Thêm `ca-phe`, `quan-an`, `nha-hang`, `noi-tieng`, `nen-ghe`, `nen-di`, `phai-thu`... vào KNOWLEDGE_QUERY_PATTERNS. **Ưu:** Đơn giản, nhanh. **Nhược:** Chạy theo đuôi user mãi, luôn có edge case mới.

**Phương án B — Đảo logic routing:** Thay vì "whitelist" (chỉ route FAQ nếu match pattern), dùng "blacklist" (mọi query có destination đều thử FAQ trước, chỉ vào tour-search nếu match EXPLICIT_TOUR_QUERY_PATTERNS). **Ưu:** Coverage cao hơn. **Nhược:** Có thể false positive cho queries thật sự out_of_scope.

**Phương án C — Dùng FAISS làm router:** Khi không match pattern nào nhưng có destination → thử FAISS search trước, nếu distance score đủ tốt (< threshold) → trả FAQ. Chỉ fallback "chỉ hỗ trợ du lịch" khi FAISS cũng không match. **Ưu:** Tận dụng multilingual embedding. **Nhược:** Chậm hơn, cần tune threshold cẩn thận.

**Phương án D — Hybrid:** Kết hợp B + C. Nếu query có destination → luôn thử FAQ retrieval (keyword + FAISS), chỉ reject nếu cả 2 đường đều không match.

### 5. Thiếu script chạy server chuẩn

Không có file `run.sh`, `Makefile`, hay `scripts/start_server.py` → user phải tự nhớ activate venv, dẫn đến bug hiện tại.

---

## Tóm tắt trạng thái các component

| Component | Trạng thái | Ghi chú |
|---|---|---|
| Server (FastAPI + Uvicorn) | ✅ Chạy | Nhưng dùng sai Python |
| FAQ Retrieval Pipeline | ❌ Disabled | Do sai Python → thiếu deps |
| FAISS Index | ✅ Đã rebuild | Dùng `paraphrase-multilingual-MiniLM-L12-v2` |
| FAQ Metadata (3504 entries) | ✅ Đầy đủ | Phủ 50+ destinations, 17 tag categories |
| Intent Model (PhoBERT) | ❌ Không tồn tại | Rule-based fallback đang hoạt động |
| Gemini API | ⚠️ Chưa config | `GOOGLE_API_KEY` chưa set → dùng deterministic fallback |
| Knowledge routing | ✅ Đã sửa | Thêm transport, service, entertainment patterns |
| Service routing | ✅ Đã sửa | SERVICE_QUERY_PATTERNS mới, bypass tour check |
| Location extraction | ✅ Đã sửa | 100+ aliases, loại bỏ VnCoreNLP dependency |
| Tour Search | ✅ Hoạt động | 6 tours sample, filter by dest/time/price |

## Các thay đổi code đã thực hiện (session này)

1. **`services/entity_normalizer.py`** — Mở rộng `DESTINATION_ALIASES` từ 15 → 100+ entries
2. **`extractors/extract_location.py`** — Thay VnCoreNLP bằng alias-based extraction
3. **`pipelines/tour_pipeline.py`** — Thêm SERVICE_QUERY_PATTERNS, mở rộng KNOWLEDGE_QUERY_PATTERNS, FAQ_QUERY_TAG_PATTERNS, fix routing logic
4. **`pipelines/retrieval.py`** — Đổi sang multilingual embedding model, adjust threshold
5. **`pipelines/create_faiss_index.py`** — Dùng multilingual model, đã rebuild index
6. **`faq_index.faiss`** — Đã rebuild với model mới
