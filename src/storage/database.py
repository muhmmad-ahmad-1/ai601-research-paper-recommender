import os
from typing import Dict, List, Optional
import uuid
from datetime import datetime
import json
import numpy as np
from supabase import create_client
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseManager:
    def __init__(self):
        # Initialize Supabase client
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase_client = create_client(self.supabase_url, self.supabase_key)
        
        # Initialize Milvus connection
        self.milvus_host = os.getenv("MILVUS_HOST")
        self.milvus_port = os.getenv("MILVUS_PORT")
        connections.connect(
            alias="default",
            host=self.milvus_host,
            port=self.milvus_port
        )
        
        # Initialize Milvus collection
        self._init_milvus_collection()
    
    def _init_milvus_collection(self):
        """Initialize Milvus collection for embeddings"""
        collection_name = "paper_embeddings"
        
        # Define collection schema
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=36),
            FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=36),
            FieldSchema(name="section_id", dtype=DataType.VARCHAR, max_length=36),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536)  # OpenAI embedding dimension
        ]
        
        schema = CollectionSchema(fields=fields, description="Paper and section embeddings")
        
        # Create collection if it doesn't exist
        try:
            collection = Collection(name=collection_name, schema=schema)
        except Exception:
            collection = Collection(name=collection_name, schema=schema)
    
    def store_paper(self, paper_data: Dict) -> str:
        """Store paper metadata in Supabase and return paper_id"""
        paper_record = {
            'paper_id': str(uuid.uuid4()),
            'title': paper_data['title'],
            'doi': None,
            'publication_date': datetime.strptime(paper_data['year'], '%Y').date(),
            'journal': None,
            'conference': None,
            'pdf_url': paper_data['paper_url'],
            'abstract': paper_data['abstract'],
            'citation_count': len(paper_data['cited_by']),
            'object_path': f"paper-content/{paper_data['paper_id']}"
        }
        
        result = self.supabase_client.table('papers').insert(paper_record).execute()
        return result.data[0]['paper_id']
    
    def store_authors(self, paper_id: str, authors: List[str]) -> List[str]:
        """Store authors and return list of author_ids"""
        author_ids = []
        
        for idx, author in enumerate(authors):
            # Check if author exists
            result = self.supabase_client.table('authors').select('author_id').eq('name', author).execute()
            
            if not result.data:
                # Create new author
                author_record = {
                    'name': author,
                    'affiliation': None
                }
                result = self.supabase_client.table('authors').insert(author_record).execute()
                author_id = result.data[0]['author_id']
            else:
                author_id = result.data[0]['author_id']
            
            author_ids.append(author_id)
            
            # Create paper-author relationship
            paper_author_record = {
                'paper_id': paper_id,
                'author_id': author_id,
                'author_order': idx + 1
            }
            self.supabase_client.table('paper_authors').insert(paper_author_record).execute()
        
        return author_ids
    
    def store_sections(self, paper_id: str, sections: Dict) -> List[str]:
        """Store sections and return list of section_ids"""
        section_ids = []
        
        # Upload sections to Supabase Storage
        storage_path = f"paper-content/{paper_id}"
        self.supabase_client.storage.from_("paper-content").upload(
            path=f"{paper_id}/sections.json",
            file=json.dumps(sections).encode()
        )
        
        for section_name, section_content in sections.items():
            section_record = {
                'paper_id': paper_id,
                'section_type': section_name,
                'object_path': f"{storage_path}/sections.json"
            }
            result = self.supabase_client.table('sections').insert(section_record).execute()
            section_ids.append(result.data[0]['section_id'])
        
        return section_ids
    
    def store_citations(self, paper_id: str, citations: List[str], cited_by: List[str]) -> None:
        """Store citations in both directions"""
        # Store papers that this paper cites
        for cited_paper in citations:
            citation_record = {
                'citing_paper_id': paper_id,
                'cited_paper_id': cited_paper,
                'object_path': None
            }
            self.supabase_client.table('citations').insert(citation_record).execute()
        
        # Store papers that cite this paper
        for citing_paper in cited_by:
            citation_record = {
                'citing_paper_id': citing_paper,
                'cited_paper_id': paper_id,
                'object_path': None
            }
            self.supabase_client.table('citations').insert(citation_record).execute()
    
    def store_keywords(self, paper_id: str, keywords: List[str]) -> None:
        """Store keywords and their relationships"""
        for keyword in keywords:
            # Check if keyword exists
            result = self.supabase_client.table('keywords').select('keyword_id').eq('name', keyword).execute()
            
            if not result.data:
                # Create new keyword
                keyword_record = {
                    'name': keyword
                }
                result = self.supabase_client.table('keywords').insert(keyword_record).execute()
                keyword_id = result.data[0]['keyword_id']
            else:
                keyword_id = result.data[0]['keyword_id']
            
            # Create paper-keyword relationship
            paper_keyword_record = {
                'paper_id': paper_id,
                'keyword_id': keyword_id
            }
            self.supabase_client.table('paper_keywords').insert(paper_keyword_record).execute()
    
    def store_embedding(self, embedding: np.ndarray, paper_id: str, section_id: Optional[str] = None) -> None:
        """Store embedding in Milvus"""
        collection = Collection("paper_embeddings")
        collection.insert([{
            "id": str(uuid.uuid4()),
            "paper_id": paper_id,
            "section_id": section_id,
            "embedding": embedding.tolist()
        }])
    
    def close(self):
        """Close database connections"""
        connections.disconnect("default")
