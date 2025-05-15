import logging
from typing import Dict
from transformation import (
    PaperTransformer,
    EmbeddingGenerator,
    CitationGraph,
    ContentChunker
)
from storage import (
    PaperStorage,
    EmbeddingStorage,
    GraphStorage,
    ChunkStorage
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransformationPipeline:
    """Orchestrates transformations and storage for RAG and analytics."""
    
    def __init__(self, input_path: str = "parsed_papers.jsonl"):
        self.input_path = input_path
        self.paper_transformer = PaperTransformer()
        self.embedding_generator = EmbeddingGenerator()
        self.citation_graph = CitationGraph()
        self.content_chunker = ContentChunker()
        self.paper_storage = PaperStorage()
        self.embedding_storage = EmbeddingStorage()
        self.graph_storage = GraphStorage()
        self.chunk_storage = ChunkStorage()
    
    def run_pipeline(self) -> Dict:
        """Run transformations and store results in databases.
        
        Returns:
            Dict: Pipeline results
        """
        # Transform paper metadata
        data_json, papers, authors, paper_authors, keywords, paper_keywords, sections, citations, paper_id_mapping = \
            self.paper_transformer.transform_papers(self.input_path)

        # Store in Supabase and update paper_id_mapping
        paper_id_mapping = self.paper_storage.store_papers(
            papers, authors, paper_authors, keywords, paper_keywords, sections, citations, paper_id_mapping
        )
        
        # Generate and store paper embeddings
        embeddings, paper_ids = self.embedding_generator.generate_embeddings(self.input_path, paper_id_mapping)
        pk = self.embedding_storage.store_embeddings(embeddings)
        self.embedding_storage.store_embedding_id(paper_ids,pk)
        print(len(data_json), len(paper_ids))
        # Store object jsons and update their paths
        self.paper_storage.store_json(paper_ids,data_json)
        
        # Build and store citation graph
        nodes, edges = self.citation_graph.build_graph(self.input_path)
        # Update nodes with UUID paper_id
        nodes = [{**node, 'paper_id': paper_id_mapping.get(node['paper_id'], node['paper_id'])} 
                 for node in nodes]
        edges = [{'source': paper_id_mapping.get(edge['source'], edge['source']),
                  'target': paper_id_mapping.get(edge['target'], edge['target'])} 
                 for edge in edges]
        self.graph_storage.store_graph(nodes, edges)
        pagerank = self.citation_graph.compute_metrics(nodes, edges)
        
        # Chunk sections and store embeddings
        chunks, section_records = self.content_chunker.chunk_content(self.input_path, paper_id_mapping)
        pk = self.chunk_storage.store_chunks(chunks)
        self.chunk_storage.store_section_embedding_ids(section_records, pk)
        results = {
            'pagerank': pagerank,
            'status': 'Transformations and storage completed in Supabase, Milvus, and Dgraph'
        }
        logger.info("Completed pipeline")
        return results
