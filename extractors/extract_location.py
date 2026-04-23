import os
import json
from vncorenlp import VnCoreNLP

# Khởi tạo VnCoreNLP
try:
    # current_dir = os.path.dirname(os.path.abspath(__file__))
    # jar_path = os.path.join(current_dir, "VnCoreNLP-1.1.1.jar")
    vncorenlp = VnCoreNLP("training/VnCoreNLP-1.1.1.jar", annotators="wseg,ner", max_heap_size='-Xmx2g')
except Exception as e:
    print(f"Lỗi khi khởi tạo VnCoreNLP: {e}")
    exit(1)

def preprocess_text(text):
    """Phân đoạn từ và nhận diện thực thể bằng VnCoreNLP."""
    try:
        # Gọi VnCoreNLP để xử lý văn bản
        annotated_text = vncorenlp.annotate(text)
        return annotated_text
    except Exception as e:
        print(f"Lỗi khi xử lý văn bản: {e}")
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
    