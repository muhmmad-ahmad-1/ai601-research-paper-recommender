from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from .ingest_and_store import ProcessingWorkflow  # Adjust path if needed

# Define the callable for Airflow to execute
def run_workflow():
    workflow = ProcessingWorkflow(
        output_file="parsed_papers.jsonl",  # You can customize this
        criterion="relevance"
    )
    try:
        workflow.run_single(  # You can use run_multiple here if needed
            query="cs.AI",     # Customize your topic
            num_papers=5,
            max_extensions=1
        )
    except Exception as e:
        print("PIPELINE BROKE -------- ",e)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'start_date': datetime(2025, 5, 14),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='processing_workflow_every_4_hours',
    default_args=default_args,
    schedule_interval='0 */4 * * *',  # Every 4 hours
    catchup=False,
    tags=['arxiv', 'pipeline', 'workflow'],
) as dag:

    run_processing_task = PythonOperator(
        task_id='run_processing_workflow',
        python_callable=run_workflow,
    )
