import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle


def create_faiss_index(input_file='data/processed/faq_cleaned.json', index_file="faq_index.faiss", metadata_file="faq_metadata.json"):

     # Load the JSON data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract questions from the JSON data
    questions = [item['question'] for item in data]
    if not questions:
        raise ValueError("No questions found in FAQ data")
    
    # Initialize the SentenceTransformer model
    model = SentenceTransformer("all-MiniLM-L6-v2")
    # Convert questions to embeddings
    embeddings = model.encode(questions, show_progress_bar=True)

    
    # Create Faiss index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.ascontiguousarray(embeddings.astype('float32'))) # Ensure the embeddings are contiguous in memory

    # Save the Faiss index
    faiss.write_index(index, index_file)
    print(f"Index saved to {index_file}")

    #save to metadata
    metadata = [{"index": i, "question": item["question"], "answer": item["answer"], "tags": item["tags"]}
                for i, item in enumerate(data)]
    
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Saved metadata to {metadata_file}")

if __name__ == "__main__":
    create_faiss_index()
