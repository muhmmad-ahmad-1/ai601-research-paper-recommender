import streamlit as st
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
src_path = str(Path(__file__).parent.parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from recommendation.rag_recommender import RAGRecommender
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize RAG recommender
@st.cache_resource
def get_recommender():
    """Initialize and cache the RAG recommender."""
    try:
        return RAGRecommender()
    except Exception as e:
        st.error(f"Failed to initialize recommender: {e}")
        return None

def format_paper_recommendation(rec: dict) -> str:
    """Format a paper recommendation for display in chat."""
    output = [
        f"📄 **{rec['title']}**",
        f"🔗 [Read Paper]({rec['url']})",
        "",
        "**Why this paper is relevant:**",
        rec['generated_summary'],
        ""
    ]
    
    # Add section content if available
    if rec.get('section_content'):
        output.extend([
            "**Relevant Section:**",
            f"{rec['section_content'][:300]}...",
            ""
        ])
    
    return "\n".join(output)

def get_chatbot_response(user_query: str, recommender: RAGRecommender) -> str:
    """
    Get response from RAG recommender and format it for chat.
    Returns a markdown-formatted string.
    """
    try:
        # Get recommendations
        recommendations = recommender.get_recommendations(user_query, top_k=2)
        
        if not recommendations:
            return """
            I couldn't find any papers directly relevant to your query. 
            Try rephrasing your question or being more specific about the research area you're interested in.
            """
        
        # Format the response
        response_parts = [
            "Here are some relevant papers I found:",
            ""
        ]
        
        for i, rec in enumerate(recommendations, 1):
            response_parts.extend([
                f"**{i}. {rec['title']}**",
                f"🔗 [Read Paper]({rec['url']})",
                "",
                "**Why this paper is relevant:**",
                rec['generated_summary'],
                ""
            ])
            
            # Add section content if available
            # if rec.get('section_content'):
            #     response_parts.extend([
            #         "**Relevant Section:**",
            #         f"{rec['section_content'][:300]}...",
            #         ""
            #     ])
            
            response_parts.append("---")
        
        return "\n".join(response_parts)
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return f"""
        I encountered an error while searching for papers. Please try again.
        If the problem persists, contact the system administrator.
        Error details: {str(e)}
        """

# --- Chatbot Page UI ---
st.title("🤖 AI Research Paper Assistant")
st.markdown("""
Ask me about AI research papers! I'll help you find relevant papers and explain why they might be useful for your research.

For example, you can ask:
- What are the latest advances in transformer architecture?
- Show me papers about attention mechanisms in large language models
- What are recent developments in prompt engineering?
""")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get recommender instance
recommender = get_recommender()
if recommender is None:
    st.error("Failed to initialize the paper recommender. Please check your environment variables and try again.")
    st.stop()

# Chat input
if prompt := st.chat_input("What would you like to know about AI research?"):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Get and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Searching for relevant papers..."):
            response = get_chatbot_response(prompt, recommender)
            st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
