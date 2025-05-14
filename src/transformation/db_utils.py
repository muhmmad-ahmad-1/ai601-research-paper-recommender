import os
import logging
import requests
import uuid
from supabase import create_client
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import pydgraph
from typing import Any, Dict, List
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DBUtils:
    """Handles connections to Supabase, Milvus, and Dgraph."""
    
    def __init__(self):
        # Supabase (PostgreSQL)
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase_client = create_client(self.supabase_url, self.supabase_key)
        self.pg_engine = create_engine(f"postgresql+psycopg2://{os.getenv('SUPABASE_USER')}:{os.getenv('SUPABASE_PASSWORD')}@{os.getenv('SUPABASE_HOST')}/postgres")
        
        # Milvus (Zilliz Cloud)
        self.milvus_host = os.getenv("MILVUS_HOST")
        self.milvus_token = os.getenv("MILVUS_TOKEN")
        connections.connect(host=self.milvus_host, token=self.milvus_token)
        
        # Dgraph
        self.dgraph_endpoint = os.getenv("DGRAPH_ENDPOINT")
        self.dgraph_api_key = os.getenv("DGRAPH_API_KEY")
        self.dgraph_headers = {"X-Auth-Token": self.dgraph_api_key, "Content-Type": "application/json"}
        self.dgraph_client = pydgraph.DgraphClient(pydgraph.DgraphClientStub(self.dgraph_endpoint.replace("/graphql", "")))
    
    def create_milvus_collection(self, collection_name: str, dimension: int = 1024) -> Collection:
        """Create or get a Milvus collection."""
        if utility.has_collection(collection_name):
            return Collection(collection_name)
        
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="section_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension),
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=50),
        ]
        schema = CollectionSchema(fields, description=f"Embeddings for {collection_name}")
        collection = Collection(collection_name, schema)
        collection.create_index(
            field_name="embedding",
            index_params={"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}}
        )
        collection.load()
        logger.info(f"Created Milvus collection: {collection_name}")
        return collection
    
    def insert_postgres(self, table_name: str, data: List[Dict], returning: str = None) -> List[str]:
        """Insert data into Supabase table and return specified column if requested.
        
        Args:
            table_name: Table to insert into
            data: List of dictionaries containing data
            returning: Column name to return (e.g., 'paper_id')
        
        Returns:
            List of values from the 'returning' column, or empty list if not specified
        """
        if not data:
            return []
        
        columns = data[0].keys()
        values = [tuple(item[col] for col in columns) for item in data]
        columns_str = ','.join(columns)
        placeholders = ','.join(['%s'] * len(columns))
        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        
        if returning:
            query += f" RETURNING {returning}"
        
        try:
            with self.pg_engine.connect() as conn:
                result = conn.execute(text(query), values)
                conn.commit()
                if returning:
                    return [row[0] for row in result.fetchall()]
                return []
        except Exception as e:
            logger.error(f"Failed to insert into {table_name}: {e}")
            raise
    
    def execute_graphql(self, query: str, variables: Dict = None) -> Dict:
        """Execute a GraphQL query or mutation."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        try:
            response = requests.post(self.dgraph_endpoint, json=payload, headers=self.dgraph_headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"GraphQL request failed: {e}")
            raise