from supabase import create_client
import os
from typing import Set, List

class SupabaseClient:
    """Handles interactions with Supabase."""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.client = create_client(self.supabase_url, self.supabase_key)
    
    def get_existing_keywords(self) -> Set[str]:
        """Fetch existing keywords from Supabase.
        
        Returns:
            Set[str]: Set of keyword names
        """
        response = self.client.table("keywords").select("name").execute()
        if response.data:
            return {row["name"].lower() for row in response.data}
        return set()
    
    def get_existing_domains(self) -> List[str]:
        """Fetch unique domains from Supabase.
        
        Returns:
            List[str]: List of domain names
        """
        response = self.client.table("papers").select("domain").execute()
        if response.data:
            return sorted({row["domain"].strip().lower() for row in response.data if row.get("domain")})
        return []
    
    def get_existing_arxiv_ids(self) -> Set[str]:
        """Fetch all base arXiv IDs already stored in Supabase."""
        response = self.client.table("papers").select("paper_id").execute()
        if response.data:
            return {row["paper_id"].split("v")[0] for row in response.data}
        return set()
