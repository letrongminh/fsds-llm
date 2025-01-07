import json
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.pgvector import PGVector
from src.core.embedding import EmbeddingClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FAQVectorSearch:
    def __init__(self):
        self.pgvector = PGVector()
        self.embedding_client = EmbeddingClient(
            embedding_model_id="cohere.embed-multilingual-v3"
        )

    def load_and_add_documents(self, json_path: str):
        try:
            with open(json_path, "r", encoding="utf-8") as file:
                faq_data = json.load(file)

            logger.info(f"Loaded {len(faq_data)} documents from {json_path}")
            for doc in faq_data:
                all_questions = doc.get("variations", [])

                embeddings = self.embedding_client.embed_documents(all_questions)

                if not embeddings:
                    logger.error(f"Failed to embed documents for {all_questions}")
                    continue

                doc_ids = self.pgvector.add_documents(
                    documents=[
                        {
                            "variations": all_questions,
                            "answer": doc.get("answer", ""),
                            "metadata": doc.get("metadata", ""),
                        }
                    ],
                    get_embedding_fn=lambda x: embeddings,
                )

                logger.info(f"Added document with IDs: {doc_ids}")

        except Exception as e:
            logger.error(f"Error processing documents: {e}")
            raise


def main():
    # Initialize FAQ search system
    faq_search = FAQVectorSearch()

    # Add documents if needed
    should_add = input(
        "Do you want to load FAQ documents into the vector store? (y/n): "
    ).lower()
    if should_add == "y":
        logger.info("Loading FAQ documents into vector store...")
        faq_search.load_and_add_documents("faq_enriched.json")
        logger.info("Finished loading documents")


if __name__ == "__main__":
    main()
