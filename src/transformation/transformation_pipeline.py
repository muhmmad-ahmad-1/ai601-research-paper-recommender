from typing import Dict
from .paper_transformer import PaperTransformer
from .embedding_generation import EmbeddingGenerator
from .content_chunker import ContentChunker
from .citation_graph import CitationGraph
from storage import (
    PaperStorage,
    EmbeddingStorage,
    GraphStorage,
    ChunkStorage
)

# import logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

class TransformationPipeline:
    """Orchestrates transformations and storage for RAG and analytics."""
    
    def __init__(self, input_path: str = "parsed_papers.jsonl", logger=None):
        self.input_path = input_path
        self.paper_transformer = PaperTransformer(logger)
        self.embedding_generator = EmbeddingGenerator("thenlper/gte-large", logger)
        self.citation_graph = CitationGraph(logger)
        self.content_chunker = ContentChunker("thenlper/gte-large", 10000, 200, logger)
        self.paper_storage = PaperStorage(logger)
        self.embedding_storage = EmbeddingStorage("paper_embeddings", logger)
        self.graph_storage = GraphStorage(logger)
        self.chunk_storage = ChunkStorage("paper_embeddings", logger)
        self.logger = logger
    def run_pipeline(self) -> Dict:
        """Run transformations and store results in databases.
        
        Returns:
            Dict: Pipeline results
        """
        # Transform paper metadata
        data_json, papers, authors, paper_authors, keywords, paper_keywords, sections, citations, paper_id_mapping = \
            self.paper_transformer.transform_papers(self.input_path)
        
        if not papers:
            self.logger.info('No new papers to store. All up to date')
            return
        # Store in Supabase and update paper_id_mapping
        paper_id_mapping = self.paper_storage.store_papers(
            papers, authors, paper_authors, keywords, paper_keywords, sections, citations, paper_id_mapping
        )
        
        # Generate and store paper embeddings
        embeddings, paper_ids = self.embedding_generator.generate_embeddings(self.input_path, paper_id_mapping)
        pk = self.embedding_storage.store_embeddings(embeddings)
        self.embedding_storage.store_embedding_id(paper_ids,pk)
        self.logger.info(len(data_json), len(paper_ids))
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
        chunk_ids = [chunk['chunk_id'] for chunk in chunks]
        pk = self.chunk_storage.store_chunks(chunks)
        self.chunk_storage.store_section_embedding_ids(section_records, pk,chunk_ids)
        results = {
            'pagerank': pagerank,
            'status': 'Transformations and storage completed in Supabase, Milvus, and Dgraph'
        }
        self.logger.info("Completed transformation pipeline")
        return results
