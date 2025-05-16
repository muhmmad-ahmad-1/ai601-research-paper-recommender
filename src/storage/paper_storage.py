from typing import List, Dict, Tuple
from transformation.db_utils import DBUtils, db_utils
import json


class PaperStorage:
    """Stores paper metadata in Supabase."""
    
    def __init__(self, logger=None):
        self.logger = logger
        self.db_utils = db_utils
    
    def store_papers(self, papers: List[Dict], authors: List[Dict], paper_authors: List[Dict], 
                    keywords: List[Dict], paper_keywords: List[Dict], sections: List[Dict], 
                    citations: List[Dict], paper_id_mapping: Dict) -> Dict:
        """Store papers, authors, keywords, sections, and citations in Supabase.
        
        Args:
            papers: Paper metadata with input_paper_id
            authors: Author metadata
            paper_authors: Paper-author mappings with input_paper_id and author_key
            keywords: Keyword metadata
            paper_keywords: Paper-keyword mappings with input_paper_id and keyword_key
            sections: Section metadata with input_paper_id
            citations: Citation relationships with input/cited_input_paper_id
            paper_id_mapping: Dict to store input_paper_id to UUID mappings
        
        Returns:
            Updated paper_id_mapping
        """
        # Insert authors and retrieve author_id
        author_keys = {a['name'].lower(): None for a in authors}
        existing_info = self.db_utils.fetch_postgres('authors',{})
        author_ids = self.db_utils.insert_postgres('authors', authors, returning='author_id')
        for key, author_id in zip(author_keys.keys(), author_ids):
            author_keys[key] = author_id
        author_keys.update({eo['name'].lower():eo['author_id'] for eo in existing_info})
        
        # Insert keywords and retrieve keyword_id
        keyword_keys = {k['name'].lower(): None for k in keywords}
        # Build deduplicated keyword list from the keys
        deduped_keywords = [{'name': name} for name in keyword_keys.keys()]
        # Ensure deduplication from existing keys in supabase as well
        existing_keywords = self.db_utils.fetch_postgres('keywords',filters={})
        existing_keyword_names = {row["name"] for row in existing_keywords if row.get("name")}
        deduped_keywords = [{'name':name} for name in keyword_keys.keys() if name not in existing_keyword_names]
        if deduped_keywords and len(deduped_keywords):
            keyword_ids = self.db_utils.insert_postgres('keywords', deduped_keywords, returning='keyword_id')
            for key, keyword_id in zip(keyword_keys.keys(), keyword_ids):
                keyword_keys[key] = keyword_id
            keyword_keys.update({
                row["name"].lower(): row["keyword_id"]
                for row in existing_keywords
            })
        else:
            keyword_ids = None
        
        # Insert papers and retrieve paper_id
        papers_for_insert = [{k: v for k, v in p.items() if k != 'input_paper_id'} for p in papers]
        paper_ids = self.db_utils.insert_postgres('papers', papers_for_insert, returning='paper_id')
        for input_id, paper_id in zip([p['input_paper_id'] for p in papers], paper_ids):
            paper_id_mapping[input_id] = str(paper_id)
        
        # Update paper_authors with UUIDs
        paper_authors_updated = [
            {
                'paper_id': paper_id_mapping[pa['input_paper_id']],
                'author_id': author_keys[pa['author_key']],
                'author_order': pa['author_order']
            }
            for pa in paper_authors
            if pa['input_paper_id'] in paper_id_mapping and pa['author_key'] in author_keys
        ]

        # ✅ Deduplicate by (paper_id, author_id)
        seen = set()
        deduped_paper_authors = []
        for pa in paper_authors_updated:
            key = (pa['paper_id'], pa['author_id'])
            if key not in seen:
                seen.add(key)
                deduped_paper_authors.append(pa)

        # Now insert only the unique pairs
        self.db_utils.insert_postgres('paper_authors', deduped_paper_authors)
        self.logger.info('keyword keys',keyword_keys)
        # Update paper_keywords with UUIDs
        if keyword_ids:
            paper_keywords_updated = [
                {
                    'paper_id': paper_id_mapping[pk['input_paper_id']],
                    'keyword_id': keyword_keys[pk['keyword_key']]
                }
                for pk in paper_keywords
                if pk['input_paper_id'] in paper_id_mapping and pk['keyword_key'] in keyword_keys
            ]
            paper_keywords_updated = [
                entry for entry in paper_keywords_updated 
                if entry['paper_id'] is not None and entry['keyword_id'] is not None
            ]

            self.db_utils.insert_postgres('paper_keywords', paper_keywords_updated)
        
        # Update sections with UUIDs
        sections_updated = [
            {
                'paper_id': paper_id_mapping[s['input_paper_id']],
                'section_type': s['section_type'],
                'object_path': s['object_path']
            }
            for s in sections
            if s['input_paper_id'] in paper_id_mapping
        ]
        section_ids = self.db_utils.insert_postgres('sections', sections_updated, returning='section_id')
        
        # Update citations with UUIDs
        citations_updated = [
            {
                'citing_paper_id': paper_id_mapping[c['citing_input_paper_id']],
                'cited_paper_id': paper_id_mapping.get(c['cited_input_paper_id'], None)
            }
            for c in citations
            if c['citing_input_paper_id'] in paper_id_mapping and c['cited_input_paper_id'] in paper_id_mapping
        ]
        # Filter out citations with missing cited_paper_id
        citations_valid = [c for c in citations_updated if c['cited_paper_id'] is not None]
        self.logger.info('valid citations',citations_valid)
        if citations_valid:
            self.db_utils.insert_postgres('citations', citations_valid)
        
        if not 'paper_keywords_updated' in locals():
            paper_keywords_updated = []
        
        self.logger.info(f"Stored {len(papers)} papers, {len(authors)} authors, {len(paper_authors_updated)} paper_authors, "
                    f"{len(keywords)} keywords, {len(paper_keywords_updated)} paper_keywords, {len(sections_updated)} sections, "
                    f"{len(citations_valid)} citations in Supabase")
        return paper_id_mapping

    def store_json(self, paper_ids: List[str], data_json: List[dict]) -> List[str]:
        """
        Stores each paper's JSON data in Supabase object storage and updates
        object_path field in 'papers' and 'sections' tables.

        Args:
            paper_ids: List of UUIDs for the papers.
            data_json: List of paper data dicts (same order as paper_ids).

        Returns:
            List of object storage paths for each uploaded paper.
        """
        if len(paper_ids) != len(data_json):
            raise ValueError("Length of paper_ids and data_json must match.")

        paths = []
        bucket = "paper-jsons"

        for paper_id, json_data in zip(paper_ids, data_json):
            path = f"{paper_id}/paper.json"
            full_path = f"{bucket}/{path}"
            content = json.dumps(json_data).encode("utf-8")

            try:
                # Delete existing file if needed (optional safeguard)
                self.db_utils.supabase_client.storage.from_(bucket).remove([path])

                # Upload JSON file to Supabase Storage
                self.db_utils.supabase_client.storage.from_(bucket).upload(
                    path=path,
                    file=content,
                    file_options={"content-type": "application/json"}
                )

                # Update 'papers' table
                self.db_utils.update_postgres(
                    table_name='papers',
                    row={'paper_id': paper_id},
                    data={'object_path': full_path},
                    pk='paper_id'
                )

                # Update all 'sections' for this paper
                self.db_utils.supabase_client.table('sections') \
                    .update({'object_path': full_path}) \
                    .eq('paper_id', paper_id).execute()

                paths.append(full_path)

            except Exception as e:
                self.logger.error(f"Failed to upload or update paper {paper_id}: {e}")
                paths.append(None)

        self.logger.info(f"Uploaded {len([p for p in paths if p is not None])} paper JSONs and updated DB.")
        return paths


        