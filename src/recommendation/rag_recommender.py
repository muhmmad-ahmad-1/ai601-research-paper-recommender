import logging
from typing import List, Dict, Optional
from transformation.db_utils import DBUtils
import json
import google.generativeai as genai
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGRecommender:
    """RAG-based paper recommendation system using Zilliz, Supabase, and Gemini."""
    
    def __init__(self, collection_name: str = "paper_embeddings"):
        load_dotenv()
        self.db_utils = DBUtils()
        self.collection = self.db_utils.create_milvus_collection(collection_name, dimension=1024)
        self.supabase = self.db_utils.supabase_client
        self.embedding_model = SentenceTransformer("thenlper/gte-large")
        
        # Initialize Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        
    def search_papers(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for relevant papers using vector similarity search.
        
        Args:
            query: User query string
            top_k: Number of results to return
            
        Returns:
            List of dictionaries containing paper chunks and metadata
        """
        # Get query embedding
        query_embedding = self._get_query_embedding(query)
        
        # Search in Zilliz
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10},
        }
        
        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["id", "paper_id", "section_id", "chunk_id"]
        )
        
        # Process results and fetch additional metadata
        recommendations = []
        for hits in results:
            for hit in hits:
                zilliz_id = hit.id  # This is the primary key in Zilliz
                paper_id = hit.entity.get('paper_id')
                section_id = hit.entity.get('section_id')
                chunk_id = hit.entity.get('chunk_id')
                
                # Fetch paper metadata from Supabase
                paper_metadata = self._get_paper_metadata(paper_id)
                if not paper_metadata:
                    continue
                
                # Get section content if this is a section chunk
                section_content = None
                if section_id != 'full_paper':
                    section_content = self._get_section_content(paper_metadata.get('object_path'), section_id)
                
                recommendations.append({
                    'zilliz_id': zilliz_id,
                    'paper_id': paper_id,
                    'section_id': section_id,
                    'chunk_id': chunk_id,
                    'title': paper_metadata.get('title'),
                    'abstract': paper_metadata.get('abstract'),
                    'summary': paper_metadata.get('summary'),
                    'url': paper_metadata.get('pdf_url'),
                    'section_content': section_content,
                    'similarity_score': hit.score
                })
        
        return recommendations
    
    def _get_paper_metadata(self, paper_id: str) -> Optional[Dict]:
        """
        Fetch paper metadata from Supabase papers table.
        
        Args:
            paper_id: UUID of the paper
            
        Returns:
            Dictionary containing paper metadata or None if not found
        """
        try:
            response = self.supabase.table('papers').select('*').eq('paper_id', paper_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching paper metadata for {paper_id}: {e}")
            return None
    
    def _get_section_content(self, object_path: Optional[str], section_id: str) -> Optional[str]:
        """
        Retrieve section content from Supabase object storage.
        
        Args:
            object_path: Path to the paper JSON in object storage
            section_id: UUID of the section
            
        Returns:
            Section content as string or None if not found
        """
        if not object_path:
            return None
            
        try:
            # First get the section type from sections table
            section_response = self.supabase.table('sections').select('section_type').eq('section_id', section_id).execute()
            if not section_response.data:
                return None
                
            section_type = section_response.data[0]['section_type']
            
            # Get the JSON from object storage
            bucket_name = object_path.split('/')[0]
            file_path = '/'.join(object_path.split('/')[1:])
            
            response = self.supabase.storage.from_(bucket_name).download(file_path)
            if not response:
                return None
                
            paper_data = json.loads(response.decode('utf-8'))
            return paper_data.get('sections', {}).get(section_type)
            
        except Exception as e:
            logger.error(f"Error retrieving section content for section {section_id}: {e}")
            return None
    
    def generate_summary(self, query: str, recommendations: List[Dict]) -> List[Dict]:
        """
        Generate summaries for recommended papers using Gemini.
        
        Args:
            recommendations: List of paper recommendations with chunks and metadata
            
        Returns:
            List of recommendations with added summaries
        """
        for rec in recommendations:
            # Prepare content for summarization
            content_parts = [
                f"Title: {rec['title']}",
                f"Abstract: {rec['abstract']}",
            ]
            
            # Add section content if available
            if rec.get('section_content'):
                content_parts.append(f"Relevant Section: {rec['section_content']}")
            
            content = "\n".join(content_parts)
            
            # Prepare prompt for Gemini
            prompt = f"""Given the following research paper information and the user's query, provide a concise summary that explains why this paper is relevant to the user's query:

{content}

User Query: {query}

Please provide:
1. A brief summary of why this paper is relevant
2. Key insights from the paper
3. The paper's contribution to the field

Keep the response concise and focused on relevance to the query. If the paper is not relevant to the query tell the user that NO RELEVANT PAPERS WERE FOUND."""

            try:
                # Call Gemini
                response = self.gemini_model.generate_content(prompt)
                if 'NO RELEVANT PAPERS WERE FOUND' in response.text:
                    recommendations.remove(rec)
                    continue
                if response.text:
                    rec['generated_summary'] = response.text
                else:
                    rec['generated_summary'] = "Summary generation failed. Please refer to the paper directly."
                
            except Exception as e:
                logger.error(f"Error generating summary for paper {rec['paper_id']}: {e}")
                rec['generated_summary'] = "Summary generation failed. Please refer to the paper directly."
        
        return recommendations
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """
        Get embedding for the query using the same model as paper embeddings.
        
        Args:
            query: User query string
            
        Returns:
            List of floats representing the query embedding
        """
        try:
            # Generate embedding using the same model as paper embeddings
            embedding = self.embedding_model.encode(query, show_progress_bar=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise
    
    def get_recommendations(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Main method to get paper recommendations with summaries.
        
        Args:
            query: User query string
            top_k: Number of results to return
            
        Returns:
            List of recommendations with summaries and paper links
        """
        # Search for relevant papers
        recommendations = self.search_papers(query, top_k)

        # Generate summaries
        recommendations_with_summaries = self.generate_summary(query, recommendations)

        return recommendations_with_summaries 
