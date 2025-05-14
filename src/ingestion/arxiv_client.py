import requests
import feedparser
import arxiv
import logging
from typing import List
from pathlib import Path
import xml.etree.ElementTree
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArxivClient:
    """Handles interactions with the arXiv API."""
    
    def fetch_latest_papers(self, num_papers: int = 3) -> List[str]:
        """Fetch latest papers from arXiv RSS feed.
        
        Args:
            num_papers (int): Number of papers to fetch
            
        Returns:
            List[str]: List of arXiv IDs
        """
        rss_url = "https://rss.arxiv.org/rss/cs.AI"
        response = requests.get(rss_url)  # disable SSL verification
        feed = feedparser.parse(response.content)
        
        paper_ids = []
        for entry in feed.entries[:num_papers]:
            link = entry.link
            arxiv_id = link.split('/')[-1]
            paper_ids.append(arxiv_id)
            
        logger.info(f"Found {len(paper_ids)} paper IDs: {paper_ids}")
        return paper_ids
    
    def search_papers(self, query: str, max_results: int = 10) -> List[str]:
        """Search papers on arXiv based on query.
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            
        Returns:
            List[str]: List of arXiv IDs
        """
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        client = arxiv.Client()
        results = list(client.results(search))
        
        paper_ids = [result.get_short_id().split('v')[0] for result in results]
        logger.info(f"Found {len(paper_ids)} papers matching query: {paper_ids}")
        return paper_ids
    
    def download_paper(self, arxiv_id: str, output_dir: str) -> bool:
        """Download LaTeX source for a single paper.
        
        Args:
            arxiv_id (str): arXiv ID of the paper
            output_dir (str): Directory to store the downloaded file
            
        Returns:
            bool: True if download succeeded, False otherwise
        """
        src_url = f"https://arxiv.org/e-print/{arxiv_id}"
        response = requests.get(src_url)
        
        if response.status_code == 200:
            file_path = Path(output_dir) / f"{arxiv_id}.tar.gz"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(response.content)
            logger.info(f"Downloaded LaTeX source: {file_path}")
            return True
        else:
            logger.error(f"Failed to download {arxiv_id}, status code: {response.status_code}")
            return False
    
    def search_by_title(self, title: str) -> str:
        """Search arXiv API using paper title.
        
        Args:
            title (str): Paper title
            
        Returns:
            str: arXiv ID if found, None otherwise
        """
        query = f"http://export.arxiv.org/api/query?search_query=ti:\"{title}\"&start=0&max_results=1"
        try:
            resp = requests.get(query)
            resp.raise_for_status()
            root = xml.etree.ElementTree.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entry = root.find("atom:entry", ns)
            if entry is not None:
                id_elem = entry.find("atom:id", ns)
                if id_elem is not None:
                    return id_elem.text.strip().split('/')[-1]
        except Exception as e:
            logger.error(f"arXiv search error: {e}")
        return None