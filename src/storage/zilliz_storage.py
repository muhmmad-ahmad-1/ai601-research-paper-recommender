from typing import Dict, List, Optional
import logging
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class ZillizStorage:
    def __init__(
        self,
        uri: str,
        token: str,
        collection_name: str = "papers",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.uri = uri
        self.token = token
        self.collection_name = collection_name
        self.embedding_model = SentenceTransformer(embedding_model)
        self._connect()
        self._ensure_collection()

    def _connect(self):
        try:
            connections.connect(alias="default", uri=self.uri, token=self.token)
            logger.info("Connected to Zilliz Cloud")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise

    def _ensure_collection(self):
        try:
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                return

            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="paper_url", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="abstract", dtype=DataType.VARCHAR, max_length=20000),
                FieldSchema(name="year", dtype=DataType.VARCHAR, max_length=10),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="chunk_index", dtype=DataType.INT64),
                FieldSchema(name="authors", dtype=DataType.JSON),
                FieldSchema(name="citations", dtype=DataType.JSON),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384),
                FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=50)
            ]

            schema = CollectionSchema(fields=fields, description="Chunked paper collection")
            self.collection = Collection(name=self.collection_name, schema=schema)

            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024}
            }
            self.collection.create_index(field_name="embedding", index_params=index_params)
            logger.info(f"Created collection {self.collection_name}")

        except Exception as e:
            logger.error(f"Collection setup failed: {e}")
            raise

    def _generate_embedding(self, text: str) -> List[float]:
        try:
            max_length = 512
            truncated_text = " ".join(text.split()[:max_length])
            embedding = self.embedding_model.encode(truncated_text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    def _chunk_text(self, text: str, chunk_size: int = 5000, overlap: int = 200) -> List[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks

    def store_paper(self, paper_data: Dict) -> List[str]:
        try:
            content = paper_data.get("sections", "")
            if isinstance(content, list):
                content = "\n".join(content)
            elif isinstance(content, dict):
                content = "\n".join([f"{k}\n{v}" for k, v in content.items()])
            elif not isinstance(content, str):
                content = str(content)

            chunks = self._chunk_text(content)
            chunk_ids = []

            for idx, chunk in enumerate(chunks):
                embedding = self._generate_embedding(chunk)
                data = {
                    "paper_id": str(paper_data.get("paper_id", "")),
                    "paper_url": str(paper_data.get("paper_url", "")),
                    "title": str(paper_data.get("title", "")),
                    "abstract": str(paper_data.get("abstract", "")),
                    "year": str(paper_data.get("year", "")),
                    "content": str(chunk),
                    "chunk_index": idx,
                    "authors": paper_data.get("authors", []) or [],
                    "citations": paper_data.get("citations", []) or [],
                    "embedding": embedding,
                    "created_at": datetime.utcnow().isoformat(),
                }
                result = self.collection.insert([data])
                chunk_ids.append(str(result.primary_keys[0]))

            self.collection.flush()
            logger.info(f"Stored {len(chunks)} chunks for paper {paper_data.get('paper_id')}")
            return chunk_ids

        except Exception as e:
            logger.error(f"Failed to store paper chunks: {e}")
            raise

    def search_papers(self, query: str, limit: int = 10, filter_expr: Optional[str] = None) -> List[Dict]:
        try:
            query_embedding = self._generate_embedding(query)
            self.collection.load()

            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 10}
            }

            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=limit,
                expr=filter_expr,
                output_fields=[
                    "paper_id", "title", "abstract", "content", "chunk_index",
                    "authors", "citations", "year", "paper_url"
                ]
            )

            papers = []
            seen_ids = set()

            for hits in results:
                for hit in hits:
                    doc = hit.entity.to_dict()
                    paper_id = doc.get("paper_id", "")
                    if paper_id and paper_id not in seen_ids:
                        doc["score"] = hit.distance
                        papers.append(doc)
                        seen_ids.add(paper_id)

            return papers

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
        finally:
            self.collection.release()

    def get_all_chunks_for_paper(self, paper_id: str) -> List[Dict]:
        try:
            self.collection.load()
            results = self.collection.query(
                expr=f'paper_id == "{paper_id}"',
                output_fields=[
                    "chunk_index", "content", "paper_id", "title", "abstract", 
                    "authors", "citations", "year", "paper_url", "created_at"
                ]
            )
            # Sort by chunk index to preserve original order
            return sorted(results, key=lambda x: x["chunk_index"])
        except Exception as e:
            logger.error(f"Failed to retrieve chunks: {e}")
            raise
        finally:
            self.collection.release()
