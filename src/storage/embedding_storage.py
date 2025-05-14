import logging
from typing import List, Dict
from ..transformation.db_utils import DBUtils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingStorage:
    """Stores embeddings in Milvus."""
    
    def __init__(self, collection_name: str = "paper_embeddings"):
        self.db_utils = DBUtils()
        self.collection = self.db_utils.create_milvus_collection(collection_name, dimension=768)
    
    def store_embeddings(self, embeddings: List[Dict]) -> None:
        """Store embeddings in Milvus.
        
        Args:
            embeddings: Embedding records
        """
        self.collection.insert(embeddings)
        logger.info(f"Stored {len(embeddings)} embeddings in Milvus collection {self.collection.name}")