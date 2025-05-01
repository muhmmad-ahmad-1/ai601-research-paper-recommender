import streamlit as st
import requests
from typing import List, Dict
import json

# Configure the page
st.set_page_config(
    page_title="AI Research Paper Recommender",
    page_icon="📚",
    layout="wide"
)

# Constants
API_URL = "http://localhost:8000"

def main():
    st.title("AI Research Paper Recommender")
    st.markdown("Discover relevant AI research papers using advanced NLP techniques")
    
    # Search interface
    with st.form("search_form"):
        query = st.text_input("Enter your research interest or topic")
        max_results = st.slider("Number of results", 5, 50, 10)
        submitted = st.form_submit_button("Search")
    
    if submitted and query:
        try:
            # Call the API
            response = requests.post(
                f"{API_URL}/recommend",
                json={
                    "query": query,
                    "max_results": max_results
                }
            )
            response.raise_for_status()
            results = response.json()
            
            # Display results
            st.subheader("Recommended Papers")
            for paper in results["papers"]:
                with st.expander(paper.get("title", "Untitled")):
                    st.write(f"**Authors:** {', '.join(paper.get('authors', []))}")
                    st.write(f"**Abstract:** {paper.get('abstract', 'No abstract available')}")
                    st.write(f"**Published:** {paper.get('published_date', 'Unknown')}")
                    st.write(f"**Categories:** {', '.join(paper.get('categories', []))}")
                    if paper.get("pdf_url"):
                        st.markdown(f"[Download PDF]({paper['pdf_url']})")
            
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching recommendations: {str(e)}")
    
    # Add footer
    st.markdown("---")
    st.markdown("Built with ❤️ using Streamlit and FastAPI")

if __name__ == "__main__":
    main() 