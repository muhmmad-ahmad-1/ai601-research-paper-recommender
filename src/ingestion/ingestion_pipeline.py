import json
from typing import List, Dict, Optional
from .arxiv_client import ArxivClient
from .semantic_scholar_client import SemanticScholarClient
from .supabase_client import SupabaseClient
from .file_processor import FileProcessor
from .paper_parser import PaperParser
from .llm_processor import LLMProcessor
import os
import arxiv
import shutil

# import logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

class IngestionPipeline:
    """Orchestrates the paper ingestion pipeline."""
    
    def __init__(self, output_dir: str = "papers_latex",criterion:str ='relevance', logger=None):
        """Initialize the ingestion pipeline.

        Args:
            output_dir (str): Directory to store downloaded and processed papers
        """
        self.output_dir = output_dir
        self.paper_ids = []
        self.final_tex_files = {}
        self.papers = []
        self.citation_link = {}
        
        self.arxiv_client = ArxivClient(logger)
        self.semantic_scholar_client = SemanticScholarClient(logger)
        self.file_processor = FileProcessor(output_dir, logger)
        self.paper_parser = PaperParser(logger)
        self.llm_processor = LLMProcessor(os.getenv("OPENROUTER_API_KEY"), logger)
        self.supabase_client = SupabaseClient()
        self.criterion = criterion
        self.logger = logger

    def fetch_papers(self, query: Optional[str] = None, num_papers: int = 3) -> None:
        """Fetch paper IDs from arXiv.

        Args:
            query (Optional[str]): Search query
            num_papers (int): Number of papers to fetch
        """
        if query:
            self.paper_ids = self.arxiv_client.search_papers(query, num_papers,criterion=self.criterion)
        else:
            self.paper_ids = self.arxiv_client.fetch_latest_papers(num_papers)

    def deduplicate_papers(self) -> None:
        """Remove papers already in Supabase from the paper ID list."""
        existing_ids = self.supabase_client.get_existing_arxiv_ids()
        original_count = len(self.paper_ids)

        self.paper_ids = [pid for pid in self.paper_ids if pid.split("v")[0] not in existing_ids]
        
        self.logger.info(f"Deduplicated papers: {original_count - len(self.paper_ids)} already exist in Supabase.")


    def download_and_extract(self) -> None:
        """Download and extract papers."""
        valid_ids = []
        for arxiv_id in self.paper_ids:
            if self.arxiv_client.download_paper(arxiv_id, self.output_dir):
                if self.file_processor.extract_tar(arxiv_id):
                    valid_ids.append(arxiv_id)
                else:
                    self.file_processor.cleanup(arxiv_id)
            else:
                self.file_processor.cleanup(arxiv_id)
        self.paper_ids = valid_ids

    def organize_files(self) -> None:
        """Organize LaTeX and citation files."""
        self.final_tex_files = {}
        valid_ids = []
        for arxiv_id in self.paper_ids:
            file_info = self.file_processor.organize_files(arxiv_id)
            if file_info["tex_file_count"] > 0:
                self.final_tex_files[arxiv_id] = file_info
                valid_ids.append(arxiv_id)
            self.file_processor.cleanup(arxiv_id)
        self.paper_ids = valid_ids

    def fetch_metadata(self) -> None:
        """Fetch paper metadata from arXiv and Semantic Scholar."""
        search = arxiv.Search(id_list=self.paper_ids)
        client = arxiv.Client()
        results = list(client.results(search))

        valid_ids = []
        for result in results:
            abstract_cleaned = result.summary.replace('\n', ' ').strip()
            full_id = result.get_short_id()
            base_id = full_id.split('v')[0]
            published_date = result.published

            paper_data = {
                'paper_id': base_id,
                'paper_url': result.entry_id,
                'title': result.title,
                'abstract': abstract_cleaned,
                'year': result.published.year,
                'date': published_date.strftime('%d-%m-%Y')
            }

            additional_data = self.semantic_scholar_client.get_paper_metadata(base_id, result.title)
            paper_data.update(additional_data)

            try:
                if (self.final_tex_files[base_id]['tex_file_count'] < 1 or
                    not result.title or
                    not paper_data.get('authors')):
                    self.logger.warning(f"Invalid paper data for {base_id}")
                    self.file_processor.cleanup(base_id)
                    continue
            except KeyError:
                self.logger.warning(f"Key error ... {base_id}")
                continue

            self.papers.append(paper_data)
            valid_ids.append(base_id)

        self.paper_ids = valid_ids

    def process_files(self) -> None:
        """Process LaTeX files."""
        valid_ids = []
        for arxiv_id in self.paper_ids:
            if arxiv_id in self.final_tex_files:
                self.file_processor.process_tex_files(arxiv_id, self.final_tex_files[arxiv_id])
                valid_ids.append(arxiv_id)
        self.paper_ids = valid_ids

    def parse_papers(self) -> None:
        """Parse papers to extract sections and citations."""
        valid_papers = []
        valid_ids = []
        for paper in self.papers:
            base_id = paper['paper_id']
            filepath = os.path.join(
                self.output_dir,
                base_id,
                self.final_tex_files[base_id]['dest']
            )
            paper_data = self.paper_parser.parse_tex(filepath, paper)
            if paper_data and paper_data.get('sections'):
                valid_papers.append(paper_data)
                valid_ids.append(base_id)
            else:
                self.file_processor.cleanup(base_id)

        self.papers = valid_papers
        self.paper_ids = valid_ids

    def process_cited_papers(self,max_extensions:int = 1) -> None:
        """Process cited papers."""
        cited_papers = []
        original_paper_ids = self.paper_ids.copy()

        for paper in self.papers:
            arxiv_id = paper['paper_id']
            citations = self.semantic_scholar_client.get_cited_papers(arxiv_id, paper['title'])
            self.paper_ids = [c.get('arxivId') for c in citations]
            self.deduplicate_papers()
            citations = [c for c in citations if c.get('arxivId') in self.paper_ids ]
            self.paper_ids = original_paper_ids.copy()
            for citation in citations[:max_extensions]:
                cited_arxiv_id = citation.get('arxivId')
                if cited_arxiv_id and cited_arxiv_id not in self.paper_ids:
                    self.citation_link[cited_arxiv_id] = arxiv_id
                    cited_papers.append({
                        'paper_id': cited_arxiv_id,
                        'title': citation.get('title', '')
                    })
                    continue

                title = citation.get('title', '')
                if not title:
                    continue

                cited_arxiv_id = self.arxiv_client.search_by_title(title)
                if cited_arxiv_id and cited_arxiv_id not in self.paper_ids:
                    self.citation_link[cited_arxiv_id] = arxiv_id
                    cited_papers.append({
                        'paper_id': cited_arxiv_id,
                        'title': title
                    })
                    self.logger.info(f"Found cited paper: {cited_arxiv_id}")
        papers = self.papers.copy()
        self.papers = []
        if cited_papers:
            self.paper_ids = [p['paper_id'] for p in cited_papers]
            self.download_and_extract()
            self.organize_files()
            self.fetch_metadata()
            self.process_files()
            self.parse_papers()
        self.cited_paper_ids = self.paper_ids.copy()
        self.paper_ids = original_paper_ids
        papers.extend(self.papers)
        self.papers = papers.copy()

    def process_citing_papers(self,max_extensions:int = 1) -> None:
        """Process citing papers."""
        citing_papers = []
        original_paper_ids = self.paper_ids.copy()

        for paper in self.papers:
            arxiv_id = paper['paper_id']
            citations = self.semantic_scholar_client.get_citing_papers(arxiv_id, paper['title'])
            self.paper_ids = [c.get('arxivId') for c in citations]
            self.deduplicate_papers()
            citations = [c for c in citations if c.get('arxivId') in self.paper_ids ]
            self.paper_ids = original_paper_ids.copy()
            for citation in citations[:max_extensions]:
                cited_arxiv_id = citation.get('arxivId')
                if cited_arxiv_id and cited_arxiv_id not in self.paper_ids:
                    self.citation_link[cited_arxiv_id] = arxiv_id
                    citing_papers.append({
                        'paper_id': cited_arxiv_id,
                        'title': citation.get('title', '')
                    })
                    continue

                title = citation.get('title', '')
                if not title:
                    continue

                cited_arxiv_id = self.arxiv_client.search_by_title(title)
                if cited_arxiv_id and cited_arxiv_id not in self.paper_ids:
                    self.citation_link[cited_arxiv_id] = arxiv_id
                    citing_papers.append({
                        'paper_id': cited_arxiv_id,
                        'title': title
                    })
                    self.logger.info(f"Found citing paper: {cited_arxiv_id}")
        papers = self.papers.copy()
        self.papers = []
        if citing_papers:
            self.paper_ids = [p['paper_id'] for p in citing_papers]
            self.download_and_extract()
            self.organize_files()
            self.fetch_metadata()
            self.process_files()
            self.parse_papers()
        self.citing_paper_ids = self.paper_ids.copy()
        self.paper_ids = original_paper_ids
        papers.extend(self.papers)
        self.papers = papers.copy()

    def enrich_paper_metadata(self) -> None:
        """Enrich papers with keywords and domain name and summary."""
        known_keywords = self.supabase_client.get_existing_keywords()
        known_domains = self.supabase_client.get_existing_domains()
        
        self.logger.info("Went into enrichment phase")
        for i, paper in enumerate(self.papers):
            if not paper.get('paper_id'):
                continue
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")
            if not title or not abstract:
                self.logger.warning(f"Missing title or abstract for paper {paper['paper_id']}")
                continue

            metadata = self.llm_processor.run_agentic_worflow(title, abstract, known_keywords, known_domains)
            keywords, domain, summary = metadata['keywords'], metadata['domain'], metadata['summary']


            if keywords:
                paper["keywords"] = keywords
                self.logger.info(f"Generated keywords for paper {paper['paper_id']}")
          
            if domain:
                paper["domain"] = domain
                self.logger.info(f"Generated domain for paper {paper['paper_id']}")

            if summary:
                paper["summary"] = summary
                self.logger.info(f"Generated summary for paper {paper['paper_id']}")
    
    def save_papers(self, output_path: str = "parsed_papers.jsonl") -> None:
        """Save processed papers to JSONL file.

        Args:
            output_path (str): Path to save the JSONL file
        """
        with open(output_path, "w") as f:
            for paper in self.papers:
                f.write(json.dumps(paper) + "\n")
        self.logger.info(f"Saved parsed data at: {output_path}")
    
    def delete_latex(self):
        """Delete downloaded and extracted LaTeX directories."""
        shutil.rmtree(self.output_dir)
        # all_ids = set(self.paper_ids)
        # if hasattr(self, 'cited_paper_ids'):
        #     all_ids.update(self.cited_paper_ids)
        # if hasattr(self, 'citing_paper_ids'):
        #     all_ids.update(self.citing_paper_ids)

        # for paper_id in all_ids:
        #     dir_path = os.path.join(self.output_dir, paper_id)
        #     if os.path.isdir(dir_path):
        #         try:
        #             shutil.rmtree(dir_path)
        #             self.logger.info(f"Deleted LaTeX directory for {paper_id}")
        #         except Exception as e:
        #             self.logger.error(f"Failed to delete {dir_path}: {e}")
    
    def run_pipeline(self, query: Optional[str] = None, num_papers: int = 3,max_extentions: int = 5) -> List[Dict]:
        """Run the complete ingestion pipeline.

        Args:
            query (Optional[str]): Search query
            num_papers (int): Number of papers to process

        Returns:
            List[Dict]: Processed papers
        """
        self.paper_ids = []
        self.final_tex_files = {}
        self.papers = []
        self.citation_link = {}
        self.fetch_papers(query, num_papers)
        self.deduplicate_papers()
        self.download_and_extract()
        self.organize_files()
        self.fetch_metadata()
        self.process_files()
        self.parse_papers()
        self.process_cited_papers(max_extentions)
        self.process_citing_papers(max_extentions)
        self.enrich_paper_metadata()
        self.papers.append({"citation_links": self.citation_link})
        self.save_papers()
        self.delete_latex()
        # try:
        #     self.fetch_papers(query, num_papers)
        #     self.download_and_extract()
        #     self.organize_files()
        #     self.fetch_metadata()
        #     self.process_files()
        #     self.parse_papers()
        #     self.process_cited_papers()
        #     self.process_citing_papers()
        #     self.enrich_with_keywords_and_domains()
        #     self.papers.append({"citation_links": self.citation_link})
        #     self.save_papers()
        # except:
        #     return self.papers
        # finally:
        #     self.delete_latex()
        return self.papers
