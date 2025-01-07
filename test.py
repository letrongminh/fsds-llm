import streamlit as st
from src.core.tools import OrderQuerySystem
from src.core.pgvector import PGVector
from src.core.embedding import EmbeddingClient
import json
from typing import Dict, List
from contextlib import contextmanager

embedding_client = EmbeddingClient()
vector_db = PGVector()


def get_faq_response(query: str) -> Dict:
    """Get response from FAQ system"""
    # Get embedding for query using EmbeddingClient
    query_embeddings = embedding_client.embed_documents(
        texts=[query], input_type="search_query"
    )

    if not query_embeddings:
        return {"found": False}

    query_embedding = query_embeddings[0]

    # Search similar questions
    results = vector_db.similarity_search(
        query_embedding=query_embedding, k=3, similarity_threshold=0.7
    )

    if results:
        return {
            "found": True,
            "answer": results[0]["answer"],
            "similarity": results[0]["similarity"],
        }
    return {"found": False}


print(get_faq_response("Vì sao đơn hàng không được giao một lần?"))
