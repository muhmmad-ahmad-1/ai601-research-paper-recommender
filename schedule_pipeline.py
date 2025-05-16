from prefect import flow
from src.workflow import processing_workflow_with_logging

processing_workflow_with_logging.serve(name="flowing", cron="0 */4 * * *")

# prefect server start (In one terminal)
# run : python schedule_pipeline.py in another terminal
# now you have it scheduled
# doing prefect agent start -p default in yet another terminal will make the agent listen for scheduled flows and run them on their time 
#(in this case every 4 hours)