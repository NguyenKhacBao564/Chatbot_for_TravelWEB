import logging

try:
    from vncorenlp import VnCoreNLP
except ImportError:
    VnCoreNLP = None


logger = logging.getLogger(__name__)
vncorenlp = None


def get_vncorenlp():
    global vncorenlp
    if VnCoreNLP is None:
        logger.warning("vncorenlp is not installed; location NER is disabled")
        return None
    if vncorenlp is None:
        try:
            vncorenlp = VnCoreNLP(
                "training/VnCoreNLP-1.1.1.jar",
                annotators="wseg,ner",
                max_heap_size='-Xmx2g',
            )
        except Exception as exc:
            logger.warning("Không thể khởi tạo VnCoreNLP location extractor: %s", exc)
            return None
    return vncorenlp

def preprocess_text(text):
    """Phân đoạn từ và nhận diện thực thể bằng VnCoreNLP."""
    nlp = get_vncorenlp()
    if nlp is None:
        return None
    try:
        return nlp.annotate(text)
    except Exception as e:
        logger.warning("Lỗi khi xử lý văn bản location: %s", e)
        return None

def extract_loc_entities(annotated_text):
    """Trích xuất chỉ tên tỉnh/thành phố, bỏ các từ như 'tỉnh', 'thành_phố'."""
    prefixes_to_remove = {"tỉnh", "thành_phố", "huyện", "quận", "thị_xã"}
    
    entities = []
    for sentence in annotated_text['sentences']:
        current_entity = []
        current_label = None
        
        for token in sentence:
            word = token['form']
            ner_label = token['nerLabel']
            
            # Kiểm tra nhãn B-LOC hoặc I-LOC
            if ner_label in ['B-LOC', 'I-LOC']:
                # Chỉ thêm từ nếu không phải prefix cần bỏ
                if ner_label == 'B-LOC' and word.lower() in prefixes_to_remove:
                    continue  # Bỏ qua 'tỉnh', 'thành_phố', v.v.
                current_entity.append(word)
                current_label = 'LOC'
            else:
                if current_entity:
                    entities.append({
                        "text": " ".join(current_entity),
                        "label": current_label
                    })
                    current_entity = []
                    current_label = None
        
        # Kiểm tra nếu còn thực thể cuối câu
        if current_entity:
            entities.append({
                "text": " ".join(current_entity),
                "label": current_label
            })
    
    return entities

def extract_location(query):
    """Trích xuất tên địa điểm từ truy vấn, trả về chuỗi tên địa điểm."""
    # Phân đoạn và nhận diện thực thể
    annotated_text = preprocess_text(query)
    if annotated_text:
        # Trích xuất các thực thể LOC
        loc_entities = extract_loc_entities(annotated_text)
        
        # Thay dấu _ bằng khoảng trắng và trả về tên địa điểm đầu tiên
        for entity in loc_entities:
            location = entity["text"].replace("_", " ")
            return location
        
        # Nếu không tìm thấy địa điểm, trả về None
        return "None"
    else:
        return "None"
