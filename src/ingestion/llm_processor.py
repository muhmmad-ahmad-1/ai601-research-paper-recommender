import re
import json
from typing import List, Optional
from pydantic import BaseModel
from langgraph.graph import StateGraph
from .openrouter_api import query_openrouter


class PaperState(BaseModel):
    title: str
    abstract: str
    max_keywords: int = 10
    known_keywords: Optional[List[str]] = None
    known_domains: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    domain: Optional[str] = None
    summary: Optional[str] = None

class LLMProcessor:
    """Handles LLM-based processing for keywords and domains."""
    
    def __init__(self, api_key: str, logger):
        self.api_key = api_key
        self.logger = logger

        # Define the graph using LangGraph
        builder = StateGraph(PaperState)

        builder.add_node("extract_keywords", self.extract_keywords_node)
        builder.add_node("classify_domain", self.classify_domain_node)
        builder.add_node("generate_summary", self.generate_summary_node)

        builder.set_entry_point("extract_keywords")
        builder.add_edge("extract_keywords", "classify_domain")
        builder.add_edge("classify_domain", "generate_summary")

        self.graph = builder.compile()

    def run_agentic_worflow(self, title: str, abstract: str, known_keywords: List[str], known_domains: List[str]):
        """Runs the LangGraph agentic workflow to extract keywords, domain, summary from paper"""
        initial_state = PaperState(
            title=title,
            abstract=abstract,
            known_keywords=known_keywords,
            known_domains=known_domains
        )

        final_state = self.graph.invoke(initial_state)
        # print(final_state)
        return {
            "keywords": final_state["keywords"],
            "domain": final_state["domain"],
            "summary": final_state["summary"]
        }

    def extract_keywords_node(self, state: PaperState) -> PaperState:
        """ LangGraph Node for Agentic worflow to extract keywords """
        state.keywords = self.get_keywords(state.title, state.abstract, state.known_keywords)
        return state

    def classify_domain_node(self, state: PaperState) -> PaperState:
        """ LangGraph Node for Agentic worflow to classify domain """
        state.domain = self.get_domain(state.title, state.abstract, state.known_domains)
        return state

    def generate_summary_node(self, state: PaperState) -> PaperState:
        """ LangGraph Node for Agentic worflow to generate summary """
        state.summary = self.get_summary(state.title, state.abstract)
        return state

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
            f"Known Keywords: {known_kw_str}\n\n"
            f"Title: {title}\n\n"
            f"Abstract: {abstract}"
            f"Keywords should be broad enough such that multiple papers can fit into it but still sufficiently specific.\n"
            "Each keyword should be short (no more than 3-4 words)"
            f'Return the output as JSON dictionary like with the key "keywords": ["keyword1", "keyword2"] and nothing else. DO NOT write ```json <dict> ```. '
        )

        # print(prompt)

        try:
            content = query_openrouter(prompt, self.api_key,self.logger)
            matchh = re.search(r"\{.*\}", content)
            if matchh:
                dict_str = matchh.group(0)
                return json.loads(dict_str)['keywords']
            else:
                self.logger.error("LLM keywords error: No dictionary found in the string")
                return []
            
        except Exception as e:
            self.logger.error(f"LLM keywords error: {e}")
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
            f"Available Domains: {domain_list}\n\n"
            f"Title: {title}\n\n"
            f"Abstract: {abstract} \n"
            f"Domain should be broad enough such that multiple papers can fit into it but not all. For example, representation learning or contrastive learning are valid, but machine learning is not. \n"
            f"The domain should be short (no more than 3-4 words)\n"
            f'Return the output as JSON dictionary like with the key "domain": "domain name" and nothing else. DO NOT write ```json <dict> ```.'
        )

        try:
            return json.loads(query_openrouter(prompt, self.api_key,self.logger).strip())['domain']
        except Exception as e:
            self.logger.error(f"LLM domain classification error: {e}")
            return None

    def get_summary(self, title: str, abstract: str) -> str:
        """Generate a summary using LLM.

        Args:
            title (str): Paper title
            abstract (str): Paper abstract

        Returns:
            str: Generated summary
        """

        prompt = (
            f"Given the following paper title : {title} and abstract: {abstract}, generate a concise and informative summary.\n "
            f"The summary should be of 3-4 sentences max. Focus on what the paper is about and its core contribution.\n "
            f'Return the output as JSON dictionary like with the key "summary": "Here is the summary" and nothing else. DO NOT write ```json <dict> ```.'
        )

        try:
            return json.loads(query_openrouter(prompt, self.api_key,self.logger).strip())['summary']
        except Exception as e:
            self.logger.error(f"LLM summary error: {e}")
            return None
