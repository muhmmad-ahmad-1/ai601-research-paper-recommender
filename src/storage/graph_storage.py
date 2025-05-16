from typing import List, Dict
from transformation.db_utils import DBUtils, db_utils

class GraphStorage:
    """Stores citation graph in Dgraph using DQL."""
    
    def __init__(self,logger=None):
        self.db_utils = db_utils
        self.logger = logger
        self.db_utils.ensure_schema()
    

    def store_graph(self, nodes: List[Dict], edges: List[Dict]) -> None:
        """Store citation graph in Dgraph using DQL.
        
        Args:
            nodes (List[Dict]): Graph nodes
            edges (List[Dict]): Graph edges
        """
        # Step 1: Add all nodes (papers) with blank node identifiers
        paper_uid_map = {}  # Maps paper_id -> generated UID (for citation links)

        for node in nodes:
            uid_placeholder = f"_:paper_{node['paper_id']}"
            paper_obj = {
                "uid": uid_placeholder,
                "dgraph.type": "Paper",
                "paper_id": node["paper_id"],
                "title": node.get("title", ""),
                "year": node.get("year"),
                "authors": node.get("authors", [])
            }

            uids = self.db_utils.execute_dql_mutation(set_obj=paper_obj)
            paper_uid_map[node["paper_id"]] = uids.get(f"paper_{node['paper_id']}")
        
        # Step 2: Add citations as reverse edges (cites)
        for edge in edges:
            src_uid = paper_uid_map.get(edge["source"])
            tgt_uid = paper_uid_map.get(edge["target"])

            if src_uid and tgt_uid:
                edge_obj = {
                    "uid": src_uid,
                    "cites": [{"uid": tgt_uid}]
                }
                self.db_utils.execute_dql_mutation(set_obj=edge_obj)
            else:
                self.logger.warning(f"Missing UID for citation: {edge}")

        self.logger.info(f"Stored graph with {len(nodes)} nodes and {len(edges)} edges in Dgraph")
