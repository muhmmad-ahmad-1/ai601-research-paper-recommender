import logging
from typing import List
from .openrouter_api import query_openrouter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMProcessor:
    """Handles LLM-based processing for keywords and domains."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def get_keywords(self, title: str, abstract: str, known_keywords: List[str], max_keywords: int = 10) -> List[str]:
        """Generate keywords using LLM.
        
        Args:
            title (str): Paper title
            abstract (str): Paper abstract
            known_keywords (List[str]): Existing keywords
            max_keywords (int): Maximum number of keywords
            
        Returns:
            List[str]: Generated keywords
        """
        known_kw_str = ", ".join(sorted(known_keywords)) if known_keywords else "None"
        
        prompt = (
            f"Given the following paper title and abstract, extract up to {max_keywords} concise and meaningful research keywords.\n"
            f"Use relevant terms from this list of known keywords if they apply, but feel free to override or add better ones if necessary.\n"
            f"Return a comma-separated list of keywords only.\n\n"
            f"Known Keywords: {known_kw_str}\n\n"
            f"Title: {title}\n\n"
            f"Abstract: {abstract}"
            f"Keywords should be broad enough such that multiple papers can fit into it but still sufficiently specific.\n"
            "Each keyword should be short (no more than 3-4 words)"
        )
        
        try:
            content = query_openrouter(prompt, self.api_key)
            return [kw.strip().lower() for kw in content.split(",") if kw.strip()]
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return []
    
    def get_domain(self, title: str, abstract: str, known_domains: List[str]) -> str:
        """Classify paper into a domain using LLM.
        
        Args:
            title (str): Paper title
            abstract (str): Paper abstract
            known_domains (List[str]): Existing domains
            
        Returns:
            str: Generated domain
        """
        domain_list = ", ".join(sorted(known_domains)) if known_domains else "None"
        
        prompt = (
            "Given the following paper title and abstract, identify the single most relevant research domain from the list below.\n"
            "Choose only one domain from the list if it applies. If none are relevant, suggest one better suited.\n"
            "Return only the domain name, no explanation.\n\n"
            f"Available Domains: {domain_list}\n\n"
            f"Title: {title}\n\n"
            f"Abstract: {abstract} \n"
            f"Domain should be broad enough such that multiple papers can fit into it but not all. For example, representation learning or contrastive learning are valid, but machine learning is not. \n"
            "The domain should be short (no more than 3-4 words)"
        )
        
        try:
            return query_openrouter(prompt, self.api_key)
        except Exception as e:
            logger.error(f"LLM domain classification error: {e}")
            return None