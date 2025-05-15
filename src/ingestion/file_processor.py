import os
import re
import shutil
import tarfile
from pathlib import Path
from typing import Dict, List, Any


class FileProcessor:
    """Handles file operations for downloading, extracting, and organizing LaTeX files."""
    
    def __init__(self, output_dir: str = "papers_latex", logger = None):
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        self.logger = logger
    
    def extract_tar(self, arxiv_id: str) -> bool:
        """Extract a .tar.gz file for a paper.
        
        Args:
            arxiv_id (str): arXiv ID of the paper
            
        Returns:
            bool: True if extraction succeeded, False otherwise
        """
        tar_path = os.path.join(self.output_dir, f"{arxiv_id}.tar.gz")
        extract_path = os.path.join(self.output_dir, f"temp_{arxiv_id}")
        
        if not os.path.exists(extract_path):
            try:
                with tarfile.open(tar_path, "r:gz") as tar:
                    tar.extractall(path=extract_path)
                self.logger.info(f"Extracted paper {arxiv_id} to {extract_path}")
                return True
            except (tarfile.ReadError, tarfile.CompressionError, EOFError, FileNotFoundError) as e:
                self.logger.error(f"Failed to extract paper {arxiv_id}: {e}")
                return False
        return True
    
    def organize_files(self, arxiv_id: str) -> Dict[str, Any]:
        """Organize .tex, .bbl, and .bib files for a paper.
        
        Args:
            arxiv_id (str): arXiv ID of the paper
            
        Returns:
            Dict[str, Any]: File organization info
        """
        root_path = Path(os.path.join(self.output_dir, f"temp_{arxiv_id}"))
        filtered_path = Path(os.path.join(self.output_dir, arxiv_id))
        filtered_path.mkdir(parents=True, exist_ok=True)
        
        file_info = {"tex_file_count": 0, "citation_files": [], "dest": None}
        
        for ext in (".tex", ".bib", ".bbl"):
            for file in root_path.rglob(f"*{ext}"):
                dest = filtered_path / file.name
                shutil.copy(file, dest)
                if ext == ".tex":
                    file_info["tex_file_count"] += 1
                    file_info["dest"] = file.name
                else:
                    file_info["citation_files"].append(file.name)
        
        return file_info
    
    def cleanup(self, arxiv_id: str) -> None:
        """Clean up temporary files and folders.
        
        Args:
            arxiv_id (str): arXiv ID of the paper
        """
        try:
            shutil.rmtree(os.path.join(self.output_dir, f"temp_{arxiv_id}"))
            os.remove(os.path.join(self.output_dir, f"{arxiv_id}.tar.gz"))
            self.logger.info(f"Deleted temp folder and tar file for {arxiv_id}")
        except FileNotFoundError:
            pass
    
    def clean_tex_content(self, tex_content: str) -> str:
        """Clean LaTeX content by removing comments and figures.
        
        Args:
            tex_content (str): Raw LaTeX content
            
        Returns:
            str: Cleaned LaTeX content
        """
        tex_content = re.sub(r'^\s*%.*$', '', tex_content, flags=re.MULTILINE)
        
        figure_patterns = [
            r'\\begin{figure.*?\\end{figure}',
            r'\\begin{wrapfigure.*?\\end{wrapfigure}',
            r'\\includesvg(\[.*?\])?{.*?}',
            r'\\includegraphics(\[.*?\])?{.*?}'
        ]
        
        for pattern in figure_patterns:
            tex_content = re.sub(pattern, '', tex_content, flags=re.DOTALL)
        
        tex_content = re.sub(r'^\s*\n', '', tex_content, flags=re.MULTILINE)
        return tex_content
    
    def process_tex_files(self, arxiv_id: str, file_info: Dict[str, Any]) -> None:
        """Process and combine LaTeX files.
        
        Args:
            arxiv_id (str): arXiv ID of the paper
            file_info (Dict[str, Any]): File organization info
        """
        folder_path = os.path.join(self.output_dir, arxiv_id)
        
        if file_info["tex_file_count"] > 1:
            self._create_combined_tex_file(arxiv_id, folder_path, file_info)
        else:
            self._clean_single_tex_file(arxiv_id, folder_path, file_info)
    
    def _create_combined_tex_file(self, arxiv_id: str, folder_path: str, file_info: Dict[str, Any]) -> None:
        """Create a combined LaTeX file from multiple files."""
        tex_files = [f for f in Path(folder_path).iterdir() if f.suffix == '.tex']
        
        main_tex_file = None
        for tex_file in tex_files:
            with open(tex_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '\\documentclass' in content:
                    main_tex_file = tex_file
                    main_filename = tex_file.name.split(".")[0]
                    break
        
        if not main_tex_file:
            self.logger.error(f"No main LaTeX file found for {arxiv_id}")
            return
        
        tex_content_dict = self._load_tex_files(tex_files)
        main_tex_content = tex_content_dict[main_filename]
        
        input_pattern = re.compile(r'\\input{([^}]+)}')
        include_pattern = re.compile(r'\\include{([^}]+)}')
        
        main_tex_content = input_pattern.sub(
            lambda m: self._handle_input_include(m, tex_content_dict), 
            main_tex_content
        )
        main_tex_content = include_pattern.sub(
            lambda m: self._handle_input_include(m, tex_content_dict), 
            main_tex_content
        )
        
        combined_tex_path = os.path.join(folder_path, 'combined_output.tex')
        with open(combined_tex_path, 'w', encoding='utf-8') as f:
            f.write(main_tex_content)
        
        file_info["dest"] = "combined_output.tex"
        self.logger.info(f"Created combined tex file for {arxiv_id}")
    
    def _clean_single_tex_file(self, arxiv_id: str, folder_path: str, file_info: Dict[str, Any]) -> None:
        """Clean a single LaTeX file."""
        fpath = os.path.join(folder_path, file_info['dest'])
        
        with open(fpath, 'r', encoding='utf-8') as f:
            tex_content = f.read()
        
        cleaned_content = self.clean_tex_content(tex_content)
        
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        self.logger.info(f"Cleaned single tex file for {arxiv_id}")
    
    def _load_tex_files(self, tex_files: List[Path]) -> Dict[str, str]:
        """Load and clean LaTeX files."""
        tex_content_dict = {}
        for tex_file in tex_files:
            with open(tex_file, 'r', encoding='utf-8') as f:
                raw_content = f.read()
                cleaned_content = self.clean_tex_content(raw_content)
                tex_content_dict[tex_file.stem] = cleaned_content
        return tex_content_dict
    
    def _handle_input_include(self, match: re.Match, tex_content_dict: Dict[str, str]) -> str:
        """Handle \\input and \\include commands."""
        file_path = match.group(1).strip()
        file_name = os.path.basename(file_path)
        if file_name.endswith('.tex'):
            file_name = file_name.replace('.tex', '')
        return tex_content_dict.get(file_name, "")