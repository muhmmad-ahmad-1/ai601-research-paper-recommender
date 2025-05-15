import re
import os
import bibtexparser
from typing import Dict, List, Optional

class PaperParser:
    """Parses LaTeX files to extract sections and citations."""
    
    def __init__(self, logger=None):
        self.logger = logger
        
    def parse_tex(self, tex_file_path: str, paper_data: Dict) -> Optional[Dict]:
        """Parse LaTeX file to extract sections and citations.
        
        Args:
            tex_file_path (str): Path to the LaTeX file
            paper_data (Dict): Existing paper metadata
            
        Returns:
            Optional[Dict]: Updated paper data with sections and citations
        """
        try:
            with open(tex_file_path, 'r', encoding='utf-8') as file:
                tex_content = file.read()
        except UnicodeDecodeError as e:
            self.logger.error(f"Error decoding file {tex_file_path}: {e}")
            return None
        
        section_pattern = r'\\section\*?{(.*?)}(.*?)(?=\\section\*?{|\\Z)'
        sections = re.findall(section_pattern, tex_content, flags=re.DOTALL)
        
        section_dict = {}
        paper_data['tables'] = []
        
        for section_name, content in sections:
            section_dict[section_name] = content.strip()
            
            table_pattern = r'\\begin{table}(.*?)\\end{table}'
            tables = re.findall(table_pattern, content, flags=re.DOTALL)
            if tables:
                paper_data['tables'].extend(tables)
            
            section_dict[section_name] = re.sub(
                table_pattern, 
                '', 
                section_dict[section_name], 
                flags=re.DOTALL
            )
        
        paper_data["sections"] = section_dict
        
        if section_dict:
            last_section = list(section_dict.keys())[-1]
            concluding_remarks, citations = self._extract_citations(
                section_dict[last_section],
                paper_data['paper_id'],
                paper_data.get('citation_files', [])
            )
            paper_data['sections'][last_section] = concluding_remarks
            paper_data['citations'] = citations
        
        return paper_data
    
    def _extract_citations(self, tex_content: str, arxiv_id: str, citation_files: List[str]) -> tuple[str, List[Dict]]:
        """Extract citations from LaTeX content and citation files.
        
        Args:
            tex_content (str): LaTeX content
            arxiv_id (str): arXiv ID of the paper
            citation_files (List[str]): List of citation file names
            
        Returns:
            tuple[str, List[Dict]]: Cleaned content and list of citations
        """
        citations = []
        base_path = os.path.join("papers_latex", arxiv_id)
        
        for citation_file in citation_files:
            fpath = os.path.join(base_path, citation_file)
            if citation_file.endswith('.bib') and os.path.exists(fpath):
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        bib_content = bibtexparser.load(f)
                    for entry in bib_content.entries:
                        title = entry.get('title', '').strip()
                        if title:
                            citations.append({
                                'key': entry.get('ID', ''),
                                'title': title
                            })
                except Exception as e:
                    self.logger.warning(f"Failed to parse .bib file {citation_file}: {e}")
        
        if not citations:
            for citation_file in citation_files:
                fpath = os.path.join(base_path, citation_file)
                if citation_file.endswith('.bbl') and os.path.exists(fpath):
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        entries = re.split(r'\\bibitem\{(.+?)\}', content)[1:]
                        for i in range(0, len(entries), 2):
                            key = entries[i].strip()
                            body = entries[i + 1].strip()
                            author_match = re.match(r'^(.*?)\\newblock', body, re.DOTALL)
                            authors = author_match.group(1).strip().replace('\n', ' ') if author_match else None
                            title_match = re.search(r'\\newblock\s+(.*?)\\newblock', body, re.DOTALL)
                            title = title_match.group(1).strip().replace('\n', ' ') if title_match else None
                            year_match = re.search(r'(\d{4})\.', body)
                            year = year_match.group(1) if year_match else None
                            citations.append({
                                "key": key,
                                "authors": authors,
                                "title": title,
                                "year": year
                            })
                    except Exception as e:
                        self.logger.warning(f"Failed to parse .bbl file {citation_file}: {e}")
        
        if not citations:
            env_match = re.search(
                r'\\begin{thebibliography}.*?\\end{thebibliography}',
                tex_content,
                re.DOTALL
            )
            if env_match:
                bib_content = env_match.group(0)
                bibitem_pattern = r'\\bibitem\s*(?:\[.*?\])?\s*{([^}]+)}\s*([^\\]+)'
                entries = re.findall(bibitem_pattern, bib_content, flags=re.DOTALL)
                for key, content in entries:
                    title_match = re.search(r'{\s*([^}]+)\s*}', content)
                    if title_match:
                        title = title_match.group(1).strip()
                        citations.append({'key': key, 'title': title})
        
        self.logger.info(f"Extracted {len(citations)} citations for {arxiv_id}")
        return tex_content, citations