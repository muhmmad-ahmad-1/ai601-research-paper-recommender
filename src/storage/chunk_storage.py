from typing import List, Dict
from transformation.db_utils import DBUtils, db_utils

class ChunkStorage:
    """Stores section/chunk embeddings in Milvus."""
    
    def __init__(self, collection_name: str = "paper_embeddings", logger=None):
        self.logger = logger
        self.db_utils = db_utils
        self.collection = self.db_utils.create_milvus_collection(collection_name, dimension=1024)
    
    def store_chunks(self, chunks: List[Dict]) -> None:
        """Store chunks in Milvus.
        
        Args:
            chunks: Chunk embedding records
        """
        insert_result = self.collection.insert(chunks)
        self.logger.info(f"Stored {len(chunks)} chunks in Milvus")
        primary_keys = insert_result.primary_keys
        return primary_keys
    
    def store_section_embedding_ids(self, section_records: List[Dict[str, str]], embedding_ids: List[str], chunk_ids: List[str]) -> None:
        """
        Updates the sections table with corresponding embedding IDs.

        Args:
            section_records: List of dicts with 'paper_id' and 'section_id' as keys.
            embedding_ids: List of Milvus primary keys (embedding IDs) to be stored.
            chunk_ids: List of chunk_id strings
        """
        assert len(section_records) == len(embedding_ids) == len(chunk_ids), "Mismatch in length of records and embedding IDs"

        cached = {}

        for record, eid, chunk_id in zip(section_records, embedding_ids, chunk_ids):
            paper_id = record["paper_id"]
            section_id = record["section_id"]

            key = (paper_id, section_id)

            if key not in cached:
                res = self.db_utils.fetch_postgres("sections", {"paper_id": paper_id, "section_id": section_id})
                cached[key] = res[0] if res else None

            record_s = cached[key]
            if not record_s:
                continue  # Skip if not found

            if chunk_id == "1":
                # Update existing row
                self.db_utils.update_postgres(
                    table_name="sections",
                    row={"paper_id": paper_id, "section_id": section_id},
                    data={"embedding_id": eid},
                    pk=["paper_id", "section_id"]
                )
            else:
                # Insert new chunked row
                self.db_utils.insert_postgres(
                    table_name="sections",
                    data={
                        "paper_id": paper_id,
                        "section_id": section_id,
                        "section_type": record_s["section_type"],
                        "object_path": record_s["object_path"],
                        "chunk_id": chunk_id,
                        "embedding_id": eid
                    }
                )
