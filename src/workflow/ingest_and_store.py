from src.transformation import TransformationPipeline
from src.ingestion import IngestionPipeline
from typing import List, Optional

# import logging
# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)

class ProcessingWorkflow:
    """
    Runs a job to ingest and store latest papers or those based on a query.
    Handles errors gracefully and allows sequential processing of multiple queries.
    """

    def __init__(self, output_file: str = "parsed_papers.jsonl",criterion:str = 'relevance', logger = None):
        self.output_file = output_file
        self.criterion = criterion
        self.logger = logger
        self.ingestor = IngestionPipeline(criterion=criterion, logger=logger)
        self.transformer = TransformationPipeline(self.output_file, logger)

    def run_single(self, query: Optional[str] = None, num_papers: int = 5, max_extensions: int = 1):
        """
        Runs ingestion and transformation for a single query or recent papers.

        Args:
            query (str): Search query (e.g., "graph neural networks").
            num_papers (int): Number of papers to retrieve.
            max_extensions (int): Max retries/extensions during ingestion.
        """
        try:
            self.logger.info(f"Running ingestion {'for query: ' + query + 'based on' + self.criterion if query else 'for latest papers'}")
            if query:
                self.ingestor.run_pipeline(query=query, num_papers=num_papers, max_extentions=max_extensions)
            else:
                self.ingestor.run_pipeline(num_papers=num_papers)

            self.logger.info("Starting transformation pipeline...")
            self.transformer.run_pipeline()

        except Exception as e:
            self.logger.error(f"Processing failed: {e}", exc_info=True)
            return

    def run_multiple(self, queries: List[str], num_papers: int = 3, max_extensions: int = 1):
        """
        Runs sequential ingestion and transformation for multiple queries.

        Args:
            queries (List[str]): List of search queries.
            num_papers (int): Papers per query.
            max_extensions (int): Max retries/extensions per query.
        """
        for query in queries:
            self.logger.info(f"\n==== Processing query: '{query}' ====")
            self.run_single(query=query, num_papers=num_papers, max_extensions=max_extensions)
