import json
import logging
from typing import List, Dict, Tuple
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaperTransformer:
    """Transforms paper metadata for storage."""
    
    def transform_papers(self, input_path: str) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict], List[Dict], List[Dict], Dict]:
        """Process papers, authors, keywords, sections, and citations.
        
        Args:
            input_path: Path to JSONL file
            
        Returns:
            Tuple of papers, authors, paper_authors, keywords, paper_keywords, sections, citations, 
            and mapping of input paper_id to UUID
        """
        data_json = []
        papers = []
        authors = []
        paper_authors = []
        keywords = []
        paper_keywords = []
        sections = []
        citations = []
        existing_authors = {}  # name -> author data
        existing_keywords = {}  # keyword -> keyword data
        paper_id_mapping = {}  # input paper_id -> UUID (to be populated after insertion)
        
        with open(input_path, 'r') as f:
            for line in f:
                data = json.loads(line.strip())
                if 'paper_id' not in data:
                    continue
                data_json.append(data)
                input_paper_id = data['paper_id']  # e.g., arXiv ID
                # Paper
                date_str = data.get('date', '')
                try:
                    publication_date = datetime.strptime(date_str, '%d-%m-%Y').date().isoformat()
                except ValueError:
                    publication_date = None
                doi = data.get('doi',None)
                if doi == "N/A":
                    doi = None
                arxiv_id = data.get('paper_id',None)
                if arxiv_id == "N/A":
                    arxiv_id = None

                papers.append({
                    'input_paper_id': input_paper_id,  # Temporary for mapping
                    'title': data.get('title', ''),
                    'doi': doi,
                    'publication_date': publication_date,
                    'journal': data.get('journal', None),
                    'conference': data.get('venue', None),
                    'pdf_url': data.get('url', None),
                    'abstract': data.get('abstract', None),
                    'citation_count': data.get('citationCount', 0),
                    'influential_citation_count': data.get('influentialCitationCount',0),
                    'arxiv_id':arxiv_id,
                    'domain': data.get('domain',None),
                    'summary': data.get('summary',None),
                })
                
                # Authors
                for idx, author in enumerate(data.get('authors', [])):
                    author_name = author.get('name', '')
                    if not author_name:
                        continue
                    author_key = author_name.lower()
                    author_h_index = author.get('hIndex',None) if author.get('hIndex',None) != 'N/A' else None
                    citation_count = author.get('citationCount',None) if author.get('citationCount',None) != 'N/A' else None
                    influential_citation_count = author.get('influentialCitationCount',None) if author.get('influentialCitationCount',None) != 'N/A' else None

                    
                    if author_key not in existing_authors:
                        existing_authors[author_key] = {
                            'name': author_name,
                            'affiliation': author.get('affiliation', None),
                            'h_index': author_h_index,
                            'citation_count': citation_count,
                            'influential_citation_count': influential_citation_count,
                            'semanticid': author.get('authorId',None)
                        }
                    paper_authors.append({
                        'input_paper_id': input_paper_id,
                        'author_key': author_key,
                        'author_order': idx + 1
                    })
                
                # Keywords
                for kw in data.get('keywords', []):
                    kw = kw.strip()
                    if not kw:
                        continue
                    kw_key = kw.lower()
                    if kw_key not in existing_keywords:
                        existing_keywords[kw_key] = {'name': kw}
                    paper_keywords.append({
                        'input_paper_id': input_paper_id,
                        'keyword_key': kw_key
                    })
                
                # Sections
                for section_name, content in data.get('sections', {}).items():
                    sections.append({
                        'input_paper_id': input_paper_id,
                        'section_type': section_name,
                        'object_path': None,
                        'chunk_id' : str(1)
                    })
                
                # Citations
                for citation in data.get('citations', []):
                    cited_id = citation.get('paper_id', None)
                    if cited_id:
                        citations.append({
                            'citing_input_paper_id': input_paper_id,
                            'cited_input_paper_id': cited_id
                        })
        
        # Convert author/keyword dicts to lists
        authors = [{'name': data['name'], 'affiliation': data['affiliation'], 
                    'h_index': data['h_index'], 'citation_count': data['citation_count'], 'influential_citation_count':data['influential_citation_count'],'semanticid':data['semanticid']}
                   for data in existing_authors.values()]
        keywords = [{'name': data['name']} for data in existing_keywords.values()]
        
        logger.info(f"Transformed {len(papers)} papers, {len(authors)} authors, {len(keywords)} keywords, "
                    f"{len(sections)} sections, {len(citations)} citations")
        return data_json,papers, authors, paper_authors, keywords, paper_keywords, sections, citations, paper_id_mapping
