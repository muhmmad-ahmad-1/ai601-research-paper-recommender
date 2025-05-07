import json
from typing import Dict, List, Optional
import numpy as np
import openrouter
from .database import DatabaseManager

class DataLake:
    def __init__(self):
        self.db = DatabaseManager()
        self.openrouter_client = openrouter.Client(api_key=openrouter.api_key)
    
    def process_paper(self, paper_data: Dict) -> None:
        """Process a single paper and store all its data"""
        try:
            # 1. Store paper metadata
            paper_id = self.db.store_paper(paper_data)
            
            # 2. Store authors
            self.db.store_authors(paper_id, paper_data['authors'])
            
            # 3. Store sections
            section_ids = self.db.store_sections(paper_id, paper_data['sections'])
            
            # 4. Store citations (both directions)
            self.db.store_citations(paper_id, paper_data['citations'], paper_data['cited_by'])
            
            # 5. Extract and store keywords
            keywords = self._extract_keywords(paper_data['title'], paper_data['abstract'])
            self.db.store_keywords(paper_id, keywords)
            
            # 6. Create and store embeddings
            self._create_and_store_embeddings(paper_id, paper_data, section_ids)
            
        except Exception as e:
            print(f"Error processing paper {paper_data['paper_id']}: {str(e)}")
            raise
    
    def _extract_keywords(self, title: str, abstract: str) -> List[str]:
        """Extract keywords using OpenRouter API"""
        prompt = f"""
        Extract key technical terms and concepts from the following research paper:
        Title: {title}
        Abstract: {abstract}
        
        Return only the most relevant keywords, separated by commas.
        """
        
        response = self.openrouter_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        
        keywords = response.choices[0].message.content.split(',')
        return [k.strip() for k in keywords]
    
    def _create_embedding(self, text: str) -> np.ndarray:
        """Create embedding using OpenRouter API"""
        response = self.openrouter_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return np.array(response.data[0].embedding)
    
    def _create_and_store_embeddings(self, paper_id: str, paper_data: Dict, section_ids: List[str]) -> None:
        """Create and store embeddings for paper and its sections"""
        # Create embedding for abstract
        abstract_embedding = self._create_embedding(paper_data['abstract'])
        self.db.store_embedding(abstract_embedding, paper_id)
        
        # Create embeddings for each section
        for section_name, section_content in paper_data['sections'].items():
            section_embedding = self._create_embedding(section_content)
            section_id = section_ids[list(paper_data['sections'].keys()).index(section_name)]
            self.db.store_embedding(section_embedding, paper_id, section_id)
    
    def process_jsonl_file(self, file_path: str) -> None:
        """Process all papers in a JSONL file"""
        with open(file_path, 'r') as f:
            for line in f:
                paper_data = json.loads(line)
                self.process_paper(paper_data)
    
    def close(self):
        """Close all connections"""
        self.db.close()
