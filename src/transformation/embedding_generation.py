import json
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from datetime import datetime
import uuid 


class EmbeddingGenerator:
    """Generates semantic embeddings for papers."""
    
    def __init__(self, model_name: str = "thenlper/gte-large", logger = None):
        self.model = SentenceTransformer(model_name)
        self.logger = logger
    
    def generate_embeddings(self, input_path: str, paper_id_mapping: Dict) -> List[Dict]:
        """Generate embeddings for papers using UUID paper_id.
        
        Args:
            input_path: Path to JSONL file
            paper_id_mapping: Mapping of input paper_id to UUID
            
        Returns:
            List of embedding records
        """
        entities = []
        paper_ids = []
        with open(input_path, 'r') as f:
            for line in f:
                paper = json.loads(line.strip())
                if 'paper_id' not in paper or paper['paper_id'] not in paper_id_mapping:
                    continue
                text = self._combine_text(paper)
                embedding = self.model.encode(text, show_progress_bar=False).tolist()
                entities.append({
                    "paper_id": paper_id_mapping[paper['paper_id']],
                    "section_id": "full paper",
                    "embedding": embedding,
                    "chunk_id": str(0),
                    "created_at": datetime.utcnow().isoformat()
                })
                paper_ids.append(paper_id_mapping[paper['paper_id']])
        
        self.logger.info(f"Generated {len(entities)} paper embeddings")
        return entities, paper_ids
    
    def _combine_text(self, paper: Dict) -> str:
        """Combine relevant text fields for embedding."""
        parts = [
            paper.get('title', ''),
            paper.get('abstract', ''),
            ' '.join(paper.get('sections', {}).values())
        ]
        return ' '.join([p for p in parts if p])