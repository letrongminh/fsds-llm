from openai import OpenAI
from typing import List

class EmbeddingClient:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "text-embedding-3-small"

    def embed_documents(self, texts: List[str], input_type: str = "search_document") -> List[List[float]]:
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            # Extract embeddings from response
            embeddings = [item.embedding for item in response.data]
            return embeddings
        except Exception as e:
            print(f"Error embedding documents: {e}")
            return []
