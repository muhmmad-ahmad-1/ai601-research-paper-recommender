import json
import logging
from typing import List, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from datetime import datetime
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentChunker:
    """Splits paper sections into chunks."""
    
    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5", chunk_size: int = 1500,chunk_overlap: int = 200):
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.model = SentenceTransformer(model_name)
    
    def chunk_content(self, input_path: str, paper_id_mapping: Dict) -> List[Dict]:
        """Split sections, generate embeddings, and return records.
        
        Args:
            input_path: Path to JSONL file
            paper_id_mapping: Mapping of input paper_id to UUID
            
        Returns:
            List of chunk embedding records
        """
        chunks = []
        with open(input_path, 'r') as f:
            for line in f:
                paper = json.loads(line.strip())
                if 'paper_id' not in paper or 'sections' not in paper or paper['paper_id'] not in paper_id_mapping:
                    continue
                paper_id = paper_id_mapping[paper['paper_id']]
                for section_name, content in paper['sections'].items():
                    section_id = paper['section_id'][section_name]
                    split_texts = self.splitter.split_text(content)
                    for i, text in enumerate(split_texts):
                        embedding = self.model.encode(text).tolist()
                        chunks.append({
                            "paper_id": paper_id,
                            "section_id": section_id,
                            "embedding": embedding,
                            "chunk_id": i+1,
                            "created_at": datetime.utcnow().isoformat()
                        })
        
        logger.info(f"Generated {len(chunks)} section chunks")
        return chunks