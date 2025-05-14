
class TransformationPipeline:
    """
    Takes in jsonl files and applies transformations to the raw paper data in a format suitable for storage.
    """
    def __init__(self, supabase_client, milvus_client):
        self.supabase_client = supabase_client
        self.milvus_client = milvus_client
        