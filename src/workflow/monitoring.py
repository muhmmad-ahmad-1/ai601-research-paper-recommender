from typing import Dict, List, Optional
import logging
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class WorkflowMonitor:
    """Monitors and logs workflow execution."""
    
    def __init__(self, log_dir: str = "logs/workflows"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    def log_workflow_start(self, workflow_id: str, query: str, max_results: int):
        """Log the start of a workflow execution."""
        log_entry = {
            "workflow_id": workflow_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event": "workflow_start",
            "query": query,
            "max_results": max_results
        }
        self._write_log(workflow_id, log_entry)
        
    def log_agent_start(self, workflow_id: str, agent_name: str, input_data: Dict):
        """Log the start of an agent execution."""
        log_entry = {
            "workflow_id": workflow_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event": "agent_start",
            "agent": agent_name,
            "input": input_data
        }
        self._write_log(workflow_id, log_entry)
        
    def log_agent_end(self, workflow_id: str, agent_name: str, output_data: Dict):
        """Log the end of an agent execution."""
        log_entry = {
            "workflow_id": workflow_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event": "agent_end",
            "agent": agent_name,
            "output": output_data
        }
        self._write_log(workflow_id, log_entry)
        
    def log_workflow_end(self, workflow_id: str, result: Dict):
        """Log the end of a workflow execution."""
        log_entry = {
            "workflow_id": workflow_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event": "workflow_end",
            "result": result
        }
        self._write_log(workflow_id, log_entry)
        
    def log_error(self, workflow_id: str, error: Exception):
        """Log an error during workflow execution."""
        log_entry = {
            "workflow_id": workflow_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event": "error",
            "error_type": type(error).__name__,
            "error_message": str(error)
        }
        self._write_log(workflow_id, log_entry)
        
    def _write_log(self, workflow_id: str, log_entry: Dict):
        """Write a log entry to the workflow log file."""
        log_file = self.log_dir / f"{workflow_id}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
    def get_workflow_logs(self, workflow_id: str) -> List[Dict]:
        """Retrieve all logs for a specific workflow."""
        log_file = self.log_dir / f"{workflow_id}.jsonl"
        if not log_file.exists():
            return []
            
        logs = []
        with open(log_file, "r") as f:
            for line in f:
                logs.append(json.loads(line))
        return logs
        
    def get_workflow_metrics(self, workflow_id: str) -> Dict:
        """Calculate metrics for a workflow execution."""
        logs = self.get_workflow_logs(workflow_id)
        if not logs:
            return {}
            
        start_time = None
        end_time = None
        agent_times = {}
        
        for log in logs:
            timestamp = datetime.fromisoformat(log["timestamp"])
            
            if log["event"] == "workflow_start":
                start_time = timestamp
            elif log["event"] == "workflow_end":
                end_time = timestamp
            elif log["event"] == "agent_start":
                agent = log["agent"]
                if agent not in agent_times:
                    agent_times[agent] = {"start": timestamp}
            elif log["event"] == "agent_end":
                agent = log["agent"]
                if agent in agent_times:
                    agent_times[agent]["end"] = timestamp
                    
        metrics = {
            "total_duration": (end_time - start_time).total_seconds() if start_time and end_time else None,
            "agent_durations": {}
        }
        
        for agent, times in agent_times.items():
            if "start" in times and "end" in times:
                metrics["agent_durations"][agent] = (times["end"] - times["start"]).total_seconds()
                
        return metrics 