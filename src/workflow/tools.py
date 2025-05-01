from typing import Optional, Dict, List
from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
import logging
from src.storage.b2_storage import B2Storage
from src.storage.database import DatabaseManager
from src.ingestion.arxiv_api import ArxivAPI

logger = logging.getLogger(__name__)

class ArxivSearchInput(BaseModel):
    query: str = Field(description="Search query for arXiv papers")
    max_results: int = Field(default=10, description="Maximum number of results to return")

class ArxivSearchTool(BaseTool):
    name = "arxiv_search"
    description = "Search for papers on arXiv"
    args_schema = ArxivSearchInput
    
    def __init__(self, arxiv_api: ArxivAPI):
        self.arxiv_api = arxiv_api
        
    def _run(self, query: str, max_results: int = 10) -> List[Dict]:
        try:
            return self.arxiv_api.search_papers(query, max_results)
        except Exception as e:
            logger.error(f"Error in arXiv search: {str(e)}")
            raise

class PaperStorageInput(BaseModel):
    paper_data: Dict = Field(description="Paper metadata to store")
    pdf_path: Optional[str] = Field(default=None, description="Path to PDF file")

class PaperStorageTool(BaseTool):
    name = "store_paper"
    description = "Store paper metadata and PDF in the database and B2 storage"
    args_schema = PaperStorageInput
    
    def __init__(self, db_manager: DatabaseManager, b2_storage: B2Storage):
        self.db_manager = db_manager
        self.b2_storage = b2_storage
        
    def _run(self, paper_data: Dict, pdf_path: Optional[str] = None) -> Dict:
        try:
            # Store metadata in database
            db_result = self.db_manager.store_paper(paper_data)
            
            # Store PDF in B2 if provided
            b2_result = None
            if pdf_path:
                b2_file_id = self.b2_storage.upload_file(pdf_path)
                b2_result = {"b2_file_id": b2_file_id}
                
            return {
                "database": db_result,
                "storage": b2_result
            }
        except Exception as e:
            logger.error(f"Error storing paper: {str(e)}")
            raise

class PaperRetrievalInput(BaseModel):
    arxiv_id: str = Field(description="arXiv paper ID")

class PaperRetrievalTool(BaseTool):
    name = "get_paper"
    description = "Retrieve paper metadata and PDF from storage"
    args_schema = PaperRetrievalInput
    
    def __init__(self, db_manager: DatabaseManager, b2_storage: B2Storage):
        self.db_manager = db_manager
        self.b2_storage = b2_storage
        
    def _run(self, arxiv_id: str) -> Dict:
        try:
            # Get metadata from database
            metadata = self.db_manager.get_paper(arxiv_id)
            
            # Get PDF URL from B2 if available
            pdf_url = None
            if metadata.get("b2_file_id"):
                pdf_url = self.b2_storage.get_file_url(metadata["b2_file_id"])
                
            return {
                "metadata": metadata,
                "pdf_url": pdf_url
            }
        except Exception as e:
            logger.error(f"Error retrieving paper: {str(e)}")
            raise 