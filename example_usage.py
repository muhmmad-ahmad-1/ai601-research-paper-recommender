import json
from typing import Dict
import logging
import os
from dotenv import load_dotenv

from src.recommendation.rag_recommender import RAGRecommender

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if required environment variables are set."""
    required_vars = [
        "GOOGLE_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "MILVUS_URI",
        "MILVUS_TOKEN"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            "Please set these in your .env file or environment."
        )

def format_recommendation(rec: Dict) -> str:
    """Format a single recommendation for display."""
    # Basic paper information
    output = [
        f"Title: {rec['title']}",
        f"URL: {rec['url']}",
        f"Similarity Score: {rec['similarity_score']:.3f}",
        f"Zilliz ID: {rec['zilliz_id']}",
        f"Paper ID: {rec['paper_id']}",
        "",
        "Paper Summary (from database):",
        f"{rec['summary'] or 'No summary available'}",
        "",
        "Generated Summary (Gemini):",
        f"{rec['generated_summary']}",
        ""
    ]
    
    # Add section information if this is a section chunk
    if rec['section_id'] != 'full_paper':
        output.extend([
            f"Section ID: {rec['section_id']}",
            f"Chunk ID: {rec['chunk_id']}",
            "",
            "Relevant Section Content:",
            f"{rec['section_content'][:500]}..." if rec['section_content'] else "No section content available",
            ""
        ])
    else:
        output.extend([
            "Full Paper Embedding",
            f"Abstract: {rec['abstract'][:500]}..." if rec['abstract'] else "No abstract available",
            ""
        ])
    
    output.append("---")
    return "\n".join(output)

def save_recommendations(recommendations: list, filename: str = 'recommendations.json'):
    """Save recommendations to a JSON file with proper formatting."""
    # Create a more readable format for JSON storage
    formatted_recs = []
    for rec in recommendations:
        formatted_rec = {
            'metadata': {
                'zilliz_id': rec['zilliz_id'],
                'paper_id': rec['paper_id'],
                'section_id': rec['section_id'],
                'chunk_id': rec['chunk_id'],
                'similarity_score': rec['similarity_score']
            },
            'paper_info': {
                'title': rec['title'],
                'url': rec['url'],
                'stored_summary': rec['summary'],
                'abstract': rec['abstract']
            },
            'content': {
                'section_content': rec['section_content'] if rec['section_id'] != 'full_paper' else None,
                'generated_summary': rec['generated_summary']
            }
        }
        formatted_recs.append(formatted_rec)
    
    with open(filename, 'w') as f:
        json.dump(formatted_recs, f, indent=2)
        logger.info(f"Saved recommendations to {filename}")

def main():
    # Load environment variables and check required ones
    load_dotenv()
    check_environment()
    
    # Initialize the recommender
    recommender = RAGRecommender()
    
    # Example queries to demonstrate both full paper and section chunk retrieval
    queries = [
        "What is YOLO and how does it work?",
        "What are the recent advances in tiny object detection?",
        "What are the recent advances on vehicle speed estimation?"
    ]
    
    for query in queries:
        try:
            print(f"\nRecommendations for query: '{query}'\n")
            print("=" * 80)
            
            # Get recommendations
            recommendations = recommender.get_recommendations(query, top_k=1)
            
            # Print results
            for i, rec in enumerate(recommendations, 1):
                print(f"Recommendation {i}:")
                print(format_recommendation(rec))
            
            # Save results to a file
            save_recommendations(recommendations, f'recommendations_{query[:30].replace(" ", "_")}.json')
            
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            continue

if __name__ == "__main__":
    main() 
