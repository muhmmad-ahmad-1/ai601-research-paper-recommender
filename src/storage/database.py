import os
from typing import Dict, List, Optional
import uuid
from datetime import datetime
import json
import numpy as np
from supabase import create_client
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType,utility
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class DatabaseManager:
    def __init__(self):
        # Initialize Supabase client
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase_client = create_client(self.supabase_url, self.supabase_key)
        self.uri = os.getenv("MILVUS_URI")
        self.token = os.getenv("MILVUS_TOKEN")
        self.collection_name = "paper_embeddings"
        self.embedding_model_name = "thenlper/gte-base"
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        self.collection = None
        # Initialize Milvus collection
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
                FieldSchema(name="section_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1024),
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=50),
            ]

            schema = CollectionSchema(fields=fields, description="Paper and section embeddings")
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
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise
    
    def store_paper(self, paper_data: Dict) -> str:
        """Store paper metadata in Supabase and return paper_id"""
        paper_record = {
            'title': paper_data['title'],
            'doi': paper_data['doi'] if paper_data.get('doi') else " ",
            'authors': paper_data['authors'],
            'publication_date': datetime.strptime(paper_data['year'], '%Y').date(),
            'journal': paper_data['journal'] if paper_data.get('journal') else " ",
            'conference': paper_data['conference'] if paper_data.get('conference') else " ",
            'keywords': paper_data['keywords'],
            'pdf_url': paper_data['paper_url'],
            'abstract': paper_data['abstract'],
            'citation_count': len(paper_data['cited_by']),
            'object_path': f"paper-content/{paper_data['paper_id']}",
            'arxiv_id': str(paper_data['paper_id'])
        }
        
        result = self.supabase_client.table('papers').insert(paper_record).execute()
        return result.data[0]['paper_id']
    

    def store_embedding(self, embedding: List, paper_id: str, section_id: Optional[str] = None,chunk_id: Optional[str] = None) -> None:
        """Store embedding in Milvus"""
        collection = Collection("paper_embeddings")
        result = collection.insert([{
            "paper_id": paper_id,
            "section_id": section_id if section_id else " ",
            "created_at": datetime.utcnow().isoformat(),
            "embedding": embedding,
            "chunk_id": chunk_id if chunk_id else " "
        }])
        logger.info(f"Inserted {len(result.primary_keys)} embeddings into Milvus")
        return result.primary_keys[0]
    
    def close(self):
        """Close database connections"""
        connections.disconnect("default")


    # def store_authors(self, paper_id: str, authors: List[str]) -> List[str]:
    #     """Store authors and return list of author_ids"""
    #     author_ids = []
        
    #     for idx, author in enumerate(authors):
    #         # Check if author exists
    #         result = self.supabase_client.table('authors').select('author_id').eq('name', author).execute()
            
    #         if not result.data:
    #             # Create new author
    #             author_record = {
    #                 'name': author,
    #                 'affiliation': None
    #             }
    #             result = self.supabase_client.table('authors').insert(author_record).execute()
    #             author_id = result.data[0]['author_id']
    #         else:
    #             author_id = result.data[0]['author_id']
            
    #         author_ids.append(author_id)
            
    #         # Create paper-author relationship
    #         paper_author_record = {
    #             'paper_id': paper_id,
    #             'author_id': author_id,
    #             'author_order': idx + 1
    #         }
    #         self.supabase_client.table('paper_authors').insert(paper_author_record).execute()
        
    #     return author_ids
    
    # def store_sections(self, paper_id: str, sections: Dict) -> List[str]:
    #     """Store sections and return list of section_ids"""
    #     section_ids = []
        
    #     # Upload sections to Supabase Storage
    #     storage_path = f"paper-content/{paper_id}"
    #     self.supabase_client.storage.from_("paper-content").upload(
    #         path=f"{paper_id}/sections.json",
    #         file=json.dumps(sections).encode()
    #     )
        
    #     for section_name, section_content in sections.items():
    #         embeddings = self._generate_embedding(section_content)
    #         embeddings = np.array(embeddings).astype(np.float32).tolist()
    #         # Store embedding in Milvus
    #         self.store_embedding(embeddings, section_name, paper_id)
    #         section_record = {
    #             'paper_id': paper_id,
    #             'section_type': section_name,
    #             'object_path': f"{storage_path}/sections.json"
    #         }
    #         result = self.supabase_client.table('sections').insert(section_record).execute()
    #         section_ids.append(result.data[0]['section_id'])
        
    #     return section_ids
    
    # def store_citations(self, paper_id: str, citations: List[str], cited_by: List[str]) -> None:
    #     """Store citations in both directions"""
    #     # Store papers that this paper cites
    #     for cited_paper in citations:
    #         citation_record = {
    #             'citing_paper_id': paper_id,
    #             'cited_paper_id': cited_paper,
    #             'object_path': None
    #         }
    #         self.supabase_client.table('citations').insert(citation_record).execute()
        
    #     # Store papers that cite this paper
    #     for citing_paper in cited_by:
    #         citation_record = {
    #             'citing_paper_id': citing_paper,
    #             'cited_paper_id': paper_id,
    #             'object_path': None
    #         }
    #         self.supabase_client.table('citations').insert(citation_record).execute()
    
    # def store_keywords(self, paper_id: str, keywords: List[str]) -> None:
    #     """Store keywords and their relationships"""
    #     for keyword in keywords:
    #         # Check if keyword exists
    #         result = self.supabase_client.table('keywords').select('keyword_id').eq('name', keyword).execute()
            
    #         if not result.data:
    #             # Create new keyword
    #             keyword_record = {
    #                 'name': keyword
    #             }
    #             result = self.supabase_client.table('keywords').insert(keyword_record).execute()
    #             keyword_id = result.data[0]['keyword_id']
    #         else:
    #             keyword_id = result.data[0]['keyword_id']
            
    #         # Create paper-keyword relationship
    #         paper_keyword_record = {
    #             'paper_id': paper_id,
    #             'keyword_id': keyword_id
    #         }
    #         self.supabase_client.table('paper_keywords').insert(paper_keyword_record).execute()
