import json
import networkx as nx
from typing import Dict, Tuple, List


class CitationGraph:
    """Builds citation graph."""
    
    def __init__(self, logger=None): 
        self.logger = logger
    
    def build_graph(self, input_path: str) -> Tuple[List[Dict], List[Dict]]:
        """Build citation graph from JSONL file.
        
        Args:
            input_path (str): Path to JSONL file
            
        Returns:
            Tuple[List[Dict], List[Dict]]: Nodes and edges
        """
        nodes = []
        edges = []
        with open(input_path, 'r') as f:
            for line in f:
                data = json.loads(line.strip())
                if 'paper_id' in data:
                    nodes.append({
                        'paper_id': data['paper_id'],
                        'title': data.get('title', ''),
                        'year': data.get('year', ''),
                        'authors': [a.get('name', '') for a in data.get('authors', [])]
                    })
                elif 'citation_links' in data:
                    edges.extend([
                        {'source': cited_id, 'target': citing_id}
                        for cited_id, citing_id in data['citation_links'].items()
                    ])
        
        self.logger.info(f"Built graph with {len(nodes)} nodes and {len(edges)} edges")
        return nodes, edges
    
    def compute_metrics(self, nodes: List[Dict], edges: List[Dict]) -> Dict[str, float]:
        """Compute PageRank scores using NetworkX.
        
        Args:
            nodes (List[Dict]): Graph nodes
            edges (List[Dict]): Graph edges
            
        Returns:
            Dict[str, float]: PageRank scores
        """
        G = nx.DiGraph()
        for node in nodes:
            G.add_node(node['paper_id'])
        for edge in edges:
            G.add_edge(edge['source'], edge['target'])
        
        pagerank = nx.pagerank(G, alpha=0.85, max_iter=100)
        self.logger.info(f"Computed PageRank for {len(pagerank)} papers")
        return pagerank