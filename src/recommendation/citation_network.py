from typing import List, Dict
from transformation.db_utils import db_utils 
import json

class CitationLogic:
    def fetch_all_citation_graph(self, limit: int = 100) -> List[Dict]:
        query = f"""
        {{
            allPapers(func: has(paper_id), first: {limit}) {{
                uid
                paper_id
                title
                year
                cites {{
                    uid
                    paper_id
                    title
                    year
                }}
            }}
        }}
        """
        res = db_utils.execute_dql_query(query)

        return res

    def fetch_cited_by(self, paper_id: str) -> List[Dict]:
        query = """
        query citedBy($pid: string) {
            citedBy(func: eq(paper_id, $pid)) @recurse(reverse: true) {
                uid
                paper_id
                title
                year
                ~cites {
                    uid
                    paper_id
                    title
                    year
                }
            }
        }
        """
        return db_utils.execute_dql_query(query, variables={"$pid": paper_id}).get("citedBy", [])

    def fetch_cites(self, paper_id: str) -> List[Dict]:
        query = """
        query cites($pid: string) {
            citing(func: eq(paper_id, $pid)) {
                uid
                paper_id
                title
                year
                cites {
                    uid
                    paper_id
                    title
                    year
                }
            }
        }
        """
        citing = db_utils.execute_dql_query(query, variables={"$pid": paper_id}).get("citing", [])
        return citing[0].get("cites", []) if citing else []

    def fetch_neighbors(self, paper_id: str, depth: int = 1) -> List[Dict]:
        query = f"""
        query neighbors($pid: string) {{
            neighbors(func: eq(paper_id, $pid)) @recurse(depth: {depth}) {{
                uid
                paper_id
                title
                year
                cites
                ~cites
            }}
        }}
        """
        return db_utils.execute_dql_query(query, variables={"$pid": paper_id}).get("neighbors", [])

    def search_paper_by_title_or_id(self, query_str: str, limit: int = 5) -> List[Dict]:
        query = f"""
        {{
            papers(func: anyoftext(title, "{query_str}"), first: {limit}) {{
                uid
                paper_id
                title
                year
            }}
        }}
        """
        return db_utils.execute_dql_query(query).get("papers", [])

