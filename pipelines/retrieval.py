import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from google import genai
from google.genai import types


class RetrievalPipeline:
    def __init__(self, index_file="faq_index.faiss", metadata_file="faq_metadata.json"):
        # Tải metadata
        with open(metadata_file, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        # Tải Faiss index
        self.index = faiss.read_index(index_file)

        # Khởi tạo model embedding
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def get_retrieved_context(self, user_query, top_k=1):
        # Embed câu hỏi
        query_embedding = self.model.encode([user_query], show_progress_bar=False)
        query_embedding = np.array(query_embedding).astype("float32")

        # Tìm top-k vector gần nhất
        distances, indices = self.index.search(query_embedding, top_k)
        print("Distances:", distances)
        
        #kiểm tra xem câu trả lời có phù hợp không, tự đặt ngưỡng 
        if distances[0][0] > 1:
            return "None"

        # Tạo context từ metadata
        context_lines = []
        for idx in indices[0]:
            if idx < len(self.metadata):
                item = self.metadata[idx]
                context_lines.append(f"{item['answer']}")
        print("Context lines :", context_lines)
        return "\n---\n".join(context_lines) if context_lines else ""

