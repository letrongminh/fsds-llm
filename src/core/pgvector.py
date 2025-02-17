import logging
import psycopg
from typing import List, Dict, Any, Optional
import json
import os

logger = logging.getLogger(__name__)

class PGVector:
    def __init__(self):
        self._init_db()

    def _get_connection_string(self):
        """Get database connection string from environment variables"""
        host = os.getenv('PGHOST', 'localhost')
        user = os.getenv('PGUSER', 'postgres')
        password = os.getenv('PGPASSWORD', 'postgres')
        database = os.getenv('PGDATABASE', 'postgres')
        return f"postgresql://{user}:{password}@{host}:5432/{database}"

    def _init_db(self):
        with psycopg.connect(self._get_connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
          CREATE TABLE IF NOT EXISTS documents (
          id SERIAL PRIMARY KEY,
          question TEXT NOT NULL,
          answer TEXT NOT NULL,
          metadata JSONB,
          embedding vector(1536),
          created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP)
        """
                )

                cur.execute(
                    """
          CREATE INDEX IF NOT EXISTS documents_embedding_idx 
          ON documents USING vchordrq (embedding vector_l2_ops)
          WITH (options = $$
          residual_quantization = true
          [build.internal]
          lists = [4096]
          spherical_centroids = false
          $$)
        """
                )
                conn.commit()

    def add_documents(self, documents: List[Dict], get_embedding_fn) -> List[int]:
        """
        Add documents and their embeddings to the database

        Args:
            documents: List of document dictionaries
            embeddings: List of embedding vectors

        Returns:
            List of document IDs
        """

        doc_ids = []
        with psycopg.connect(self._get_connection_string()) as conn:
            with conn.cursor() as cur:
                for doc in documents:
                    all_questions = doc.get("variations", [])
                    answer = doc.get("answer", "")
                    metadata = doc.get("metadata", "")

                embeddings = get_embedding_fn(all_questions)

                for question, embedding in zip(all_questions, embeddings):
                    cur.execute(
                        """
              INSERT INTO documents (question, answer, embedding, metadata)
              VALUES (%s, %s, %s, %s)
              RETURNING id;
              """,
                        (question, answer, embedding, json.dumps(metadata)),
                    )
                    doc_ids.append(cur.fetchone()[0])
            conn.commit()
        return doc_ids

    def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 3,
        filter_metadata: Dict = None,
        similarity_threshold: float = 0.8,
    ):
        with psycopg.connect(self._get_connection_string()) as conn:
            with conn.cursor() as cur:
                filter_condition = ""
                params = [query_embedding]

                if filter_metadata:
                    filter_condition = "AND metadata @> %s::jsonb"
                    params.append(json.dumps(filter_metadata))

                cur.execute(
                    f"""
            SELECT 
                question,
                answer,
                metadata,
                1 - (embedding <=> %s::vector) as similarity
            FROM documents
            WHERE 1=1 
                {filter_condition}
                AND 1 - (embedding <=> %s::vector) >= %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """,
                    params
                    + [query_embedding, similarity_threshold, query_embedding, k],
                )

                results = []
                for row in cur.fetchall():
                    results.append(
                        {
                            "question": row[0],
                            "answer": row[1],
                            "metadata": row[2],
                            "similarity": row[3],
                        }
                    )

                return results

    def delete_document(self, doc_id: int) -> bool:
        """Delete a document by its ID"""
        with psycopg.connect(self._get_connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted
