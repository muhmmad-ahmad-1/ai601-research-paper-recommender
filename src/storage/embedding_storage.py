from typing import List, Dict
from transformation.db_utils import DBUtils, db_utils


class EmbeddingStorage:
    """Stores embeddings in Milvus."""
    
    def __init__(self, collection_name: str = "paper_embeddings", logger=None):
        self.logger = logger
        self.db_utils = db_utils
        self.collection = self.db_utils.create_milvus_collection(collection_name, dimension=1024)
        self.supabase = self.db_utils.supabase_client
    
    def store_embeddings(self, embeddings: List[Dict]) -> None:
        """Store embeddings in Milvus.
        
        Args:
            embeddings: Embedding records
        """
        result = self.collection.insert(embeddings)
        self.logger.info(f"Stored {len(embeddings)} embeddings in Milvus collection {self.collection.name}")
        return result.primary_keys

    def store_embedding_id(self, paper_ids: List[str], embedding_ids: List[str]) -> None:
        """
        Update the embedding_id field in the 'papers' table for each paper_id.

        Args:
            paper_ids: List of paper_id values (primary keys).
            embedding_ids: Corresponding list of embedding_id values.
        """
        if len(paper_ids) != len(embedding_ids):
            raise ValueError("paper_ids and embedding_ids must be the same length")

        for pid, eid in zip(paper_ids, embedding_ids):
            try:
                self.db_utils.update_postgres(
                    table_name="papers",
                    row={"paper_id": pid},
                    data={"embedding_id": eid},
                    pk="paper_id"
                )
            except Exception as e:
                self.logger.error(f"Failed to update embedding_id for paper_id={pid}: {e}")
    
    def store_section_embedding_id(self, section_ids: List[str], paper_ids: List[str], embedding_ids: List[str]) -> None:
        """
        Update the embedding_id field in the 'sections' table using section_id and paper_id as composite keys.

        Args:
            section_ids: List of section_id values (part of composite key).
            paper_ids: List of paper_id values (part of composite key).
            embedding_ids: Corresponding list of embedding_id values.
        """
        if not (len(section_ids) == len(paper_ids) == len(embedding_ids)):
            raise ValueError("section_ids, paper_ids, and embedding_ids must be the same length")

        for sec_id, pid, eid in zip(section_ids, paper_ids, embedding_ids):
            try:
                self.db_utils.update_postgres(
                    table_name="sections",
                    row={"section_id": sec_id, "paper_id": pid},
                    data={"embedding_id": eid},
                    pk=["section_id", "paper_id"]  # assuming your update_postgres handles composite keys
                )
            except Exception as e:
                self.logger.error(f"Failed to update embedding_id for section_id={sec_id}, paper_id={pid}: {e}")

