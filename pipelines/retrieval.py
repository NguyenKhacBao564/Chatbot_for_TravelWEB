import json
import logging

try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
except ImportError:
    faiss = None
    np = None
    SentenceTransformer = None

from schemas.chat_response import FAQSource


logger = logging.getLogger(__name__)


class RetrievalPipeline:
    def __init__(
        self,
        index_file="faq_index.faiss",
        metadata_file="faq_metadata.json",
        distance_threshold=1.0,
    ):
        if faiss is None or np is None or SentenceTransformer is None:
            raise RuntimeError("faiss-cpu, numpy and sentence-transformers are required for FAQ retrieval")
        self.distance_threshold = distance_threshold
        with open(metadata_file, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        self.index = faiss.read_index(index_file)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def retrieve(self, user_query, top_k=3):
        """Return FAQ matches with metadata for response/debugging."""
        query_embedding = self.model.encode([user_query], show_progress_bar=False)
        query_embedding = np.array(query_embedding).astype("float32")

        distances, indices = self.index.search(query_embedding, top_k)
        logger.debug("FAQ retrieval distances: %s", distances)

        sources = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata) or distance > self.distance_threshold:
                continue
            item = self.metadata[idx]
            sources.append(
                FAQSource(
                    question=item.get("question"),
                    answer=item.get("answer"),
                    tags=item.get("tags", []),
                    score=round(1 / (1 + float(distance)), 4),
                    source=f"faq_metadata:{idx}",
                )
            )
        return sources

    def get_retrieved_context(self, user_query, top_k=1):
        sources = self.retrieve(user_query, top_k=top_k)
        if not sources:
            return "None"
        return "\n---\n".join(source.answer or "" for source in sources)
