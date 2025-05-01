from b2sdk.v2 import InMemoryAccountInfo, B2Api
from typing import BinaryIO, Optional
import logging
import os

logger = logging.getLogger(__name__)

class B2Storage:
    """Manages file storage using Backblaze B2 Cloud Storage."""
    
    def __init__(self, 
                 application_key_id: str,
                 application_key: str,
                 bucket_name: str):
        """
        Initialize B2 storage client.
        
        Args:
            application_key_id: B2 application key ID
            application_key: B2 application key
            bucket_name: Name of the B2 bucket to use
        """
        self.info = InMemoryAccountInfo()
        self.api = B2Api(self.info)
        self.api.authorize_account("production", application_key_id, application_key)
        self.bucket = self.api.get_bucket_by_name(bucket_name)
        
    def upload_file(self, 
                   file_path: str,
                   file_name: Optional[str] = None,
                   content_type: str = "application/pdf") -> str:
        """
        Upload a file to B2 storage.
        
        Args:
            file_path: Path to the local file
            file_name: Optional custom file name in B2
            content_type: MIME type of the file
            
        Returns:
            B2 file ID
        """
        if not file_name:
            file_name = os.path.basename(file_path)
            
        try:
            with open(file_path, 'rb') as file:
                file_info = self.bucket.upload_bytes(
                    file.read(),
                    file_name,
                    content_type=content_type
                )
            return file_info.id_
        except Exception as e:
            logger.error(f"Error uploading file to B2: {str(e)}")
            raise
            
    def download_file(self, file_id: str, destination_path: str) -> None:
        """
        Download a file from B2 storage.
        
        Args:
            file_id: B2 file ID
            destination_path: Local path to save the file
        """
        try:
            file_info = self.api.get_file_info_by_id(file_id)
            self.bucket.download_file_by_id(
                file_id,
                destination_path
            )
        except Exception as e:
            logger.error(f"Error downloading file from B2: {str(e)}")
            raise
            
    def get_file_url(self, file_id: str) -> str:
        """
        Get the download URL for a file.
        
        Args:
            file_id: B2 file ID
            
        Returns:
            Download URL for the file
        """
        try:
            file_info = self.api.get_file_info_by_id(file_id)
            return self.api.get_download_url_for_fileid(file_id)
        except Exception as e:
            logger.error(f"Error getting file URL: {str(e)}")
            raise
            
    def delete_file(self, file_id: str) -> None:
        """
        Delete a file from B2 storage.
        
        Args:
            file_id: B2 file ID
        """
        try:
            self.bucket.delete_file_version(file_id)
        except Exception as e:
            logger.error(f"Error deleting file from B2: {str(e)}")
            raise 