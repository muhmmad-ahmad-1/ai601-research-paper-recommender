from typing import Dict, List, TypedDict, Annotated, Sequence
from langgraph.graph import Graph, StateGraph
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
import logging
from src.workflow.agents import PaperIngestionAgent, PaperProcessingAgent, RecommendationAgent
from src.workflow.tools import ArxivSearchTool, PaperStorageTool, PaperRetrievalTool

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    next: Annotated[str, "The next agent to call"]
    current_agent: Annotated[str, "The current agent being used"]

def create_workflow_graph(
    arxiv_api,
    db_manager,
    b2_storage,
    openai_api_key: str
) -> Graph:
    """Create the workflow graph for paper processing."""
    
    # Initialize tools
    tools = [
        ArxivSearchTool(arxiv_api),
        PaperStorageTool(db_manager, b2_storage),
        PaperRetrievalTool(db_manager, b2_storage)
    ]
    tool_executor = ToolExecutor(tools)
    
    # Initialize agents
    ingestion_agent = PaperIngestionAgent(tools)
    processing_agent = PaperProcessingAgent(tools)
    recommendation_agent = RecommendationAgent(tools)
    
    # Define workflow states
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("ingestion", ingestion_agent.ingest_papers)
    workflow.add_node("processing", processing_agent.process_paper)
    workflow.add_node("recommendation", recommendation_agent.recommend_papers)
    
    # Define edges
    workflow.add_edge("ingestion", "processing")
    workflow.add_edge("processing", "recommendation")
    
    # Set entry point
    workflow.set_entry_point("ingestion")
    
    # Compile the graph
    return workflow.compile()

class WorkflowManager:
    """Manages the execution of agent workflows."""
    
    def __init__(
        self,
        arxiv_api,
        db_manager,
        b2_storage,
        openai_api_key: str
    ):
        self.graph = create_workflow_graph(
            arxiv_api,
            db_manager,
            b2_storage,
            openai_api_key
        )
        
    async def run_workflow(
        self,
        query: str,
        max_results: int = 10
    ) -> Dict:
        """
        Run the complete workflow for paper processing.
        
        Args:
            query: Search query for papers
            max_results: Maximum number of results to process
            
        Returns:
            Dictionary containing workflow results
        """
        try:
            # Initialize state
            initial_state = {
                "messages": [HumanMessage(content=f"Find and process {max_results} papers about {query}")],
                "next": "ingestion",
                "current_agent": "ingestion"
            }
            
            # Run workflow
            result = await self.graph.ainvoke(initial_state)
            return result
        except Exception as e:
            logger.error(f"Error in workflow execution: {str(e)}")
            raise
