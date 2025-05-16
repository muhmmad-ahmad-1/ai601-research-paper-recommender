from prefect import flow, task, get_run_logger
from .ingest_and_store import ProcessingWorkflow

@task
def run_processing_task(query: str = "cs.AI", num_papers: int = 5, max_extensions: int = 1):
    logger = get_run_logger()
    logger.info("Starting ProcessingWorkflow through Prefect...")

    # Initialize with logger
    if query == 'cs.AI':
        workflow = ProcessingWorkflow(output_file="parsed_papers.jsonl", criterion="latest", logger=logger)
    else:
        workflow = ProcessingWorkflow(output_file="parsed_papers.jsonl", criterion="relevance", logger=logger)

    workflow.run_single(query=query, num_papers=num_papers, max_extensions=max_extensions)

    logger.info("ProcessingWorkflow completed with Prefect...")

@flow(name="Preprocessing: Storing Workflow with Prefect Logging")
def processing_workflow_with_logging():
    run_processing_task()       #pass arguments here

if __name__ == "__main__":
    processing_workflow_with_logging()
