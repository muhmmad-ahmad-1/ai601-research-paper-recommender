from src.storage.datalake import DataLake
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize DataLake
    datalake = DataLake()
    
    try:
        # Process the JSONL file
        datalake.process_jsonl_file('parsed_269paper.jsonl')
        print("Successfully processed all papers!")
    except Exception as e:
        print(f"Error processing papers: {str(e)}")
    finally:
        # Close connections
        datalake.close()

if __name__ == "__main__":
    main() 