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
        self.collection.insert(chunks)
        logger.info(f"Stored {len(chunks)} chunks in Milvus")