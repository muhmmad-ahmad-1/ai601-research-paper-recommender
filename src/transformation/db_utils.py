import os
import logging
import requests
import uuid
from supabase import create_client
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import pydgraph
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DBUtils:
    """Handles connections to Supabase, Milvus, and Dgraph."""
    
    def __init__(self):
        # Supabase (PostgreSQL via REST client)
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase_client = create_client(self.supabase_url, self.supabase_key)

        # Removed raw PostgreSQL connection using SQLAlchemy
        # self.pg_engine = create_engine(...)

        # Milvus (Zilliz Cloud)
        self.milvus_uri = os.getenv("MILVUS_URI")
        self.milvus_token = os.getenv("MILVUS_TOKEN")
        try:
            connections.connect(alias="default", uri=self.milvus_uri, token=self.milvus_token)
            logger.info("Connected to Zilliz Cloud")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise

        # Dgraph Cloud (DQL via gRPC)
        self.dgraph_endpoint = os.getenv("DGRAPH_ENDPOINT")
        self.dgraph_api_key = os.getenv("DGRAPH_API_KEY")

        if not self.dgraph_endpoint or not self.dgraph_api_key:
            raise ValueError("Missing DGRAPH_ENDPOINT or DGRAPH_API_KEY in environment.")

        try:
            stub = pydgraph.DgraphClientStub.from_cloud(
                self.dgraph_endpoint,
                self.dgraph_api_key
            )
            self.dgraph_client = pydgraph.DgraphClient(stub)
            logger.info("Connected to Dgraph Cloud via gRPC.")
        except Exception as e:
            logger.error(f"Failed to connect to Dgraph Cloud: {e}")
            raise
    def create_milvus_collection(self, collection_name: str, dimension: int = 1024) -> Collection:
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

    def insert_postgres(self, table_name, data, returning=None):
        try:
            response = self.supabase_client.table(table_name).insert(data).execute()
            print(response)

            # If using httpx.Client under the hood (which supabase-py does), you can check status
            if not response.data:
                raise Exception(f"Insert failed: {response}")  # or log the full response

            if returning:
                return [row[returning] for row in response.data if returning in row]
            return []
        except Exception as e:
            logger.error(f"Failed to insert into {table_name}: {e}")
            raise


    def execute_dql_query(self, query: str, variables: Dict[str, Any] = None) -> Dict:
        txn = self.dgraph_client.txn(read_only=True)
        try:
            res = txn.query(query, variables=variables) if variables else txn.query(query)
            return res.json
        finally:
            txn.discard()

    def execute_dql_mutation(self, set_obj: Dict = None, del_obj: Dict = None) -> Dict:
        txn = self.dgraph_client.txn()
        try:
            if set_obj:
                res = txn.mutate(set_obj=set_obj)
            elif del_obj:
                res = txn.mutate(del_obj=del_obj)
            else:
                raise ValueError("Must provide either set_obj or del_obj")
            txn.commit()
            return res.uids
        finally:
            txn.discard()

    def set_schema(self, schema: str):
        try:
            self.dgraph_client.alter(pydgraph.Operation(schema=schema))
            logger.info("Schema set successfully.")
        except Exception as e:
            logger.error(f"Failed to set schema: {e}")
            raise

    def drop_all(self):
        try:
            self.dgraph_client.alter(pydgraph.Operation(drop_all=True))
            logger.info("Dropped all data in Dgraph.")
        except Exception as e:
            logger.error(f"Failed to drop all: {e}")
            raise
    
    def set_schema(self):
        schema = """
        paper_id: string @index(exact) .
        title: string .
        year: int .
        authors: [string] .
        cites: [uid] @reverse .

        type Paper {
            paper_id
            title
            year
            authors
            cites
        }
        """
        op = pydgraph.Operation(schema=schema)
        self.dgraph_client.alter(op)
    
    def ensure_schema(self):
        """Check if required schema is set. If not, apply schema."""
        try:
            query = """schema {}"""
            txn = self.dgraph_client.txn(read_only=True)
            res = txn.query(query)
            txn.discard()

            # Extract existing predicate names
            existing_preds = {entry['predicate'] for entry in res.json.get('schema', [])}
            required_preds = {"paper_id", "title", "year", "authors", "cites"}

            if not required_preds.issubset(existing_preds):
                logger.warning("Missing predicates in schema. Applying default schema...")
                self.set_schema()
            else:
                logger.info("Schema already contains required predicates.")
        except Exception as e:
            logger.error(f"Schema check failed: {e}. Applying schema as fallback.")
            self.set_schema()



