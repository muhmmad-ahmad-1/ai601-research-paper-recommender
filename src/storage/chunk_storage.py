import logging
from typing import List, Dict
from ..transformation.db_utils import DBUtils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChunkStorage:
    """Stores section/chunk embeddings in Milvus."""
    
    def __init__(self, collection_name: str = "paper_embeddings"):
        self.db_utils = DBUtils()
        self.collection = self.db_utils.create_milvus_collection(collection_name, dimension=1024)
    
    def store_chunks(self, chunks: List[Dict]) -> None:
        """Store chunks in Milvus.
        
        Args:
            chunks: Chunk embedding records
        """
        insert_result = self.collection.insert(chunks)
        logger.info(f"Stored {len(chunks)} chunks in Milvus")
        primary_keys = insert_result.primary_keys
        return primary_keys
    
    def store_section_embedding_ids(self, section_records: List[Dict[str, str]], embedding_ids: List[str]) -> None:
        """
        Updates the sections table with corresponding embedding IDs.

        Args:
            section_records: List of dicts with 'paper_id' and 'section_id' as keys.
            embedding_ids: List of Milvus primary keys (embedding IDs) to be stored.
        """
        assert len(section_records) == len(embedding_ids), "Mismatch in length of records and embedding IDs"

        for record, eid in zip(section_records, embedding_ids):
            self.db_utils.update_postgres(
                table_name="sections",
                row={"paper_id": record["paper_id"], "section_id": record["section_id"]},
                data={"embedding_id": eid},
                pk=["paper_id", "section_id"]
            )
