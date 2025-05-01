from typing import Dict, List, Optional
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import BaseTool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chat_models import ChatOpenAI
import logging

logger = logging.getLogger(__name__)

class PaperIngestionAgent:
    """Agent responsible for paper ingestion and initial processing."""
    
    def __init__(self, tools: List[BaseTool]):
        self.tools = tools
        self.llm = ChatOpenAI(temperature=0)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI research paper ingestion agent. Your task is to collect and process papers from arXiv."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        self.agent = create_openai_functions_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)
        
    async def ingest_papers(self, query: str, max_results: int = 10) -> Dict:
        """Ingest papers based on a query."""
        try:
            result = await self.agent_executor.ainvoke({
                "input": f"Find and process {max_results} papers about {query}",
                "chat_history": []
            })
            return result
        except Exception as e:
            logger.error(f"Error in paper ingestion: {str(e)}")
            raise

class PaperProcessingAgent:
    """Agent responsible for processing and analyzing papers."""
    
    def __init__(self, tools: List[BaseTool]):
        self.tools = tools
        self.llm = ChatOpenAI(temperature=0)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI research paper processing agent. Your task is to analyze and extract insights from papers."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        self.agent = create_openai_functions_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)
        
    async def process_paper(self, paper_id: str) -> Dict:
        """Process a single paper."""
        try:
            result = await self.agent_executor.ainvoke({
                "input": f"Analyze paper with ID {paper_id}",
                "chat_history": []
            })
            return result
        except Exception as e:
            logger.error(f"Error in paper processing: {str(e)}")
            raise

class RecommendationAgent:
    """Agent responsible for generating paper recommendations."""
    
    def __init__(self, tools: List[BaseTool]):
        self.tools = tools
        self.llm = ChatOpenAI(temperature=0)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI research paper recommendation agent. Your task is to find relevant papers based on user interests."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        self.agent = create_openai_functions_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)
        
    async def recommend_papers(self, query: str, max_results: int = 10) -> Dict:
        """Generate paper recommendations."""
        try:
            result = await self.agent_executor.ainvoke({
                "input": f"Find {max_results} relevant papers about {query}",
                "chat_history": []
            })
            return result
        except Exception as e:
            logger.error(f"Error in paper recommendation: {str(e)}")
            raise 