import requests
import time
import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SemanticScholarClient:
    """Handles interactions with the Semantic Scholar API."""
    
    def __init__(self):
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.rate_limit_delay = 1.0
    
    def retry_request(self, method: str, url: str, max_retries: int = 5, backoff_factor: int = 2, **kwargs) -> requests.Response:
        """Generic retry logic for API requests with exponential backoff."""
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.request(method, url, **kwargs)
                if response.status_code == 429:
                    logger.warning("Rate limited. Waiting before retry...")
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.error(f"[Attempt {attempt}] API error: {e}")
                if attempt < max_retries:
                    time.sleep(backoff_factor ** attempt)
                else:
                    logger.error("Max retries exceeded.")
                    raise
    
    def get_paper_metadata(self, arxiv_id: str, paper_title: str = None) -> Dict[str, Any]:
        """Retrieve paper details from Semantic Scholar.
        
        Args:
            arxiv_id (str): arXiv ID of the paper
            paper_title (str, optional): Paper title for verification
            
        Returns:
            Dict[str, Any]: Paper metadata
        """
        query_url = f"{self.base_url}/paper/arXiv:{arxiv_id}"
        params = {
            "fields": "paperId,title,authors.name,authors.authorId,authors.affiliations,year,externalIds,venue,journal,url,doi,citationCount,influentialCitationCount"
        }
        
        try:
            response = self.retry_request("GET", query_url, params=params)
            paper_data = response.json()
            
            if paper_title and paper_data.get('title', '').lower() != paper_title.lower():
                logger.warning(f"Title mismatch: Found '{paper_data.get('title')}'")
            
            author_ids = [a.get("authorId") for a in paper_data.get("authors", []) if a.get("authorId")]
            author_metrics = self.get_author_metrics(author_ids)
            
            authors = [
                {
                    "name": author.get("name", "N/A"),
                    "affiliations": author.get("affiliations", []) or ['N/A'],
                    "authorId": author.get("authorId"),
                    "hIndex": author_metrics.get(author.get("authorId"), {}).get("hIndex", "N/A"),
                    "citationCount": author_metrics.get(author.get("authorId"), {}).get("citationCount", "N/A"),
                    "author_order": author.get("author_order", 0)
                }
                for author in paper_data.get('authors', [])
            ]
            
            return {
                "title": paper_data.get("title", "N/A"),
                "year": paper_data.get("year", "N/A"),
                "venue": paper_data.get("venue", "N/A"),
                "journal": paper_data.get("journal", {}).get("name", "N/A") if paper_data.get("journal") else "N/A",
                "url": paper_data.get("url", "N/A"),
                "semanticId": paper_data.get("paperId", "N/A"),
                "doi": paper_data.get("doi", "N/A"),
                "authors": authors,
                "arxiv_id": arxiv_id,
                "citationCount": paper_data.get("citationCount", 0),
                "influentialCitationCount": paper_data.get("influentialCitationCount", 0),
            }
        except Exception as e:
            logger.error(f"Failed to retrieve paper details: {e}")
            return {}
    
    def get_author_metrics(self, author_ids: List[str]) -> Dict[str, Any]:
        """Get h-index and citation count for authors.
        
        Args:
            author_ids (List[str]): List of author IDs
            
        Returns:
            Dict[str, Any]: Author metrics
        """
        if not author_ids:
            return {}
        
        url = f"{self.base_url}/author/batch"
        params = {'fields': 'name,hIndex,citationCount'}
        payload = {"ids": author_ids}
        
        try:
            response = self.retry_request("POST", url, params=params, json=payload)
            authors_data = response.json()
            return {
                author['authorId']: {
                    "name": author.get("name", "N/A"),
                    "hIndex": author.get("hIndex", 0),
                    "citationCount": author.get("citationCount", 0),
                    "affiliations": author.get("affiliations", []) or ['N/A'],
                    "author_order": i + 1
                }
                for i, author in enumerate(authors_data)
            }
        except Exception as e:
            logger.error(f"Failed to fetch author metrics: {e}")
            return {}
    
    def fetch_paper_data(self, arxiv_id: str) -> Dict[str, Any]:
        """Fetch paper data including citations and references.
        
        Args:
            arxiv_id (str): arXiv ID of the paper
            
        Returns:
            Dict[str, Any]: Paper data
        """
        url = f"{self.base_url}/paper/arXiv:{arxiv_id}"
        fields = ",".join([
            "title", "year", "paperId", "externalIds",
            "citations.title", "citations.authors", "citations.year", "citations.url", "citations.paperId", "citations.externalIds",
            "references.title", "references.authors", "references.year", "references.url", "references.paperId", "references.externalIds"
        ])
        params = {"fields": fields}
        time.sleep(self.rate_limit_delay)
        
        try:
            response = self.retry_request("GET", url, params=params)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch paper data: {e}")
            return {}
    
    def extract_paper_info(self, papers: List[Dict], max_results: int = 100) -> List[Dict]:
        """Standardize and enrich paper data.
        
        Args:
            papers (List[Dict]): List of paper data
            max_results (int): Maximum number of results to return
            
        Returns:
            List[Dict]: Enriched paper info
        """
        results = []
        arxiv_count = 0
        for paper in papers:
            arxiv_id = paper.get("externalIds", {}).get("ArXiv")
            if arxiv_id:
                arxiv_count += 1
                results.append({
                    'title': paper.get('title', 'N/A'),
                    'authors': [a.get('name') for a in paper.get('authors', [])],
                    'year': paper.get('year', 'N/A'),
                    'url': paper.get('url', 'N/A'),
                    'semanticId': paper.get('paperId', 'N/A'),
                    'arxivId': arxiv_id
                })
            if arxiv_count >= max_results:
                break
        return results
    
    def get_citing_papers(self, arxiv_id: str, paper_title: str = None, max_results: int = 100) -> List[Dict]:
        """Get papers that cite the given paper.
        
        Args:
            arxiv_id (str): arXiv ID of the paper
            paper_title (str, optional): Paper title for verification
            max_results (int): Maximum number of results
            
        Returns:
            List[Dict]: Citing papers
        """
        data = self.fetch_paper_data(arxiv_id)
        if not data:
            return []
        if paper_title and data.get("title", "").lower() != paper_title.lower():
            logger.warning(f"Title mismatch: Found '{data.get('title')}'")
        return self.extract_paper_info(data.get("citations", []), max_results)
    
    def get_cited_papers(self, arxiv_id: str, paper_title: str = None, max_results: int = 100) -> List[Dict]:
        """Get papers cited by the given paper.
        
        Args:
            arxiv_id (str): arXiv ID of the paper
            paper_title (str, optional): Paper title for verification
            max_results (int): Maximum number of results
            
        Returns:
            List[Dict]: Cited papers
        """
        data = self.fetch_paper_data(arxiv_id)
        if not data:
            return []
        if paper_title and data.get("title", "").lower() != paper_title.lower():
            logger.warning(f"Title mismatch: Found '{data.get('title')}'")
        return self.extract_paper_info(data.get("references", []), max_results)