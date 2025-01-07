import json
from typing import Optional
from .bedrock_client import BedrockClient


class EmbeddingClient(BedrockClient):
    def __init__(self):
        super().__init__(model_id="cohere.embed-multilingual-v3")

    def embed_documents(self, texts: list[str], input_type: str = "search_document"):

        body = {"texts": texts, "input_type": input_type}

        try:
            response = self.invoke_model(body)

            # Parse the response
            response_body = json.loads(response.get("body").read().decode("utf-8"))

            # Extract the embeddings from the response
            embeddings = response_body.get("embeddings")
            return embeddings
        except Exception as e:
            print(f"Error embedding documents: {e}")
            return []
